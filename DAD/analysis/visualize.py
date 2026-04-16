"""
Visualize price data to spot patterns visually.
Creates plots of: price time series, distributions, spreads, and volume.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import warnings
from pathlib import Path
warnings.filterwarnings('ignore')

from load_data import get_product_trades, get_product_prices, load_all_trades

# Ensure outputs go to DAD/scripts
OUTPUT_DIR = Path(__file__).parent
OUTPUT_DIR.mkdir(exist_ok=True)


def plot_price_timeseries():
    """Plot price over time for both products."""
    print("\n" + "="*60)
    print("PRICE TIMESERIES DATA")
    print("="*60)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    for idx, symbol in enumerate(["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]):
        trades = get_product_trades(symbol)

        if len(trades) == 0:
            continue

        # Create absolute timestamp (combine day + timestamp)
        # Assuming each day is 24*100 units long (day -2, -1, 0)
        trades = trades.copy()
        trades["abs_timestamp"] = trades["day"] * 10000 + trades["timestamp"]

        ax = axes[idx]
        ax.scatter(trades["abs_timestamp"], trades["price"], alpha=0.5, s=20, color="blue")
        ax.plot(trades["abs_timestamp"], trades["price"], alpha=0.3, linewidth=0.5, color="blue")

        # Add VWAP line
        vwap = (trades["price"] * trades["quantity"]).sum() / trades["quantity"].sum()
        ax.axhline(vwap, color="red", linestyle="--", linewidth=2, label=f"VWAP: {vwap:.2f}")

        ax.set_title(f"{symbol} - Price Over Time", fontsize=12, fontweight="bold")
        ax.set_ylabel("Price (XIRECs)")
        ax.set_xlabel("Timestamp")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Print data
        print(f"\n{symbol}:")
        print(f"  VWAP: {vwap:.2f}")
        print(f"  Min price: {trades['price'].min():.2f}")
        print(f"  Max price: {trades['price'].max():.2f}")
        print(f"  First price: {trades['price'].iloc[0]:.2f}")
        print(f"  Last price: {trades['price'].iloc[-1]:.2f}")
        print(f"  Price direction: {'UP' if trades['price'].iloc[-1] > trades['price'].iloc[0] else 'DOWN'}")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "price_timeseries.png", dpi=100)
    print(f"\n[Saved: {OUTPUT_DIR / 'price_timeseries.png'}]")
    plt.close()


def plot_price_distributions():
    """Plot histograms of prices for both products."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for idx, symbol in enumerate(["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]):
        trades = get_product_trades(symbol)

        if len(trades) == 0:
            continue

        ax = axes[idx]

        # Get histogram data
        counts, bins, patches = ax.hist(trades["price"], bins=30, color="skyblue", edgecolor="black", alpha=0.7)

        ax.axvline(trades["price"].mean(), color="red", linestyle="--", linewidth=2, label=f"Mean: {trades['price'].mean():.2f}")
        ax.axvline(trades["price"].median(), color="green", linestyle="--", linewidth=2, label=f"Median: {trades['price'].median():.2f}")

        ax.set_title(f"{symbol} - Price Distribution", fontsize=12, fontweight="bold")
        ax.set_xlabel("Price (XIRECs)")
        ax.set_ylabel("Frequency")
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

        # Print histogram data
        print(f"\n{'='*60}")
        print(f"HISTOGRAM DATA: {symbol}")
        print(f"{'='*60}")
        for i in range(len(counts)):
            bin_start = bins[i]
            bin_end = bins[i+1]
            count = int(counts[i])
            bar = "█" * (count // 10) if count > 0 else ""
            print(f"[{bin_start:7.0f} - {bin_end:7.0f}]: {count:4d} trades {bar}")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "price_distributions.png", dpi=100)
    print("\n[Saved: price_distributions.png]")
    plt.close()


def plot_volume_analysis():
    """Plot traded volume over time."""
    print("\n" + "="*60)
    print("VOLUME ANALYSIS DATA")
    print("="*60)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    for idx, symbol in enumerate(["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]):
        trades = get_product_trades(symbol)

        if len(trades) == 0:
            continue

        trades = trades.copy()
        trades["abs_timestamp"] = trades["day"] * 10000 + trades["timestamp"]

        ax = axes[idx]
        ax.bar(trades["abs_timestamp"], trades["quantity"], width=50, color="teal", alpha=0.7)

        ax.set_title(f"{symbol} - Volume Over Time", fontsize=12, fontweight="bold")
        ax.set_ylabel("Quantity (units)")
        ax.set_xlabel("Timestamp")
        ax.grid(True, alpha=0.3, axis="y")

        # Print data
        print(f"\n{symbol}:")
        print(f"  Total volume: {trades['quantity'].sum()} units")
        print(f"  Avg trade size: {trades['quantity'].mean():.1f} units")
        print(f"  Min trade size: {trades['quantity'].min()} units")
        print(f"  Max trade size: {trades['quantity'].max()} units")
        print(f"  Std dev trade size: {trades['quantity'].std():.1f} units")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "volume_analysis.png", dpi=100)
    print("\n[Saved: volume_analysis.png]")
    plt.close()


def plot_price_momentum():
    """Plot price changes (momentum) to visualize trends."""
    print("\n" + "="*60)
    print("PRICE MOMENTUM DATA")
    print("="*60)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    for idx, symbol in enumerate(["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]):
        trades = get_product_trades(symbol)

        if len(trades) < 2:
            continue

        prices = trades["price"].values
        momentum = np.diff(prices)  # Price changes

        trades = trades.copy()
        trades["abs_timestamp"] = trades["day"] * 10000 + trades["timestamp"]

        ax = axes[idx]

        # Color momentum: red for negative (price drops), green for positive (price rises)
        colors = ["red" if m < 0 else "green" for m in momentum]
        ax.bar(trades["abs_timestamp"].values[1:], momentum, width=50, color=colors, alpha=0.7)
        ax.axhline(0, color="black", linestyle="-", linewidth=1)

        # Add rolling average of momentum
        if len(momentum) > 5:
            rolling_avg = pd.Series(momentum).rolling(window=5).mean()
            ax.plot(trades["abs_timestamp"].values[1:], rolling_avg, color="blue", linewidth=2, label="5-trade MA", alpha=0.8)

        ax.set_title(f"{symbol} - Price Momentum (Change Between Trades)", fontsize=12, fontweight="bold")
        ax.set_ylabel("Price Change (XIRECs)")
        ax.set_xlabel("Timestamp")
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

        # Print data
        print(f"\n{symbol}:")
        print(f"  Momentum mean: {momentum.mean():+.4f}")
        print(f"  Momentum std: {momentum.std():.4f}")
        print(f"  Up moves: {(momentum > 0).sum()} ({(momentum > 0).sum() / len(momentum) * 100:.1f}%)")
        print(f"  Down moves: {(momentum < 0).sum()} ({(momentum < 0).sum() / len(momentum) * 100:.1f}%)")
        print(f"  Max price jump: {momentum.max():+.0f}")
        print(f"  Max price drop: {momentum.min():+.0f}")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "price_momentum.png", dpi=100)
    print("\n[Saved: price_momentum.png]")
    plt.close()


def plot_bid_ask_spreads():
    """Plot bid-ask spreads over time."""
    from analyze_prices import calculate_spreads

    print("\n" + "="*60)
    print("BID-ASK SPREAD DATA")
    print("="*60)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    for idx, symbol in enumerate(["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]):
        spreads_df = calculate_spreads(symbol)

        if len(spreads_df) == 0:
            print(f"\n{symbol}: No bid/ask data")
            continue

        spreads_df = spreads_df.copy()
        spreads_df["abs_timestamp"] = spreads_df["day"] * 10000 + spreads_df["timestamp"]

        ax = axes[idx]

        # Plot bid, mid, and ask
        ax.scatter(spreads_df["abs_timestamp"], spreads_df["best_bid"], label="Best Bid", alpha=0.5, s=15, color="red")
        ax.scatter(spreads_df["abs_timestamp"], spreads_df["mid_price"], label="Mid Price", alpha=0.5, s=15, color="blue")
        ax.scatter(spreads_df["abs_timestamp"], spreads_df["best_ask"], label="Best Ask", alpha=0.5, s=15, color="green")

        ax.set_title(f"{symbol} - Bid/Mid/Ask Over Time", fontsize=12, fontweight="bold")
        ax.set_ylabel("Price (XIRECs)")
        ax.set_xlabel("Timestamp")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Print data
        print(f"\n{symbol}:")
        print(f"  Bid range: {spreads_df['best_bid'].min():.0f} - {spreads_df['best_bid'].max():.0f}")
        print(f"  Ask range: {spreads_df['best_ask'].min():.0f} - {spreads_df['best_ask'].max():.0f}")
        print(f"  Avg spread: {spreads_df['spread'].mean():.2f}")
        print(f"  Min spread: {spreads_df['spread'].min():.2f}")
        print(f"  Max spread: {spreads_df['spread'].max():.2f}")
        print(f"  Spread std dev: {spreads_df['spread'].std():.2f}")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "bid_ask_spreads.png", dpi=100)
    print("\n[Saved: bid_ask_spreads.png]")
    plt.close()


def plot_comparison():
    """Side-by-side comparison: overlay both products normalized."""
    print("\n" + "="*60)
    print("PRODUCT COMPARISON DATA")
    print("="*60)

    fig, ax = plt.subplots(figsize=(14, 6))

    comparison_data = {}
    for symbol, color in [("ASH_COATED_OSMIUM", "blue"), ("INTARIAN_PEPPER_ROOT", "orange")]:
        trades = get_product_trades(symbol)

        if len(trades) == 0:
            continue

        trades = trades.copy()
        trades["abs_timestamp"] = trades["day"] * 10000 + trades["timestamp"]

        # Normalize to percentage change from first price
        normalized_price = (trades["price"] / trades["price"].iloc[0] - 1) * 100

        ax.scatter(trades["abs_timestamp"], normalized_price, label=symbol, alpha=0.6, s=20, color=color)
        ax.plot(trades["abs_timestamp"], normalized_price, alpha=0.3, linewidth=1, color=color)

        # Store data for printout
        comparison_data[symbol] = {
            "first_price": trades["price"].iloc[0],
            "last_price": trades["price"].iloc[-1],
            "pct_change": (trades["price"].iloc[-1] / trades["price"].iloc[0] - 1) * 100,
            "max_pct": normalized_price.max(),
            "min_pct": normalized_price.min()
        }

    ax.set_title("Price Movement Comparison (Normalized % Change)", fontsize=14, fontweight="bold")
    ax.set_ylabel("% Change from First Trade")
    ax.set_xlabel("Timestamp")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="black", linestyle="--", linewidth=1)

    # Print data
    for symbol, data in comparison_data.items():
        print(f"\n{symbol}:")
        print(f"  First price: {data['first_price']:.2f}")
        print(f"  Last price: {data['last_price']:.2f}")
        print(f"  Total % change: {data['pct_change']:+.2f}%")
        print(f"  Max % gain: {data['max_pct']:+.2f}%")
        print(f"  Max % loss: {data['min_pct']:+.2f}%")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "price_comparison.png", dpi=100)
    print("\n[Saved: price_comparison.png]")
    plt.close()


if __name__ == "__main__":
    print("Generating visualizations...\n")

    # Open file for writing analysis output (UTF-8 encoding for Unicode support)
    with open(OUTPUT_DIR / "analysis_output.txt", "w", encoding="utf-8") as f:
        f.write("="*80 + "\n")
        f.write("ANALYSIS OUTPUT - ROUND 1 DATA\n")
        f.write("="*80 + "\n\n")

        # Redirect prints to both console and file
        import sys
        class Tee:
            def __init__(self, *files):
                self.files = files
            def write(self, data):
                for f in self.files:
                    f.write(data)
            def flush(self):
                for f in self.files:
                    f.flush()

        original_stdout = sys.stdout
        sys.stdout = Tee(sys.stdout, f)

        f.write("\n\nSTARTING VISUALIZATION ANALYSIS...\n\n")

        plot_price_timeseries()
        plot_price_distributions()
        plot_volume_analysis()
        plot_price_momentum()
        plot_bid_ask_spreads()
        plot_comparison()

        sys.stdout = original_stdout

    print("\n[DONE] All visualizations saved!")
    print("[DONE] Analysis data saved to: analysis_output.txt")
    print("\nFiles generated:")
    print("  - price_timeseries.png: Is there a trend or mean-reversion?")
    print("  - price_momentum.png: Are price changes correlated? (trending vs random)")
    print("  - price_comparison.png: How do the two products differ?")
    print("  - price_distributions.png: Histogram data (now in analysis_output.txt)")
    print("  - bid_ask_spreads.png: Bid/ask behavior")
    print("  - volume_analysis.png: Trading volume patterns")
    print("\nOpen analysis_output.txt to see all the data!")
