import random
from collections import defaultdict
from player import Player, PlayerAction, PlayerStatus
from card import Card, Rank, Suit # Import necessary Card components
from game import GamePhase # Import GamePhase if needed for explicit phase checking

# Attempt to import the hand evaluation utility
try:
    from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate
    PYPOKERENGINE_AVAILABLE = True
except ImportError:
    print("Warning: pypokerengine not found. AggroBot will use simplified logic.")
    PYPOKERENGINE_AVAILABLE = False

class AggroBot(Player):
    """
    An aggressive poker bot that uses hand strength estimation,
    pot odds, and situational awareness to make decisions.
    """
    def __init__(self, name, stack, num_simulations=500, bluff_frequency=0.15):
        super().__init__(name, stack)
        self.num_simulations = num_simulations
        self.bluff_frequency = bluff_frequency # Chance to bluff in certain spots

    def card_index_to_str(self, index: int) -> str | None:
        """Converts a card index (0-51) to a string format (e.g., "H2", "SK")."""
        if index < 0 or index > 51:
             return None

        # Card.get_index = (self.suit.value * 13) + self.rank.value - 2 (Corrected interpretation)
        # Index 0-51 mapping:
        suit_val = index // 13 # 0=S, 1=H, 2=D, 3=C (Assuming standard enum order)
        rank_val = (index % 13) # 0='2', 1='3', ..., 11='K', 12='A'

        # Format for pypokerengine (SuitRank like "SK", "HA")
        pokerengine_suits = ['S', 'H', 'D', 'C']
        pokerengine_ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

        # Safety check if index somehow leads to out-of-bounds for lists
        if not (0 <= suit_val < len(pokerengine_suits) and 0 <= rank_val < len(pokerengine_ranks)):
            print(f"Warning: Calculated invalid suit/rank values ({suit_val}, {rank_val}) from index {index}")
            return None

        suit_str = pokerengine_suits[suit_val]
        rank_str = pokerengine_ranks[rank_val]

        return suit_str + rank_str # Like "SK", "HA"


    def _estimate_strength(self, hole_card_indices: list[int], community_card_indices: list[int], num_active_opponents: int) -> float:
        """
        Estimates the win rate of the current hand against a number of random opponents.
        Returns a float between 0.0 and 1.0. Returns 0.0 if estimation is unavailable.
        """
        if not PYPOKERENGINE_AVAILABLE:
             # Basic fallback remains crude
             valid_hole_indices = [i for i in hole_card_indices if i is not None and i >= 0]
             valid_community_indices = [i for i in community_card_indices if i is not None and i > 0] # Community uses 0 for empty

             if not valid_community_indices and len(valid_hole_indices) == 2: # Pre-flop only
                 rank1_val = (valid_hole_indices[0] % 13)
                 rank2_val = (valid_hole_indices[1] % 13)
                 score = 0
                 if rank1_val >= 8: score += rank1_val # T+
                 if rank2_val >= 8: score += rank2_val
                 if rank1_val == rank2_val: score += 15 # Pair bonus
                 return min(max(score / 40.0, 0.05), 0.95)
             else:
                 return 0.4 # Neutral guess post-flop

        # Filter out 0s or invalid indices before converting
        hole_cards_str = [s for s in map(self.card_index_to_str, filter(lambda x: x is not None and x >= 0, hole_card_indices)) if s is not None]
        community_cards_str = [s for s in map(self.card_index_to_str, filter(lambda x: x is not None and x > 0, community_card_indices)) if s is not None] # Community cards use 0 for empty

        if len(hole_cards_str) != 2:
             # print(f"Warning: Cannot estimate strength with invalid hole cards: {hole_cards_str} from indices {hole_card_indices}")
             return self._estimate_strength([], [], 0) # Use the basic fallback

        effective_num_players = max(2, num_active_opponents + 1)

        try:
            community_arg = gen_cards(community_cards_str) if community_cards_str else None
            win_rate = estimate_hole_card_win_rate(
                nb_simulation=self.num_simulations,
                nb_player=effective_num_players,
                hole_card=gen_cards(hole_cards_str),
                community_card=community_arg
            )
            return win_rate
        except Exception as e:
            print(f"Error during hand strength estimation: {e}")
            print(f" > hole_str: {hole_cards_str}, comm_str: {community_cards_str}")
            return self._estimate_strength([], [], 0) # Use basic fallback


    def _get_game_phase(self, community_card_indices: list[int]) -> GamePhase:
        """Determines the current game phase based on community cards."""
        num_community = sum(1 for idx in community_card_indices if idx is not None and idx > 0) # Count dealt (non-zero)
        if num_community == 0:
            return GamePhase.PRE_FLOP
        elif num_community == 3:
            return GamePhase.FLOP
        elif num_community == 4:
            return GamePhase.TURN
        elif num_community >= 5:
            return GamePhase.RIVER
        else:
            return GamePhase.SETUP


    def action(self, game_state: list[int], action_history: list) -> tuple[PlayerAction, int]:

        # --- 1. Parse Game State (CORRECTED INDICES) ---
        # Structure Refresher (len 17 for 4 players):
        # 0, 1: Hole cards
        # 2-6: Community cards
        # 7: Pot
        # 8: Current Bet
        # 9: Big Blind
        # 10: Active Player Index
        # 11: Num Players
        # 12, 13, 14, 15: Stacks (for 4 players)
        # 16: Game Number
        try:
            state_len = len(game_state)
            if state_len < 12: # Minimum length check (up to num_players index)
                 raise IndexError(f"Game state too short (len {state_len})")

            hole_card_indices = game_state[0:2]
            community_card_indices = game_state[2:7]
            pot = int(game_state[7])
            current_bet = int(game_state[8])
            big_blind = int(game_state[9])          # CORRECTED
            my_active_index = int(game_state[10])     # CORRECTED
            num_total_players = int(game_state[11])   # CORRECTED

            # Check if num_total_players is reasonable before slicing
            if not (1 <= num_total_players <= 10): # Max 10 players reasonable?
                raise ValueError(f"Unreasonable number of players: {num_total_players}")

            stacks_start_index = 12                # CORRECTED
            stacks_end_index = stacks_start_index + num_total_players
            game_num_index = stacks_end_index

            if state_len < game_num_index + 1:
                 raise IndexError(f"Game state length ({state_len}) insufficient for {num_total_players} players (expected at least {game_num_index+1})")

            player_stacks = [int(s) for s in game_state[stacks_start_index : stacks_end_index]] # CORRECTED
            game_number = int(game_state[game_num_index]) # CORRECTED

        except (IndexError, TypeError, ValueError) as e:
             print(f"!! Error parsing game_state: {e}")
             print(f"   Received game_state (len {len(game_state)}): {game_state}")
             return PlayerAction.FOLD, 0

        # --- Basic consistency checks after parsing ---
        if not (0 <= my_active_index < num_total_players):
            print(f"!! Invalid parsed player index {my_active_index} for {num_total_players} players.")
            return PlayerAction.FOLD, 0
        if len(player_stacks) != num_total_players:
             print(f"!! Parsed stacks length {len(player_stacks)} doesn't match num_players {num_total_players}.")
             return PlayerAction.FOLD, 0
        # --- End parsing ---

        my_stack = player_stacks[my_active_index]
        my_current_bet_this_round = self.bet_amount

        call_amount = max(0, current_bet - my_current_bet_this_round)

        # --- 2. Estimate Hand Strength & Phase ---
        phase = self._get_game_phase(community_card_indices)
        # Simplistic active opponent count
        num_active_opponents = num_total_players - 1
        strength = self._estimate_strength(hole_card_indices, community_card_indices, num_active_opponents)

        # --- 3. Decision Logic (No changes needed here from previous version) ---
        if not self.can_make_action():
             print(f"Warning: {self.name} asked for action but status is {self.status}. Folding.")
             return PlayerAction.FOLD, 0

        if my_stack <= 0 and self.status != PlayerStatus.ALL_IN:
             print(f"Warning: {self.name} has 0 stack but is not ALL_IN. Status: {self.status}. Folding.")
             return PlayerAction.FOLD, 0
        if self.status == PlayerStatus.ALL_IN:
             # print(f"Info: {self.name} is ALL_IN, no action to take.") # Can be noisy
             return PlayerAction.FOLD, 0 # Engine shouldn't ask, but fold if it does

        can_check = (call_amount <= 0)

        # A) Can Check or Bet
        if can_check:
            bet_ratio = 0.0
            if strength > 0.80: bet_ratio = random.uniform(0.7, 1.1)
            elif strength > 0.60: bet_ratio = random.uniform(0.5, 0.75)
            elif strength > 0.45: bet_ratio = random.uniform(0.4, 0.6)
            else: bet_ratio = random.uniform(0.4, 0.6)

            potential_bet = int(pot * bet_ratio)
            min_bet = big_blind if pot > 0 or phase != GamePhase.PRE_FLOP else 0
            potential_bet = max(potential_bet, min_bet)
            amount_to_bet = min(potential_bet, my_stack)

            is_strong = strength > 0.65
            is_medium = strength > 0.50

            if is_strong:
                 if amount_to_bet > 0:
                     action = PlayerAction.ALL_IN if amount_to_bet == my_stack else PlayerAction.BET
                     # print(f"{self.name} {action.value}s {amount_to_bet} (Strong Hand)") # Less verbose
                     return action, amount_to_bet
                 else:
                     # print(f"{self.name} checks (Strong Hand, cannot bet)")
                     return PlayerAction.CHECK, 0
            elif is_medium:
                 if random.random() < 0.6 and amount_to_bet > 0:
                     action = PlayerAction.ALL_IN if amount_to_bet == my_stack else PlayerAction.BET
                     # print(f"{self.name} {action.value}s {amount_to_bet} (Medium Hand)")
                     return action, amount_to_bet
                 else:
                     # print(f"{self.name} checks (Medium Hand)")
                     return PlayerAction.CHECK, 0
            else: # Weak
                 should_bluff = (random.random() < self.bluff_frequency and
                                 amount_to_bet > 0 and
                                 pot > big_blind * 2)
                 if should_bluff:
                      action = PlayerAction.ALL_IN if amount_to_bet == my_stack else PlayerAction.BET
                      # print(f"{self.name} attempts a bluff {action.value} of {amount_to_bet}!")
                      return action, amount_to_bet
                 else:
                      # print(f"{self.name} checks (Weak Hand)")
                      return PlayerAction.CHECK, 0

        # B) Must Call, Fold, or Raise
        else:
            can_afford_call = my_stack >= call_amount

            if not can_afford_call:
                 if strength > 0.85: # Only commit remaining stack if very strong
                      # print(f"{self.name} goes all-in for {my_stack} (Cannot afford call {call_amount}, but strong hand)")
                      # Signal Call, engine handles All-in adjustment via take_action
                      return PlayerAction.CALL, call_amount
                 else:
                     # print(f"{self.name} folds (Cannot afford call {call_amount})")
                     return PlayerAction.FOLD, 0

            # Affordable call, calculate odds
            pot_odds = call_amount / (pot + call_amount) if (pot + call_amount) > 0 else 0
            required_equity = pot_odds

            # Calculate potential raise size
            raise_multiplier = 0.0
            if strength > 0.85: raise_multiplier = random.uniform(2.5, 3.2)
            elif strength > 0.70: raise_multiplier = random.uniform(2.0, 2.8)
            else: raise_multiplier = random.uniform(1.8, 2.5)

            potential_raise_to_total = int(current_bet * raise_multiplier)
            min_raise_delta = max(call_amount, big_blind) # Raise must be at least the call amount (or BB if call=0) larger
            min_raise_to_total = current_bet + min_raise_delta
            potential_raise_to_total = max(potential_raise_to_total, min_raise_to_total)

            target_total_bet_on_raise = potential_raise_to_total
            raise_cost_needed = max(0, target_total_bet_on_raise - my_current_bet_this_round)

            actual_raise_cost = min(raise_cost_needed, my_stack)
            final_total_bet_if_raise = my_current_bet_this_round + actual_raise_cost

            # Valid raise? Must increase bet and meet min increment
            is_a_valid_raise = (final_total_bet_if_raise > current_bet and
                                 (final_total_bet_if_raise - current_bet) >= min_raise_delta)
            # Make sure we are actually *adding* chips if raising
            can_actually_raise = actual_raise_cost > call_amount if is_a_valid_raise else False


            is_strong = strength > 0.75
            adjusted_required_equity = required_equity - (0.05 if phase != GamePhase.RIVER else 0)

            if is_strong:
                 if can_actually_raise: # Check if our stack allows a valid raise
                       # print(f"{self.name} raises to {final_total_bet_if_raise} (Strong Hand)")
                       # Provide the TARGET total bet for the RAISE action
                       return PlayerAction.RAISE, final_total_bet_if_raise
                 else:
                       # print(f"{self.name} calls {call_amount} (Strong Hand, couldn't raise effectively)")
                       return PlayerAction.CALL, call_amount

            elif strength > adjusted_required_equity + 0.10: # Good equity
                  should_raise_aggressively = (random.random() < 0.4 and
                                               phase != GamePhase.RIVER and
                                               can_actually_raise)
                  if should_raise_aggressively:
                       # print(f"{self.name} raises to {final_total_bet_if_raise} (Aggressive semi-value)")
                       return PlayerAction.RAISE, final_total_bet_if_raise
                  else:
                       # print(f"{self.name} calls {call_amount} (Decent equity)")
                       return PlayerAction.CALL, call_amount

            elif strength > adjusted_required_equity - 0.05: # Marginal equity
                  should_bluff_raise_marginal = (random.random() < self.bluff_frequency * 0.3 and
                                                phase != GamePhase.RIVER and
                                                can_actually_raise)
                  should_call_marginal = (random.random() < 0.3)

                  if should_bluff_raise_marginal:
                       # print(f"{self.name} attempts a marginal bluff raise to {final_total_bet_if_raise}!")
                       return PlayerAction.RAISE, final_total_bet_if_raise
                  elif should_call_marginal:
                       # print(f"{self.name} calls {call_amount} (Marginal equity / Draw)")
                       return PlayerAction.CALL, call_amount
                  else:
                       # print(f"{self.name} folds (Marginal equity, odds not good enough)")
                       return PlayerAction.FOLD, 0

            else: # Low equity
                  is_huge_bet = call_amount > pot
                  can_consider_bluff_raise = (phase != GamePhase.RIVER and
                                             not is_huge_bet and
                                             can_actually_raise)
                  should_bluff_raise = (random.random() < self.bluff_frequency and
                                        can_consider_bluff_raise)

                  if should_bluff_raise:
                       # print(f"{self.name} attempts a big bluff raise to {final_total_bet_if_raise}!")
                       return PlayerAction.RAISE, final_total_bet_if_raise
                  else:
                       # print(f"{self.name} folds (Low equity, couldn't bluff)")
                       return PlayerAction.FOLD, 0


        # Failsafe
        print(f"Warning: {self.name} reached end of logic without decision. Folding.")
        return PlayerAction.FOLD, 0