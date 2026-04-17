"""
Grid Search with Realistic Order Matching

Validates Phase 2 optimal parameters against realistic order matching.
Tests if position limit configurations remain optimal when using real fills.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root / "analysis"))

from load_data import load_all_trades, load_all_prices
from backtest_v2_with_matching import simulate_portfolio_with_matching


def run_grid_search():
    """
    Test multiple position limit configurations with realistic order matching.
    Validates that Phase 2 optimal parameters remain optimal with real fills.
    """

    print("=" * 100)
    print("GRID SEARCH: POSITION LIMIT OPTIMIZATION WITH REALISTIC ORDER MATCHING")
    print("=" * 100)
    print("\nPhase 2 identified ±80 as optimal position limit.")
    print("This grid search validates whether that holds with realistic order matching.\n")

    # Load data
    trades_df = load_all_trades()
    prices_df = load_all_prices()

    print(f"Data loaded: {len(trades_df)} trades, {len(prices_df)} price snapshots\n")

    # Test configurations - comprehensive grid
    configs = [
        # Symmetrical limits
        {"osmium_pos_limit": 40, "pepper_pos_limit": 40, "name": "Conservative (40/40)"},
        {"osmium_pos_limit": 50, "pepper_pos_limit": 50, "name": "Moderate-Cons (50/50)"},
        {"osmium_pos_limit": 60, "pepper_pos_limit": 60, "name": "Moderate (60/60)"},
        {"osmium_pos_limit": 70, "pepper_pos_limit": 70, "name": "Moderate-Agg (70/70)"},
        {"osmium_pos_limit": 80, "pepper_pos_limit": 80, "name": "Aggressive (80/80)"},
        {"osmium_pos_limit": 90, "pepper_pos_limit": 90, "name": "Very Aggressive (90/90)"},

        # Asymmetrical - Osmium higher
        {"osmium_pos_limit": 80, "pepper_pos_limit": 40, "name": "Osmium Agg, Pepper Cons (80/40)"},
        {"osmium_pos_limit": 80, "pepper_pos_limit": 60, "name": "Mixed: Osmium Agg, Pepper Mod (80/60)"},

        # Asymmetrical - Pepper higher
        {"osmium_pos_limit": 40, "pepper_pos_limit": 80, "name": "Osmium Cons, Pepper Agg (40/80)"},
        {"osmium_pos_limit": 60, "pepper_pos_limit": 80, "name": "Mixed: Osmium Mod, Pepper Agg (60/80)"},
    ]

    results = []

    print(f"Testing {len(configs)} configurations...\n")
    print(f"{'Config':<40} {'Portfolio Value':>18} {'Target %':>10}")
    print("-" * 70)

    for i, config in enumerate(configs, 1):
        name = config.pop("name")
        config["initial_balance"] = 100000

        result = simulate_portfolio_with_matching(
            trades_df, prices_df, config, match_mode="all"
        )
        result["name"] = name

        # Calculate target progress
        target_progress = (result["final_portfolio_value"] / 200000) * 100

        print(f"{name:<40} {result['final_portfolio_value']:>18,.0f} {target_progress:>9.1f}%")

        results.append(result)

    # Summary and analysis
    print("\n" + "=" * 100)
    print("ANALYSIS: RANKED BY FINAL PORTFOLIO VALUE")
    print("=" * 100 + "\n")

    results_sorted = sorted(results, key=lambda x: x["final_portfolio_value"], reverse=True)

    for rank, result in enumerate(results_sorted, 1):
        target_progress = (result["final_portfolio_value"] / 200000) * 100
        osmium_pos = result['final_positions']['ASH_COATED_OSMIUM']
        pepper_pos = result['final_positions']['INTARIAN_PEPPER_ROOT']

        print(f"{rank:2d}. {result['name']:<40}")
        print(f"    Portfolio Value: {result['final_portfolio_value']:>15,.0f} ({target_progress:>6.1f}% of target)")
        print(f"    Final Positions: Osmium={osmium_pos:>4}, Pepper={pepper_pos:>4}")
        print(f"    Trades Executed: {result['num_trades']:>6}")
        print()

    # Key findings
    print("=" * 100)
    print("KEY FINDINGS")
    print("=" * 100)

    best = results_sorted[0]
    print(f"\nOptimal Configuration with Realistic Matching:")
    print(f"  {best['name']}")
    print(f"  Portfolio Value: {best['final_portfolio_value']:,.0f} XIRECs")
    print(f"  Target Achievement: {(best['final_portfolio_value'] / 200000) * 100:.1f}%")

    # Phase 2 comparison
    phase2_optimal = "Aggressive (80/80)"
    phase2_result = next((r for r in results if r['name'] == phase2_optimal), None)

    if phase2_result:
        print(f"\nPhase 2 Optimal Parameter (±80/±80):")
        print(f"  Portfolio Value: {phase2_result['final_portfolio_value']:,.0f} XIRECs")
        print(f"  Rank: #{results_sorted.index(phase2_result) + 1} of {len(results)}")
        print(f"  Status: {'STILL OPTIMAL' if phase2_result == best else 'REPLACED BY BETTER CONFIG'}")

    # Validation
    print("\n" + "=" * 100)
    print("VALIDATION CHECKLIST")
    print("=" * 100)

    checks = [
        ("Phase 2 config in top 3", results_sorted.index(phase2_result) < 3 if phase2_result else False),
        ("All configs exceed 200k target", all(r["final_portfolio_value"] >= 200000 for r in results)),
        ("Grid search completed successfully", len(results) == len(configs)),
    ]

    for check, result in checks:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check}")

    all_pass = all(result for _, result in checks)

    print("\n" + "=" * 100)
    if all_pass:
        print("[PASS] GRID SEARCH VALIDATION PASSED")
        if phase2_result and phase2_result == best:
            print("       Phase 2 parameters remain optimal with realistic order matching.")
            print("       Ready to deploy for competition.")
        else:
            print("       New optimal configuration found! Review and consider adopting.")
    else:
        print("[WARN] GRID SEARCH VALIDATION FAILED")
        print("       Review fill rates, position limits, or matching logic.")
    print("=" * 100 + "\n")

    return results_sorted


if __name__ == "__main__":
    results = run_grid_search()
