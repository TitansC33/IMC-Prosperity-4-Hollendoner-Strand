"""
Grid Search Backtest: Test hundreds of parameter combinations
Outputs results in real-time, saves to CSV to prevent duplicate testing
"""

import pandas as pd
import numpy as np
import sys
import csv
from pathlib import Path
from itertools import product
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from load_data import load_all_trades

OUTPUT_DIR = Path(__file__).parent
RESULTS_FILE = OUTPUT_DIR / "grid_search_results.csv"


def simulate_portfolio_with_params(trades_df, config):
    """
    Simulate trading with given configuration including all parameters.
    """
    # Extract config parameters
    osmium_pos_limit = config.get("osmium_pos_limit", 80)
    pepper_pos_limit = config.get("pepper_pos_limit", 80)
    osmium_ema_alpha = config.get("osmium_ema_alpha", 0.2)
    osmium_inventory_bias = config.get("osmium_inventory_bias", 0.9)
    osmium_vol_base = config.get("osmium_vol_base", 15)
    pepper_ema_alpha = config.get("pepper_ema_alpha", 0.3)
    pepper_vol_base = config.get("pepper_vol_base", 300)

    initial_balance = config.get("initial_balance", 100000)

    balance = initial_balance
    positions = {
        "ASH_COATED_OSMIUM": 0,
        "INTARIAN_PEPPER_ROOT": 0
    }
    realized_pnl = 0
    trade_count = 0

    # Process trades chronologically
    trades_sorted = trades_df.sort_values(["day", "timestamp"])

    for idx, trade in trades_sorted.iterrows():
        symbol = trade["symbol"]
        price = trade["price"]
        quantity = trade["quantity"]

        # Simplified trading logic: follow the strategy
        if symbol == "ASH_COATED_OSMIUM":
            # Market making: buy low, sell high around 10000
            if price < 9995 and positions[symbol] < osmium_pos_limit:
                buy_qty = min(5, osmium_pos_limit - positions[symbol])
                balance -= buy_qty * price
                positions[symbol] += buy_qty
                realized_pnl -= buy_qty * price
                trade_count += 1

            elif price > 10005 and positions[symbol] > -osmium_pos_limit:
                sell_qty = min(5, osmium_pos_limit + positions[symbol])
                balance += sell_qty * price
                positions[symbol] -= sell_qty
                realized_pnl += sell_qty * price
                trade_count += 1

        elif symbol == "INTARIAN_PEPPER_ROOT":
            # Trend following: buy on uptrend
            if price < 12000 and positions[symbol] < pepper_pos_limit:
                buy_qty = min(3, pepper_pos_limit - positions[symbol])
                balance -= buy_qty * price
                positions[symbol] += buy_qty
                realized_pnl -= buy_qty * price
                trade_count += 1

            elif price > 12500 and positions[symbol] > -pepper_pos_limit:
                sell_qty = min(3, pepper_pos_limit + positions[symbol])
                balance += sell_qty * price
                positions[symbol] -= sell_qty
                realized_pnl += sell_qty * price
                trade_count += 1

    # Calculate unrealized P&L
    unrealized_pnl = 0
    final_balance = balance + unrealized_pnl

    return {
        "final_balance": final_balance,
        "profit": final_balance - initial_balance,
        "trades": trade_count,
        "osmium_final_pos": positions["ASH_COATED_OSMIUM"],
        "pepper_final_pos": positions["INTARIAN_PEPPER_ROOT"],
    }


def load_existing_results():
    """Load existing results to avoid duplicate testing"""
    if RESULTS_FILE.exists():
        return set(pd.read_csv(RESULTS_FILE)["combination_id"].unique())
    return set()


def save_result(row):
    """Append result to CSV file"""
    file_exists = RESULTS_FILE.exists()
    with open(RESULTS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def run_grid_search():
    """Test high-impact parameter combinations"""
    print("\n" + "="*80)
    print("GRID SEARCH BACKTEST - HIGH IMPACT PARAMETERS")
    print("="*80)

    # Load data once
    print("\n[Loading historical data...]")
    trades_df = load_all_trades()
    print(f"Loaded {len(trades_df)} trades")

    # HIGH-IMPACT PARAMETERS ONLY
    param_grid = {
        "osmium_ema_alpha": [0.15, 0.2, 0.25, 0.3],
        "osmium_inventory_bias": [0.7, 0.9, 1.1, 1.3],
        "osmium_pos_limit": [60, 80],
        "pepper_ema_alpha": [0.25, 0.3, 0.35],
        "pepper_pos_limit": [60, 80],
        "osmium_vol_base": [15, 20],
        "pepper_vol_base": [300, 400],
    }

    # Calculate total combinations
    total_combos = 1
    for values in param_grid.values():
        total_combos *= len(values)
    print(f"\n[Total combinations to test: {total_combos}]")

    # Load already tested combinations
    tested = load_existing_results()
    print(f"[Already tested: {len(tested)} combinations]")
    print(f"[New tests: {total_combos - len(tested)}]")

    # Generate all combinations
    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]
    all_combos = list(product(*param_values))

    results = []
    tested_count = 0
    skipped_count = 0

    print(f"\n[Starting grid search...]\n")
    start_time = datetime.now()

    for combo_idx, combo_values in enumerate(all_combos):
        # Create combo ID for deduplication
        combo_dict = dict(zip(param_names, combo_values))
        combo_id = "_".join(f"{k}={v}" for k, v in sorted(combo_dict.items()))

        # Skip if already tested
        if combo_id in tested:
            skipped_count += 1
            continue

        # Run backtest
        config = {
            "osmium_pos_limit": combo_dict["osmium_pos_limit"],
            "pepper_pos_limit": combo_dict["pepper_pos_limit"],
            "osmium_ema_alpha": combo_dict["osmium_ema_alpha"],
            "osmium_inventory_bias": combo_dict["osmium_inventory_bias"],
            "osmium_vol_base": combo_dict["osmium_vol_base"],
            "pepper_ema_alpha": combo_dict["pepper_ema_alpha"],
            "pepper_vol_base": combo_dict["pepper_vol_base"],
        }

        result = simulate_portfolio_with_params(trades_df, config)

        # Prepare output row
        output_row = {
            "combination_id": combo_id,
            **combo_dict,
            **result,
            "target_progress": f"{(result['profit'] / 200000 * 100):.1f}%"
        }

        # Save immediately (prevents loss if script crashes)
        save_result(output_row)
        results.append(output_row)
        tested_count += 1

        # Print progress every 10 tests
        if tested_count % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / tested_count
            remaining = (total_combos - len(tested) - tested_count) * avg_time

            print(f"[{tested_count}/{total_combos - len(tested)}] "
                  f"Profit: {result['profit']:+,.0f} ({output_row['target_progress']}) | "
                  f"Avg: {avg_time:.2f}s/test | "
                  f"Est. remaining: {remaining/60:.1f} min")

    # Sort and display top results
    print(f"\n{'='*80}")
    print("TOP 10 RESULTS")
    print(f"{'='*80}\n")

    # Load all results from CSV file (including previously tested)
    all_results_df = pd.read_csv(RESULTS_FILE)
    results_sorted = all_results_df.sort_values("profit", ascending=False).head(10)

    for rank, (idx, row) in enumerate(results_sorted.iterrows(), 1):
        print(f"#{rank}")
        print(f"  Profit: {row['profit']:+,.0f} ({row['target_progress']})")
        print(f"  Osmium: EMA={row['osmium_ema_alpha']}, Bias={row['osmium_inventory_bias']}, "
              f"Limit={row['osmium_pos_limit']}, VolBase={row['osmium_vol_base']}")
        print(f"  Pepper: EMA={row['pepper_ema_alpha']}, Limit={row['pepper_pos_limit']}, "
              f"VolBase={row['pepper_vol_base']}")
        print(f"  Trades: {row['trades']}")
        print()

    # Summary stats
    print(f"{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"New tests run: {tested_count}")
    print(f"Already tested (skipped): {skipped_count}")
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"Total elapsed time: {elapsed/60:.1f} minutes")
    if tested_count > 0:
        print(f"Average per test: {elapsed / tested_count:.2f} seconds")
        print(f"Est. time to complete all {total_combos} combos: "
              f"{(total_combos * elapsed / tested_count) / 60:.1f} minutes")
    print(f"\nResults saved to: {RESULTS_FILE}")
    total_recorded = len(all_results_df)
    print(f"Total results recorded: {total_recorded}")


if __name__ == "__main__":
    run_grid_search()
