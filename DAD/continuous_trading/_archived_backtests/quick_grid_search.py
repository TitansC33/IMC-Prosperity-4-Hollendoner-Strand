"""Quick grid search with key parameter variations"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd().parent.parent / "analysis"))

from load_data import load_all_trades, load_all_prices, get_order_depth_at_timestamp
from trader import Trader, TradingState, OrderDepth, Trade, Listing, Observation
from order_matcher import OrderMatcher
import json
import numpy as np

def run_backtest(config):
    """Run backtest with given parameter config"""
    trades_df = load_all_trades()
    prices_df = load_all_prices()
    trades_sorted = trades_df.sort_values(['day', 'timestamp']).reset_index(drop=True)

    trader = Trader()
    trader.POSITION_LIMITS = config['position_limits']
    trader.OSMIUM_EWM_ALPHA = config['osmium_ewm_alpha']
    trader.OSMIUM_SPREAD = config['osmium_spread']
    trader.OSMIUM_SKEW_FACTOR = config['osmium_skew']
    trader.PEPPER_LARGE_ORDER_THRESHOLD = config['pepper_threshold']
    trader.PEPPER_QUOTE_IMPROVEMENT = config['pepper_quote_imp']
    trader.PEPPER_SKEW_FACTOR = config['pepper_skew']

    state_data = {}
    positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
    position_limits = config['position_limits']
    balance = 100000
    matcher = OrderMatcher(match_mode="all")

    trade_count = 0
    sample_indices = np.linspace(0, len(trades_sorted)-1, min(200, len(trades_sorted))).astype(int)

    for idx in sample_indices:
        trade_row = trades_sorted.iloc[idx]
        symbol = trade_row["symbol"]
        price, qty, timestamp, day = int(trade_row["price"]), int(trade_row["quantity"]), int(trade_row["timestamp"]), int(trade_row["day"])
        depth_snapshot = get_order_depth_at_timestamp(prices_df, day, timestamp, symbol)

        if depth_snapshot:
            order_depth = OrderDepth()
            order_depth.buy_orders, order_depth.sell_orders = depth_snapshot["buy_orders"], depth_snapshot["sell_orders"]
            state = TradingState(json.dumps(state_data), timestamp, {symbol: Listing(symbol, symbol, "XIREC")},
                               {symbol: order_depth}, {symbol: []}, {symbol: [Trade(symbol, price, qty)]},
                               positions.copy(), Observation({}, {}))
            result, _, traderData = trader.run(state)
            state_data = json.loads(traderData)

            for order in result.get(symbol, []):
                match_result = matcher.match_order(order, order_depth, [Trade(symbol, price, qty, timestamp=timestamp)],
                                                  positions[symbol], position_limits[symbol])
                if match_result.filled > 0:
                    is_buy = order.quantity > 0
                    if is_buy:
                        positions[symbol] += match_result.filled
                        balance -= match_result.filled * match_result.fill_price
                    else:
                        positions[symbol] -= match_result.filled
                        balance += match_result.filled * match_result.fill_price
                    trade_count += 1

    return balance - 100000


configs_to_test = [
    ('BASELINE', 20, 0.002, 5, 0.2, 18, 1, 0.3),
    ('POS_40', 40, 0.002, 5, 0.2, 18, 1, 0.3),
    ('POS_60', 60, 0.002, 5, 0.2, 18, 1, 0.3),
    ('POS_80', 80, 0.002, 5, 0.2, 18, 1, 0.3),
    ('SPREAD_4', 20, 0.002, 4, 0.2, 18, 1, 0.3),
    ('SPREAD_6', 20, 0.002, 6, 0.2, 18, 1, 0.3),
    ('EWM_005', 20, 0.005, 5, 0.2, 18, 1, 0.3),
    ('EWM_001', 20, 0.001, 5, 0.2, 18, 1, 0.3),
    ('THRESH_15', 20, 0.002, 5, 0.2, 15, 1, 0.3),
    ('THRESH_22', 20, 0.002, 5, 0.2, 22, 1, 0.3),
    ('QUOTE_0', 20, 0.002, 5, 0.2, 18, 0, 0.3),
    ('QUOTE_2', 20, 0.002, 5, 0.2, 18, 2, 0.3),
    ('SKEW_OS_15', 20, 0.002, 5, 0.15, 18, 1, 0.3),
    ('SKEW_OS_25', 20, 0.002, 5, 0.25, 18, 1, 0.3),
    ('SKEW_PS_25', 20, 0.002, 5, 0.2, 18, 1, 0.25),
    ('SKEW_PS_4', 20, 0.002, 5, 0.2, 18, 1, 0.4),
    ('COMBO_60_4', 60, 0.002, 4, 0.2, 18, 1, 0.3),
    ('COMBO_80_6', 80, 0.002, 6, 0.2, 18, 1, 0.3),
]

print("=" * 130)
print("TARGETED GRID SEARCH: Key Parameter Variations (200-trade sample)")
print("=" * 130)
print(f"{'Name':<15} {'Pos':<6} {'EWM':<10} {'O-Spread':<10} {'O-Skew':<10} {'P-Thresh':<10} {'P-Quote':<10} {'P-Skew':<10} {'Profit':<15}")
print("-" * 130)

results = []
for name, pos, ewm, o_spread, o_skew, p_thresh, p_quote, p_skew in configs_to_test:
    config = {
        'position_limits': {'ASH_COATED_OSMIUM': pos, 'INTARIAN_PEPPER_ROOT': pos},
        'osmium_ewm_alpha': ewm,
        'osmium_spread': o_spread,
        'osmium_skew': o_skew,
        'pepper_threshold': p_thresh,
        'pepper_quote_imp': p_quote,
        'pepper_skew': p_skew,
    }

    try:
        profit = run_backtest(config)
        results.append((name, profit))
        print(f"{name:<15} {pos:<6} {ewm:<10.4f} {o_spread:<10} {o_skew:<10.2f} {p_thresh:<10} {p_quote:<10} {p_skew:<10.2f} ${profit:>13,.0f}")
    except Exception as e:
        print(f"{name:<15} ERROR: {str(e)[:60]}")

results.sort(key=lambda x: x[1], reverse=True)

print("\n" + "=" * 130)
print("RANKING (Top 10):")
print("=" * 130)
for i, (name, profit) in enumerate(results[:10]):
    delta = profit - 32480
    pct = (delta / 32480 * 100) if delta else 0
    marker = " <-- IMPROVEMENT!" if profit > 32480 else ""
    print(f"{i+1:2}. {name:<15} ${profit:>10,.0f}   ({delta:+10,.0f}, {pct:+6.1f}%){marker}")

print(f"\nNOTE: Baseline (Sean original, pos_limit=20): $32,480")
print(f"Best found: {results[0][0]} with ${results[0][1]:,.0f}")
