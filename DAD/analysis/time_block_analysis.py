"""
Analyze data in time blocks (efficient summary version).
Shows day-by-day and breaks each day into ~5 blocks for comparison.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from load_data import get_product_trades
import warnings
warnings.filterwarnings('ignore')

# Ensure outputs go to DAD/scripts
OUTPUT_DIR = Path(__file__).parent
OUTPUT_DIR.mkdir(exist_ok=True)


def analyze_by_time_blocks_efficient(symbol: str, output_file=None):
    """
    Analyze price, volume, momentum in time blocks (5 blocks per day).
    Summary format - not verbose.
    """
    trades = get_product_trades(symbol)

    if len(trades) == 0:
        print(f"No trades for {symbol}")
        return

    print(f"\n{'='*100}")
    print(f"TIME BLOCK ANALYSIS: {symbol}")
    print(f"{'='*100}\n")

    # Analyze each day separately
    for day in [-2, -1, 0]:
        day_trades = trades[trades["day"] == day].copy()

        if len(day_trades) == 0:
            continue

        print(f"DAY {day}")
        print(f"{'-'*100}")

        min_ts = day_trades['timestamp'].min()
        max_ts = day_trades['timestamp'].max()

        # Create 50 equal-sized blocks for the day
        num_blocks = 50
        block_size = (max_ts - min_ts) / num_blocks

        print(f"{'Block':<8} {'Time Range':<20} {'Trades':<8} {'Vol':<8} {'Price':<20} {'Change':<10} {'Momentum':<12}")
        print(f"{'-'*100}")

        for block_num in range(num_blocks):
            block_start = min_ts + (block_num * block_size)
            block_end = min_ts + ((block_num + 1) * block_size)

            block_trades = day_trades[(day_trades['timestamp'] >= block_start) &
                                      (day_trades['timestamp'] <= block_end)]

            if len(block_trades) == 0:
                continue

            prices = block_trades['price'].values
            volumes = block_trades['quantity'].values

            # Calculate metrics
            price_start = prices[0]
            price_end = prices[-1]
            price_change = price_end - price_start
            price_change_pct = (price_change / price_start) * 100 if price_start != 0 else 0

            momentum_changes = np.diff(prices)
            up_moves = (momentum_changes > 0).sum()
            down_moves = (momentum_changes < 0).sum()
            total_moves = up_moves + down_moves

            momentum_str = f"{up_moves}U/{down_moves}D" if total_moves > 0 else "N/A"
            price_range = f"{price_start:.0f}-{price_end:.0f}"

            print(f"{block_num+1:<8} {int(block_start):5d}-{int(block_end):5d}      {len(block_trades):<8} {volumes.sum():<8.0f} {price_range:<20} {price_change_pct:+7.2f}%   {momentum_str:<12}")

        print()


def compare_days_summary(symbol: str, output_file=None):
    """
    Compare overall stats by day in table format.
    """
    trades = get_product_trades(symbol)

    if len(trades) == 0:
        return

    print(f"\n{'='*100}")
    print(f"DAY-BY-DAY SUMMARY: {symbol}")
    print(f"{'='*100}\n")
    print(f"{'Day':<6} {'Trades':<10} {'Volume':<12} {'Avg/Trade':<12} {'Price Range':<18} {'VWAP':<12} {'% Change':<12}")
    print(f"{'-'*100}")

    for day in [-2, -1, 0]:
        day_trades = trades[trades["day"] == day]

        if len(day_trades) == 0:
            continue

        prices = day_trades['price'].values
        volumes = day_trades['quantity'].values

        vwap = (prices * volumes).sum() / volumes.sum()
        price_start = prices[0]
        price_end = prices[-1]
        price_change_pct = (price_end - price_start) / price_start * 100

        price_range = f"{prices.min():.0f}-{prices.max():.0f}"
        avg_trade = volumes.mean()

        print(f"{day:<6} {len(day_trades):<10} {volumes.sum():<12.0f} {avg_trade:<12.1f} {price_range:<18} {vwap:<12.2f} {price_change_pct:+11.2f}%")

    print()


if __name__ == "__main__":
    output_file = OUTPUT_DIR / "time_block_analysis.txt"

    # Clear and start output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("TIME BLOCK ANALYSIS - EFFICIENT SUMMARY\n")
        f.write("(50 blocks per day, focusing on key metrics)\n")
        f.write("="*100 + "\n\n")

    print("TIME BLOCK ANALYSIS - EFFICIENT SUMMARY")
    print("(50 blocks per day, focusing on key metrics)")

    # Redirect output to both console and file
    import sys
    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, data):
            for f in self.files:
                f.write(data)
        def flush(self):
            for f in self.files:
                f.flush()

    with open(output_file, "a", encoding="utf-8") as f:
        original_stdout = sys.stdout
        sys.stdout = Tee(sys.stdout, f)

        for symbol in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
            compare_days_summary(symbol, output_file)
            analyze_by_time_blocks_efficient(symbol, output_file)

        sys.stdout = original_stdout

    print(f"\nAnalysis complete. Output saved to: {output_file}")
