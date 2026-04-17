"""Ultra fine-grained search: PSK 0.20-0.22, TH 10-14"""
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

    for idx in np.linspace(0, len(trades_sorted)-1, min(200, len(trades_sorted))).astype(int):
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

    return balance - 100000


# Ultra-fine grid: very small increments
pepper_skews = [0.195, 0.200, 0.205, 0.210, 0.215, 0.220, 0.225]
pepper_thresholds = [10, 11, 12, 13, 14]

configs_to_test = []
for skew in pepper_skews:
    for threshold in pepper_thresholds:
        name = f"PSK{skew:.3f}_TH{threshold}"
        configs_to_test.append((name, skew, threshold))

print("=" * 160)
print("ULTRA FINE-GRAINED SEARCH: Skew × Threshold (Osmium: pos=60, spread=4, Testing sweet spot)")
print("=" * 160)
print(f"{'Name':<20} {'P-Skew':<10} {'P-Thresh':<10} {'Profit':<15} {'vs PSK21_TH12':<15} {'% vs Best':<10}")
print("-" * 160)

results = []
baseline = 302740

for name, p_skew, p_thresh in configs_to_test:
    config = {
        'position_limits': {'ASH_COATED_OSMIUM': 60, 'INTARIAN_PEPPER_ROOT': 60},
        'osmium_ewm_alpha': 0.002,
        'osmium_spread': 4.0,
        'osmium_skew': 0.2,
        'pepper_threshold': p_thresh,
        'pepper_quote_imp': 1,
        'pepper_skew': p_skew,
    }

    try:
        profit = run_backtest(config)
        results.append((name, p_skew, p_thresh, profit))
        delta = profit - baseline
        pct = (delta / baseline * 100)
        marker = " ***NEW***" if profit > baseline else ""
        print(f"{name:<20} {p_skew:<10.3f} {p_thresh:<10} ${profit:>13,.0f} {delta:>+13,.0f} {pct:>+8.2f}%{marker}")
    except Exception as e:
        print(f"{name:<20} ERROR: {str(e)[:50]}")

results.sort(key=lambda x: x[3], reverse=True)

print("\n" + "=" * 160)
print("TOP 15:")
print("=" * 160)
print(f"{'Rank':<5} {'Name':<20} {'P-Skew':<10} {'P-Thresh':<10} {'Profit':<15} {'vs $302,740':<15} {'% Improvement':<10}")
print("-" * 160)

for i, (name, p_skew, p_thresh, profit) in enumerate(results[:15]):
    delta = profit - 302740
    pct = (delta / 302740 * 100)
    marker = " ← NEW BEST!" if profit > 302740 else ""
    print(f"{i+1:<5} {name:<20} {p_skew:<10.3f} {p_thresh:<10} ${profit:>13,.0f} {delta:>+13,.0f} {pct:>+8.2f}%{marker}")

print(f"\nCurrent Best: PSK0.21_TH12 with $302,740")
print(f"New Best: {results[0][0]} with ${results[0][3]:,.0f}")
if results[0][3] > 302740:
    improvement = results[0][3] - 302740
    pct_gain = (improvement / 302740 * 100)
    print(f"IMPROVEMENT: +${improvement:,.0f} ({pct_gain:.2f}% better!)")
    print(f"\nUltra-Optimal Configuration:")
    print(f"  Position Limits: 60")
    print(f"  Osmium Spread: 4")
    print(f"  Pepper Skew: {results[0][1]}")
    print(f"  Pepper Threshold: {results[0][2]}")
else:
    print(f"\nPSK=0.21, TH=12 appears to be the sweet spot in this range.")
