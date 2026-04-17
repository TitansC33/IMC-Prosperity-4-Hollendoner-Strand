"""Tight grid search around SPREAD_4 and COMBO_60_4 winners"""
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


# Tight grid around winners
configs_to_test = [
    # Original baseline
    ('BASELINE', 20, 0.002, 5.0, 0.2, 18, 1, 0.3),

    # Spread variations (fine-grained)
    ('SPREAD_3.0', 20, 0.002, 3.0, 0.2, 18, 1, 0.3),
    ('SPREAD_3.5', 20, 0.002, 3.5, 0.2, 18, 1, 0.3),
    ('SPREAD_4.0', 20, 0.002, 4.0, 0.2, 18, 1, 0.3),
    ('SPREAD_4.5', 20, 0.002, 4.5, 0.2, 18, 1, 0.3),

    # Position limits with spread=4 (fine-grained)
    ('POS40_SP4', 40, 0.002, 4.0, 0.2, 18, 1, 0.3),
    ('POS50_SP4', 50, 0.002, 4.0, 0.2, 18, 1, 0.3),
    ('POS60_SP4', 60, 0.002, 4.0, 0.2, 18, 1, 0.3),
    ('POS70_SP4', 70, 0.002, 4.0, 0.2, 18, 1, 0.3),
    ('POS80_SP4', 80, 0.002, 4.0, 0.2, 18, 1, 0.3),

    # Position limits with spread=3.5
    ('POS60_SP3.5', 60, 0.002, 3.5, 0.2, 18, 1, 0.3),
    ('POS70_SP3.5', 70, 0.002, 3.5, 0.2, 18, 1, 0.3),

    # Osmium skew tweaks
    ('POS60_SP4_SK15', 60, 0.002, 4.0, 0.15, 18, 1, 0.3),
    ('POS60_SP4_SK25', 60, 0.002, 4.0, 0.25, 18, 1, 0.3),

    # Pepper threshold/quote with best Osmium
    ('POS60_SP4_TH15', 60, 0.002, 4.0, 0.2, 15, 1, 0.3),
    ('POS60_SP4_TH20', 60, 0.002, 4.0, 0.2, 20, 1, 0.3),
    ('POS60_SP4_QT0', 60, 0.002, 4.0, 0.2, 18, 0, 0.3),
    ('POS60_SP4_QT2', 60, 0.002, 4.0, 0.2, 18, 2, 0.3),

    # Pepper skew with best Osmium
    ('POS60_SP4_PSK25', 60, 0.002, 4.0, 0.2, 18, 1, 0.25),
    ('POS60_SP4_PSK35', 60, 0.002, 4.0, 0.2, 18, 1, 0.35),

    # EWM alpha variations with best found
    ('POS60_SP4_EWM001', 60, 0.001, 4.0, 0.2, 18, 1, 0.3),
    ('POS60_SP4_EWM005', 60, 0.005, 4.0, 0.2, 18, 1, 0.3),
]

print("=" * 140)
print("TIGHT GRID SEARCH: Fine-grained optimization around SPREAD_4 and COMBO_60_4")
print("=" * 140)
print(f"{'Name':<20} {'Pos':<6} {'EWM':<10} {'Spread':<10} {'O-Skew':<10} {'P-Thresh':<10} {'P-Qoute':<10} {'P-Skew':<10} {'Profit':<15}")
print("-" * 140)

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
        results.append((name, profit, pos, o_spread))
        print(f"{name:<20} {pos:<6} {ewm:<10.4f} {o_spread:<10.1f} {o_skew:<10.2f} {p_thresh:<10} {p_quote:<10} {p_skew:<10.2f} ${profit:>13,.0f}")
    except Exception as e:
        print(f"{name:<20} ERROR: {str(e)[:60]}")

results.sort(key=lambda x: x[1], reverse=True)

print("\n" + "=" * 140)
print("RANKING (Top 15):")
print("=" * 140)
print(f"{'Rank':<5} {'Name':<20} {'Pos':<6} {'Spread':<10} {'Profit':<15} {'vs Baseline':<15} {'% Gain':<10}")
print("-" * 140)

for i, (name, profit, pos, spread) in enumerate(results[:15]):
    delta = profit - 32480
    pct = (delta / 32480 * 100)
    marker = " ***" if profit > 141361 else ""
    print(f"{i+1:<5} {name:<20} {pos:<6} {spread:<10.1f} ${profit:>13,.0f} {delta:>+13,.0f} {pct:>+8.1f}%{marker}")

print(f"\nPrevious Best: SPREAD_4 with $141,361")
print(f"New Best: {results[0][0]} with ${results[0][1]:,.0f}")
if results[0][1] > 141361:
    print(f"IMPROVEMENT: +${results[0][1] - 141361:,.0f} ({(results[0][1] - 141361)/141361*100:.1f}% better!)")
