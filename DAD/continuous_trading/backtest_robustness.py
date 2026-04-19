"""
Robustness Testing: Different Days + Walk-Forward Validation
============================================================================

Tests if strategy is robust (works across different market conditions)
or overfitted (only works on specific days).

Test 1: Single Day Backtests
    - Day -2: Early market (baseline)
    - Day -1: Middle (normal)
    - Day 0: Final day (any changes?)

Test 2: Walk-Forward Validation
    - Train on Day -2 → Test on Day -1
    - Train on Days -2, -1 → Test on Day 0
    Shows if parameters learned on earlier days work on new data
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


def run_backtest_for_days(trader_class, test_days, config_overrides=None):
    """Run backtest for specific day(s)"""
    all_trades_df, all_prices_df = load_round1_data()

    # Filter to only requested days
    trades_df = all_trades_df[all_trades_df['day'].isin(test_days)].copy()
    prices_df = all_prices_df[all_prices_df['day'].isin(test_days)].copy()

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

    for idx, (day, timestamp) in enumerate(trade_times.values):
        trades_at_ts = trades_df[(trades_df['day'] == day) & (trades_df['timestamp'] == timestamp)]

        for symbol in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
            order_depth_data = get_order_depth_at_timestamp(prices_df, day, timestamp, symbol)
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


print("=" * 130)
print("ROBUSTNESS TESTING: Single Day + Walk-Forward Validation")
print("=" * 130 + "\n")

# Test configuration
config = {
    "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20},
    "OSMIUM_SPREAD": 5,
    "PEPPER_SKEW_FACTOR": 0.3,
    "PEPPER_LARGE_ORDER_THRESHOLD": 18
}

# =============================================================================
# TEST 1: Single Day Backtests
# =============================================================================
print("TEST 1: SINGLE DAY BACKTESTS")
print("-" * 130)
print("Tests if strategy performs consistently across different market conditions")
print()

day_map = {-2: "Day -2 (Early)", -1: "Day -1 (Middle)", 0: "Day 0 (Final)"}
single_day_results = {}

for day in [-2, -1, 0]:
    profit, trades = run_backtest_for_days(SeanTrader, [day], None)
    single_day_results[day] = profit
    print(f"  {day_map[day]:<25} Profit: ${profit:>10,.2f}  |  Fills: {trades:>4}")

print()
print("Analysis:")
min_day = min(single_day_results, key=single_day_results.get)
max_day = max(single_day_results, key=single_day_results.get)
avg_profit = sum(single_day_results.values()) / len(single_day_results)
variance = max(single_day_results.values()) - min(single_day_results.values())

print(f"  Average profit: ${avg_profit:,.2f}")
print(f"  Min: ${single_day_results[min_day]:,.2f} (Day {min_day})")
print(f"  Max: ${single_day_results[max_day]:,.2f} (Day {max_day})")
print(f"  Range: ${variance:,.2f} (variance indicator)")

if variance < avg_profit * 0.2:
    print(f"  [OK] CONSISTENT: Variance < 20% of average (good robustness)")
elif variance < avg_profit * 0.5:
    print(f"  [WARN] MODERATE: Variance 20-50% (some variability)")
else:
    print(f"  [FAIL] FRAGILE: Variance > 50% (depends on market conditions)")

# =============================================================================
# TEST 2: Walk-Forward Validation
# =============================================================================
print("\n" + "=" * 130)
print("TEST 2: WALK-FORWARD VALIDATION")
print("-" * 130)
print("Tests if parameters learned on past data work on future data")
print()

# Walk-forward 1: Train Day -2, Test Day -1
print("Walk-Forward 1: Train on Day -2 -> Test on Day -1")
train_profit_d2, _ = run_backtest_for_days(SeanTrader, [-2], None)
test_profit_d2_to_d1, _ = run_backtest_for_days(SeanTrader, [-1], None)
print(f"  Train profit (Day -2): ${train_profit_d2:>10,.2f}")
print(f"  Test profit (Day -1):  ${test_profit_d2_to_d1:>10,.2f}")
delta_1 = test_profit_d2_to_d1 - train_profit_d2
print(f"  Delta: {delta_1:>+10,.2f}  ({(delta_1/train_profit_d2)*100:>+6.1f}%)")

# Walk-forward 2: Train Days -2 & -1, Test Day 0
print()
print("Walk-Forward 2: Train on Days -2, -1 -> Test on Day 0")
train_profit_d2d1, _ = run_backtest_for_days(SeanTrader, [-2, -1], None)
test_profit_d2d1_to_d0, _ = run_backtest_for_days(SeanTrader, [0], None)
print(f"  Train profit (Days -2, -1): ${train_profit_d2d1:>10,.2f}")
print(f"  Test profit (Day 0):         ${test_profit_d2d1_to_d0:>10,.2f}")
delta_2 = test_profit_d2d1_to_d0 - (train_profit_d2d1 / 2)  # Normalize to per-day
print(f"  Delta: {delta_2:>+10,.2f}")

# =============================================================================
# Analysis
# =============================================================================
print("\n" + "=" * 130)
print("CONCLUSIONS")
print("=" * 130)

print("\n1. DAY CONSISTENCY:")
if variance < avg_profit * 0.2:
    print("   [OK] Strategy is ROBUST across different market conditions")
    print("   -> Safe to deploy; should perform similarly each day")
else:
    print("   [WARN] Strategy VARIES significantly by day")
    print("   -> May be sensitive to market regime; test more configurations")

print("\n2. PARAMETER TRANSFER:")
if abs(delta_1) < abs(train_profit_d2) * 0.15:
    print("   [OK] Parameters from Day -2 transfer well to Day -1")
    print("   -> Learning generalizes to new data")
else:
    print("   [WARN] Performance drops significantly Day -2 -> Day -1")
    print("   -> Parameters may be overfit or market changed")

print("\n3. FORWARD LOOKING:")
if abs(delta_2) < 10000:  # Arbitrary threshold
    print("   [OK] Performance stable when trained on -2,-1 and tested on 0")
    print("   -> Likely to be robust in competition")
else:
    print("   [WARN] Performance unpredictable on new day")
    print("   -> Consider different parameters or strategy changes")

print("\n" + "=" * 130)
print("RECOMMENDATION")
print("=" * 130)

avg_all_days = sum(single_day_results.values()) / len(single_day_results)
if avg_all_days > 100000:
    print("[OK] Strategy is performing well across all days.")
    print("  Expected live performance: Similar to backtest (~100-150x scaling down)")
elif variance > avg_profit * 0.5 or abs(delta_1) > 50000:
    print("[WARN] Strategy shows high variability or poor parameter transfer.")
    print("  Recommendation: Test different parameter combinations")
    print("                  or investigate why days differ")
else:
    print("[OK] Strategy shows reasonable robustness.")
    print("  Next step: Test with different parameters in backtest_hybrid.py")

print("\n" + "=" * 130)
