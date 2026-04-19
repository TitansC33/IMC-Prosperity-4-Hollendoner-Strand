"""
Find Robust Configuration: Grid Search with Day-by-Day Validation
==================================================================

Tests multiple parameter combinations and ranks them by:
1. Consistency across days (low variance = good)
2. Profit on early days (Days -2, -1)
3. Overall performance

Goal: Find parameters that DON'T lose on Days -2 and -1
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import pandas as pd
import json
import importlib.util
from trader import Trader, TradingState, OrderDepth, Trade, Listing, Observation
from order_matcher import OrderMatcher

# Load seanTrader
spec = importlib.util.spec_from_file_location("seanTrader", Path(__file__).parent / "seanTrader.py")
seanTrader_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seanTrader_module)
SeanTrader = seanTrader_module.Trader


def load_round1_data():
    """Load all ROUND1 data"""
    trades_list, prices_list = [], []
    data_dir = Path(__file__).parent.parent.parent / "data" / "ROUND1"
    for day in [-2, -1, 0]:
        trades_df = pd.read_csv(data_dir / f"trades_round_1_day_{day}.csv", sep=';')
        trades_df['day'] = day
        trades_list.append(trades_df)

        prices_df = pd.read_csv(data_dir / f"prices_round_1_day_{day}.csv", sep=';')
        prices_list.append(prices_df)

    return pd.concat(trades_list, ignore_index=True), pd.concat(prices_list, ignore_index=True)


def get_order_depth_at_timestamp(prices_df, day, timestamp, symbol):
    """Get order depth at specific timestamp"""
    mask = (prices_df['day'] == day) & (prices_df['timestamp'] == timestamp) & (prices_df['product'] == symbol)
    row = prices_df[mask]
    if row.empty:
        return None

    row = row.iloc[0]
    order_depth = OrderDepth()

    for i in range(1, 4):
        if f'bid_price_{i}' in row.index and pd.notna(row[f'bid_price_{i}']):
            try:
                order_depth.buy_orders[int(row[f'bid_price_{i}'])] = int(row[f'bid_volume_{i}'])
            except:
                pass
        if f'ask_price_{i}' in row.index and pd.notna(row[f'ask_price_{i}']):
            try:
                order_depth.sell_orders[int(row[f'ask_price_{i}'])] = -int(row[f'ask_volume_{i}'])
            except:
                pass

    return order_depth if (order_depth.buy_orders or order_depth.sell_orders) else None


def run_backtest_for_day(trader_class, day, config_overrides=None):
    """Run backtest for ONE specific day"""
    all_trades_df, all_prices_df = load_round1_data()

    trades_df = all_trades_df[all_trades_df['day'] == day].copy()
    prices_df = all_prices_df[all_prices_df['day'] == day].copy()

    if trader_class == SeanTrader:
        trader = SeanTrader()
    else:
        trader = trader_class()
        trader.POSITION_LIMITS = {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20}
        trader.OSMIUM_SPREAD = 5
        trader.PEPPER_SKEW_FACTOR = 0.3
        trader.PEPPER_LARGE_ORDER_THRESHOLD = 18

    if config_overrides:
        for key, value in config_overrides.items():
            setattr(trader, key, value)

    trade_times = trades_df[['day', 'timestamp']].drop_duplicates().sort_values(['day', 'timestamp']).reset_index(drop=True)

    state_data = {}
    positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
    balance = 100000
    matcher = OrderMatcher(match_mode="all")

    trade_count = 0

    for idx, (day_val, timestamp) in enumerate(trade_times.values):
        trades_at_ts = trades_df[(trades_df['day'] == day_val) & (trades_df['timestamp'] == timestamp)]

        for symbol in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
            order_depth_data = get_order_depth_at_timestamp(prices_df, day_val, timestamp, symbol)
            if not order_depth_data:
                continue

            symbol_trades = trades_at_ts[trades_at_ts['symbol'] == symbol]
            market_trades_list = [
                Trade(symbol, int(row['price']), int(row['quantity']))
                for _, row in symbol_trades.iterrows()
            ]

            state = TradingState(
                json.dumps(state_data),
                timestamp,
                {symbol: Listing(symbol, symbol, "XIREC")},
                {symbol: order_depth_data},
                {symbol: []},
                {symbol: market_trades_list},
                positions.copy(),
                Observation({}, {})
            )

            result, _, traderData = trader.run(state)
            state_data = json.loads(traderData)

            for order in result.get(symbol, []):
                match_result = matcher.match_order(
                    order, order_depth_data, market_trades_list,
                    positions[symbol], trader.POSITION_LIMITS[symbol]
                )
                if match_result.filled > 0:
                    is_buy = order.quantity > 0
                    if is_buy:
                        positions[symbol] += match_result.filled
                        balance -= match_result.filled * match_result.fill_price
                    else:
                        positions[symbol] -= match_result.filled
                        balance += match_result.filled * match_result.fill_price
                    trade_count += 1

    return balance - 100000, trade_count


# ==============================================================================
# GRID SEARCH: Test multiple configurations
# ==============================================================================

print("=" * 130)
print("FINDING ROBUST CONFIGURATION: Grid Search with Day-by-Day Validation")
print("=" * 130 + "\n")

# Test configurations - targeting fixes for Days -2, -1
configs = [
    # Baseline (current)
    ("Baseline (pos=20, sp=5, pskew=0.3)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20},
        "OSMIUM_SPREAD": 5,
        "PEPPER_SKEW_FACTOR": 0.3
    }),

    # Smaller positions (less aggressive)
    ("Conservative (pos=10, sp=5)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 10, "INTARIAN_PEPPER_ROOT": 10},
        "OSMIUM_SPREAD": 5,
        "PEPPER_SKEW_FACTOR": 0.3
    }),

    # Tighter spreads (more competitive)
    ("Tight Spread (pos=20, sp=3)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20},
        "OSMIUM_SPREAD": 3,
        "PEPPER_SKEW_FACTOR": 0.3
    }),

    # Lower skew (less aggressive inventory management)
    ("Lower Skew (pos=20, sp=5, pskew=0.15)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20},
        "OSMIUM_SPREAD": 5,
        "PEPPER_SKEW_FACTOR": 0.15
    }),

    # Combination: Conservative + Tight Spread
    ("Conservative Tight (pos=10, sp=3)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 10, "INTARIAN_PEPPER_ROOT": 10},
        "OSMIUM_SPREAD": 3,
        "PEPPER_SKEW_FACTOR": 0.3
    }),

    # Combination: Conservative + Lower Skew
    ("Conservative Low-Skew (pos=10, sp=5, pskew=0.15)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 10, "INTARIAN_PEPPER_ROOT": 10},
        "OSMIUM_SPREAD": 5,
        "PEPPER_SKEW_FACTOR": 0.15
    }),

    # Very tight spread + small position
    ("Ultra Conservative (pos=10, sp=2, pskew=0.1)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 10, "INTARIAN_PEPPER_ROOT": 10},
        "OSMIUM_SPREAD": 2,
        "PEPPER_SKEW_FACTOR": 0.1
    }),

    # Larger threshold (less aggressive order detection)
    ("Higher Threshold (pos=20, sp=5, th=25)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20},
        "OSMIUM_SPREAD": 5,
        "PEPPER_LARGE_ORDER_THRESHOLD": 25,
        "PEPPER_SKEW_FACTOR": 0.3
    }),
]

results = []

print(f"{'Config':<35} {'Day -2':>12} {'Day -1':>12} {'Day 0':>12} {'Avg':>12} {'Variance':>12} {'Wins':>6}")
print("-" * 130)

for config_name, overrides in configs:
    # Test each day
    d2_profit, _ = run_backtest_for_day(Trader, -2, overrides)
    d1_profit, _ = run_backtest_for_day(Trader, -1, overrides)
    d0_profit, _ = run_backtest_for_day(Trader, 0, overrides)

    profits = [d2_profit, d1_profit, d0_profit]
    avg = sum(profits) / len(profits)
    variance = max(profits) - min(profits)

    # Count winning days
    wins = sum(1 for p in profits if p > 0)

    results.append({
        "name": config_name,
        "day_-2": d2_profit,
        "day_-1": d1_profit,
        "day_0": d0_profit,
        "avg": avg,
        "variance": variance,
        "wins": wins,
        "overrides": overrides
    })

    print(f"{config_name:<35} ${d2_profit:>10,.0f} ${d1_profit:>10,.0f} ${d0_profit:>10,.0f} ${avg:>10,.0f} ${variance:>10,.0f} {wins:>5}/3")

# ==============================================================================
# RANKINGS
# ==============================================================================

print("\n" + "=" * 130)
print("RANKED BY ROBUSTNESS SCORE (wins * avg - variance penalty)")
print("=" * 130 + "\n")

# Score: higher wins, higher avg, lower variance
for r in results:
    r["score"] = (r["wins"] * 50000) + r["avg"] - (r["variance"] * 0.1)

results.sort(key=lambda x: x["score"], reverse=True)

print(f"{'Rank':<5} {'Config':<35} {'Score':>12} {'Wins':>6} {'Avg':>12} {'Variance':>12}")
print("-" * 130)

for i, r in enumerate(results, 1):
    print(f"{i:<5} {r['name']:<35} {r['score']:>10,.0f} {r['wins']:>5}/3 ${r['avg']:>10,.0f} ${r['variance']:>10,.0f}")

# ==============================================================================
# BEST CONFIG DETAILS
# ==============================================================================

best = results[0]

print("\n" + "=" * 130)
print("BEST CONFIGURATION (Highest Robustness Score)")
print("=" * 130 + "\n")

print(f"Name: {best['name']}")
print(f"Score: {best['score']:,.0f}")
print()

print("Day-by-Day Breakdown:")
print(f"  Day -2: ${best['day_-2']:>10,.0f}")
print(f"  Day -1: ${best['day_-1']:>10,.0f}")
print(f"  Day 0:  ${best['day_0']:>10,.0f}")
print(f"  Average: ${best['avg']:>10,.0f}")
print(f"  Variance: ${best['variance']:>10,.0f}")
print(f"  Wins: {best['wins']}/3 days profitable")
print()

print("Parameters to use in backtest_hybrid.py:")
print()
print("  (Trader, \"" + best['name'] + "\", {")
for key, value in best['overrides'].items():
    if isinstance(value, dict):
        print(f"      \"{key}\": {value},")
    else:
        print(f"      \"{key}\": {value},")
print("  }),")
print()

# ==============================================================================
# COMPARISON vs BASELINE
# ==============================================================================

baseline = [r for r in results if "Baseline" in r['name']][0]
improvement = best['avg'] - baseline['avg']
improvement_pct = (improvement / baseline['avg'] * 100) if baseline['avg'] != 0 else 0

print("=" * 130)
print("COMPARISON vs BASELINE")
print("=" * 130)
print()

print(f"Baseline (current):")
print(f"  Day -2: ${baseline['day_-2']:>10,.0f} (LOSS)")
print(f"  Day -1: ${baseline['day_-1']:>10,.0f} (LOSS)")
print(f"  Day 0:  ${baseline['day_0']:>10,.0f} (PROFIT)")
print(f"  Average: ${baseline['avg']:>10,.0f}")
print()

print(f"Best Found:")
print(f"  Day -2: ${best['day_-2']:>10,.0f} {'(BETTER!)' if best['day_-2'] > baseline['day_-2'] else '(worse)'}")
print(f"  Day -1: ${best['day_-1']:>10,.0f} {'(BETTER!)' if best['day_-1'] > baseline['day_-1'] else '(worse)'}")
print(f"  Day 0:  ${best['day_0']:>10,.0f} {'(BETTER!)' if best['day_0'] > baseline['day_0'] else '(worse)'}")
print(f"  Average: ${best['avg']:>10,.0f}")
print()

if improvement > 0:
    print(f"Improvement: +${improvement:,.0f} ({improvement_pct:+.1f}%)")
    print("Status: [BETTER] New config improved on baseline")
elif improvement == 0:
    print("No improvement from baseline")
else:
    print(f"Decrease: ${improvement:,.0f} ({improvement_pct:+.1f}%)")
    print("Status: [WORSE] New config underperforms baseline")

print()
print("=" * 130)
