import os
import time
from player import Player, PlayerStatus, PlayerAction
from game import PokerGame, GamePhase
from baseplayers import InputPlayer
from bot_cfr import CFRBot
from baseplayers import FoldPlayer, RaisePlayer
from bot_mccfr import MCCFRPokerBot
from bot_aggressive import AggroBot

def run_game():

    players = [
        AggroBot("AggroBot_1", 1000),
        MCCFRPokerBot("MCCFR_Bot", 1000),
        AggroBot("AggroBot_2", 1000, bluff_frequency=0.25),
        #RaisePlayer("Charlie", 1000),
        FoldPlayer("David", 1000),
        # You can mix and match players as needed
    ]

    # Create game
    game = PokerGame(players, big_blind=20)

    # Run several hands
    for hand_num in range(1, 6): # Run 5 hands
        print(f"\n\n--- Starting Hand #{hand_num} ---")
        game.start_new_hand()

        # Main game loop for one hand
        num_consecutive_errors = 0
        MAX_ERRORS = 3 # How many invalid moves before auto-fold

        while game.phase != GamePhase.SHOWDOWN:

            active_players_can_act = [p for p in game.players if p.can_make_action()]
            if not active_players_can_act:
                 # This state can be normal if everyone folds/is all-in before showdown
                 # print("No players left who can act. Waiting for game phase advance.")
                 break # Exit inner loop, let game advance/end naturally

            if not game.players[game.active_player_index].can_make_action():
                # print("Current active player cannot act. Trying to adjust.") # Can be noisy
                if not game._adjust_active_player_index():
                    print("Adjustment failed finding next player. Ending hand.")
                    break
                game.display_game_state()
                continue


            player = game.players[game.active_player_index]

            # This check was potentially causing issues/was redundant. Rely on game.is_betting_round_complete()
            # if len(active_players_can_act) == 1 and player.bet_amount == game.current_bet and game.current_bet > 0:
            #      # Complex edge cases (like BB option pre-flop) exist. Let engine handle round end.
            #      pass


            print(f"\nTurn: {player.name} ({player.status.value}, Stack: ${player.stack}, Bet: {player.bet_amount})")
            # Only show cards for non-FoldPlayer/non-InputPlayer types if needed
            if "FoldPlayer" not in str(type(player)) and "InputPlayer" not in str(type(player)):
                try:
                   print(f"Cards: {[str(c) for c in player.hole_cards]}")
                except Exception: # Handle case where cards might be None unexpectedly
                   print("Cards: [Error displaying]")
            elif isinstance(player, InputPlayer):
                 print(f"Your cards: {[str(c) for c in player.hole_cards]}")


            is_successful = False
            try:
                # Ensure game_state is up-to-date before passing to bot? game.get_game_state() is called within game.get_player_input()
                is_successful = game.get_player_input() # This calls player.action internally
                if is_successful: # Reset errors ONLY on success
                    num_consecutive_errors = 0
            except Exception as e:
                import traceback
                print(f"!! Error during player {player.name}'s turn: {e}")
                traceback.print_exc() # Print detailed traceback for debugging
                is_successful = False

            if not is_successful:
                num_consecutive_errors += 1
                print(f"Invalid command or action failed ({num_consecutive_errors}/{MAX_ERRORS}).")
                if num_consecutive_errors >= MAX_ERRORS:
                    print(f"Player {player.name} failed {MAX_ERRORS} consecutive times. Auto-folding.")
                    try:
                        # Manually make the player fold - ensure this doesn't raise another exception
                        game.player_action(PlayerAction.FOLD, 0)
                    except Exception as fold_e:
                         print(f"!! Error trying to auto-fold player {player.name}: {fold_e}")
                         # If folding fails, we might be stuck, break the loop
                         break
                    num_consecutive_errors = 0 # Reset after attempting auto-fold
                else:
                     # Maybe add a small delay after an error before retrying?
                     time.sleep(0.2)


            # Reduced delay, can be 0 for faster simulation
            time.sleep(0.05)

            # Check again if the hand/game ended after the action
            if game.phase == GamePhase.SHOWDOWN:
                break


        print(f"\n--- Hand #{hand_num} Ended ---")
        # Display final player stacks
        print("Final Stacks:")
        for p in game.players:
             print(f"  {p.name}: ${p.stack}")

        # Optional: Remove players with no chips for subsequent hands
        # players_with_chips = [p for p in game.players if p.stack > 0]
        # if len(players_with_chips) <= 1:
        #     print("\nGame Over!")
        #     if players_with_chips:
        #         print(f"Winner: {players_with_chips[0].name}")
        #     break # End game if only one player remains
        # game.players = players_with_chips # Update game's player list (might need engine support)

        if hand_num < 5: # Don't pause after the last hand
           print("Preparing next hand...")
           time.sleep(2) # Pause between hands


if __name__ == "__main__":
    run_game()