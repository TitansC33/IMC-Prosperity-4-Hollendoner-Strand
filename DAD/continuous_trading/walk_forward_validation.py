"""
Walk-Forward Validation: Proper Time Order
===========================================

Tests if parameters learned on past days actually work on future days.
This simulates real trading: you develop on old data, then deploy on new data.

Walk-Forward Schedule:
1. Develop on Day -2 → Deploy on Day -1 (can parameters learned on Day -2 work on Day -1?)
2. Develop on Day -2, -1 → Deploy on Day 0 (parameters from first 2 days work on final day?)
3. Full training on all 3 days (simulates knowing the future - unrealistic but shows ceiling)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

import pandas as pd
import json
import importlib.util
from trader import Trader, TradingState, OrderDepth, Trade, Listing, Observation
from order_matcher import OrderMatcher

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


# Configurations to test
baseline_config = {
    "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20},
    "OSMIUM_SPREAD": 5,
    "PEPPER_SKEW_FACTOR": 0.3
}

ultra_conservative_config = {
    "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 10, "INTARIAN_PEPPER_ROOT": 10},
    "OSMIUM_SPREAD": 2,
    "PEPPER_SKEW_FACTOR": 0.1
}

print("=" * 130)
print("WALK-FORWARD VALIDATION: Proper Time Order Testing")
print("=" * 130)
print()

# ==============================================================================
# Test 1: Day -2 Only (Development Set)
# ==============================================================================
print("PHASE 1: DEVELOPMENT (Day -2 only)")
print("-" * 130)
print("This is what you 'know' about the market after the first day\n")

d2_baseline, _ = run_backtest_for_days(Trader, [-2], baseline_config)
d2_ultra, _ = run_backtest_for_days(Trader, [-2], ultra_conservative_config)

print(f"Day -2 Results (training data):")
print(f"  Baseline:          ${d2_baseline:>10,.0f}")
print(f"  Ultra Conservative: ${d2_ultra:>10,.0f}")
print()

# ==============================================================================
# Test 2: Day -1 (Test Set - deployed parameters from Day -2)
# ==============================================================================
print("PHASE 2: DEPLOYMENT ON DAY -1")
print("-" * 130)
print("You learned parameters on Day -2, now deploy on Day -1 (new data)\n")

d1_baseline, _ = run_backtest_for_days(Trader, [-1], baseline_config)
d1_ultra, _ = run_backtest_for_days(Trader, [-1], ultra_conservative_config)

print(f"Day -1 Results (test set - new market):")
print(f"  Baseline:          ${d1_baseline:>10,.0f}")
print(f"  Ultra Conservative: ${d1_ultra:>10,.0f}")
print()

d2_to_d1_baseline_delta = d1_baseline - d2_baseline
d2_to_d1_ultra_delta = d1_ultra - d2_ultra

print(f"Parameter Transfer (Day -2 -> Day -1):")
print(f"  Baseline delta:            ${d2_to_d1_baseline_delta:>+10,.0f}")
print(f"  Ultra Conservative delta:  ${d2_to_d1_ultra_delta:>+10,.0f}")
print()

if abs(d2_to_d1_ultra_delta) < abs(d2_to_d1_baseline_delta):
    print("  [BETTER] Ultra Conservative parameters transfer better to Day -1")
else:
    print("  [WORSE] Ultra Conservative has larger performance drop")
print()

# ==============================================================================
# Test 3: Days -2, -1 (Development) -> Day 0 (Test)
# ==============================================================================
print("PHASE 3: EXTENDED DEVELOPMENT -> FINAL TEST")
print("-" * 130)
print("Using Days -2, -1 as training, deploy on Day 0 (final unknown day)\n")

d2d1_baseline, _ = run_backtest_for_days(Trader, [-2, -1], baseline_config)
d2d1_ultra, _ = run_backtest_for_days(Trader, [-2, -1], ultra_conservative_config)

d0_baseline, _ = run_backtest_for_days(Trader, [0], baseline_config)
d0_ultra, _ = run_backtest_for_days(Trader, [0], ultra_conservative_config)

print(f"Days -2, -1 (training):")
print(f"  Baseline:          ${d2d1_baseline:>10,.0f}")
print(f"  Ultra Conservative: ${d2d1_ultra:>10,.0f}")
print()

print(f"Day 0 (test set - completely new day):")
print(f"  Baseline:          ${d0_baseline:>10,.0f}")
print(f"  Ultra Conservative: ${d0_ultra:>10,.0f}")
print()

d2d1_to_d0_baseline_delta = d0_baseline - (d2d1_baseline / 2)
d2d1_to_d0_ultra_delta = d0_ultra - (d2d1_ultra / 2)

print(f"Parameter Transfer (Days -2,-1 -> Day 0):")
print(f"  Baseline delta:            ${d2d1_to_d0_baseline_delta:>+10,.0f}")
print(f"  Ultra Conservative delta:  ${d2d1_to_d0_ultra_delta:>+10,.0f}")
print()

# ==============================================================================
# Overall Walk-Forward Score
# ==============================================================================
print("=" * 130)
print("WALK-FORWARD VALIDATION RESULTS")
print("=" * 130)
print()

# Sequential testing: Dev -> Test -> Test
print("Sequential Profitability:")
print(f"  Day -2 (development):    Baseline: ${d2_baseline:>10,.0f}  |  Ultra: ${d2_ultra:>10,.0f}")
print(f"  Day -1 (test):           Baseline: ${d1_baseline:>10,.0f}  |  Ultra: ${d1_ultra:>10,.0f}")
print(f"  Day 0 (test):            Baseline: ${d0_baseline:>10,.0f}  |  Ultra: ${d0_ultra:>10,.0f}")
print()

total_baseline = d2_baseline + d1_baseline + d0_baseline
total_ultra = d2_ultra + d1_ultra + d0_ultra

print(f"Total Over 3 Days:")
print(f"  Baseline:          ${total_baseline:>10,.0f}")
print(f"  Ultra Conservative: ${total_ultra:>10,.0f}")
print()

print(f"Parameter Consistency Score:")
baseline_consistency = abs(d2_to_d1_baseline_delta) + abs(d2d1_to_d0_baseline_delta)
ultra_consistency = abs(d2_to_d1_ultra_delta) + abs(d2d1_to_d0_ultra_delta)

print(f"  Baseline (lower is better):           {baseline_consistency:>10,.0f}")
print(f"  Ultra Conservative (lower is better):  {ultra_consistency:>10,.0f}")
print()

if ultra_consistency < baseline_consistency:
    print("  [BETTER] Ultra Conservative is more consistent across days")
    improvement_pct = ((baseline_consistency - ultra_consistency) / baseline_consistency * 100)
    print(f"           {improvement_pct:.1f}% better consistency")
else:
    print("  [WORSE] Ultra Conservative is less consistent than baseline")
    worse_pct = ((ultra_consistency - baseline_consistency) / baseline_consistency * 100)
    print(f"         {worse_pct:.1f}% worse consistency")

print()
print("=" * 130)
print("CONCLUSION")
print("=" * 130)
print()

if ultra_consistency < baseline_consistency:
    print("[PASS] Ultra Conservative generalizes better to unseen days")
    print("       Parameters learned on Day -2 carry over to Day -1 more smoothly")
    print("       Better for real-world deployment where you can't retrain daily")
else:
    print("[FAIL] Ultra Conservative doesn't generalize well")
    print("       Parameters learned on Day -2 don't work well on Day -1")
    print("       Would need daily retraining for deployment")

print()
print(f"Expected Live Performance:")
print(f"  Baseline:          ~${(total_baseline / 3 / 100):.0f}-${(total_baseline / 3 * 2 / 100):.0f}")
print(f"  Ultra Conservative: ~${(total_ultra / 3 / 100):.0f}-${(total_ultra / 3 * 2 / 100):.0f}")
print("  (Assuming 50-100x scaling down from backtest)")

print()
