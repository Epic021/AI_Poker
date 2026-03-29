from player import Player, PlayerAction
import random
from collections import defaultdict
from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate

class MCCFRPokerBot(Player):
    def __init__(self, name, stack, num_simulations=1000, exploration=0.1):
        super().__init__(name, stack)
        self.num_simulations = num_simulations
        self.regrets = defaultdict(lambda: [0, 0, 0])  # Regret storage (Fold, Call, Raise)
        self.strategy = defaultdict(lambda: [1/3, 1/3, 1/3])  # Strategy initialization
        self.exploration = exploration  # Exploration factor for randomness

    def action(self, game_state, action_history):
        hole_cards = game_state[:2]
        community_cards = game_state[2:7]
        pot = game_state[7]
        current_raise = game_state[8]
        num_players = game_state[11]

        hand_strength = self.evaluate_hand_strength(hole_cards, community_cards, num_players)
        return self.mccfr_decision(hand_strength, current_raise, pot)

    def evaluate_hand_strength(self, hole_cards, community_cards, num_players):
        hole_cards_str = [self.card_index_to_str(card) for card in hole_cards]
        community_cards_str = [self.card_index_to_str(card) for card in community_cards if card != 0]  # Ignore undealt cards
        return estimate_hole_card_win_rate(
            self.num_simulations, num_players, gen_cards(hole_cards_str), gen_cards(community_cards_str)
        )

    def card_index_to_str(self, index):
        suits = ['S', 'H', 'D', 'C']  # Spades, Hearts, Diamonds, Clubs
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        if not (0 <= index <= 52):  # Validate index range (0-51)
            raise ValueError(f"Invalid card index: {index}. Expected 0-51.")
        rank = ranks[index % 13]  # Extract rank (0-12)
        suit = suits[index // 13]  # Extract suit (0-3)
        return f"{suit}{rank}"  # Correct format (e.g., "H2", "SK")


    def get_strategy(self, hand_strength):
        """ Compute the probability distribution for actions based on regrets. """
        key = round(hand_strength, 2)  # Discretize hand strength
        regrets = self.regrets[key]

        # Convert regrets to positive values for probability calculation
        positive_regrets = [max(r, 0) for r in regrets]
        total_positive_regret = sum(positive_regrets)

        if total_positive_regret > 0:
            strategy = [r / total_positive_regret for r in positive_regrets]
        else:
            strategy = [1/3, 1/3, 1/3]  # Default to uniform strategy

        return strategy

    def mccfr_decision(self, hand_strength, current_raise, pot):
        """ Choose an action based on regret-matching strategy. """
        strategy = self.get_strategy(hand_strength)

        # Exploration: Occasionally take a random action
        if random.random() < self.exploration:
            action = random.choices([PlayerAction.FOLD, PlayerAction.CALL, PlayerAction.RAISE], [1/3, 1/3, 1/3])[0]
        else:
            action = random.choices([PlayerAction.FOLD, PlayerAction.CALL, PlayerAction.RAISE], strategy)[0]

        # Determine bet amount for raise
        if action == PlayerAction.RAISE:
            raise_amount = min(self.stack, max(current_raise * 2, pot // 2))
            return action, raise_amount
        elif action == PlayerAction.CALL:
            return action, min(self.stack, current_raise) if current_raise > 0 else (PlayerAction.CHECK, 0)
        else:
            return PlayerAction.FOLD, 0

    def update_regrets(self, history, terminal_value):
        """ Update regrets based on the difference between expected and actual outcomes. """
        for hand_strength, chosen_action in history:
            key = round(hand_strength, 2)  # Discretize hand strength
            strategy = self.get_strategy(hand_strength)
            regrets = self.regrets[key]

            action_values = [0, 0, 0]  # Expected values for (Fold, Call, Raise)
            action_index = [PlayerAction.FOLD, PlayerAction.CALL, PlayerAction.RAISE].index(chosen_action)

            for i in range(3):
                action_values[i] = terminal_value if i == action_index else 0

            regret_deltas = [action_values[i] - sum(action_values[j] * strategy[j] for j in range(3)) for i in range(3)]
            self.regrets[key] = [regrets[i] + regret_deltas[i] for i in range(3)]
