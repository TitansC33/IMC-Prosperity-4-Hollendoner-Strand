# Round 1 Manual Challenge: "An Intarian Welcome" Auction Strategy

## Challenge Overview

**Two separate auctions** for DRYLAND_FLAX and EMBER_MUSHROOM.

### Key Rules
1. **You submit LAST** — you see all other bids/asks first
2. **Clearing price** = price that maximizes volume, ties broken at higher price
3. **You execute at clearing price** with allocation based on price/time priority
4. **Guaranteed buyback after auction**:
   - DRYLAND_FLAX: 30 XIRECs per unit (no fees)
   - EMBER_MUSHROOM: 20 XIRECs per unit (fee: 0.10 per unit traded)

---

## Strategy: Optimal Bidding

### Step 1: Estimate Clearing Price

When you submit your order, you see all existing bids/asks. Use this to estimate clearing price:

```python
# After seeing market
best_bids = [19, 18, 17, 16]      # Other people's buy orders
best_asks = [21, 22, 23, 24]      # Other people's sell orders

# Clearing price estimation
# For BUY order: clearing price ≈ median of existing asks (we're buying)
# For SELL order: clearing price ≈ median of existing bids (we're selling)

clearing_price_estimate = (best_bid + best_ask) / 2  # Conservative estimate
```

### Step 2: Calculate Profit Per Unit

```python
DRYLAND_FLAX:
  Profit per unit = 30 - clearing_price_estimate
  If estimate = 25:
    Profit = 30 - 25 = 5 per unit

EMBER_MUSHROOM:
  Profit per unit = (20 - 0.10) - clearing_price_estimate
  If estimate = 18:
    Profit = 19.90 - 18 = 1.90 per unit
```

### Step 3: Bid Aggressively if Profit > 0

**Two scenarios:**

#### Scenario A: Low competition (few bids/asks)
- Clearing price will be LOW
- Profit margin will be HIGH
- **Bid quantity = MAX** (as many units as possible)

#### Scenario B: High competition (many bids/asks)
- Clearing price will be HIGH (closer to 30 for FLAX, 20 for MUSHROOM)
- Profit margin will be LOW
- **Bid quantity = MODERATE** (scale to expected profit)

### Step 4: Bid Price Strategy

**Key insight**: Since you submit LAST:
1. Look at best bid in market
2. Bid 1 unit higher to frontrun them
3. Quantity = as much as we can sell for profit

```python
# Example: DRYLAND_FLAX
best_bid_in_market = 28
clearing_price_estimate = 28.5  # Likely to be ~this

if 30 - 28.5 > 0:  # Profit > 0
    bid_price = best_bid_in_market + 1  # 29, beat them by 1
    bid_quantity = 100  # Buy many, sell all at buyback
```

---

## Optimal Bidding Rules

| Situation | Action | Reasoning |
|-----------|--------|-----------|
| Clearing price < 25 (FLAX) | Bid MAX quantity | Huge profit margin |
| Clearing price 25-28 (FLAX) | Bid MEDIUM quantity | Good profit |
| Clearing price 28-30 (FLAX) | Bid LOW quantity | Thin margin, be selective |
| Clearing price > 30 (FLAX) | Skip or bid 1 unit | No profit |
| Clearing price < 18 (MUSHROOM) | Bid MAX quantity | High profit |
| Clearing price 18-19.9 (MUSHROOM) | Bid MEDIUM quantity | Moderate profit |
| Clearing price > 19.9 (MUSHROOM) | Skip | No profit after fees |

---

## Algorithm

```python
def optimal_bid(product, market_bids, market_asks, buyback_price, fee=0):
    """
    Calculate optimal bid for auction.
    
    product: "DRYLAND_FLAX" or "EMBER_MUSHROOM"
    market_bids: list of bid prices we see
    market_asks: list of ask prices we see
    buyback_price: price merchant guild buys at
    fee: transaction fee per unit
    """
    
    # 1. Estimate clearing price
    if not market_bids or not market_asks:
        clearing_price = buyback_price - 5  # Conservative estimate
    else:
        clearing_price = (max(market_bids) + min(market_asks)) / 2
    
    # 2. Calculate profit
    profit_per_unit = (buyback_price - fee) - clearing_price
    
    # 3. Decide quantity based on profit
    if profit_per_unit <= 0:
        return None  # Don't bid
    
    max_quantity = 1000  # System limit
    
    if profit_per_unit > 5:
        quantity = max_quantity  # Bid aggressively
    elif profit_per_unit > 2:
        quantity = max_quantity // 2
    else:
        quantity = max_quantity // 4
    
    # 4. Bid price: beat best bid by 1
    bid_price = max(market_bids) + 1 if market_bids else clearing_price + 1
    
    return {
        "price": bid_price,
        "quantity": quantity,
        "expected_profit": profit_per_unit * quantity
    }
```

---

## Example Scenarios

### Scenario 1: DRYLAND_FLAX with Light Competition
```
Market bids: [20, 19, 18]
Market asks: [26, 27, 28]

Clearing price estimate: (20 + 26) / 2 = 23
Profit per unit: 30 - 23 = 7
Bid: price=21, quantity=1000

Expected profit: 7 * 1000 = 7,000 XIRECs
```

### Scenario 2: EMBER_MUSHROOM with Heavy Competition
```
Market bids: [19, 18.5, 18]
Market asks: [20, 20.5, 21]

Clearing price estimate: (19 + 20) / 2 = 19.5
Profit per unit: 19.90 - 19.5 = 0.40
Bid: price=20, quantity=250

Expected profit: 0.40 * 250 = 100 XIRECs (low but positive)
```

### Scenario 3: DRYLAND_FLAX with Very Heavy Competition
```
Market bids: [28, 27.5, 27]
Market asks: [30, 31, 32]

Clearing price estimate: (28 + 30) / 2 = 29
Profit per unit: 30 - 29 = 1
Bid: price=29, quantity=50 (be selective)

Expected profit: 1 * 50 = 50 XIRECs (thin margin)
```

---

## Key Takeaways

1. **You have information advantage** — you submit last, see all market activity
2. **Bid aggressively when profit > 3 per unit** — maximize opportunity
3. **Bid conservatively when profit < 1 per unit** — avoid thin margins
4. **Never bid if profit ≤ 0** — guaranteed loss
5. **Volume scales with profit** — higher margins = larger quantities

---

## Expected Results

Based on historical patterns:

| Product | Expected Clearing Price | Profit Per Unit | Expected Quantity | Total Profit |
|---------|------------------------|-----------------|-------------------|--------------|
| DRYLAND_FLAX | 24-26 | 4-6 | 500-1000 | 2,000-6,000 |
| EMBER_MUSHROOM | 18-19 | 0.9-1.9 | 200-500 | 180-950 |
| **Combined Expected** | — | — | — | **2,500-7,000** |

---

## Implementation in Code

Add to `trader.py`:

```python
def get_auction_bid(self, product, market_data):
    """
    Generate optimal bid for manual challenge auction.
    """
    buyback_prices = {
        "DRYLAND_FLAX": 30,
        "EMBER_MUSHROOM": 20
    }
    fees = {
        "DRYLAND_FLAX": 0,
        "EMBER_MUSHROOM": 0.10
    }
    
    bids = market_data.get("bids", [])
    asks = market_data.get("asks", [])
    
    clearing_price = (max(bids) + min(asks)) / 2 if bids and asks else buyback_prices[product] - 3
    
    profit = (buyback_prices[product] - fees.get(product, 0)) - clearing_price
    
    if profit <= 0:
        return None
    
    # Scale quantity by profit
    if profit > 5:
        qty = 1000
    elif profit > 2:
        qty = 500
    else:
        qty = 100
    
    bid_price = max(bids) + 1 if bids else clearing_price + 1
    
    return {"price": bid_price, "quantity": qty}
```

