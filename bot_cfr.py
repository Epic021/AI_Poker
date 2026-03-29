from hand_evaluator import HandEvaluator , HandRank
from player import Player , PlayerAction , PlayerStatus
from card import Card , Rank , Suit

import random
import pickle
import json
from player import Player, PlayerAction

class CFRBot(Player):
    def __init__(self, name, stack, strategy_file="trained_cfr.pkl"):
        super().__init__(name, stack)
        self.strategy = self.load_strategy(strategy_file)

    def load_strategy(self, filename):
        """Load the trained CFR strategy from a pickle file."""
        try:
            with open(filename, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            print(f"Warning: {filename} not found. Using a random strategy.")
            return {}

    def action(self, game_state, action_history):
        """Decide an action based on the trained CFR strategy."""
        state_key = tuple(game_state)  # Convert game state to a hashable format
        
        if state_key in self.strategy:
            action_probs = self.strategy[state_key]  # Get action probabilities
        else:
            action_probs = {"fold": 1/3, "call": 1/3, "raise": 1/3}  # Default if no info
        
        # Choose action based on probabilities
        chosen_action = random.choices(["fold", "call", "raise"], weights=[action_probs.get(a, 1/3) for a in ["fold", "call", "raise"]], k=1)[0]

        # Convert to PlayerAction and return amount
        if chosen_action == "raise":
            return PlayerAction.RAISE, game_state[3]  # Raise by the current raise amount
        elif chosen_action == "call":
            return PlayerAction.CALL, game_state[3]  # Call the current raise
        return PlayerAction.FOLD, 0  # Fold
