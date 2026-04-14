"""
Spread Modeling for Round 1 Products
=====================================
Analyzes bid-ask spread behavior for:
  - ASH_COATED_OSMIUM    (mean-reverting around 10,000)
  - INTARIAN_PEPPER_ROOT (linear trend: base + timestamp/1000)

Usage:
    python analysis/spread_model.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ROUND1")
DAYS = [-2, -1, 0]
PRODUCTS = ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]

OUTPUT_PLOT = os.path.join(os.path.dirname(__file__), "spread_plots.png")

# ---------------------------------------------------------------------------
# Fair value models
# ---------------------------------------------------------------------------

def fair_value(product: str, day: int, timestamp: int) -> float:
    """Return the theoretical fair value for a product at a given time."""
    if product == "ASH_COATED_OSMIUM":
        return 10_000.0
    elif product == "INTARIAN_PEPPER_ROOT":
        base = 10_000 + (day + 2) * 1_000
        return base + timestamp / 1_000
    raise ValueError(f"Unknown product: {product}")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_prices() -> pd.DataFrame:
    frames = []
    for day in DAYS:
        path = os.path.join(DATA_DIR, f"prices_round_1_day_{day}.csv")
        df = pd.read_csv(path, sep=";")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Best bid/ask spread (only valid when both sides exist)
    df["spread"] = df["ask_price_1"] - df["bid_price_1"]

    # Fair value and deviation
    df["fair_value"] = df.apply(
        lambda r: fair_value(r["product"], r["day"], r["timestamp"]), axis=1
    )
    df["mid_deviation"] = df["mid_price"] - df["fair_value"]

    # Distance of best bid/ask from fair value
    df["bid_distance"] = df["fair_value"] - df["bid_price_1"]   # positive = bid below fv
    df["ask_distance"] = df["ask_price_1"] - df["fair_value"]   # positive = ask above fv

    return df

# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def print_stats(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("SPREAD MODEL — SUMMARY STATISTICS")
    print("=" * 60)

    for product in PRODUCTS:
        sub = df[df["product"] == product].dropna(subset=["spread"])
        spread = sub["spread"]
        mid_dev = sub["mid_deviation"]

        print(f"\n{'─'*40}")
        print(f"  {product}")
        print(f"{'─'*40}")
        print(f"  Rows with valid spread : {len(sub):,}")
        print()
        print(f"  Bid-Ask Spread:")
        print(f"    Mean        : {spread.mean():.2f}")
        print(f"    Median      : {spread.median():.2f}")
        print(f"    Stdev       : {spread.std():.2f}")
        print(f"    Min         : {spread.min():.2f}")
        print(f"    Max         : {spread.max():.2f}")
        print(f"    5th pct     : {spread.quantile(0.05):.2f}")
        print(f"    95th pct    : {spread.quantile(0.95):.2f}")
        print()
        print(f"  Mid-Price Deviation from Fair Value:")
        print(f"    Mean        : {mid_dev.mean():.4f}")
        print(f"    Stdev       : {mid_dev.std():.4f}")
        print(f"    Min         : {mid_dev.min():.4f}")
        print(f"    Max         : {mid_dev.max():.4f}")

        # Half-spread decomposition
        bid_dist = sub["bid_distance"].dropna()
        ask_dist = sub["ask_distance"].dropna()
        print()
        print(f"  Half-Spread Decomposition (distance from fair value):")
        print(f"    Avg bid distance (fv - best_bid): {bid_dist.mean():.2f}")
        print(f"    Avg ask distance (best_ask - fv): {ask_dist.mean():.2f}")

    print()

# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_spread(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(14, 14))
    fig.suptitle("Round 1 Spread Analysis", fontsize=15, fontweight="bold")

    for col_idx, product in enumerate(PRODUCTS):
        sub = df[df["product"] == product].dropna(subset=["spread"])

        # ── Row 0: Spread over time (day 0 only) ──────────────────────────
        day0 = sub[sub["day"] == 0].sort_values("timestamp")
        ax = axes[0][col_idx]
        ax.plot(day0["timestamp"], day0["spread"], linewidth=0.6, color="steelblue")
        ax.set_title(f"{product}\nSpread Over Time (Day 0)")
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Spread (ask₁ – bid₁)")
        ax.axhline(sub["spread"].mean(), color="red", linestyle="--",
                   linewidth=1, label=f"Mean={sub['spread'].mean():.1f}")
        ax.legend(fontsize=8)

        # ── Row 1: Spread distribution (histogram) ─────────────────────────
        ax = axes[1][col_idx]
        spread_vals = sub["spread"]
        ax.hist(spread_vals, bins=40, color="steelblue", edgecolor="white", linewidth=0.4)
        ax.axvline(spread_vals.mean(), color="red", linestyle="--",
                   linewidth=1.2, label=f"Mean={spread_vals.mean():.1f}")
        ax.axvline(spread_vals.median(), color="orange", linestyle="--",
                   linewidth=1.2, label=f"Median={spread_vals.median():.1f}")
        ax.set_title(f"{product}\nSpread Distribution (all days)")
        ax.set_xlabel("Spread")
        ax.set_ylabel("Count")
        ax.legend(fontsize=8)

        # ── Row 2: Spread vs mid-price deviation from fair value ───────────
        ax = axes[2][col_idx]
        sample = sub.sample(min(3000, len(sub)), random_state=42)
        ax.scatter(sample["mid_deviation"], sample["spread"],
                   s=4, alpha=0.4, color="steelblue")
        ax.set_title(f"{product}\nSpread vs Mid Deviation from Fair Value")
        ax.set_xlabel("Mid – Fair Value")
        ax.set_ylabel("Spread")

    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT, dpi=150)
    print(f"Plot saved to: {OUTPUT_PLOT}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Loading price data...")
    df = load_prices()
    print(f"Loaded {len(df):,} rows across {df['day'].nunique()} days.")

    print("Engineering features...")
    df = engineer_features(df)

    print_stats(df)
    plot_spread(df)
