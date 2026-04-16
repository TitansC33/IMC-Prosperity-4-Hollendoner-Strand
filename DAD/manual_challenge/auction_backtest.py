"""
Backtest auction strategy using bid-ask characteristics from continuous trading data.
Extracts order book microstructure patterns and simulates auction clearing prices.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "analysis"))

from load_data import load_all_prices, load_all_trades


def analyze_order_book_characteristics():
    """
    Extract bid-ask patterns from continuous trading data.
    These patterns will inform our auction clearing price estimation.
    """
    prices_df = load_all_prices()

    characteristics = {}

    for symbol in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
        symbol_prices = prices_df[prices_df["product"] == symbol]

        # Extract bid and ask prices
        best_bids = symbol_prices["bid_price_1"].dropna()
        best_asks = symbol_prices["ask_price_1"].dropna()

        # Calculate spreads
        spreads = best_asks - best_bids

        # Mid-prices
        mids = (best_bids + best_asks) / 2

        characteristics[symbol] = {
            "avg_bid": best_bids.mean(),
            "avg_ask": best_asks.mean(),
            "avg_spread": spreads.mean(),
            "spread_std": spreads.std(),
            "bid_depth": symbol_prices["bid_volume_1"].mean(),
            "ask_depth": symbol_prices["ask_volume_1"].mean(),
            "mid_price": mids.mean(),
        }

    return characteristics


def simulate_auction_with_market_characteristics(product_name, fair_value, buyback_price,
                                                  num_participants=40, avg_spread=15):
    """
    Simulate auction clearing price using market microstructure.

    Participants submit bids/asks drawn from realistic distribution.
    """

    # Generate participant bids (lower than fair value)
    bid_std = avg_spread / 2
    participant_bids = np.random.normal(fair_value - avg_spread/2, bid_std, num_participants)
    participant_bids = np.clip(participant_bids, fair_value - avg_spread, fair_value)

    # Generate participant asks (higher than fair value)
    participant_asks = np.random.normal(fair_value + avg_spread/2, bid_std, num_participants)
    participant_asks = np.clip(participant_asks, fair_value, fair_value + avg_spread)

    # Remove outliers
    participant_bids = sorted([b for b in participant_bids if b > 0])
    participant_asks = sorted([a for a in participant_asks if a < buyback_price * 1.2])

    if not participant_bids or not participant_asks:
        return None

    # Actual clearing price (median of all prices, or volume-weighted approximation)
    all_prices = participant_bids + participant_asks
    actual_clearing = np.median(all_prices)

    # Our estimation: midpoint of best bid/ask
    best_bid = max(participant_bids)
    best_ask = min(participant_asks)
    estimated_clearing = (best_bid + best_ask) / 2

    return {
        "product": product_name,
        "actual_clearing": actual_clearing,
        "estimated_clearing": estimated_clearing,
        "estimation_error": abs(actual_clearing - estimated_clearing),
        "best_bid": best_bid,
        "best_ask": best_ask,
        "bid_ask_spread": best_ask - best_bid,
        "buyback_price": buyback_price
    }


def test_auction_bid(scenario, product_name, fee=0):
    """
    Test our bidding strategy on the simulated auction.
    """
    estimated_clearing = scenario["estimated_clearing"]
    best_bid = scenario["best_bid"]
    buyback_price = scenario["buyback_price"]

    # Calculate profit based on our estimate
    profit_per_unit_estimated = (buyback_price - fee) - estimated_clearing

    if profit_per_unit_estimated <= 0:
        return {"profit": 0, "quantity": 0, "bid_price": None, "viable": False}

    # Scale quantity by profit
    if profit_per_unit_estimated > 5:
        quantity = 500
    elif profit_per_unit_estimated > 2:
        quantity = 250
    else:
        quantity = 50

    # Bid price: beat best bid
    bid_price = best_bid + 1

    # Expected profit (our estimate)
    expected_profit = profit_per_unit_estimated * quantity

    # Actual profit (real clearing - what we estimated)
    actual_profit_per_unit = (buyback_price - fee) - scenario["actual_clearing"]
    actual_profit = actual_profit_per_unit * quantity

    return {
        "profit_estimated": expected_profit,
        "profit_actual": actual_profit,
        "quantity": quantity,
        "bid_price": bid_price,
        "viable": profit_per_unit_estimated > 0,
        "profit_per_unit": profit_per_unit_estimated,
        "estimation_error": scenario["estimation_error"]
    }


def run_auction_backtest():
    """Run auction backtest using market characteristics from continuous trading data."""

    print("="*80)
    print("AUCTION BACKTEST: Using Continuous Trading Market Microstructure")
    print("="*80 + "\n")

    # Step 1: Analyze order book characteristics
    print("Step 1: Analyzing order book characteristics from continuous trading data...")
    characteristics = analyze_order_book_characteristics()

    print("\nMarket Microstructure Found:")
    for symbol, chars in characteristics.items():
        print(f"\n{symbol}:")
        print(f"  Avg spread: {chars['avg_spread']:.2f} XIRECs")
        print(f"  Bid depth: {chars['bid_depth']:.0f} units")
        print(f"  Ask depth: {chars['ask_depth']:.0f} units")

    # Step 2: Simulate auctions
    print("\n" + "="*80)
    print("Step 2: Simulating 200 auction scenarios...")
    print("="*80 + "\n")

    osmium_spread = characteristics["ASH_COATED_OSMIUM"]["avg_spread"]
    pepper_spread = characteristics["INTARIAN_PEPPER_ROOT"]["avg_spread"]

    results = []

    for scenario_num in range(200):
        # DRYLAND_FLAX auction (fair value ~25, buyback at 30)
        flax_scenario = simulate_auction_with_market_characteristics(
            "DRYLAND_FLAX",
            fair_value=25,
            buyback_price=30,
            num_participants=40,
            avg_spread=osmium_spread * 1.5  # Slightly wider than Osmium
        )
        flax_bid = test_auction_bid(flax_scenario, "DRYLAND_FLAX", fee=0)

        # EMBER_MUSHROOM auction (fair value ~18, buyback at 20)
        mushroom_scenario = simulate_auction_with_market_characteristics(
            "EMBER_MUSHROOM",
            fair_value=18,
            buyback_price=20,
            num_participants=40,
            avg_spread=pepper_spread * 0.3  # Lower spread than Pepper
        )
        mushroom_bid = test_auction_bid(mushroom_scenario, "EMBER_MUSHROOM", fee=0.10)

        results.append({
            "scenario": scenario_num,
            "flax_actual_clearing": flax_scenario["actual_clearing"],
            "flax_estimated_clearing": flax_scenario["estimated_clearing"],
            "flax_viable": flax_bid["viable"],
            "flax_profit": flax_bid["profit_actual"],
            "flax_quantity": flax_bid["quantity"],
            "mushroom_actual_clearing": mushroom_scenario["actual_clearing"],
            "mushroom_estimated_clearing": mushroom_scenario["estimated_clearing"],
            "mushroom_viable": mushroom_bid["viable"],
            "mushroom_profit": mushroom_bid["profit_actual"],
            "mushroom_quantity": mushroom_bid["quantity"],
        })

    df = pd.DataFrame(results)

    # Analysis
    print("RESULTS:\n")

    for product in ["flax", "mushroom"]:
        viable = df[df[f"{product}_viable"]]
        total = len(df)

        print(f"\n{product.upper()}:")
        print(f"  Viable bids: {len(viable)}/{total} ({len(viable)/total*100:.1f}%)")

        if len(viable) > 0:
            print(f"  Avg profit per scenario: {viable[f'{product}_profit'].mean():,.0f} XIRECs")
            print(f"  Avg bid quantity: {viable[f'{product}_quantity'].mean():.0f} units")
            print(f"  Total profit across all scenarios: {viable[f'{product}_profit'].sum():,.0f} XIRECs")
            print(f"  Avg estimation error: {(100 - (viable[f'{product}_estimated_clearing'].values / viable[f'{product}_actual_clearing'].values * 100)).mean():.2f}%")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    flax_total = df[df["flax_viable"]]["flax_profit"].sum()
    mushroom_total = df[df["mushroom_viable"]]["mushroom_profit"].sum()
    total_auction_profit = flax_total + mushroom_total

    print(f"\nExpected profit from auctions (per Round 1):")
    print(f"  DRYLAND_FLAX: {flax_total/100:,.0f} XIRECs (across {len(df[df['flax_viable']])} profitable scenarios)")
    print(f"  EMBER_MUSHROOM: {mushroom_total/100:,.0f} XIRECs (across {len(df[df['mushroom_viable']])} profitable scenarios)")
    print(f"  **TOTAL: {total_auction_profit/100:,.0f} XIRECs**")

    print(f"\nCombined with algorithmic trading (+340,091):")
    print(f"  Algorithmic: 340,091 XIRECs")
    print(f"  Auctions: {total_auction_profit/100:,.0f} XIRECs")
    print(f"  **TOTAL EXPECTED: {340091 + total_auction_profit/100:,.0f} XIRECs**")

    return df


if __name__ == "__main__":
    results = run_auction_backtest()
