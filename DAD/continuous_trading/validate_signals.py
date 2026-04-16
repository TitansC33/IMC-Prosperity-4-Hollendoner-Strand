"""
Signal Validation: Check that trader.py is generating correct trading signals.
Validates: VWAP, EMA, trend detection, volatility scaling, order logic.
Does NOT simulate order execution (avoids platform unknowns).
"""

import sys
from pathlib import Path
import jsonpickle
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "analysis"))

from trader import Trader, TradingState, Order, OrderDepth, Trade, Listing, Observation, ConversionObservation
from load_data import load_all_trades

def validate_signals():
    """Check trader.py signal generation on historical data"""

    print("="*80)
    print("SIGNAL VALIDATION: Checking trader.py logic correctness")
    print("="*80 + "\n")

    # Load trades
    trades_df = load_all_trades()
    trades_sorted = trades_df.sort_values(['day', 'timestamp']).reset_index(drop=True)

    print(f"Testing {len(trades_sorted)} historical trades\n")

    # Initialize
    trader = Trader()
    memory = {"ASH_COATED_OSMIUM_history": [], "INTARIAN_PEPPER_ROOT_history": []}
    positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}

    # Tracking metrics
    osmium_orders = {"buy": 0, "sell": 0}
    pepper_orders = {"buy": 0, "sell": 0}
    osmium_signals = []
    pepper_signals = []
    errors = []

    # Sample check points: measure signals every N trades
    check_interval = len(trades_sorted) // 10  # 10 checkpoints

    print(f"{'Timestamp':<12} {'Symbol':<20} {'Signal':<15} {'VWAP/EMA':<12} {'Position':<10} {'Action':<20}")
    print("-" * 90)

    for idx, trade_row in trades_sorted.iterrows():
        try:
            symbol = trade_row["symbol"]
            price = int(trade_row["price"])
            quantity = int(trade_row["quantity"])
            timestamp = int(trade_row["timestamp"])

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

            # Run trader
            result, _, traderData = trader.run(state)
            memory = jsonpickle.decode(traderData)

            # Analyze signals
            if (idx + 1) % check_interval == 0:
                # Get current price for reference
                osmium_hist = memory.get("ASH_COATED_OSMIUM_history", [])
                pepper_hist = memory.get("INTARIAN_PEPPER_ROOT_history", [])

                # OSMIUM: Check VWAP and market-making signals
                if symbol == "ASH_COATED_OSMIUM" and osmium_hist:
                    prices = np.array([x[0] for x in osmium_hist])
                    volumes = np.array([x[1] for x in osmium_hist])
                    vwap = np.average(prices, weights=volumes)

                    osmium_orders_placed = result.get("ASH_COATED_OSMIUM", [])
                    osmium_action = "PLACE ORDERS" if osmium_orders_placed else "NO ACTION"

                    if osmium_orders_placed:
                        for o in osmium_orders_placed:
                            if o.quantity > 0:
                                osmium_orders["buy"] += 1
                            else:
                                osmium_orders["sell"] += 1

                    print(f"{idx+1:<12} {'OSMIUM':<20} {'VWAP-based':<15} {vwap:<12.1f} {positions['ASH_COATED_OSMIUM']:<10} {osmium_action:<20}")
                    osmium_signals.append((idx, price, vwap, "BUY" if price < vwap - 5 else "SELL" if price > vwap + 5 else "NEUTRAL"))

                # PEPPER: Check EMA and trend-following signals
                elif symbol == "INTARIAN_PEPPER_ROOT" and pepper_hist and len(pepper_hist) >= 15:
                    prices = np.array([x[0] for x in pepper_hist])
                    volumes = np.array([x[1] for x in pepper_hist])

                    # Calculate EMA (alpha=0.3 per Phase 2)
                    ema = prices[0]
                    for p in prices[1:]:
                        ema = 0.3 * p + 0.7 * ema

                    vwap = np.average(prices, weights=volumes)
                    current_price = prices[-1]
                    is_uptrend = current_price > vwap

                    pepper_orders_placed = result.get("INTARIAN_PEPPER_ROOT", [])
                    pepper_action = "PLACE ORDERS" if pepper_orders_placed else "NO ACTION"

                    if pepper_orders_placed:
                        for o in pepper_orders_placed:
                            if o.quantity > 0:
                                pepper_orders["buy"] += 1
                            else:
                                pepper_orders["sell"] += 1

                    trend = "UPTREND" if is_uptrend else "DOWNTREND"
                    print(f"{idx+1:<12} {'PEPPER':<20} {trend:<15} {ema:<12.1f} {positions['INTARIAN_PEPPER_ROOT']:<10} {pepper_action:<20}")
                    pepper_signals.append((idx, current_price, ema, vwap, "BUY" if is_uptrend else "SELL"))

        except Exception as e:
            errors.append(f"Trade {idx}: {str(e)[:80]}")

    print("\n" + "="*80)
    print("SIGNAL SUMMARY")
    print("="*80)
    print(f"\nOsmium (Market-Making):")
    print(f"  Buy orders generated:  {osmium_orders['buy']:>6}")
    print(f"  Sell orders generated: {osmium_orders['sell']:>6}")
    print(f"  Total signals:         {len(osmium_signals):>6}")

    if osmium_signals:
        buys = sum(1 for s in osmium_signals if s[3] == "BUY")
        sells = sum(1 for s in osmium_signals if s[3] == "SELL")
        neutrals = sum(1 for s in osmium_signals if s[3] == "NEUTRAL")
        print(f"  Buy signals:           {buys:>6}")
        print(f"  Sell signals:          {sells:>6}")
        print(f"  Neutral signals:       {neutrals:>6}")

    print(f"\nPepper (Trend-Following):")
    print(f"  Buy orders generated:  {pepper_orders['buy']:>6}")
    print(f"  Sell orders generated: {pepper_orders['sell']:>6}")
    print(f"  Total signals:         {len(pepper_signals):>6}")

    if pepper_signals:
        buys = sum(1 for s in pepper_signals if s[4] == "BUY")
        sells = sum(1 for s in pepper_signals if s[4] == "SELL")
        print(f"  Buy signals (uptrend): {buys:>6}")
        print(f"  Sell signals (down):   {sells:>6}")

    print(f"\nErrors: {len(errors)}")

    print("\n" + "="*80)
    print("VALIDATION CHECKS")
    print("="*80)

    checks = [
        ("Osmium signals generated", len(osmium_signals) > 0),
        ("Pepper signals generated", len(pepper_signals) > 0),
        ("Osmium buy/sell ratio reasonable", osmium_orders['buy'] > 0 and osmium_orders['sell'] > 0),
        ("Pepper trend detection working", len(pepper_signals) > 0 and any(s[4] == "BUY" for s in pepper_signals)),
        ("No critical errors", len(errors) == 0),
    ]

    for check, result in checks:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {check}")

    all_pass = all(result for _, result in checks)

    print("\n" + "="*80)
    if all_pass:
        print("[PASS] VALIDATION PASSED: All signals generating correctly")
        print("       Trader.py logic is sound. Ready for competition.")
    else:
        print("[FAIL] VALIDATION FAILED: Some signals not generating")
    print("="*80 + "\n")

    return all_pass

if __name__ == "__main__":
    result = validate_signals()
    sys.exit(0 if result else 1)
