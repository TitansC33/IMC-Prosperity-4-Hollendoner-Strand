"""CORRECT full backtest: process timestamps with both prices AND trades"""
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
        prices_list.append(prices_df)

    trades_df = pd.concat(trades_list, ignore_index=True)
    prices_df = pd.concat(prices_list, ignore_index=True)

    return trades_df, prices_df

def get_order_depth_at_timestamp(prices_df, day, timestamp, symbol):
    """Get order depth snapshot at specific day/timestamp"""
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

def run_backtest_on_round1_correct(trader_class, config_overrides=None):
    """Run CORRECT backtest: process timestamps with prices AND trades"""
    trades_df, prices_df = load_round1_data()

    print(f"  Loaded {len(trades_df)} trades and {len(prices_df)} price snapshots")

    trader = trader_class()

    # Apply config overrides if provided
    if config_overrides:
        for key, value in config_overrides.items():
            setattr(trader, key, value)

    # Get all unique (day, timestamp) pairs from prices (this is the correct time grid)
    time_grid = prices_df[['day', 'timestamp']].drop_duplicates().sort_values(['day', 'timestamp']).reset_index(drop=True)

    print(f"  Processing {len(time_grid)} timestamps")

    state_data = {}
    positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
    balance = 100000
    matcher = OrderMatcher(match_mode="all")

    trade_count = 0
    orders_count = 0

    for idx, (day, timestamp) in enumerate(time_grid.values):
        # Get trades at this timestamp
        trades_at_ts = trades_df[(trades_df['day'] == day) & (trades_df['timestamp'] == timestamp)]

        for symbol in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
            # Get order depth for this symbol at this timestamp
            order_depth_data = get_order_depth_at_timestamp(prices_df, day, timestamp, symbol)

            if order_depth_data:
                # Get market trades for this symbol at this timestamp
                symbol_trades = trades_at_ts[trades_at_ts['symbol'] == symbol]
                market_trades_list = [
                    Trade(symbol, int(row['price']), int(row['quantity']))
                    for _, row in symbol_trades.iterrows()
                ]

                # Build trading state
                state = TradingState(
                    json.dumps(state_data),
                    timestamp,
                    {symbol: Listing(symbol, symbol, "XIREC")},
                    {symbol: order_depth_data},
                    {symbol: []},
                    {symbol: market_trades_list},  # Pass ALL market trades at this timestamp
                    positions.copy(),
                    Observation({}, {})
                )

                # Run trader
                result, _, traderData = trader.run(state)
                state_data = json.loads(traderData)

                # Match trader's orders
                for order in result.get(symbol, []):
                    orders_count += 1

                    match_result = matcher.match_order(
                        order,
                        order_depth_data,
                        market_trades_list,
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

        if (idx + 1) % 200 == 0:
            print(f"    {idx + 1}/{len(time_grid)} timestamps processed...")

    return balance - 100000, trade_count, orders_count, positions

# Test all versions
print("=" * 140)
print("CORRECT FULL ROUND1 BACKTEST: Process timestamps with both prices AND trades")
print("=" * 140)
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
    ("Conservative Pepper (pos=60, sp=4, pskew=0.28)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 60, "INTARIAN_PEPPER_ROOT": 60},
        "OSMIUM_SPREAD": 4,
        "PEPPER_SKEW_FACTOR": 0.28
    }),
]

for name, overrides in configs:
    print(f"Testing: {name}")
    try:
        profit, trades, orders, positions = run_backtest_on_round1_correct(Trader, overrides)
        results.append((name, profit, trades, orders, overrides or {}))
        print(f"  Result: ${profit:,.2f} profit | {trades} fills | {orders} orders placed")
        print()
    except Exception as e:
        import traceback
        print(f"  ERROR: {str(e)}")
        traceback.print_exc()
        print()

results.sort(key=lambda x: x[1], reverse=True)

print("=" * 140)
print("RANKINGS (Correct Full ROUND1 Backtest - Timestamps + Prices + Trades):")
print("=" * 140)
print(f"{'Rank':<5} {'Configuration':<50} {'Profit':<15} {'Fills':<10} {'Orders':<10} {'vs Best':<15}")
print("-" * 140)

if results:
    best = results[0][1]
    for i, (name, profit, trades, orders, config) in enumerate(results):
        vs_best = profit - best
        marker = " <-- BEST" if vs_best == 0 else ""
        print(f"{i+1:<5} {name:<50} ${profit:>13,.2f} {trades:>8} {orders:>9} {vs_best:>+13,.2f}{marker}")

print("\n" + "=" * 140)
if results:
    print(f"WINNER: {results[0][0]} with ${results[0][1]:,.2f}")
