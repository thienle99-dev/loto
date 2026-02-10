
import math

def calculate_tokens(total_players, num_winners, bet_amount):
    if total_players <= 0 or num_winners <= 0:
        return 0, 0
    
    # Formula from src/bot/handlers/game.py:
    # token_per_winner = (total_players * bet_amount / num_winners) - bet_amount
    token_per_winner = (total_players * bet_amount / num_winners) - bet_amount
    
    num_losers = total_players - num_winners
    total_gained = num_winners * token_per_winner
    total_lost = num_losers * bet_amount
    
    return token_per_winner, total_gained, total_lost

def run_tests():
    scenarios = [
        (10, 1, 5.0),
        (10, 2, 5.0),
        (10, 3, 5.0),
        (10, 10, 5.0),
        (2, 1, 5.0),
        (7, 3, 5.0),
    ]
    
    print(f"{'Players':<10} | {'Winners':<10} | {'Token/Win':<15} | {'Total Gain':<15} | {'Total Loss':<15} | {'Balance'}")
    print("-" * 85)
    
    for tp, nw, bet in scenarios:
        tpw, tg, tl = calculate_tokens(tp, nw, bet)
        balance = tg - tl
        print(f"{tp:<10} | {nw:<10} | {tpw:<15.4f} | {tg:<15.4f} | {tl:<15.4f} | {balance:.10f}")

if __name__ == "__main__":
    run_tests()
