"""Grid search backtest for Sean's strategy parameters"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd().parent.parent / "analysis"))

from load_data import load_all_trades, load_all_prices, get_order_depth_at_timestamp
from trader import Trader, TradingState, OrderDepth, Trade, Listing, Observation
from order_matcher import OrderMatcher
import json
import numpy as np
from itertools import product

def run_backtest(config):
    """Run backtest with given parameter config"""
    trades_df = load_all_trades()
    prices_df = load_all_prices()
    trades_sorted = trades_df.sort_values(['day', 'timestamp']).reset_index(drop=True)

    # Create trader with custom params
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

# Define parameter grid (reduced for speed)
param_grid = {
    'pos_limit': [20, 40, 60, 80],
    'ewm_alpha': [0.001, 0.002, 0.005],
    'osmium_spread': [4, 5, 6],
    'osmium_skew': [0.15, 0.2, 0.25],
    'pepper_threshold': [15, 18, 22],
    'pepper_quote': [0, 1, 2],
    'pepper_skew': [0.25, 0.3, 0.4],
}

results = []
tested = 0
total = np.prod([len(v) for v in param_grid.values()])

print("=" * 100)
print(f"GRID SEARCH: Testing ~{total} parameter combinations")
print("=" * 100)
print(f"{'Status':<10} {'Pos Lim':<10} {'EWM':<10} {'O-Spread':<10} {'O-Skew':<10} {'P-Thresh':<10} {'P-Quote':<10} {'P-Skew':<10} {'Profit':<15}")
print("-" * 100)

for vals in product(*param_grid.values()):
    pos_limit, ewm, o_spread, o_skew, p_thresh, p_quote, p_skew = vals

    config = {
        'position_limits': {'ASH_COATED_OSMIUM': pos_limit, 'INTARIAN_PEPPER_ROOT': pos_limit},
        'osmium_ewm_alpha': ewm,
        'osmium_spread': o_spread,
        'osmium_skew': o_skew,
        'pepper_threshold': p_thresh,
        'pepper_quote_imp': p_quote,
        'pepper_skew': p_skew,
    }

    try:
        profit = run_backtest(config)
        tested += 1
        results.append((config, profit))

        if tested % 10 == 0:
            status = f"{tested}/{total}"
            print(f"{status:<10} {pos_limit:<10} {ewm:<10.4f} {o_spread:<10} {o_skew:<10.2f} {p_thresh:<10} {p_quote:<10} {p_skew:<10.2f} ${profit:>13,.0f}")
    except Exception as e:
        print(f"ERROR: {e}")

# Sort by profit
results.sort(key=lambda x: x[1], reverse=True)

print("\n" + "=" * 100)
print("TOP 10 CONFIGURATIONS:")
print("=" * 100)
print(f"{'Rank':<6} {'Pos':<6} {'EWM':<10} {'O-Sp':<6} {'O-Sk':<6} {'P-Th':<6} {'P-Qo':<5} {'P-Sk':<6} {'Profit':<15}")
print("-" * 100)

for i, (config, profit) in enumerate(results[:10]):
    limits = config['position_limits']['ASH_COATED_OSMIUM']
    print(f"{i+1:<6} {limits:<6} {config['osmium_ewm_alpha']:<10.4f} {config['osmium_spread']:<6} "
          f"{config['osmium_skew']:<6.2f} {config['pepper_threshold']:<6} {config['pepper_quote_imp']:<5} "
          f"{config['pepper_skew']:<6.2f} ${profit:>13,.0f}")

print(f"\nBaseline (Sean's original, pos_limit=20): $32,480 (estimated from full run)")
print(f"Best found: ${results[0][1]:,.0f}")
print(f"Improvement: {((results[0][1] - 32480) / 32480 * 100):.1f}%")
EOF
