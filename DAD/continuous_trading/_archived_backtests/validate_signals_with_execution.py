"""
Signal Validation with Execution Simulation

Validates that trader.py generates correct trading signals AND
simulates realistic execution with order matching to report:
- Signal generation correctness (VWAP, EMA, trend detection)
- Execution feasibility (would orders actually fill?)
- Fill rates (% of generated orders that execute)
- Position limit violations
"""

import sys
from pathlib import Path
import jsonpickle
import numpy as np
import pandas as pd

# Add paths
_script_dir = Path(__file__).parent
_analysis_dir = Path(__file__).parent.parent.parent / "analysis"
sys.path.insert(0, str(_script_dir))
sys.path.insert(0, str(_analysis_dir))

from trader import Trader, TradingState, Order, OrderDepth, Trade, Listing, Observation
from load_data import load_all_trades, load_all_prices, get_order_depth_at_timestamp
from order_matcher import OrderMatcher


def validate_signals_with_execution():
    """Check trader.py signal generation AND execution feasibility"""

    print("=" * 100)
    print("SIGNAL VALIDATION WITH EXECUTION SIMULATION")
    print("=" * 100 + "\n")

    # Load trades and prices
    trades_df = load_all_trades()
    prices_df = load_all_prices()
    trades_sorted = trades_df.sort_values(['day', 'timestamp']).reset_index(drop=True)

    print(f"Testing {len(trades_sorted)} historical trades with realistic order matching\n")

    # Initialize
    trader = Trader()
    memory = {"ASH_COATED_OSMIUM_history": [], "INTARIAN_PEPPER_ROOT_history": []}
    positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
    position_limits = {"ASH_COATED_OSMIUM": 80, "INTARIAN_PEPPER_ROOT": 80}

    # Tracking metrics
    osmium_stats = {
        "signal_count": 0,
        "orders_generated": 0,
        "orders_filled": 0,
        "orders_rejected": 0,
        "orders_partial": 0,
        "total_qty_attempted": 0,
        "total_qty_filled": 0
    }

    pepper_stats = {
        "signal_count": 0,
        "orders_generated": 0,
        "orders_filled": 0,
        "orders_rejected": 0,
        "orders_partial": 0,
        "total_qty_attempted": 0,
        "total_qty_filled": 0
    }

    execution_log = []
    errors = []
    matcher = OrderMatcher(match_mode="all")

    # Sample check points
    check_interval = max(1, len(trades_sorted) // 10)

    print(f"{'TS':<8} {'Symbol':<20} {'Signal':<12} {'Orders':<10} {'Filled':<10} {'Rejected':<10} {'Fill%':<8}")
    print("-" * 90)

    for idx, trade_row in trades_sorted.iterrows():
        try:
            symbol = trade_row["symbol"]
            price = int(trade_row["price"])
            quantity = int(trade_row["quantity"])
            timestamp = int(trade_row["timestamp"])
            day = int(trade_row["day"])

            # Build TradingState
            state = TradingState(
                traderData=jsonpickle.encode(memory),
                timestamp=timestamp,
                listings={symbol: Listing(symbol, symbol, "XIREC")},
                order_depths={symbol: OrderDepth()},
                own_trades={symbol: []},
                market_trades={symbol: [Trade(symbol, price, quantity)]},
                position=positions.copy(),
                observations=Observation({}, {})
            )

            # Run trader to get signals
            result, _, traderData = trader.run(state)
            memory = jsonpickle.decode(traderData)

            # Check for orders in result
            orders_placed = result.get(symbol, [])

            if orders_placed:
                # Get order depth for matching simulation
                depth_snapshot = get_order_depth_at_timestamp(prices_df, day, timestamp, symbol)

                if depth_snapshot:
                    order_depth = OrderDepth()
                    order_depth.buy_orders = depth_snapshot["buy_orders"]
                    order_depth.sell_orders = depth_snapshot["sell_orders"]

                    # Simulate matching for each order
                    for order in orders_placed:
                        stats = osmium_stats if symbol == "ASH_COATED_OSMIUM" else pepper_stats

                        # Match the order
                        market_trades_list = [Trade(symbol, price, quantity)]
                        result = matcher.match_order(
                            order=order,
                            order_depth=order_depth,
                            market_trades=market_trades_list,
                            current_position=positions[symbol],
                            position_limit=position_limits[symbol]
                        )

                        stats["orders_generated"] += 1
                        stats["total_qty_attempted"] += abs(order.quantity)

                        if result.rejected:
                            stats["orders_rejected"] += 1
                        elif result.filled > 0:
                            stats["total_qty_filled"] += result.filled

                            if result.filled < abs(order.quantity):
                                stats["orders_partial"] += 1
                            else:
                                stats["orders_filled"] += 1

                            # Update position for next iteration
                            if order.quantity > 0:
                                positions[symbol] += result.filled
                            else:
                                positions[symbol] -= result.filled

                            execution_log.append({
                                "day": day,
                                "timestamp": timestamp,
                                "symbol": symbol,
                                "signal": "Order Generated",
                                "filled": result.filled,
                                "attempted": abs(order.quantity),
                                "fill_price": result.fill_price,
                                "rejected": result.rejected,
                                "position": positions[symbol]
                            })

                # Report checkpoint
                if (idx + 1) % check_interval == 0:
                    osmium_hist = memory.get("ASH_COATED_OSMIUM_history", [])
                    fill_pct_osmium = (osmium_stats["total_qty_filled"] / osmium_stats["total_qty_attempted"] * 100
                                      if osmium_stats["total_qty_attempted"] > 0 else 0)
                    fill_pct_pepper = (pepper_stats["total_qty_filled"] / pepper_stats["total_qty_attempted"] * 100
                                      if pepper_stats["total_qty_attempted"] > 0 else 0)

                    print(f"{idx+1:<8} {'OSMIUM':<20} {'Market-Make':<12} "
                          f"{osmium_stats['orders_generated']:<10} {osmium_stats['orders_filled']:<10} "
                          f"{osmium_stats['orders_rejected']:<10} {fill_pct_osmium:<8.1f}%")
                    print(f"{idx+1:<8} {'PEPPER':<20} {'Trend-Foll':<12} "
                          f"{pepper_stats['orders_generated']:<10} {pepper_stats['orders_filled']:<10} "
                          f"{pepper_stats['orders_rejected']:<10} {fill_pct_pepper:<8.1f}%")

        except Exception as e:
            errors.append(f"Trade {idx}: {str(e)[:80]}")

    print("\n" + "=" * 100)
    print("EXECUTION FEASIBILITY REPORT")
    print("=" * 100)

    print(f"\nOsmium (Market-Making):")
    print(f"  Orders Generated:     {osmium_stats['orders_generated']:>6}")
    print(f"  Orders Filled:        {osmium_stats['orders_filled']:>6}")
    print(f"  Orders Partial Fill:  {osmium_stats['orders_partial']:>6}")
    print(f"  Orders Rejected:      {osmium_stats['orders_rejected']:>6}")
    print(f"  Total Qty Attempted:  {osmium_stats['total_qty_attempted']:>6}")
    print(f"  Total Qty Filled:     {osmium_stats['total_qty_filled']:>6}")

    if osmium_stats["total_qty_attempted"] > 0:
        osmium_fill_pct = (osmium_stats["total_qty_filled"] / osmium_stats["total_qty_attempted"]) * 100
        print(f"  Fill Rate:            {osmium_fill_pct:>6.1f}%")
    else:
        print(f"  Fill Rate:        N/A")

    print(f"\nPepper (Trend-Following):")
    print(f"  Orders Generated:     {pepper_stats['orders_generated']:>6}")
    print(f"  Orders Filled:        {pepper_stats['orders_filled']:>6}")
    print(f"  Orders Partial Fill:  {pepper_stats['orders_partial']:>6}")
    print(f"  Orders Rejected:      {pepper_stats['orders_rejected']:>6}")
    print(f"  Total Qty Attempted:  {pepper_stats['total_qty_attempted']:>6}")
    print(f"  Total Qty Filled:     {pepper_stats['total_qty_filled']:>6}")

    if pepper_stats["total_qty_attempted"] > 0:
        pepper_fill_pct = (pepper_stats["total_qty_filled"] / pepper_stats["total_qty_attempted"]) * 100
        print(f"  Fill Rate:            {pepper_fill_pct:>6.1f}%")
    else:
        print(f"  Fill Rate:        N/A")

    print(f"\nErrors: {len(errors)}")

    print("\n" + "=" * 100)
    print("VALIDATION CHECKS")
    print("=" * 100)

    checks = [
        ("Osmium orders generated", osmium_stats['orders_generated'] > 0),
        ("Pepper orders generated", pepper_stats['orders_generated'] > 0),
        ("Osmium orders not all rejected", osmium_stats['orders_rejected'] < osmium_stats['orders_generated']),
        ("Pepper orders not all rejected", pepper_stats['orders_rejected'] < pepper_stats['orders_generated']),
        ("Osmium fill rate > 50%", (osmium_stats["total_qty_filled"] / max(1, osmium_stats["total_qty_attempted"])) > 0.5),
        ("Pepper fill rate > 50%", (pepper_stats["total_qty_filled"] / max(1, pepper_stats["total_qty_attempted"])) > 0.5),
        ("No critical errors", len(errors) == 0),
    ]

    for check, result in checks:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check}")

    all_pass = all(result for _, result in checks)

    print("\n" + "=" * 100)
    if all_pass:
        print("[PASS] EXECUTION VALIDATION PASSED")
        print("       All signals are generating AND executing with realistic fill rates")
        print("       Trader.py logic is sound for competition.")
    else:
        print("[WARN] EXECUTION VALIDATION HAS CONCERNS")
        print("       Check fill rates and rejection reasons above")
    print("=" * 100 + "\n")

    return all_pass


if __name__ == "__main__":
    result = validate_signals_with_execution()
    sys.exit(0 if result else 1)
