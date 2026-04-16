"""
Data Loading Utilities for IMC Prosperity Backtesting

Loads trades and order depth (prices) data from ROUND1 CSV files.
"""

import pandas as pd
from pathlib import Path


def get_data_dir():
    """Get path to ROUND1 data directory"""
    return Path(__file__).parent.parent / "data" / "ROUND1"


def load_trades(day: int) -> pd.DataFrame:
    """
    Load trades for a specific day.

    Args:
        day: Day number (-2, -1, or 0)

    Returns:
        DataFrame with columns: timestamp, buyer, seller, symbol, currency, price, quantity
    """
    data_dir = get_data_dir()
    file = data_dir / f"trades_round_1_day_{day}.csv"

    df = pd.read_csv(file, sep=";")

    # Convert types
    df["timestamp"] = df["timestamp"].astype(int)
    df["price"] = df["price"].astype(float)
    df["quantity"] = df["quantity"].astype(int)

    return df


def load_prices(day: int) -> pd.DataFrame:
    """
    Load order depths (prices) for a specific day.

    Provides bid/ask levels at each timestamp.

    Args:
        day: Day number (-2, -1, or 0)

    Returns:
        DataFrame with columns:
        - day, timestamp, product
        - bid_price_1, bid_volume_1, bid_price_2, bid_volume_2, bid_price_3, bid_volume_3
        - ask_price_1, ask_volume_1, ask_price_2, ask_volume_2, ask_price_3, ask_volume_3
        - mid_price, profit_and_loss
    """
    data_dir = get_data_dir()
    file = data_dir / f"prices_round_1_day_{day}.csv"

    df = pd.read_csv(file, sep=";")

    # Convert types
    df["timestamp"] = df["timestamp"].astype(int)
    df["mid_price"] = pd.to_numeric(df["mid_price"], errors="coerce")

    # Convert bid/ask prices and volumes to float/int
    for i in range(1, 4):
        df[f"bid_price_{i}"] = pd.to_numeric(df[f"bid_price_{i}"], errors="coerce")
        df[f"bid_volume_{i}"] = pd.to_numeric(df[f"bid_volume_{i}"], errors="coerce").fillna(0).astype(int)
        df[f"ask_price_{i}"] = pd.to_numeric(df[f"ask_price_{i}"], errors="coerce")
        df[f"ask_volume_{i}"] = pd.to_numeric(df[f"ask_volume_{i}"], errors="coerce").fillna(0).astype(int)

    return df


def load_all_trades() -> pd.DataFrame:
    """
    Load and combine trades from all 3 days.

    Returns:
        DataFrame with all trades, sorted by day and timestamp
    """
    dfs = []
    for day in [-2, -1, 0]:
        df = load_trades(day)
        df["day"] = day
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    return combined.sort_values(["day", "timestamp"]).reset_index(drop=True)


def load_all_prices() -> pd.DataFrame:
    """
    Load and combine order depths (prices) from all 3 days.

    Returns:
        DataFrame with all price snapshots, sorted by day and timestamp
    """
    dfs = []
    for day in [-2, -1, 0]:
        df = load_prices(day)
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    return combined.sort_values(["day", "timestamp"]).reset_index(drop=True)


def get_order_depth_at_timestamp(prices_df: pd.DataFrame, day: int, timestamp: int, product: str):
    """
    Get order depth snapshot for a product at specific day/timestamp.

    Returns:
        Dict with 'buy_orders' and 'sell_orders' (both dicts of {price: volume})
        or None if no snapshot exists
    """
    row = prices_df[
        (prices_df["day"] == day) &
        (prices_df["timestamp"] == timestamp) &
        (prices_df["product"] == product)
    ]

    if row.empty:
        return None

    row = row.iloc[0]

    buy_orders = {}
    for i in range(1, 4):
        price = row[f"bid_price_{i}"]
        volume = row[f"bid_volume_{i}"]
        if pd.notna(price) and volume > 0:
            buy_orders[int(price)] = volume

    sell_orders = {}
    for i in range(1, 4):
        price = row[f"ask_price_{i}"]
        volume = row[f"ask_volume_{i}"]
        if pd.notna(price) and volume > 0:
            sell_orders[int(price)] = volume

    return {
        "buy_orders": buy_orders,
        "sell_orders": sell_orders,
        "mid_price": row["mid_price"]
    }
