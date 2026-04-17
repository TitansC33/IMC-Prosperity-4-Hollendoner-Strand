import subprocess
import sys

print("=" * 130)
print("TESTING BEST ROBUST CONFIG IN FULL BACKTEST")
print("=" * 130 + "\n")

# Run backtest_hybrid with the new best config
code = """
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
    trades_df, prices_df = load_round1_data()
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
            market_trades_list = [Trade(symbol, int(row['price']), int(row['quantity'])) for _, row in symbol_trades.iterrows()]
            state = TradingState(json.dumps(state_data), timestamp, {symbol: Listing(symbol, symbol, "XIREC")},
                {symbol: order_depth_data}, {symbol: []}, {symbol: market_trades_list}, positions.copy(), Observation({}, {}))
            result, _, traderData = trader.run(state)
            state_data = json.loads(traderData)
            for order in result.get(symbol, []):
                match_result = matcher.match_order(order, order_depth_data, market_trades_list, positions[symbol], trader.POSITION_LIMITS[symbol])
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

print("Testing: Ultra Conservative (pos=10, sp=2, pskew=0.1)")
profit, trades, pos = run_backtest_hybrid(Trader, {
    "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 10, "INTARIAN_PEPPER_ROOT": 10},
    "OSMIUM_SPREAD": 2,
    "PEPPER_SKEW_FACTOR": 0.1
})
print(f"  Result: ${profit:,.2f} profit from {trades} trades")
print(f"  Positions: Osmium={pos['ASH_COATED_OSMIUM']}, Pepper={pos['INTARIAN_PEPPER_ROOT']}")

print()
print("Testing: Sean Baseline (pos=20, sp=5) - for comparison")
profit_b, trades_b, pos_b = run_backtest_hybrid(SeanTrader, None)
print(f"  Result: ${profit_b:,.2f} profit from {trades_b} trades")
print(f"  Positions: Osmium={pos_b['ASH_COATED_OSMIUM']}, Pepper={pos_b['INTARIAN_PEPPER_ROOT']}")

print()
print("Comparison:")
improvement = profit - profit_b
print(f"  Ultra Conservative: ${profit:>10,.2f}")
print(f"  Sean Baseline:      ${profit_b:>10,.2f}")
print(f"  Difference:         ${improvement:>+10,.2f}")
"""

exec(code)
