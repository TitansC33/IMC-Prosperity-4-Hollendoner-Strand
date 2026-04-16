"""
Load and parse Round 1 market data from CSV files.
Handles: prices (order book snapshots) and trades (execution history)
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "ROUND1"

def load_prices(day: int) -> pd.DataFrame:
    """
    Load order book snapshots for a given day.

    Args:
        day: -2, -1, or 0 (where 0 is the last day of available data)

    Returns:
        DataFrame with columns:
        - day, timestamp, product
        - bid_price_1, bid_volume_1, ..., bid_price_3, bid_volume_3
        - ask_price_1, ask_volume_1, ..., ask_price_3, ask_volume_3
        - mid_price, profit_and_loss
    """
    file = DATA_DIR / f"prices_round_1_day_{day}.csv"
    df = pd.read_csv(file, sep=";")
    return df


def load_trades(day: int) -> pd.DataFrame:
    """
    Load executed trades for a given day.

    Args:
        day: -2, -1, or 0

    Returns:
        DataFrame with columns:
        - timestamp, buyer, seller, symbol, currency, price, quantity
    """
    file = DATA_DIR / f"trades_round_1_day_{day}.csv"
    df = pd.read_csv(file, sep=";")
    return df


def load_all_prices() -> pd.DataFrame:
    """Load and combine prices from all 3 days."""
    dfs = []
    for day in [-2, -1, 0]:
        df = load_prices(day)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def load_all_trades() -> pd.DataFrame:
    """Load and combine trades from all 3 days."""
    dfs = []
    for day in [-2, -1, 0]:
        df = load_trades(day)
        df["day"] = day  # Add day column for tracking
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def get_product_trades(symbol: str) -> pd.DataFrame:
    """Get all trades for a specific product."""
    trades = load_all_trades()
    return trades[trades["symbol"] == symbol].reset_index(drop=True)


def get_product_prices(symbol: str) -> pd.DataFrame:
    """Get all price snapshots for a specific product."""
    prices = load_all_prices()
    return prices[prices["product"] == symbol].reset_index(drop=True)


if __name__ == "__main__":
    # Quick sanity check
    trades = load_all_trades()
    prices = load_all_prices()

    print(f"Total trades: {len(trades)}")
    print(f"Total price snapshots: {len(prices)}")
    print(f"\nUnique products in trades: {trades['symbol'].unique()}")
    print(f"Unique products in prices: {prices['product'].unique()}")

    print("\n=== ASH_COATED_OSMIUM ===")
    osmium_trades = get_product_trades("ASH_COATED_OSMIUM")
    print(f"Trades: {len(osmium_trades)}")
    print(f"Price range: {osmium_trades['price'].min():.0f} - {osmium_trades['price'].max():.0f}")

    print("\n=== INTARIAN_PEPPER_ROOT ===")
    pepper_trades = get_product_trades("INTARIAN_PEPPER_ROOT")
    print(f"Trades: {len(pepper_trades)}")
    print(f"Price range: {pepper_trades['price'].min():.0f} - {pepper_trades['price'].max():.0f}")
