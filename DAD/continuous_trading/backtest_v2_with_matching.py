"""
Improved Backtest with Realistic Order Matching

Simulates trading with real order book matching following IMC Prosperity rules:
- Order depths have priority over market trades
- Position limits enforced BEFORE matching (strict all-or-nothing)
- Price-time-priority at same price level
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
# Add analysis directory to path
_analysis_dir = Path(__file__).parent.parent.parent / "analysis"
sys.path.insert(0, str(_analysis_dir))

from load_data import load_all_trades, load_all_prices, get_order_depth_at_timestamp
from order_matcher import OrderMatcher, OrderDepth
from trader import Order, Trade


def simulate_portfolio_with_matching(trades_df, prices_df, config, match_mode="all"):
    """
    Simulate trading with realistic order matching.

    config = {
        "osmium_pos_limit": 80,
        "pepper_pos_limit": 80,
        "initial_balance": 100000
    }
    """
    osmium_limit = config.get("osmium_pos_limit", 80)
    pepper_limit = config.get("pepper_pos_limit", 80)
    initial_balance = config.get("initial_balance", 100000)

    # Track state
    balance = initial_balance
    positions = {
        "ASH_COATED_OSMIUM": 0,
        "INTARIAN_PEPPER_ROOT": 0
    }
    position_limits = {
        "ASH_COATED_OSMIUM": osmium_limit,
        "INTARIAN_PEPPER_ROOT": pepper_limit
    }

    trade_log = []
    execution_stats = {
        "ASH_COATED_OSMIUM": {"attempted": 0, "filled": 0, "partial_fills": 0, "rejected": 0, "total_qty": 0, "matched_qty": 0},
        "INTARIAN_PEPPER_ROOT": {"attempted": 0, "filled": 0, "partial_fills": 0, "rejected": 0, "total_qty": 0, "matched_qty": 0}
    }

    matcher = OrderMatcher(match_mode=match_mode)

    # Process trades chronologically
    trades_sorted = trades_df.sort_values(["day", "timestamp"]).reset_index(drop=True)

    for idx, trade_row in trades_sorted.iterrows():
        symbol = trade_row["symbol"]
        timestamp = int(trade_row["timestamp"])
        day = int(trade_row["day"])
        market_price = int(trade_row["price"])
        market_qty = int(trade_row["quantity"])

        # Strategy: Market making around fair value (simple heuristic)
        if symbol == "ASH_COATED_OSMIUM":
            # Buy low, sell high around 10000
            fair_value = 10000
            spread = 5

            # Get current order depth for this symbol at this timestamp
            depth_snapshot = get_order_depth_at_timestamp(prices_df, day, timestamp, symbol)

            if depth_snapshot:
                try:
                    # Populate OrderDepth object
                    order_depth = OrderDepth()
                    order_depth.buy_orders = depth_snapshot["buy_orders"]
                    order_depth.sell_orders = depth_snapshot["sell_orders"]

                    # Generate trading signals
                    buy_price = fair_value - spread
                    sell_price = fair_value + spread

                    orders_to_send = []

                    # Try to buy if below fair value
                    if market_price < fair_value and positions[symbol] < osmium_limit:
                        buy_qty = min(5, osmium_limit - positions[symbol])
                        orders_to_send.append(Order(symbol, buy_price, buy_qty))

                    # Try to sell if above fair value
                    if market_price > fair_value and positions[symbol] > -osmium_limit:
                        sell_qty = min(5, osmium_limit + positions[symbol])
                        orders_to_send.append(Order(symbol, sell_price, -sell_qty))

                    # Match orders
                    for order in orders_to_send:
                        market_trades_at_ts = [
                            Trade(symbol, market_price, market_qty, timestamp=timestamp)
                        ]

                        result = matcher.match_order(
                            order=order,
                            order_depth=order_depth,
                            market_trades=market_trades_at_ts,
                            current_position=positions[symbol],
                            position_limit=osmium_limit
                        )

                        execution_stats[symbol]["attempted"] += 1

                        if result.rejected:
                            execution_stats[symbol]["rejected"] += 1
                        else:
                            if result.filled > 0:
                                execution_stats[symbol]["matched_qty"] += result.filled
                                execution_stats[symbol]["total_qty"] += abs(order.quantity)

                                if result.filled < abs(order.quantity):
                                    execution_stats[symbol]["partial_fills"] += 1
                                else:
                                    execution_stats[symbol]["filled"] += 1

                                # Update position and balance
                                is_buy = order.quantity > 0
                                if is_buy:
                                    positions[symbol] += result.filled
                                    balance -= result.filled * result.fill_price
                                else:
                                    positions[symbol] -= result.filled
                                    balance += result.filled * result.fill_price

                                trade_log.append({
                                    "day": day,
                                    "timestamp": timestamp,
                                    "symbol": symbol,
                                    "side": "BUY" if is_buy else "SELL",
                                    "order_price": order.price,
                                    "fill_price": result.fill_price,
                                    "filled_qty": result.filled,
                                    "position": positions[symbol],
                                    "balance": balance,
                                    "fill_source": result.fills[0][2] if result.fills else "none"
                                })

                except Exception as e:
                    pass

        elif symbol == "INTARIAN_PEPPER_ROOT":
            # Trend following: buy on uptrend
            fair_value = 12000

            depth_snapshot = get_order_depth_at_timestamp(prices_df, day, timestamp, symbol)

            if depth_snapshot:
                try:
                    order_depth = OrderDepth()
                    order_depth.buy_orders = depth_snapshot["buy_orders"]
                    order_depth.sell_orders = depth_snapshot["sell_orders"]

                    orders_to_send = []

                    # Simple trend: if price < fair, buy; if price > fair, sell
                    if market_price < fair_value and positions[symbol] < pepper_limit:
                        buy_qty = min(3, pepper_limit - positions[symbol])
                        orders_to_send.append(Order(symbol, market_price - 1, buy_qty))

                    elif market_price > fair_value and positions[symbol] > 0:
                        sell_qty = min(positions[symbol], 3)
                        orders_to_send.append(Order(symbol, market_price + 1, -sell_qty))

                    # Match orders
                    for order in orders_to_send:
                        market_trades_at_ts = [
                            Trade(symbol, market_price, market_qty, timestamp=timestamp)
                        ]

                        result = matcher.match_order(
                            order=order,
                            order_depth=order_depth,
                            market_trades=market_trades_at_ts,
                            current_position=positions[symbol],
                            position_limit=pepper_limit
                        )

                        execution_stats[symbol]["attempted"] += 1

                        if result.rejected:
                            execution_stats[symbol]["rejected"] += 1
                        else:
                            if result.filled > 0:
                                execution_stats[symbol]["matched_qty"] += result.filled
                                execution_stats[symbol]["total_qty"] += abs(order.quantity)

                                if result.filled < abs(order.quantity):
                                    execution_stats[symbol]["partial_fills"] += 1
                                else:
                                    execution_stats[symbol]["filled"] += 1

                                # Update position and balance
                                is_buy = order.quantity > 0
                                if is_buy:
                                    positions[symbol] += result.filled
                                    balance -= result.filled * result.fill_price
                                else:
                                    positions[symbol] -= result.filled
                                    balance += result.filled * result.fill_price

                                trade_log.append({
                                    "day": day,
                                    "timestamp": timestamp,
                                    "symbol": symbol,
                                    "side": "BUY" if is_buy else "SELL",
                                    "order_price": order.price,
                                    "fill_price": result.fill_price,
                                    "filled_qty": result.filled,
                                    "position": positions[symbol],
                                    "balance": balance,
                                    "fill_source": result.fills[0][2] if result.fills else "none"
                                })

                except Exception as e:
                    pass

    # Calculate final portfolio value
    final_prices = {
        "ASH_COATED_OSMIUM": 10000,
        "INTARIAN_PEPPER_ROOT": 12500
    }

    unrealized_pnl = sum(positions[s] * final_prices[s] for s in positions)
    final_portfolio_value = balance + unrealized_pnl

    return {
        "config": config,
        "final_balance": balance,
        "final_positions": positions.copy(),
        "final_portfolio_value": final_portfolio_value,
        "num_trades": len(trade_log),
        "trade_log": trade_log,
        "execution_stats": execution_stats,
        "match_mode": match_mode
    }


def run_backtest_variants():
    """Test multiple strategy configurations with realistic matching"""
    print("=" * 100)
    print("BACKTEST WITH REALISTIC ORDER MATCHING: TESTING STRATEGY VARIANTS")
    print("=" * 100)

    # Load data
    trades_df = load_all_trades()
    prices_df = load_all_prices()

    print(f"\nData loaded: {len(trades_df)} trades, {len(prices_df)} price snapshots\n")

    # Test configurations
    configs = [
        {"osmium_pos_limit": 40, "pepper_pos_limit": 40, "name": "Conservative (±40)"},
        {"osmium_pos_limit": 60, "pepper_pos_limit": 60, "name": "Medium (±60)"},
        {"osmium_pos_limit": 80, "pepper_pos_limit": 80, "name": "Aggressive (±80)"},
    ]

    results = []

    for config in configs:
        name = config.pop("name")
        config["initial_balance"] = 100000

        print(f"Testing: {name}")
        result = simulate_portfolio_with_matching(trades_df, prices_df, config, match_mode="all")
        result["name"] = name
        results.append(result)

        print(f"  Final Portfolio Value: {result['final_portfolio_value']:+,.0f}")
        print(f"  Final Positions: Osmium={result['final_positions']['ASH_COATED_OSMIUM']:+4d}, "
              f"Pepper={result['final_positions']['INTARIAN_PEPPER_ROOT']:+4d}")
        print(f"  Trades executed: {result['num_trades']}")

        # Execution statistics
        print(f"  Osmium - Attempted: {result['execution_stats']['ASH_COATED_OSMIUM']['attempted']}, "
              f"Filled: {result['execution_stats']['ASH_COATED_OSMIUM']['filled']}, "
              f"Rejected: {result['execution_stats']['ASH_COATED_OSMIUM']['rejected']}")
        print(f"  Pepper - Attempted: {result['execution_stats']['INTARIAN_PEPPER_ROOT']['attempted']}, "
              f"Filled: {result['execution_stats']['INTARIAN_PEPPER_ROOT']['filled']}, "
              f"Rejected: {result['execution_stats']['INTARIAN_PEPPER_ROOT']['rejected']}")
        print()

    # Summary
    print("=" * 100)
    print("SUMMARY: Ranked by Final Portfolio Value")
    print("=" * 100 + "\n")

    results_sorted = sorted(results, key=lambda x: x["final_portfolio_value"], reverse=True)

    for rank, result in enumerate(results_sorted, 1):
        target_progress = (result["final_portfolio_value"] / 200000) * 100
        print(f"{rank}. {result['name']}")
        print(f"   Portfolio Value: {result['final_portfolio_value']:+,.0f}")
        print(f"   Progress to 200k target: {target_progress:.1f}%")
        print(f"   Trades executed: {result['num_trades']}")
        print()

    # Best config
    best = results_sorted[0]
    print("=" * 100)
    print("RECOMMENDED CONFIGURATION")
    print("=" * 100)
    print(f"Strategy: {best['name']}")
    print(f"Expected Portfolio Value: {best['final_portfolio_value']:+,.0f}")
    print(f"Target: 200,000 XIRECs")
    print(f"Status: {'VIABLE' if best['final_portfolio_value'] >= 200000 else 'BELOW TARGET'} "
          f"({abs(best['final_portfolio_value'] - 200000):+,.0f})")

    return results_sorted


if __name__ == "__main__":
    results = run_backtest_variants()
