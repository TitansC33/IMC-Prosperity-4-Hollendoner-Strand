"""
Backtest Loop Runner with Randomization

Runs backtests repeatedly with randomized conditions to stress-test the strategy.
Tests robustness across multiple market scenarios.

Usage:
    python run_backtest_loops.py --iterations 10 --randomize-depth --randomize-order
"""

import sys
from pathlib import Path
import argparse
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root / "analysis"))

from load_data import load_all_trades, load_all_prices
from backtest_v2_with_matching import simulate_portfolio_with_matching
from order_matcher import OrderDepth


def add_noise_to_prices(prices_df, noise_std=50):
    """Add small random noise to order depth prices to simulate market changes"""
    prices_copy = prices_df.copy()

    for col in ['bid_price_1', 'bid_price_2', 'bid_price_3',
                'ask_price_1', 'ask_price_2', 'ask_price_3', 'mid_price']:
        if col in prices_copy.columns:
            mask = prices_copy[col].notna()
            prices_copy.loc[mask, col] = (
                prices_copy.loc[mask, col] +
                np.random.normal(0, noise_std, mask.sum())
            ).astype(int)

    return prices_copy


def randomize_trade_order(trades_df, seed=None):
    """Shuffle trade order within same timestamp to test execution sensitivity"""
    if seed is not None:
        np.random.seed(seed)

    trades_copy = trades_df.copy()

    # Shuffle within each (day, timestamp) group
    for (day, ts), group in trades_copy.groupby(['day', 'timestamp']):
        if len(group) > 1:
            shuffled_indices = np.random.permutation(group.index)
            trades_copy.loc[group.index] = trades_copy.loc[shuffled_indices].values

    return trades_copy


def run_backtest_loops(
    iterations=5,
    config=None,
    randomize_depth=False,
    randomize_order=False,
    match_mode="all"
):
    """
    Run backtest multiple times with optional randomization.

    Args:
        iterations: Number of runs
        config: Position limit config (default: Phase 2 optimal)
        randomize_depth: Add price noise to order depths
        randomize_order: Shuffle trade execution order within timestamps
        match_mode: Order matching mode ('all', 'worse', 'none')
    """

    if config is None:
        config = {"osmium_pos_limit": 80, "pepper_pos_limit": 80}

    config["initial_balance"] = 100000

    # Load data
    trades_df = load_all_trades()
    prices_df = load_all_prices()

    print("=" * 100)
    print("BACKTEST LOOP RUNNER WITH RANDOMIZATION")
    print("=" * 100)
    print(f"\nConfiguration: ±{config['osmium_pos_limit']} Osmium, ±{config['pepper_pos_limit']} Pepper")
    print(f"Match Mode: {match_mode}")
    print(f"Randomization: Depth={'ON' if randomize_depth else 'OFF'}, "
          f"Order={'ON' if randomize_order else 'OFF'}")
    print(f"Iterations: {iterations}\n")

    results = []
    pnl_values = []

    print(f"{'Run':<6} {'Portfolio Value':>18} {'Target %':>10} {'Osmium Pos':>12} {'Pepper Pos':>12}")
    print("-" * 70)

    for run in range(1, iterations + 1):
        # Apply randomization if requested
        trades_to_use = trades_df
        prices_to_use = prices_df

        if randomize_order:
            trades_to_use = randomize_trade_order(trades_df, seed=run)

        if randomize_depth:
            prices_to_use = add_noise_to_prices(prices_df, noise_std=50)

        # Run backtest
        result = simulate_portfolio_with_matching(
            trades_to_use, prices_to_use, config, match_mode=match_mode
        )

        pnl = result["final_portfolio_value"]
        pnl_values.append(pnl)
        target_pct = (pnl / 200000) * 100
        osmium_pos = result["final_positions"]["ASH_COATED_OSMIUM"]
        pepper_pos = result["final_positions"]["INTARIAN_PEPPER_ROOT"]

        print(f"{run:<6} {pnl:>18,.0f} {target_pct:>9.1f}% "
              f"{osmium_pos:>12} {pepper_pos:>12}")

        results.append(result)

    # Statistical summary
    pnl_array = np.array(pnl_values)

    print("\n" + "=" * 100)
    print("STATISTICAL SUMMARY")
    print("=" * 100)

    print(f"\nPortfolio Value Statistics:")
    print(f"  Mean:              {pnl_array.mean():>15,.0f}")
    print(f"  Median:            {np.median(pnl_array):>15,.0f}")
    print(f"  Std Dev:           {pnl_array.std():>15,.0f}")
    print(f"  Min:               {pnl_array.min():>15,.0f}")
    print(f"  Max:               {pnl_array.max():>15,.0f}")
    print(f"  Variance:          {pnl_array.var():>15,.0f}")

    # Target achievement
    target = 200000
    above_target = sum(1 for pnl in pnl_values if pnl >= target)
    below_target = iterations - above_target

    print(f"\nTarget Achievement (200,000 XIRECs):")
    print(f"  Runs above target: {above_target:>6} ({(above_target/iterations)*100:.1f}%)")
    print(f"  Runs below target: {below_target:>6} ({(below_target/iterations)*100:.1f}%)")

    # Risk metrics
    margin_above_target = [pnl - target for pnl in pnl_values if pnl >= target]
    margin_below_target = [target - pnl for pnl in pnl_values if pnl < target]

    if margin_above_target:
        print(f"  Avg margin above:  {np.mean(margin_above_target):>15,.0f}")

    if margin_below_target:
        print(f"  Avg shortfall:     {np.mean(margin_below_target):>15,.0f}")

    # Coefficient of variation (risk-adjusted metric)
    cv = (pnl_array.std() / pnl_array.mean()) if pnl_array.mean() != 0 else 0
    print(f"\nRisk Metrics:")
    print(f"  Coefficient of Variation: {cv:.4f} (lower is better)")
    print(f"  Sharpe Ratio proxy:       {(pnl_array.mean() - target) / pnl_array.std():.4f}")

    # Validation
    print("\n" + "=" * 100)
    print("VALIDATION CHECKS")
    print("=" * 100)

    checks = [
        ("All runs complete", len(results) == iterations),
        ("Consistency: StdDev < 10% of Mean", cv < 0.1),
        ("Reliability: >90% above target", (above_target / iterations) > 0.9),
        ("No critical failures", all(r["final_portfolio_value"] > 0 for r in results)),
    ]

    for check, result in checks:
        status = "[PASS]" if result else "[WARN]"
        print(f"  {status} {check}")

    all_pass = all(result for _, result in checks)

    print("\n" + "=" * 100)
    if all_pass:
        print("[PASS] LOOP TESTING PASSED")
        print("       Strategy is robust and consistent across randomized scenarios.")
        print("       Ready for competition.")
    else:
        print("[WARN] LOOP TESTING SHOWS VARIABILITY")
        print("       Review inconsistencies or edge cases.")
    print("=" * 100 + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run backtests in loops with optional randomization"
    )
    parser.add_argument(
        "--iterations", type=int, default=5,
        help="Number of backtest iterations (default: 5)"
    )
    parser.add_argument(
        "--osmium-limit", type=int, default=80,
        help="Osmium position limit (default: 80)"
    )
    parser.add_argument(
        "--pepper-limit", type=int, default=80,
        help="Pepper position limit (default: 80)"
    )
    parser.add_argument(
        "--randomize-depth", action="store_true",
        help="Add price noise to order depths"
    )
    parser.add_argument(
        "--randomize-order", action="store_true",
        help="Shuffle trade execution order within timestamps"
    )
    parser.add_argument(
        "--match-mode", choices=["all", "worse", "none"], default="all",
        help="Order matching mode (default: all)"
    )

    args = parser.parse_args()

    config = {
        "osmium_pos_limit": args.osmium_limit,
        "pepper_pos_limit": args.pepper_limit
    }

    run_backtest_loops(
        iterations=args.iterations,
        config=config,
        randomize_depth=args.randomize_depth,
        randomize_order=args.randomize_order,
        match_mode=args.match_mode
    )


if __name__ == "__main__":
    main()
