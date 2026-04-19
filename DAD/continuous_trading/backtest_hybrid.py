"""
Hybrid backtest: process timestamps where trades occur, use both prices AND trades
===============================================================================

This is the CORRECT backtest for evaluating strategies on ROUND1 data.
It processes only trade timestamps (~2,218) but uses BOTH order depth (prices)
and market trades to match orders, simulating how the live simulator receives data.

See BACKTEST_GUIDE.md for:
- How to use this backtest
- Adding new configurations
- Understanding results
- Troubleshooting

Quick start: python backtest_hybrid.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd().parent.parent / "analysis"))

import pandas as pd
import json
import importlib.util
from trader import Trader, TradingState, OrderDepth, Trade, Listing, Observation
from order_matcher import OrderMatcher

# Load seanTrader dynamically so we can test both baseline and optimized versions
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

def run_backtest_hybrid(trader_class, config_overrides=None):
    """Hybrid: process trade timestamps, use prices AND trades data"""
    trades_df, prices_df = load_round1_data()

    # Create trader instance with appropriate defaults
    if trader_class == SeanTrader:
        # SeanTrader already has correct defaults
        trader = SeanTrader()
    else:
        # Current Trader has optimized defaults; reset to baseline first
        trader = trader_class()
        # Reset to Sean's original parameters
        trader.POSITION_LIMITS = {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20}
        trader.OSMIUM_SPREAD = 5
        trader.PEPPER_SKEW_FACTOR = 0.3
        trader.PEPPER_LARGE_ORDER_THRESHOLD = 18

    if config_overrides:
        for key, value in config_overrides.items():
            setattr(trader, key, value)

    # Get unique (day, timestamp) pairs from TRADES (fewer than all prices)
    trade_times = trades_df[['day', 'timestamp']].drop_duplicates().sort_values(['day', 'timestamp']).reset_index(drop=True)

    state_data = {}
    positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
    balance = 100000
    matcher = OrderMatcher(match_mode="all")

    trade_count = 0

    for idx, (day, timestamp) in enumerate(trade_times.values):
        # Get ALL trades at this (day, timestamp)
        trades_at_ts = trades_df[(trades_df['day'] == day) & (trades_df['timestamp'] == timestamp)]

        for symbol in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
            # Get order depth from prices
            order_depth_data = get_order_depth_at_timestamp(prices_df, day, timestamp, symbol)
            if not order_depth_data:
                continue

            # Get market trades for this symbol AT this timestamp
            symbol_trades = trades_at_ts[trades_at_ts['symbol'] == symbol]
            market_trades_list = [
                Trade(symbol, int(row['price']), int(row['quantity']))
                for _, row in symbol_trades.iterrows()
            ]

            # Build state with BOTH prices and trades
            state = TradingState(
                json.dumps(state_data),
                timestamp,
                {symbol: Listing(symbol, symbol, "XIREC")},
                {symbol: order_depth_data},
                {symbol: []},
                {symbol: market_trades_list},  # ALL trades at this timestamp
                positions.copy(),
                Observation({}, {})
            )

            result, _, traderData = trader.run(state)
            state_data = json.loads(traderData)

            # Match orders
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

        if (idx + 1) % 300 == 0:
            print(f"    {idx + 1}/{len(trade_times)} trade timestamps...")

    return balance - 100000, trade_count, positions

print("=" * 130)
print("HYBRID BACKTEST: Trade timestamps + both Prices AND Trades data")
print("=" * 130 + "\n")

# EDIT THIS SECTION TO ADD NEW CONFIGURATIONS
# ============================================
# Format: (trader_class, "display name", parameter_overrides)
#
# trader_class:
#   - SeanTrader: Uses Sean's original trader (pos=20, spread=5, pskew=0.3)
#   - Trader: Uses your optimized trader (reset to baseline, then overrides applied)
#
# parameter_overrides (None = use defaults):
#   - POSITION_LIMITS: dict with ASH_COATED_OSMIUM and INTARIAN_PEPPER_ROOT
#   - OSMIUM_SPREAD: int (default 5)
#   - PEPPER_SKEW_FACTOR: float (default 0.3)
#   - PEPPER_LARGE_ORDER_THRESHOLD: int (default 18)
#
# Example to add a new config:
#   (Trader, "My Config (pos=40, sp=3)", {
#       "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 40, "INTARIAN_PEPPER_ROOT": 40},
#       "OSMIUM_SPREAD": 3
#   })

configs = [
    (SeanTrader, "Sean Baseline (pos=20, spread=5)", None),
    (Trader, "SPREAD_4 (pos=20, spread=4)", {"OSMIUM_SPREAD": 4}),
    (Trader, "COMBO_60_4 (pos=60, spread=4)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 60, "INTARIAN_PEPPER_ROOT": 60},
        "OSMIUM_SPREAD": 4
    }),
    (Trader, "Optimized (pos=60, sp=4, pskew=0.25)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 60, "INTARIAN_PEPPER_ROOT": 60},
        "OSMIUM_SPREAD": 4,
        "PEPPER_SKEW_FACTOR": 0.25
    }),
    (Trader, "Conservative Pepper (pos=60, sp=4, pskew=0.28)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 60, "INTARIAN_PEPPER_ROOT": 60},
        "OSMIUM_SPREAD": 4,
        "PEPPER_SKEW_FACTOR": 0.28
    }),
]

results = []

for trader_class, name, overrides in configs:
    print(f"Testing: {name}")
    try:
        profit, trades, pos = run_backtest_hybrid(trader_class, overrides)
        results.append((name, profit, trades, overrides or {}))
        print(f"  Profit: ${profit:,.2f} | Fills: {trades}")
        print()
    except Exception as e:
        print(f"  ERROR: {e}\n")

results.sort(key=lambda x: x[1], reverse=True)

print("=" * 130)
print("RANKINGS (Hybrid ROUND1 Backtest - Trade timestamps + Prices + Trades):")
print("=" * 130)
print(f"{'Rank':<5} {'Configuration':<50} {'Profit':<15} {'Fills':<10} {'vs Best':<15}")
print("-" * 130)

if results:
    best = results[0][1]
    for i, (name, profit, trades, config) in enumerate(results):
        vs_best = profit - best
        marker = " <-- BEST" if vs_best == 0 else ""
        print(f"{i+1:<5} {name:<50} ${profit:>13,.2f} {trades:>8} {vs_best:>+13,.2f}{marker}")

print("\n" + "=" * 130)
if results:
    print(f"WINNER: {results[0][0]} with ${results[0][1]:,.2f}")
