# IMC Prosperity Trading Glossary & Order Matching Logic

## Order Matching Priority (IMC Prosperity 3)

### Matching Flow Hierarchy

When orders are placed by `Trader.run()` at a given timestamp, they are matched in the following priority order:

```
1. Order Depths (PRIMARY)
   └─ If an order can be filled COMPLETELY using volume in the relevant order depth,
      market trades are NOT considered

2. Market Trades (SECONDARY)  
   └─ Only matched if the order cannot be fully filled by order depths
   └─ Assumes buyers and sellers of market trades are willing to trade at their
      trade price and volume
```

### Key Matching Rules

#### Price Matching
- Market trades are matched at **the price of YOUR orders**, not the market trade price
- Example: If you place a sell order for €9 and there's a market trade at €10, your order fills at €9
  - This is true even though a buyer exists willing to pay €10
  - Behavior appears consistent with official Prosperity environment

#### Limit Enforcement
- **Enforced BEFORE orders are matched** to order depths
- If your position would exceed the limit (assuming all orders get filled), **all orders for that product are canceled**
- Prevents over-exposure to position limits

#### Order Book Depth Priority
- Orders from **existing order depths take priority** over new market trades
- Once order depth volume is exhausted, remaining unfilled quantity can be matched against market trades

---

## Price-Time-Priority Principle

### Standard Exchange Matching

Orders are ranked deterministically using **Price-Time-Priority**:

#### Ranking Rules
1. **By Side (Buy/Sell)**
   - Buy orders: Ranked highest to lowest price
   - Sell orders: Ranked lowest to highest price

2. **By Price Level**
   - Best price gets priority first
   - Within same price level, orders are prioritized by timestamp

3. **By Timestamp**
   - **Oldest orders get priority** (FIFO within same price)
   - Time priority applies ONLY when prices are identical

#### Fill Execution Order
When matching multiple orders at different price levels:
1. Fill at best price level first
2. Once all orders at that price level are exhausted, move to next price level
3. Continue until order quantity reaches zero or order is marked IOC (Immediate-or-Cancel)

---

## Market Trades Matching Configuration

### Match Trades Options

In backtester, control market trade matching with `--match-trades` flag:

#### `--match-trades all` (DEFAULT)
- Match market trades with prices **equal to or worse** than your quotes
- Most permissive setting
- Example: Buy order at €10 matches trades at €10 or higher

#### `--match-trades worse`
- Match market trades **strictly worse** than your quotes  
- Based on Linear Utility's Prosperity 2 write-up
- Example: Buy order at €10 only matches trades at €11+

#### `--match-trades none`
- **Do not match** market trades against orders
- Only use existing order depths for fills
- Most restrictive setting

### Usage Example
```bash
# Default behavior
prosperity3bt trader.py 1

# Disable market trade matching
prosperity3bt trader.py 1 --no-trades-matching

# Explicit configuration
prosperity3bt trader.py 1 --match-trades all
prosperity3bt trader.py 1 --match-trades worse
prosperity3bt trader.py 1 --match-trades none
```

---

## Order Execution Restrictions

### Fill-or-Kill (FOK)
- Order must execute **completely immediately** or be canceled
- Partial fills NOT allowed
- Deleted if cannot be fully matched

### Immediate-or-Cancel (IOC)
- Execute immediately for any possible quantity
- **Partial fills ARE allowed**
- Delete any remaining quantity if not fully matched
- Can create multiple trades against multiple orders

### All-or-None (AON)
- Similar to FOK
- Must execute at single price
- Deleted if cannot be fully matched at one price level

### Good-for-Day / Normal (NON)
- Order remains in book until end of day or fully matched
- Partial fills allowed
- No immediate cancellation requirement

---

## Position Limits

### Limit Enforcement Timing
- **Checked BEFORE order matching** begins
- If all submitted orders would cause position to exceed limit → **all orders are canceled**
- Prevents ANY positions beyond limits

### Conversion Limits
- Some products have conversion limits (e.g., 10 units per timestep)
- **Separate from position limits**
- Controls rate of inventory adjustment

---

## Order Book Structure

### Order Depth Components

```
Order Depth = {
  "asks": {
    price: volume,  # Sell orders (lowest prices first)
    ...
  },
  "bids": {
    price: volume,  # Buy orders (highest prices first)  
    ...
  }
}
```

### Market Trades Structure

```
Market Trades = [
  {
    "buyer": trader_id,
    "seller": trader_id,
    "symbol": product,
    "price": trade_price,
    "quantity": trade_volume,
    "timestamp": timestamp
  },
  ...
]
```

---

## Execution Sequence Per Timestep

### Processing Order
1. **Clear** all previous orders
2. **Process** deep-liquidity makers' orders (market makers)
3. **Process** occasional taker orders
4. **Process** your bot's actions (Trader.run output)
5. **Process** other bots' orders (usually takers)

### Key Implication
- **No race conditions** between you and other bots
- You get full snapshot of order book before matching
- Order cancellation/resubmission within same timestep possible
- Speed advantages minimal in this environment

---

## Trading Strategy Implications

### Market Making Strategy
1. Take any favorable trades available (buy below fair value, sell above)
2. Place passive quotes slightly better than existing liquidity
3. Manage inventory to maintain near-zero position
4. Adjust quotes based on observed order flow

### Arbitrage Strategy
- **Location Arbitrage**: Trade between local exchange and external fixed prices
- **ETF Arbitrage**: Exploit spreads between basket and synthetic value
- **Informed Trading Detection**: Identify and predict trader behavior patterns

### Key Optimization Areas
- **Parameter Tuning**: Test threshold combinations across stable regions (avoid overfitting)
- **Position Management**: Flatten positions when approaching limits
- **Order Placement**: Consider both fill probability and profit per trade
- **Inventory Management**: Use mean-reversion strategies when inventory skewed

---

## Common Products & Behavior

### Rainforest Resin
- **Fixed true price**: 10,000
- **Strategy**: Simple market making around fair value
- **Expected profit**: ~39,000 SeaShells/round

### Kelp
- **Price movement**: Slow random walk
- **Similar to Rainforest Resin** with minor adjustments
- **Key difference**: Account for price movements in quotes

### Squid Ink
- **Characteristics**: Tight spreads + occasional sharp jumps
- **Challenge**: Higher variance despite no systematic losses
- **Edge**: Detect informed trader behavior patterns

### ETF/Baskets
- **Structure**: Multiple constituent combinations that don't convert directly
- **Opportunity**: Exploit deviations between basket and synthetic value
- **Informed signal**: Use detected trader behavior to bias thresholds

---

## Testing & Validation

### Backtester Usage
```bash
# Basic run
prosperity3bt trader.py <day>

# Run on specific time period
prosperity3bt trader.py 1-5  # Run through day 5

# Different match-trades settings
prosperity3bt trader.py 1 --match-trades worse
prosperity3bt trader.py 1 --match-trades none
```

### Parameter Selection
- **Prioritize landscape stability** over peak performance
- **Avoid overfitting** by choosing flat regions of good performance
- **Test multiple parameter combinations** before live rounds
- **Monitor in real-time** and adjust based on latest data

---

## References

- **IMC Prosperity 3 Backtester**: https://github.com/jmerle/imc-prosperity-3-backtester
- **PyPI Package**: https://pypi.org/project/prosperity3bt/
- **Official Order Matching**: Uses Price-Time-Priority with order depth priority over market trades
