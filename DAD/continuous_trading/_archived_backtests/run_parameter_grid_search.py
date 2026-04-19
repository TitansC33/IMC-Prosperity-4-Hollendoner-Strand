"""
Extended Parameter Grid Search with 100 Loop Randomization

Tests combinations of tunable parameters from trader.py:
- Position Limits (selected configs)
- EMA Alpha values (OSMIUM & PEPPER)
- VWAP Window sizes
- Inventory Bias levels

Each combination runs 100 loops with market randomization for robustness.

Usage:
    # Test all combinations (massive grid)
    python run_parameter_grid_search.py --full

    # Test quick combinations (faster)
    python run_parameter_grid_search.py --quick

    # Test just EMA variations (3 x 3 = 9 combos)
    python run_parameter_grid_search.py --test-ema

    # Test just VWAP variations
    python run_parameter_grid_search.py --test-vwap

    # Test just INVENTORY variations
    python run_parameter_grid_search.py --test-inventory

    # Test a specific combination with 100 loops
    python run_parameter_grid_search.py --test-combo 80 80 0.15 15 0.7
"""

import sys
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
import shutil
import subprocess
import re

sys.path.insert(0, str(Path(__file__).parent))
_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root / "analysis"))

from run_backtest_loops import run_backtest_loops


# Define parameter grid options
POSITION_CONFIGS = [
    {"osmium": 80, "pepper": 80},  # Phase 2 optimal
    {"osmium": 90, "pepper": 90},  # New optimal
]

EMA_ALPHAS_OSMIUM = [0.12, 0.15, 0.18]  # Around Phase 2: 0.15
EMA_ALPHAS_PEPPER = [0.25, 0.30, 0.35]  # Around Phase 2: 0.30

VWAP_WINDOWS = [12, 15, 18]  # Around Phase 2: 15
INVENTORY_BIASES = [0.6, 0.7, 0.8]  # Around Phase 2: 0.7

# For quick mode: smaller subset
QUICK_EMA_OSMIUM = [0.15]
QUICK_EMA_PEPPER = [0.30]
QUICK_VWAP = [15]
QUICK_INVENTORY = [0.7]


def backup_trader_py():
    """Create backup of trader.py before modifications"""
    trader_path = Path(__file__).parent / "trader.py"
    backup_path = Path(__file__).parent / "trader_backup.py"

    if not backup_path.exists():
        shutil.copy(trader_path, backup_path)
        print(f"[CHECK] Backup created: {backup_path.name}")
    return backup_path


def modify_trader_parameters(ema_osmium, vwap_window, inventory_bias, ema_pepper):
    """Modify trader.py with new parameter values"""
    trader_path = Path(__file__).parent / "trader.py"
    backup_path = Path(__file__).parent / "trader_backup.py"

    # Read original
    with open(backup_path, 'r') as f:
        content = f.read()

    # Make replacements
    content = re.sub(
        r'OSMIUM_EMA_ALPHA = [\d.]+',
        f'OSMIUM_EMA_ALPHA = {ema_osmium}',
        content
    )
    content = re.sub(
        r'OSMIUM_VWAP_WINDOW = \d+',
        f'OSMIUM_VWAP_WINDOW = {vwap_window}',
        content
    )
    content = re.sub(
        r'OSMIUM_INVENTORY_BIAS = [\d.]+',
        f'OSMIUM_INVENTORY_BIAS = {inventory_bias}',
        content
    )
    content = re.sub(
        r'PEPPER_EMA_ALPHA = [\d.]+',
        f'PEPPER_EMA_ALPHA = {ema_pepper}',
        content
    )

    # Write modified version
    with open(trader_path, 'w') as f:
        f.write(content)


def restore_trader_py():
    """Restore trader.py to Phase 2 optimal"""
    trader_path = Path(__file__).parent / "trader.py"
    backup_path = Path(__file__).parent / "trader_backup.py"

    if backup_path.exists():
        shutil.copy(backup_path, trader_path)


def run_parameter_combination(pos_osmium, pos_pepper, ema_osmium, vwap_window, inventory_bias, ema_pepper, iterations=100):
    """
    Test one parameter combination with loop iterations
    """

    # Modify trader.py
    modify_trader_parameters(ema_osmium, vwap_window, inventory_bias, ema_pepper)

    config = {
        "osmium_pos_limit": pos_osmium,
        "pepper_pos_limit": pos_pepper,
        "initial_balance": 100000
    }

    # Run with both randomizations
    results = run_backtest_loops(
        iterations=iterations,
        config=config,
        randomize_depth=True,
        randomize_order=True,
        match_mode="all"
    )

    # Extract metrics
    pnl_values = [r["final_portfolio_value"] for r in results]
    pnl_array = np.array(pnl_values)

    return {
        "pos_osmium": pos_osmium,
        "pos_pepper": pos_pepper,
        "ema_osmium": ema_osmium,
        "vwap_window": vwap_window,
        "inventory_bias": inventory_bias,
        "ema_pepper": ema_pepper,
        "mean_pnl": pnl_array.mean(),
        "median_pnl": np.median(pnl_array),
        "std_dev": pnl_array.std(),
        "min_pnl": pnl_array.min(),
        "max_pnl": pnl_array.max(),
        "cv": (pnl_array.std() / pnl_array.mean()) if pnl_array.mean() != 0 else 0,
        "success_rate": ((pnl_array >= 200000).sum() / iterations) * 100,
        "iterations": iterations,
    }


def run_grid_search(test_type="full", iterations=100):
    """
    Run parameter grid search with specified test type
    """

    backup_trader_py()

    # Determine which parameters to test
    if test_type == "quick":
        ema_osmium_vals = QUICK_EMA_OSMIUM
        ema_pepper_vals = QUICK_EMA_PEPPER
        vwap_vals = QUICK_VWAP
        inventory_vals = QUICK_INVENTORY
    elif test_type == "full":
        ema_osmium_vals = EMA_ALPHAS_OSMIUM
        ema_pepper_vals = EMA_ALPHAS_PEPPER
        vwap_vals = VWAP_WINDOWS
        inventory_vals = INVENTORY_BIASES
    elif test_type == "ema":
        ema_osmium_vals = EMA_ALPHAS_OSMIUM
        ema_pepper_vals = EMA_ALPHAS_PEPPER
        vwap_vals = QUICK_VWAP
        inventory_vals = QUICK_INVENTORY
    elif test_type == "vwap":
        ema_osmium_vals = QUICK_EMA_OSMIUM
        ema_pepper_vals = QUICK_EMA_PEPPER
        vwap_vals = VWAP_WINDOWS
        inventory_vals = QUICK_INVENTORY
    elif test_type == "inventory":
        ema_osmium_vals = QUICK_EMA_OSMIUM
        ema_pepper_vals = QUICK_EMA_PEPPER
        vwap_vals = QUICK_VWAP
        inventory_vals = INVENTORY_BIASES

    total_combos = (len(POSITION_CONFIGS) * len(ema_osmium_vals) *
                    len(ema_pepper_vals) * len(vwap_vals) * len(inventory_vals))

    print("\n" + "=" * 140)
    print("PARAMETER GRID SEARCH WITH 100 LOOP ITERATIONS")
    print("=" * 140)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test Type: {test_type.upper()}")
    print(f"Total Combinations: {total_combos}")
    print(f"Iterations per Combo: {iterations}")
    print(f"Total Loop Runs: {total_combos * iterations:,}")
    print(f"\nParameter Ranges:")
    print(f"  Position Limits: {POSITION_CONFIGS}")
    print(f"  OSMIUM EMA Alpha: {ema_osmium_vals}")
    print(f"  PEPPER EMA Alpha: {ema_pepper_vals}")
    print(f"  VWAP Window: {vwap_vals}")
    print(f"  Inventory Bias: {inventory_vals}")
    print("=" * 140)

    all_results = []
    combo_num = 0

    for pos_config in POSITION_CONFIGS:
        for ema_osm in ema_osmium_vals:
            for ema_pep in ema_pepper_vals:
                for vwap_w in vwap_vals:
                    for inv_bias in inventory_vals:
                        combo_num += 1

                        print(f"\n[{combo_num}/{total_combos}] Testing combination:")
                        print(f"  Positions: ±{pos_config['osmium']}/±{pos_config['pepper']}")
                        print(f"  EMA: Osmium={ema_osm}, Pepper={ema_pep}")
                        print(f"  VWAP Window: {vwap_w}, Inventory Bias: {inv_bias}")
                        print(f"  Running {iterations} loops...")

                        result = run_parameter_combination(
                            pos_config["osmium"], pos_config["pepper"],
                            ema_osm, vwap_w, inv_bias, ema_pep,
                            iterations=iterations
                        )

                        all_results.append(result)

                        print(f"  [CHECK] Mean PnL: {result['mean_pnl']:>12,.0f} | Success: {result['success_rate']:>5.1f}% | CoV: {result['cv']:.4f}")

    # Restore trader.py
    restore_trader_py()

    # Print consolidated results
    print("\n" + "=" * 140)
    print("CONSOLIDATED RESULTS - ALL COMBINATIONS RANKED BY MEAN PnL")
    print("=" * 140)

    sorted_results = sorted(all_results, key=lambda x: x["mean_pnl"], reverse=True)

    print(f"\n{'Rank':<6} {'Positions':<12} {'EMA O/P':<15} {'VWAP':<6} {'Inv.Bias':<10} {'Mean PnL':>15} {'Success %':>12} {'CoV':>8}")
    print("-" * 140)

    for rank, result in enumerate(sorted_results[:20], 1):  # Top 20
        rank_marker = "[BEST]" if rank == 1 else "      "
        ema_str = f"{result['ema_osmium']:.2f}/{result['ema_pepper']:.2f}"
        pos_str = f"±{result['pos_osmium']}/±{result['pos_pepper']}"

        print(
            f"{rank_marker} {rank:<4} {pos_str:<12} {ema_str:<15} "
            f"{result['vwap_window']:<6} {result['inventory_bias']:<10.1f} "
            f"{result['mean_pnl']:>15,.0f} {result['success_rate']:>11.1f}% {result['cv']:>8.4f}"
        )

    # Best result details
    best = sorted_results[0]
    print("\n" + "=" * 140)
    print("BEST PERFORMING COMBINATION")
    print("=" * 140)

    print(f"\n[BEST] OPTIMAL PARAMETERS:")
    print(f"   Position Limits:    ±{best['pos_osmium']} Osmium, ±{best['pos_pepper']} Pepper")
    print(f"   OSMIUM_EMA_ALPHA:   {best['ema_osmium']}")
    print(f"   PEPPER_EMA_ALPHA:   {best['ema_pepper']}")
    print(f"   OSMIUM_VWAP_WINDOW: {best['vwap_window']}")
    print(f"   OSMIUM_INVENTORY_BIAS: {best['inventory_bias']}")
    print(f"\n   Mean PnL:     {best['mean_pnl']:>15,.0f} XIRECs")
    print(f"   Success Rate: {best['success_rate']:>14.1f}% (all > 200k)")
    print(f"   Worst Case:   {best['min_pnl']:>15,.0f} XIRECs ({(best['min_pnl']/200000)*100:.1f}% of target)")
    print(f"   Consistency:  {best['cv']:>15.4f} (CoV)")

    # Comparison to Phase 2
    phase2_result = next((r for r in all_results
                         if r['pos_osmium'] == 80 and r['pos_pepper'] == 80 and
                            r['ema_osmium'] == 0.15 and r['vwap_window'] == 15 and
                            r['inventory_bias'] == 0.7 and r['ema_pepper'] == 0.3), None)

    if phase2_result and phase2_result != best:
        improvement = ((best['mean_pnl'] - phase2_result['mean_pnl']) / phase2_result['mean_pnl']) * 100
        print(f"\n[UP] vs Phase 2 Optimal (80/80, 0.15/0.3, window=15, bias=0.7):")
        print(f"   Improvement: +{improvement:.1f}%")
        print(f"   Gain: {best['mean_pnl'] - phase2_result['mean_pnl']:>15,.0f} XIRECs")

    print("\n" + "=" * 140)
    print(f"Test Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 140 + "\n")

    return sorted_results


def main():
    parser = argparse.ArgumentParser(
        description="Parameter grid search with 100 loop iterations"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Full grid: all parameter combinations (SLOW - many hours)"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Quick grid: test core Phase 2 params only (for speed)"
    )
    parser.add_argument(
        "--test-ema", action="store_true",
        help="Test only EMA Alpha variations"
    )
    parser.add_argument(
        "--test-vwap", action="store_true",
        help="Test only VWAP Window variations"
    )
    parser.add_argument(
        "--test-inventory", action="store_true",
        help="Test only Inventory Bias variations"
    )
    parser.add_argument(
        "--test-combo", nargs=5, type=float, metavar=("OS_POS", "PP_POS", "EMA_OSM", "VWAP", "INV_BIAS"),
        help="Test one specific combination"
    )
    parser.add_argument(
        "--iterations", type=int, default=100,
        help="Iterations per combination (default: 100)"
    )

    args = parser.parse_args()

    if args.test_combo:
        os_pos, pp_pos, ema_osm, vwap, inv_bias = args.test_combo
        print(f"\nTesting single combination: {os_pos}/{pp_pos}, EMA={ema_osm}/{0.3}, VWAP={int(vwap)}, InvBias={inv_bias}")
        result = run_parameter_combination(
            int(os_pos), int(pp_pos), ema_osm, int(vwap), inv_bias, 0.3,
            iterations=args.iterations
        )
        restore_trader_py()
        print(f"\nResult: Mean PnL = {result['mean_pnl']:,.0f}, Success = {result['success_rate']:.1f}%")
    elif args.full:
        run_grid_search(test_type="full", iterations=args.iterations)
    elif args.test_ema:
        run_grid_search(test_type="ema", iterations=args.iterations)
    elif args.test_vwap:
        run_grid_search(test_type="vwap", iterations=args.iterations)
    elif args.test_inventory:
        run_grid_search(test_type="inventory", iterations=args.iterations)
    else:
        # Default: quick grid
        run_grid_search(test_type="quick", iterations=args.iterations)


if __name__ == "__main__":
    main()
