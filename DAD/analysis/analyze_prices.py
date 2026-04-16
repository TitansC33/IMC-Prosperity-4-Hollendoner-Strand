"""
Analyze price data to detect hidden patterns in ASH_COATED_OSMIUM vs INTARIAN_PEPPER_ROOT.
Looks for: trends, mean-reversion, autocorrelation, volatility, seasonality.
"""

import pandas as pd
import numpy as np
from load_data import get_product_trades, get_product_prices
import warnings
warnings.filterwarnings('ignore')


def calculate_vwap(df: pd.DataFrame) -> float:
    """Calculate volume-weighted average price from trades."""
    if len(df) == 0:
        return np.nan
    total_value = (df["price"] * df["quantity"]).sum()
    total_volume = df["quantity"].sum()
    return total_value / total_volume


def calculate_spreads(symbol: str) -> pd.DataFrame:
    """
    Calculate bid-ask spreads over time.
    Returns a time series of spreads at each snapshot.
    """
    prices = get_product_prices(symbol)

    # Extract bid and ask prices
    prices["best_bid"] = prices["bid_price_1"].fillna(0)
    prices["best_ask"] = prices["ask_price_1"].fillna(np.inf)

    # Only keep rows where both bid and ask exist
    valid = (prices["best_bid"] > 0) & (prices["best_ask"] < np.inf)
    prices = prices[valid].copy()

    prices["spread"] = prices["best_ask"] - prices["best_bid"]
    prices["mid_price_calc"] = (prices["best_bid"] + prices["best_ask"]) / 2

    return prices[["day", "timestamp", "product", "best_bid", "best_ask", "mid_price", "spread", "mid_price_calc"]]


def analyze_volatility(symbol: str):
    """Analyze price volatility and distribution."""
    trades = get_product_trades(symbol)

    if len(trades) == 0:
        print(f"No trades for {symbol}")
        return

    prices = trades["price"].values

    print(f"\n{'='*60}")
    print(f"VOLATILITY ANALYSIS: {symbol}")
    print(f"{'='*60}")
    print(f"Number of trades: {len(trades)}")
    print(f"Price range: {prices.min():.2f} - {prices.max():.2f}")
    print(f"Mean price: {prices.mean():.2f}")
    print(f"Median price: {np.median(prices):.2f}")
    print(f"Std Dev: {prices.std():.2f}")
    print(f"Coefficient of Variation: {prices.std() / prices.mean():.4f}")
    print(f"Range spread: {prices.max() - prices.min():.2f}")

    # VWAP
    vwap = calculate_vwap(trades)
    print(f"VWAP: {vwap:.2f}")

    return prices


def analyze_autocorrelation(symbol: str, lags: int = 10):
    """Check if price changes are autocorrelated (mean-reverting or trending)."""
    trades = get_product_trades(symbol)

    if len(trades) < lags + 1:
        print(f"Not enough trades for autocorrelation analysis")
        return

    prices = trades["price"].values
    returns = np.diff(prices)  # Price changes

    print(f"\n{'='*60}")
    print(f"AUTOCORRELATION ANALYSIS: {symbol}")
    print(f"{'='*60}")
    print(f"Analyzing {len(returns)} price changes...\n")

    # Calculate autocorrelations
    for lag in range(1, min(lags + 1, len(returns))):
        acf = np.corrcoef(returns[:-lag], returns[lag:])[0, 1]
        significance = "***" if abs(acf) > 0.15 else ""
        print(f"Lag {lag}: {acf:+.4f} {significance}")

    print("\nInterpretation:")
    print("  Positive ACF → Trending (momentum)")
    print("  Negative ACF → Mean-reverting")
    print("  ACF ≈ 0 → Random walk (no pattern)")
    print("  *** = Notable correlation")


def compare_products():
    """Side-by-side comparison of the two products."""
    print(f"\n{'='*80}")
    print(f"PRODUCT COMPARISON")
    print(f"{'='*80}\n")

    for symbol in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
        print(f"\n{symbol}:")
        analyze_volatility(symbol)
        analyze_autocorrelation(symbol, lags=8)


def price_momentum(symbol: str, window: int = 5):
    """
    Calculate momentum (price change over rolling window).
    High momentum = trending. Low momentum = mean-reverting.
    """
    trades = get_product_trades(symbol)
    prices = trades["price"].values

    if len(prices) < window + 1:
        return None

    momentum = np.diff(prices, n=window)

    print(f"\n{'='*60}")
    print(f"MOMENTUM ANALYSIS: {symbol} (window={window})")
    print(f"{'='*60}")
    print(f"Momentum mean: {momentum.mean():+.2f}")
    print(f"Momentum std: {momentum.std():.2f}")
    print(f"% positive momentum moves: {(momentum > 0).sum() / len(momentum) * 100:.1f}%")

    if momentum.mean() > momentum.std():
        print(f"\n→ TRENDING (strong upward bias)")
    elif momentum.mean() < -momentum.std():
        print(f"\n→ TRENDING (strong downward bias)")
    else:
        print(f"\n→ MEAN-REVERTING or RANDOM")


def spread_analysis():
    """Analyze bid-ask spreads for both products."""
    print(f"\n{'='*80}")
    print(f"BID-ASK SPREAD ANALYSIS")
    print(f"{'='*80}\n")

    for symbol in ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]:
        spreads_df = calculate_spreads(symbol)

        if len(spreads_df) == 0:
            print(f"{symbol}: No data with both bid and ask")
            continue

        print(f"\n{symbol}:")
        print(f"  Avg spread: {spreads_df['spread'].mean():.2f}")
        print(f"  Min spread: {spreads_df['spread'].min():.2f}")
        print(f"  Max spread: {spreads_df['spread'].max():.2f}")
        print(f"  Spread std: {spreads_df['spread'].std():.2f}")


if __name__ == "__main__":
    compare_products()
    print("\n" + "="*80)
    price_momentum("ASH_COATED_OSMIUM", window=5)
    price_momentum("INTARIAN_PEPPER_ROOT", window=5)
    print("\n" + "="*80)
    spread_analysis()
