"""Full backtest using ROUND1 complete dataset"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd().parent.parent / "analysis"))

import pandas as pd
import json
from trader import Trader, TradingState, OrderDepth, Trade, Listing, Observation
from order_matcher import OrderMatcher
import numpy as np

def load_round1_data():
    """Load all ROUND1 data (days -2, -1, 0)"""
    trades_list = []
    prices_list = []

    for day in [-2, -1, 0]:
        # Load trades (semicolon-delimited)
        trades_file = f"data/ROUND1/trades_round_1_day_{day}.csv"
        trades_df = pd.read_csv(trades_file, sep=';')
        trades_df['day'] = day
        trades_list.append(trades_df)

        # Load prices (semicolon-delimited)
        prices_file = f"data/ROUND1/prices_round_1_day_{day}.csv"
        prices_df = pd.read_csv(prices_file, sep=';')
        # day column already in prices_df
        prices_list.append(prices_df)

    trades_df = pd.concat(trades_list, ignore_index=True)
    prices_df = pd.concat(prices_list, ignore_index=True)

    return trades_df, prices_df

def get_order_depth_for_timestamp(prices_df, day, timestamp, symbol):
    """Get order depth snapshot at specific timestamp"""
    # Note: prices uses 'product' column for symbol
    mask = (prices_df['day'] == day) & (prices_df['timestamp'] == timestamp) & (prices_df['product'] == symbol)
    row = prices_df[mask]

    if row.empty:
        return None

    row = row.iloc[0]
    order_depth = OrderDepth()

    # Buy orders (bid side)
    for i in range(1, 4):
        col = f'bid_price_{i}'
        vol_col = f'bid_volume_{i}'
        if col in row.index and pd.notna(row[col]):
            try:
                order_depth.buy_orders[int(row[col])] = int(row[vol_col])
            except:
                pass

    # Sell orders (ask side)
    for i in range(1, 4):
        col = f'ask_price_{i}'
        vol_col = f'ask_volume_{i}'
        if col in row.index and pd.notna(row[col]):
            try:
                order_depth.sell_orders[int(row[col])] = -int(row[vol_col])
            except:
                pass

    return order_depth if (order_depth.buy_orders or order_depth.sell_orders) else None

def run_backtest_on_round1(trader_class, config_overrides=None):
    """Run backtest on full ROUND1 dataset"""
    trades_df, prices_df = load_round1_data()
    trades_sorted = trades_df.sort_values(['day', 'timestamp']).reset_index(drop=True)

    print(f"  Loaded {len(trades_sorted)} trades across ROUND1")

    trader = trader_class()

    # Apply config overrides if provided
    if config_overrides:
        for key, value in config_overrides.items():
            setattr(trader, key, value)

    state_data = {}
    positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
    balance = 100000
    matcher = OrderMatcher(match_mode="all")

    trade_count = 0

    for idx, trade_row in trades_sorted.iterrows():
        symbol = trade_row["symbol"]
        price, qty, timestamp, day = int(trade_row["price"]), int(trade_row["quantity"]), int(trade_row["timestamp"]), int(trade_row["day"])

        order_depth_data = get_order_depth_for_timestamp(prices_df, day, timestamp, symbol)

        if order_depth_data:
            order_depth = order_depth_data
            state = TradingState(
                json.dumps(state_data), timestamp,
                {symbol: Listing(symbol, symbol, "XIREC")},
                {symbol: order_depth},
                {symbol: []},
                {symbol: [Trade(symbol, price, qty)]},
                positions.copy(),
                Observation({}, {})
            )

            result, _, traderData = trader.run(state)
            state_data = json.loads(traderData)

            for order in result.get(symbol, []):
                match_result = matcher.match_order(
                    order, order_depth,
                    [Trade(symbol, price, qty, timestamp=timestamp)],
                    positions[symbol],
                    trader.POSITION_LIMITS[symbol]
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

        if (idx + 1) % 500 == 0:
            print(f"    {idx + 1}/{len(trades_sorted)} trades processed...")

    return balance - 100000, trade_count, positions

# Test all versions
print("=" * 120)
print("FULL ROUND1 BACKTEST: Comparing All Trader Versions")
print("=" * 120)
print()

results = []

configs = [
    ("Sean Baseline (pos=20, spread=5)", None),
    ("SPREAD_4 (pos=20, spread=4)", {"OSMIUM_SPREAD": 4}),
    ("COMBO_60_4 (pos=60, spread=4)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 60, "INTARIAN_PEPPER_ROOT": 60},
        "OSMIUM_SPREAD": 4
    }),
    ("Optimized (pos=60, sp=4, pskew=0.25)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 60, "INTARIAN_PEPPER_ROOT": 60},
        "OSMIUM_SPREAD": 4,
        "PEPPER_SKEW_FACTOR": 0.25
    }),
    ("Ultimate (pos=60, sp=4, th=10, pskew=0.225)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 60, "INTARIAN_PEPPER_ROOT": 60},
        "OSMIUM_SPREAD": 4,
        "PEPPER_LARGE_ORDER_THRESHOLD": 10,
        "PEPPER_SKEW_FACTOR": 0.225
    }),
    ("Conservative Pepper (pos=60, sp=4, pskew=0.28)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 60, "INTARIAN_PEPPER_ROOT": 60},
        "OSMIUM_SPREAD": 4,
        "PEPPER_SKEW_FACTOR": 0.28
    }),
]

for name, overrides in configs:
    print(f"Testing: {name}")
    try:
        profit, trades, positions = run_backtest_on_round1(Trader, overrides)
        results.append((name, profit, trades, overrides or {}))
        print(f"  Result: ${profit:,.2f} profit from {trades} trades")
        print()
    except Exception as e:
        print(f"  ERROR: {str(e)[:100]}")
        print()

results.sort(key=lambda x: x[1], reverse=True)

print("=" * 120)
print("RANKINGS (Full ROUND1 Dataset):")
print("=" * 120)
print(f"{'Rank':<5} {'Configuration':<45} {'Profit':<15} {'vs Sean':<15} {'vs Best':<15}")
print("-" * 120)

baseline = results[-1][1] if results else 0
best = results[0][1] if results else 0

for i, (name, profit, trades, config) in enumerate(results):
    vs_sean = profit - results[-1][1]
    vs_best = profit - best
    vs_sean_pct = (vs_sean / results[-1][1] * 100) if results[-1][1] != 0 else 0
    vs_best_pct = (vs_best / best * 100) if best != 0 else 0

    print(f"{i+1:<5} {name:<45} ${profit:>13,.2f} {vs_sean:>+13,.2f} {vs_best:>+13,.2f}")

print("\n" + "=" * 120)
print("ANALYSIS:")
print("=" * 120)
print(f"Best Config: {results[0][0]}")
print(f"Best Profit: ${results[0][1]:,.2f}")
print(f"Sean's Profit: ${results[-1][1]:,.2f}")
if results[0][1] > results[-1][1]:
    print(f"Winner: OPTIMIZED (beat Sean by ${results[0][1] - results[-1][1]:,.2f})")
else:
    print(f"Winner: SEAN (beat optimized by ${results[-1][1] - results[0][1]:,.2f})")
