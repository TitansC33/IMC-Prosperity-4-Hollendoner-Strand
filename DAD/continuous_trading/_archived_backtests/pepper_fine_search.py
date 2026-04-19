"""Fine-grained search for Pepper parameters: skew + threshold"""
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


# Fine-grained Pepper parameter sweep
# Keep Osmium fixed at optimal: pos_limit=60, spread=4
pepper_skews = [0.20, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29, 0.30]
pepper_thresholds = [12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 25]

configs_to_test = []
for skew in pepper_skews:
    for threshold in pepper_thresholds:
        name = f"PSK{skew:.2f}_TH{threshold}"
        configs_to_test.append((name, skew, threshold))

print("=" * 150)
print("PEPPER FINE-GRAINED SEARCH: Skew × Threshold (Osmium: pos=60, spread=4 FIXED)")
print("=" * 150)
print(f"{'Name':<20} {'P-Skew':<10} {'P-Thresh':<10} {'Profit':<15} {'vs Best':<15} {'% vs Best':<10}")
print("-" * 150)

results = []
tested = 0
total = len(configs_to_test)

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
        tested += 1

        if tested % 10 == 0 or tested == total:
            print(f"{name:<20} {p_skew:<10.2f} {p_thresh:<10} ${profit:>13,.0f}")
    except Exception as e:
        print(f"{name:<20} ERROR: {str(e)[:60]}")

results.sort(key=lambda x: x[3], reverse=True)
best_profit = results[0][3]

print("\n" + "=" * 150)
print("TOP 20 CONFIGURATIONS:")
print("=" * 150)
print(f"{'Rank':<5} {'Name':<20} {'P-Skew':<10} {'P-Thresh':<10} {'Profit':<15} {'vs Best':<15} {'% Gain':<10}")
print("-" * 150)

for i, (name, p_skew, p_thresh, profit) in enumerate(results[:20]):
    delta = profit - 211853
    pct = (delta / 211853 * 100)
    marker = " ***" if profit > 211853 else ""
    print(f"{i+1:<5} {name:<20} {p_skew:<10.2f} {p_thresh:<10} ${profit:>13,.0f} {delta:>+13,.0f} {pct:>+8.1f}%{marker}")

print(f"\nPrevious Best: POS60_SP4_PSK25_TH18 with $211,853")
print(f"New Best: {results[0][0]} with ${results[0][3]:,.0f}")
if results[0][3] > 211853:
    improvement = results[0][3] - 211853
    pct_gain = (improvement / 211853 * 100)
    print(f"IMPROVEMENT: +${improvement:,.0f} ({pct_gain:.1f}% better!)")
    print(f"\nWinning Configuration:")
    print(f"  Pepper Skew: {results[0][1]}")
    print(f"  Pepper Threshold: {results[0][2]}")
else:
    print(f"No improvement found. PSK=0.25, TH=18 remains optimal.")
    print(f"\nNote: Tested {total} combinations of Pepper parameters")
