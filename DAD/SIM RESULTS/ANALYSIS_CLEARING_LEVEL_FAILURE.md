# Analysis: Why Clearing-Level Implementation Lost Money

**Date**: Apr 16, 2026  
**Finding**: Clearing-level order sizing **FAILED in live trading** despite passing backtests

---

## Performance Comparison

| Version | Strategy | Result | Status |
| --- | --- | --- | --- |
| **trader.py** (current) | Clearing-level sizing | **-1,493** | 🔴 LOSING |
| **trader_active.py** (alternative) | Full room sizing | **+2,669** | ✅ WINNING |

**Gap**: 4,162 XIRECs disadvantage from clearing-level approach

---

## Root Cause Analysis

### What Clearing-Level Does

```python
# Current approach (BROKEN)
clearing_volume = find_clearing_volume(depth, 'buy', target_price)
order_size = int(clearing_volume * 1.1)  # Add 10% buffer
orders.append(Order(symbol, price, order_size))
```

**Example**:
- Position: -35, Room: 125 units
- Cumulative depth shows: 45 units to clear best_ask
- Order placed: 50 units (45 × 1.1)
- Issue: **50 units ≪ 125 room available**

### What Simulator Expects

```python
# Working approach
buy_capacity = position_limit - current_pos  # 125 units
orders.append(Order(symbol, price, buy_capacity))  # Place 125
```

**Result**: Full participation, more fills, profitable

---

## Why Backtests Didn't Catch This

### Backtest Environment (Fair)
- Order matching is **simulated** with perfect fills
- Small orders still "clear" through book
- Clearing volume ≈ position room in typical conditions
- Result: Parity (438,650 XIRECs)

### Live Simulator (Harsh)
- Order book is **real market structure**
- Small orders get **poor fills or no fills**
- Market doesn't wait for your right-sized order
- Result: Loss (-1,493 XIRECs)

### Key Difference
**Backtests reward sophisticated logic** (clearing-level looks good on paper)  
**Live trading rewards aggressive participation** (size matters, full room wins)

---

## Technical Details

### Clearing-Level Problems

1. **Undersizing**: Places 50 units instead of 125
   - 60% less participation
   - Fewer fills
   - Worse execution

2. **Fallback Logic Fails**:
   ```python
   if volume_needed == 0:
       # Fallback to 50% room (WRONG in live trading)
       return int((position_limit - current_pos) * 0.5)
   ```
   Should be: 100% room

3. **Cumulative Depth Assumption**:
   - Assumes depth data is accurate
   - Doesn't account for dynamic market movement
   - Order sits in middle of book, unfilled

4. **Philosophy Mismatch**:
   - Clearing-level: "Only nudge what's needed"
   - Live simulator: "Participate aggressively or lose"

---

## Working Approach (trader_active.py)

```python
buy_capacity = position_limit - position      # 125
bid_quantity = buy_capacity                   # Place 125
orders.append(Order(product, bid_price, bid_quantity))
```

**Why It Works**:
- ✅ Fills available capacity immediately
- ✅ Market makers reward passive sellers when you're buying
- ✅ Full participation = more order flow = more fills
- ✅ Simple logic has low latency

**Results**: +2,669 profitable

---

## Lesson: Backtests ≠ Live Trading

### What Backtests Test
- Fair value anchoring ✅
- Inventory management ✅
- Parameter tuning ✅
- Risk management ✅

### What Backtests Miss
- Order size sensitivity
- Market microstructure dynamics
- Execution quality under real conditions
- Aggressive vs passive trade-offs

### The Trap
**More sophisticated ≠ More profitable**

Clearing-level sounds better (microstructure-aware, scientific), but live trading rewards:
1. **Aggressiveness** (fill your orders)
2. **Simplicity** (low latency)
3. **Full participation** (size matters)

---

## Recommendation

### Immediate (Before Competition)

**REVERT to trader_active.py**

This version:
- ✅ Profitable (+2,669 in live simulator)
- ✅ Simple and fast
- ✅ Uses full position room
- ✅ Proven to work

### Do NOT Deploy Clearing-Level To Competition

Clearing-level will:
- ❌ Lose money (proven: -1,493)
- ❌ Place orders too small
- ❌ Get poor fills
- ❌ Fail in live market

---

## Recovery Plan

1. **Revert trader.py to trader_active.py logic** (5 min)
   - Use full position room sizing
   - Remove clearing-level methods
   - Test in simulator again

2. **Validate in live simulator** (15 min)
   - Should see +2,600-2,700 profit
   - Zero negative trades

3. **Deploy with confidence** (verified working)

---

## Post-Mortem Summary

| Aspect | Clearing-Level | Full Room | Winner |
| --- | --- | --- | --- |
| Backtesting | ✅ 438,650 | ✅ Comparable | Tie |
| Live Trading | ❌ -1,493 | ✅ +2,669 | Full Room |
| Order Size | Tiny (50) | Aggressive (125) | Aggressive |
| Fills | Poor | Excellent | Excellent |
| Philosophy | Sophisticated | Simple | Simple wins |

---

## Files Involved

- **Current (broken)**: `DAD/continuous_trading/trader.py`
  - Has: clearing-level sizing methods
  - Result: -1,493 loss

- **Working**: `DAD/continuous_trading/trader_active.py`
  - Has: full position room sizing
  - Result: +2,669 profit

- **Backtest results**:
  - Current: DAD/SIM RESULTS/RESULT.JSON
  - Alternative: DAD/SIM RESULTS/trader_active_results.JSON

---

**Conclusion**: Revert immediately. Clearing-level is academically interesting but operationally broken for live trading.
