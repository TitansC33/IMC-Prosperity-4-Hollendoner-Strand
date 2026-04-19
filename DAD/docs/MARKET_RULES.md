# IMC Prosperity Market Rules & Mechanics

## Overview

IMC Prosperity is a simulated trading environment with 5 rounds. Each round introduces new products with unique characteristics. This document outlines the core market mechanics needed to build a backtester.

---

## Order Book Structure

### OrderDepth
Each timestep provides an `OrderDepth` object containing:

```python
order_depth.buy_orders   # Dict[price -> volume] - current bids
order_depth.sell_orders  # Dict[price -> volume] - current asks
```

- **Buy orders (bids)**: Prices at which market participants want to buy
- **Sell orders (asks)**: Prices at which market participants want to sell
- Both are dictionaries mapping price levels to volumes available at that level
- Multiple price levels exist simultaneously (depth > 1)

### Order Book Characteristics

- **Bid-Ask Spread**: Distance between best bid and best ask
- **Midprice**: `(best_bid + best_ask) / 2`
- **Market Maker Presence**: High-volume participants quoting consistently on both sides
- **Market Takers**: Participants who cross the spread to execute immediately
- **Quote Noise**: Orders placed significantly away from midprice, indicating mispricing or specific strategies

---

## Order Submission & Execution

### How Trading Works

1. **Your Algorithm Runs**: At each timestep, your `Trader.run()` method is called with market state
2. **You Submit Orders**: Return a list of `Order` objects with (product, price, quantity)
3. **Orders Are Matched**: Against the order book and market trades
4. **Trades Execute**: Immediately upon submission (no queuing)

### Order Types

- **Limit Orders**: Placed at specific price levels
  - Buy orders: Enter at or below specified price
  - Sell orders: Enter at or above specified price
  
- **Market Orders**: Implemented as limit orders that cross the spread
  - Sells below the best bid
  - Buys above the best ask

### Order Matching Logic

#### Priority 1: Order Depth (Order Book)
Orders are matched against limit order book volume first:
- An order matches only if price is exactly at a book level
- Matched at the full volume available at that price level
- Higher priority than market trades

#### Priority 2: Market Trades
If order depth doesn't fully satisfy your order, match against market trades:
- Market trades are executed buys/sells between bots at a given price
- Your order is matched at the trade price, not at an intermediate level
- Assumes traders are willing to take your order instead at trade price
- Only matched if price is at or better than trade price

**Example**: If you sell at 9999 and there's a market trade at 10000:
- You get filled at 9999 (your order price), not at 10000
- This matches actual Prosperity behavior

#### Halfway Matching (Optional)
Some backtester implementations allow "halfway" matching:
- Matches at midprice regardless of volume
- Useful for testing but less realistic

### Position Limits

Each product has a maximum position (long or short):

| Round | Product | Limit |
|-------|---------|-------|
| 0 (Tutorial) | EMERALDS | 80 |
| 0 | TOMATOES | 80 |
| 1 | ASH_COATED_OSMIUM | 80 |
| 1 | INTARIAN_PEPPER_ROOT | 80 |
| Default | Any unlisted | 50 |

**Enforcement Rules**:
- Position limit checked BEFORE orders are matched
- If your orders would cause position > limit, **all orders for that product are cancelled**
- Fills are also clamped during matching to never exceed limit
- Short selling is allowed (negative positions)

---

## Order Cancellation & Rejection

### Automatic Cancellation
If any of your orders for a product would cause position to exceed limits:
- **All subsequent orders** for that product in that submission are cancelled
- Orders already processed before hitting limit are kept

### Order Constraints
- Orders must have price > 0
- Orders must have quantity ≠ 0
- Negative quantities represent sells (shorting)
- Positive quantities represent buys

---

## Profit & Loss (PnL) Calculation

### PnL Components

Each product tracks four time series:

1. **Realized PnL** (`profits_by_symbol`)
   - Locked in when position reaches zero
   - Final PnL contribution

2. **Credit** (`credit_by_symbol`)
   - Amount borrowed to open position
   - Updated on each trade execution
   - Formula: `credit += -trade.price * trade.quantity`
   - For sells (short): negative quantity → positive credit
   - For buys (long): positive quantity → negative credit

3. **Unrealized PnL** (`unrealized_by_symbol`)
   - Mark-to-market value using current midprice
   - Only exists while position is open
   - Formula: `unrealized = position * current_midprice`

4. **Balance** (`balance_by_symbol`)
   - `balance = credit + unrealized`
   - Current total account value for that product

### Trade Execution PnL

When a trade executes:
```
current_pnl = -trade.price * trade.quantity
```

- **Selling (short)**: quantity is negative → pnl is positive (profit)
- **Buying (long)**: quantity is positive → pnl is negative (cost)
- PnL locked when position closes (reaches 0)

### Example

```
Trade 1: Buy 10 at 100
  credit = -1000
  unrealized = 10 * 105 = 1050 (if midprice now 105)
  balance = -1000 + 1050 = 50 (floating profit)

Trade 2: Sell 10 at 105
  Closing trade: realized_pnl += -105 * (-10) = 1050 - 1000 = 50
  Position now 0, locked in 50 shells profit
```

---

## Trading Mechanics

### Execution Guarantees
- **Instantaneous execution**: Orders filled immediately
- **Guaranteed fills**: Your orders are prioritized by the simulator
- **No slippage on limit orders**: You get exactly the price specified

### Slippage & Liquidity

- **Limited order book depth**: Only finite volume at each price level
- **Market orders cause slippage**: Crossing multiple price levels to fill large orders
- **Position limits create scarcity**: Can't accumulate large positions, restricts volume
- **Trade quantity constraints**: Per-product limits on how much you can trade

Example slippage:
```
Want to sell 50 units
- 20 at 10000 (available at best bid)
- 20 at 9999 (next level)
- 10 at 9998 (next level)
Average fill price: (10000*20 + 9999*20 + 9998*10) / 50 ≈ 9999.2
```

### Fair Value Estimation

Multiple approaches observed:

1. **Simple Midprice**: `(best_bid + best_ask) / 2`
   - Noisy from participants placing orders at unusual prices

2. **Market Maker Midprice**: 
   - High-volume participant's quote levels
   - Less noisy than raw midprice
   - Often the "true" fair value

3. **Volume-Weighted Average Price (VWAP)**:
   - Accounts for volume at each level
   - More robust to outlier orders

4. **Hidden Fair Value**:
   - Used internally by IMC for PnL calculations
   - Estimated by analyzing order book patterns and bot behavior

---

## Market Participants

### Types of Bots/Traders

1. **Market Makers**
   - Quote consistently on both sides
   - Large position limits relative to spread
   - Volume: typically 20-30 units per side
   - Low edge per trade, high frequency

2. **Scalpers/Takers**
   - Cross the spread for immediate profit
   - Small positions: 1-5 units
   - React to mispricings

3. **Arbitrageurs**
   - Trade across multiple exchanges (when applicable)
   - Exploit price discrepancies accounting for fees/tariffs
   - Multi-product trading strategies

4. **Mean Reversion Traders**
   - Trade when price deviates from fair value
   - Use statistical signals (z-scores, volatility)
   - Reduce positions at favorable prices

### Market Trade Data

Each state may include `market_trades`: trades executed between market participants
- Used to estimate fair value
- Useful for detecting scalping opportunities
- Volume and price patterns reveal market dynamics

---

## Time & Snapshots

### Timestep Model

- **Snapshot-based**: Market state provided at discrete timestamps
- **One execution per timestep**: Your orders execute once per snapshot
- **No continuous auctions**: No pre-open/continuous matching between timestamps
- **Trading day duration**: Usually 100,000+ timestamps per 3-day round

### Typical Trading Day
- 3 trading days per round
- Daily snapshots in historical data for backtesting
- Use for strategy calibration and parameter optimization

---

## Position Management Strategy

### Inventory Management

The key to profitable market making:

1. **Avoid extreme positions**: Reduces execution flexibility
2. **Clear unprofitable positions**: Take 0-edge trades to reduce inventory
3. **Position limits as hard constraints**: Reduces available volume for future trades

### Optimal Behavior

- Buy below fair value, sell above fair value
- When long: take any favorable sell opportunity to reduce position
- When short: take any favorable buy opportunity to reduce position
- Keep position near zero to maximize trading opportunities

### Dynamic Position Sizing

Scale order size based on inventory state:
```
if position > 0:
    buy_volume = small  # already long, focus on selling
    sell_volume = large # reduce position

elif position < 0:
    buy_volume = large  # reduce position
    sell_volume = small # already short, focus on buying
```

---

## Common Pitfalls in Backtesting

### PnL Discrepancies

- **Backtester vs IMC**: Backtester may match different trades than actual platform
- **Hidden fair value**: IMC uses internally-calculated fair value for unrealized PnL
- **Market maker identification**: Harder to isolate in some datasets

### Overfitting

- Historical data is limited (3 days per round)
- Market conditions change between rounds
- Use Monte Carlo simulation to generate synthetic paths
- Test across multiple day combinations

### Order Matching Assumptions

- Different backtester implementations have different matching logic
- "Halfway" matching is unrealistic but sometimes matches official behavior
- Verify against actual Prosperity results frequently

---

## Key Rules Summary

| Rule | Impact |
|------|--------|
| **Position limits enforced pre-matching** | Can't exceed limits even if volume exists |
| **All orders cancelled if any exceeds limit** | Must manage cumulative position across orders |
| **Orders match at exact prices only** | No partial fills at intermediate levels |
| **Immediate execution** | No queuing, orders execute instantly |
| **Negative quantity = sell/short** | Conventional sign convention |
| **PnL locked when position closes** | Only realized when reaching zero position |
| **Market trades considered after order depth** | Secondary liquidity source |
| **Position limits apply long AND short** | Can short up to limit with negative quantity |

---

## References

- **Official Docs**: Prosperity Wiki at prosperity.imc.com
- **Backtester Projects**: 
  - `backtest-imc-prosperity-2023` (GitHub)
  - `prosperity4btest` (PyPI)
- **Strategy Analysis**: Team write-ups from past competitions
- **Fair Value Research**: Analyze order book patterns in historical data
