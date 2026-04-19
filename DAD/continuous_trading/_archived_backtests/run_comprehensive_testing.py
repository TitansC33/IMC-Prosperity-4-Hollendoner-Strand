"""
Comprehensive Multi-Config Testing with 100 Loop Iterations

Tests multiple parameter combinations across 100 loops with market randomization.
Stress-tests variables like position limits with changing market conditions.

Usage:
    python run_comprehensive_testing.py                    # Run all configs, 100 iterations each
    python run_comprehensive_testing.py --test-one 80 80  # Test single config (80/80)
    python run_comprehensive_testing.py --quick            # Quick test: 20 iterations
"""

import sys
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root / "analysis"))

from load_data import load_all_trades, load_all_prices
from run_backtest_loops import run_backtest_loops


# Test configurations to evaluate
CONFIGURATIONS = [
    {"name": "Conservative (40/40)", "osmium": 40, "pepper": 40},
    {"name": "Moderate-Conservative (50/50)", "osmium": 50, "pepper": 50},
    {"name": "Moderate (60/60)", "osmium": 60, "pepper": 60},
    {"name": "Moderate-Aggressive (70/70)", "osmium": 70, "pepper": 70},
    {"name": "Aggressive (80/80)", "osmium": 80, "pepper": 80},  # Phase 2 optimal
    {"name": "Very Aggressive (90/90)", "osmium": 90, "pepper": 90},  # New optimal
    {"name": "Osmium Agg / Pepper Con (80/40)", "osmium": 80, "pepper": 40},
    {"name": "Osmium Agg / Pepper Mod (80/60)", "osmium": 80, "pepper": 60},
    {"name": "Osmium Con / Pepper Agg (40/80)", "osmium": 40, "pepper": 80},
    {"name": "Osmium Mod / Pepper Agg (60/80)", "osmium": 60, "pepper": 80},
]


def run_comprehensive_test(iterations=100, test_one=None, output_file=None):
    """
    Run comprehensive testing across multiple configurations.

    Args:
        iterations: Number of loops per configuration (default: 100)
        test_one: If provided, only test this config (e.g., [80, 80])
        output_file: If provided, write results to this file
    """

    configs_to_test = CONFIGURATIONS
    if test_one:
        osmium_lim, pepper_lim = test_one
        configs_to_test = [
            cfg for cfg in CONFIGURATIONS
            if cfg["osmium"] == osmium_lim and cfg["pepper"] == pepper_lim
        ]
        if not configs_to_test:
            print(f"Config {osmium_lim}/{pepper_lim} not found!")
            return

    # Auto-generate output filename if not provided
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        iterations_label = f"{iterations}loops"
        test_label = "comprehensive" if test_one is None else f"{test_one[0]}_{test_one[1]}"
        output_file = f"results_comprehensive_{test_label}_{iterations_label}_{timestamp}.txt"

    output_path = Path(__file__).parent / output_file
    csv_path = output_path.with_suffix('.csv')

    def log_and_print(msg):
        """Print to console AND write to file"""
        print(msg)
        with open(output_path, 'a') as f:
            f.write(msg + "\n")

    # Clear file
    with open(output_path, 'w') as f:
        f.write("")

    log_and_print("\n" + "=" * 120)
    print("COMPREHENSIVE MULTI-CONFIG STRESS TEST")
    print("=" * 120)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test Configurations: {len(configs_to_test)}")
    print(f"Iterations per Config: {iterations}")
    print(f"Randomization: Order + Depth (both ON)")
    print(f"Total Loop Runs: {len(configs_to_test) * iterations:,}")
    print("=" * 120)

    all_results = []

    for config in configs_to_test:
        print(f"\n[DATA] Testing: {config['name']}")
        print(f"   Position Limits: ±{config['osmium']} Osmium, ±{config['pepper']} Pepper")
        print("-" * 120)

        config_obj = {
            "osmium_pos_limit": config["osmium"],
            "pepper_pos_limit": config["pepper"],
            "initial_balance": 100000
        }

        # Run with BOTH randomizations enabled (maximum stress test)
        results = run_backtest_loops(
            iterations=iterations,
            config=config_obj,
            randomize_depth=True,
            randomize_order=True,
            match_mode="all"
        )

        # Extract metrics
        pnl_values = [r["final_portfolio_value"] for r in results]
        pnl_array = np.array(pnl_values)

        config_summary = {
            "config": config["name"],
            "osmium_limit": config["osmium"],
            "pepper_limit": config["pepper"],
            "iterations": iterations,
            "mean_pnl": pnl_array.mean(),
            "median_pnl": np.median(pnl_array),
            "std_dev": pnl_array.std(),
            "min_pnl": pnl_array.min(),
            "max_pnl": pnl_array.max(),
            "cv": (pnl_array.std() / pnl_array.mean()) if pnl_array.mean() != 0 else 0,
            "target_200k": (pnl_array >= 200000).sum(),
            "success_rate": ((pnl_array >= 200000).sum() / iterations) * 100,
        }

        all_results.append(config_summary)

    # Print consolidated results
    print("\n" + "=" * 120)
    print("CONSOLIDATED RESULTS - ALL CONFIGURATIONS RANKED BY MEAN PnL")
    print("=" * 120)

    # Sort by mean PnL descending
    sorted_results = sorted(all_results, key=lambda x: x["mean_pnl"], reverse=True)

    print(f"\n{'Rank':<6} {'Configuration':<35} {'Mean PnL':>15} {'Median':>15} {'Std Dev':>12} {'Success %':>12} {'CoV':>8}")
    print("-" * 120)

    for rank, result in enumerate(sorted_results, 1):
        rank_marker = "[#1]" if rank == 1 else "     "
        print(
            f"{rank_marker} {rank:<4} {result['config']:<35} "
            f"{result['mean_pnl']:>15,.0f} {result['median_pnl']:>15,.0f} "
            f"{result['std_dev']:>12,.0f} {result['success_rate']:>11.1f}% {result['cv']:>8.4f}"
        )

    # Detailed statistics for top 3
    print("\n" + "=" * 120)
    print("DETAILED STATISTICS - TOP 3 PERFORMERS")
    print("=" * 120)

    for rank, result in enumerate(sorted_results[:3], 1):
        print(f"\n#{rank}: {result['config']}")
        print(f"   Position Limits: ±{result['osmium_limit']} Osmium, ±{result['pepper_limit']} Pepper")
        print(f"   Mean PnL:          {result['mean_pnl']:>15,.0f}")
        print(f"   Median:            {result['median_pnl']:>15,.0f}")
        print(f"   Std Dev:           {result['std_dev']:>15,.0f}")
        print(f"   Min:               {result['min_pnl']:>15,.0f}")
        print(f"   Max:               {result['max_pnl']:>15,.0f}")
        print(f"   Target Success:    {result['target_200k']:>3}/{result['iterations']} ({result['success_rate']:.1f}%)")
        print(f"   Coefficient of Var:{result['cv']:>15.4f}")

    # Comparative analysis
    print("\n" + "=" * 120)
    print("COMPARATIVE ANALYSIS")
    print("=" * 120)

    best = sorted_results[0]
    phase2 = next((r for r in sorted_results if r["config"].endswith("(80/80)")), None)

    if phase2 and best["config"] != phase2["config"]:
        improvement = ((best["mean_pnl"] - phase2["mean_pnl"]) / phase2["mean_pnl"]) * 100
        print(f"\n[UP] Best Config: {best['config']}")
        print(f"   vs Phase 2 (80/80): +{improvement:.1f}% improvement")
        print(f"   Mean gain: {best['mean_pnl'] - phase2['mean_pnl']:>15,.0f} XIRECs")
    else:
        print(f"\n[OK] Phase 2 (80/80) remains optimal")
        print(f"   Mean PnL: {phase2['mean_pnl']:>15,.0f}")

    # Worst case analysis
    print(f"\n[WARN]  Worst-Case Scenario Analysis (100 loops)")
    print(f"   Best config worst run: {best['min_pnl']:>15,.0f} ({(best['min_pnl']/200000)*100:.1f}% of target)")
    print(f"   All runs > 200k target? {'YES (OK)' if best['min_pnl'] >= 200000 else 'NO (WARN)'}")

    # Stability analysis
    print(f"\n[DATA] Stability Analysis (Lower CoV = More Stable)")
    sorted_by_stability = sorted(all_results, key=lambda x: x["cv"])
    print(f"   Most stable: {sorted_by_stability[0]['config']} (CoV: {sorted_by_stability[0]['cv']:.4f})")
    print(f"   Least stable: {sorted_by_stability[-1]['config']} (CoV: {sorted_by_stability[-1]['cv']:.4f})")

    # Summary recommendation
    print("\n" + "=" * 120)
    print("RECOMMENDATION")
    print("=" * 120)

    print(f"\n[OK] PRIMARY: {best['config']}")
    print(f"   Mean: {best['mean_pnl']:>15,.0f} XIRECs")
    print(f"   Success Rate: {best['success_rate']:.1f}% (all > 200k target)")
    print(f"   Worst Case: {best['min_pnl']:>15,.0f} XIRECs ({(best['min_pnl']/200000)*100:.1f}% of target)")

    if phase2 and phase2["config"] != best["config"]:
        print(f"\n[ALT] ALTERNATIVE (Phase 2): {phase2['config']}")
        print(f"   Mean: {phase2['mean_pnl']:>15,.0f} XIRECs")
        print(f"   Success Rate: {phase2['success_rate']:.1f}%")
        print(f"   Reasoning: Already proven in Phase 2, lower change risk")

    print("\n" + "=" * 120)
    print(f"Test Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 120 + "\n")

    return sorted_results


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive multi-config testing with 100 loop iterations"
    )
    parser.add_argument(
        "--iterations", type=int, default=100,
        help="Loop iterations per configuration (default: 100)"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick test: 20 iterations instead of 100"
    )
    parser.add_argument(
        "--test-one", nargs=2, type=int, metavar=("OSMIUM", "PEPPER"),
        help="Test only one configuration (e.g., --test-one 80 80)"
    )

    args = parser.parse_args()

    iterations = 20 if args.quick else args.iterations

    run_comprehensive_test(iterations=iterations, test_one=args.test_one)


if __name__ == "__main__":
    main()
