# Simulator Testing Plan - Tutorial Round ("Simulator Practice")

## Overview

The Tutorial Round tests EMERALDS (stable) and TOMATOES (fluctuating) with ±80 position limits.

This is your **sandbox to validate** trader.py before Round 1 begins. We'll test 3 configurations (A, B, C) to identify optimal parameter settings.

---

## Key Variables to Test

### Primary Tuning Parameters

These are the knobs you can turn in trader.py to optimize performance:

| Parameter | Location | Current Value | Range | Impact |
|-----------|----------|----------------|-------|--------|
| **EMA Alpha** (trend sensitivity) | Line ~148 | 0.2 | 0.1-0.5 | Higher = more responsive, noisier |
| **VWAP Window** (fair value stability) | Line ~166 | 20 trades | 10-40 | Larger = smoother, slower |
| **Inventory Bias** (rebalancing speed) | Line ~201 | 0.9 | 0.5-1.5 | Higher = more aggressive rebalancing |
| **Max Distance** (safety check) | Line ~177 | 20 units | 10-50 | Larger = allows wilder moves |
| **Penny Offset** (queue position) | Lines ~196-197 | ±1 | 0-3 | Higher = further from spread |
| **History Trim Window** | Lines ~166, ~229 | 20, 50 | 10-100 | Larger = more history, slower response |

---

## Three Test Configurations

### **TEST A: Conservative (Stable Strategy)**
**Goal**: Maximize consistent small profits, minimize risk

```python
# Configuration A - Conservative
EMA_ALPHA = 0.15                    # Slower trend detection (less noise)
VWAP_WINDOW = 30                    # Larger window (smoother fair value)
INVENTORY_BIAS = 1.2                # Aggressive rebalancing
MAX_DISTANCE = 50                   # Allow wilder moves (less interference)
PENNY_OFFSET = 1                    # Stay close to spread
HISTORY_WINDOW = 20, 40             # Smaller history
```

**Strategy Logic**:
- Trend detection is slower → misses some moves but fewer false signals
- VWAP is smoother → fair value is very stable
- Aggressive inventory rebalancing → forces position back to zero
- Wilder moves allowed → less likely to reject profitable orders

**Expected Profile**:
- ✓ Lower volatility
- ✓ More consistent daily P&L
- ✓ Fewer position limit violations
- ✗ May miss quick directional moves (TOMATOES)
- ✗ Lower total profit potential

---

### **TEST B: Aggressive (Growth Strategy)**
**Goal**: Maximize directional moves, accept higher volatility

```python
# Configuration B - Aggressive
EMA_ALPHA = 0.35                    # Faster trend detection (more responsive)
VWAP_WINDOW = 15                    # Smaller window (faster adaptation)
INVENTORY_BIAS = 0.5                # Conservative rebalancing (allow drift)
MAX_DISTANCE = 15                   # Stricter safety (prevent extreme moves)
PENNY_OFFSET = 2                    # Further from spread (reduce execution risk)
HISTORY_WINDOW = 10, 30             # Very small history (super responsive)
```

**Strategy Logic**:
- Trend detection is faster → catches TOMATOES uptrend quickly
- VWAP adapts faster → responds to price changes instantly
- Conservative rebalancing → allows positions to run with trends
- Stricter safety checks → protects against flash crashes

**Expected Profile**:
- ✓ Higher total profit (ride trends longer)
- ✓ Faster response to price changes
- ✓ Better for volatile (TOMATOES) trading
- ✗ Higher daily volatility
- ✗ More position oscillation
- ✗ Greater drawdown risk

---

### **TEST C: Balanced (Optimized Strategy)**
**Goal**: Best of both worlds - growth with stability

```python
# Configuration C - Balanced (Recommended for Round 1)
EMA_ALPHA = 0.25                    # Medium trend sensitivity
VWAP_WINDOW = 20                    # Standard fair value window
INVENTORY_BIAS = 0.85               # Moderate rebalancing
MAX_DISTANCE = 25                   # Balanced safety
PENNY_OFFSET = 1                    # Standard queue position
HISTORY_WINDOW = 20, 50             # Current settings (proven)
```

**Strategy Logic**:
- Balanced across all parameters
- Proven in backtest (340k result)
- Good trend capture with stability

**Expected Profile**:
- ✓ Strong consistent performance
- ✓ Balanced risk/reward
- ✓ Works well for both EMERALDS + TOMATOES
- ✓ Previously validated

---

## Testing Sequence

### Phase 1: Individual Tests (Sequential)

**Test A: Conservative**
- Duration: 10 iterations (full day simulation)
- Measure:
  - Total P&L
  - Daily P&L consistency (std deviation)
  - Max drawdown
  - Position oscillation (times position reverses)
  - Number of trades
- Expected: ~2-4k XIRECs, very smooth

**Test B: Aggressive**
- Duration: 10 iterations
- Same measurements
- Expected: ~5-8k XIRECs, higher volatility

**Test C: Balanced**
- Duration: 10 iterations
- Same measurements
- Expected: ~4-6k XIRECs, smooth growth

### Phase 2: Combined Comparison (Side-by-Side)

Run all three simultaneously in separate simulator windows/tabs:
- Compare final balances
- Compare P&L curves
- Compare trade counts
- Compare drawdowns

**Winner determination**:
```
Score = (Total_PnL × 0.5) + (Consistency × 0.3) + (Efficiency × 0.2)
Where:
- Total_PnL = final balance
- Consistency = inverse of std deviation
- Efficiency = PnL per trade
```

---

## How to Implement Test Configurations

### Step 1: Create test versions of trader.py

```bash
# Keep original
cp trader.py trader_original.py

# Create test variants
cp trader.py trader_test_A.py
cp trader.py trader_test_B.py
cp trader.py trader_test_C.py
```

### Step 2: Modify each file

**In trader_test_A.py (Lines ~148, ~166, ~177, ~196-197, ~201):**
```python
# Line ~148 - EMA Alpha
def calculate_ema(self, prices, alpha=0.15):  # Changed from 0.2

# Line ~166 - VWAP Window
memory[f"{symbol}_history"] = memory[f"{symbol}_history"][-30:]  # Changed from 20

# Line ~177 - Max Distance
max_distance = 50  # Changed from 20

# Line ~201 - Inventory Bias
inventory_bias = current_pos * 1.2  # Changed from 0.9

# Line ~196-197 - Penny Offset
penny_buy_price = best_bid + 1    # Keep at 1
penny_sell_price = best_ask - 1   # Keep at 1

# Line ~229 - History Window
memory[f"{symbol}_history"] = memory[f"{symbol}_history"][-40:]  # Changed from 50
```

**Repeat for trader_test_B.py and trader_test_C.py** with their respective parameters.

### Step 3: Upload & Run

1. Upload trader_test_A.py to simulator
2. Run full day simulation
3. Record results (P&L, trades, drawdown)
4. Repeat for B and C

---

## What to Measure

### Core Metrics

| Metric | Formula | What It Tells You |
|--------|---------|-------------------|
| **Total P&L** | Final balance - 100k | Raw profitability |
| **Daily Consistency** | Std dev of daily P&L | Stability |
| **Sharpe Ratio** | (Avg daily return) / (Std dev) | Risk-adjusted return |
| **Max Drawdown** | Lowest point from peak | Worst-case loss |
| **Win Rate** | Trades with profit / total trades | Success frequency |
| **Trade Count** | Total trades executed | Activity level |
| **Avg Trade Size** | Total quantity / trade count | Position sizing |

### Commodity-Specific Insights

**EMERALDS Analysis:**
- Stable price → market-making should dominate
- Look for: small frequent profits
- Success metric: >500 trades with avg 5-10 units per trade

**TOMATOES Analysis:**
- Fluctuating price → trend-following should dominate
- Look for: larger moves caught
- Success metric: <50 trades but larger sizes

---

## Optimization Framework

### After Testing, Ask These Questions:

#### 1. **Profitability Analysis**
- Which config made the most profit? (A, B, or C)
- Was it consistent across both days of simulator?
- Did one commodity outperform with a specific config?

#### 2. **Risk Analysis**
- Which had lowest drawdown?
- Which was smoothest (lowest std dev)?
- Did any config violate position limits?

#### 3. **Execution Quality**
- Which filled more orders (higher trade count)?
- Which had better average fill prices?
- Which config undercut competitors most effectively (pennying)?

#### 4. **Trend Capture**
- For TOMATOES: did any config catch the full uptrend?
- For EMERALDS: did any reduce oscillation whip-saws?
- Which EMA alpha found the sweet spot?

---

## Further Optimization Ideas

After testing A, B, C, look for refinement opportunities:

### 1. **Asymmetric Parameters** (ADVANCED)
Different settings for EMERALDS vs TOMATOES:

```python
if symbol == "EMERALDS":
    ema_alpha = 0.15  # Slower (stable commodity)
    inventory_bias = 1.2  # Aggressive rebalancing
else:  # TOMATOES
    ema_alpha = 0.35  # Faster (volatile commodity)
    inventory_bias = 0.5  # Allow trending positions
```

**Expected Impact**: +5-10% improvement by tuning each commodity separately

---

### 2. **Dynamic Parameters** (ADVANCED)
Adjust parameters based on market conditions:

```python
# If price volatility is high → use conservative settings
# If price is trending → use aggressive settings
# If price is oscillating → use balanced settings

volatility = calculate_volatility(prices[-20:])
if volatility > threshold:
    ema_alpha = 0.15  # Reduce noise
else:
    ema_alpha = 0.35  # Increase responsiveness
```

**Expected Impact**: +10-15% improvement via adaptive strategy

---

### 3. **Order Sizing Optimization** (ADVANCED)
Currently: orders max out at room_to_buy/room_to_sell (full available room)

Optimization: Scale by confidence/profit potential

```python
profit_potential = abs(current_price - fair_value)
if profit_potential > 5:
    size = room_to_buy * 1.0  # Bid full size
elif profit_potential > 2:
    size = room_to_buy * 0.7  # Bid 70%
else:
    size = room_to_buy * 0.3  # Bid 30% (low confidence)
```

**Expected Impact**: +3-5% via smarter sizing

---

### 4. **Spread Targeting** (ADVANCED)
Currently: penny logic (always ±1 from best)

Optimization: Target minimum spread width

```python
current_spread = best_ask - best_bid
if current_spread < 10:
    penny_offset = 2  # Wider spreads → better margins
elif current_spread > 30:
    penny_offset = 0  # Tight spreads → be aggressive
else:
    penny_offset = 1  # Medium
```

**Expected Impact**: +5-8% via spread adaptation

---

### 5. **Position-Dependent Pricing** (ADVANCED)
Currently: inventory bias is linear (`position × 0.9`)

Optimization: Accelerate rebalancing at extremes

```python
# When close to limits (±70+), push prices harder
if abs(current_pos) > 70:
    inventory_bias = current_pos * 1.5  # Strong push back
elif abs(current_pos) > 40:
    inventory_bias = current_pos * 0.9  # Normal
else:
    inventory_bias = current_pos * 0.5  # Weak (allow drift)
```

**Expected Impact**: +5-10% via smarter rebalancing

---

## Testing Timeline

```
Day 1: Run Tests A, B, C (individual)
├─ A: Conservative
├─ B: Aggressive
└─ C: Balanced

Day 2: Compare & Analyze Results
├─ Measure all metrics
├─ Determine winner
└─ Identify optimization opportunities

Day 3: Implement Optimization
├─ Choose best variant or hybrid
├─ Test refined version
└─ Finalize for Round 1

Round 1 (Apr 14-17): Deploy optimized trader.py
```

---

## Success Criteria

**Minimum Success (Tutorial Round):**
- All three configs should profit
- All three should stay within position limits
- Avg P&L > 2,000 XIRECs (10x higher than backtest daily rate)

**Expected Success:**
- Config C (Balanced) > Config A (Conservative)
- Config B (Aggressive) > Config C if TOMATOES trend is strong
- One config should clearly outperform

**Optimization Win:**
- After refinement, new config > best original by 5%+
- Consistency improves (lower drawdown)

---

## Execution Checklist

- [ ] Create trader_test_A.py with conservative parameters
- [ ] Create trader_test_B.py with aggressive parameters
- [ ] Create trader_test_C.py with balanced parameters
- [ ] Upload Test A to simulator, run full day
- [ ] Record: Total P&L, trade count, max drawdown, daily consistency
- [ ] Upload Test B to simulator, run full day
- [ ] Record metrics for Test B
- [ ] Upload Test C to simulator, run full day
- [ ] Record metrics for Test C
- [ ] Compare all three side-by-side
- [ ] Identify winner and optimization opportunities
- [ ] (Optional) Implement one optimization refinement
- [ ] (Optional) Test refined version
- [ ] Deploy final trader.py to Round 1

---

## Expected Results

### Simulator Performance Estimates

**Test A (Conservative):**
- Total P&L: 2,000-3,000 XIRECs
- Daily Consistency: Very high (std dev < 500)
- Max Drawdown: <1,000 XIRECs
- Trade Count: 600+ (frequent small trades)

**Test B (Aggressive):**
- Total P&L: 3,500-5,000 XIRECs  
- Daily Consistency: Medium (std dev 500-1,500)
- Max Drawdown: 1,000-2,000 XIRECs
- Trade Count: 300-400 (fewer but larger trades)

**Test C (Balanced):**
- Total P&L: 2,500-4,000 XIRECs
- Daily Consistency: High (std dev 300-800)
- Max Drawdown: <1,500 XIRECs
- Trade Count: 400-500 (balanced activity)

**Expected Winner:** Test C or Test B (depending on TOMATOES volatility)

---

## Strategy Enhancements

### **✅ INCLUDED: Volatility-Based Scaling**
**Status**: Already implemented in current trader.py

**What it does**: Scale position sizes based on current market volatility
- High volatility → smaller positions (reduce risk)
- Low volatility → larger positions (maximize opportunity)

**Implementation Details**:
```python
# In trader.py (lines 157-170)
def calculate_volatility(self, prices):
    """Calculate volatility (std dev) for position sizing"""
    if len(prices) < 2:
        return 0
    return np.std(prices[-20:])

def get_position_scale(self, volatility, base_volatility=15):
    """Scale position size based on volatility"""
    if volatility < base_volatility * 0.7:
        return 1.0  # Low volatility: full size
    elif volatility > base_volatility * 1.3:
        return 0.6  # High volatility: 60% size
    else:
        return 0.8  # Medium: 80% size
```

**How it works**:
- Osmium (Stable): base_volatility=15, scales between 60%-100% based on market conditions
- Pepper (Volatile): base_volatility=300, higher threshold allows larger positions even in volatile markets

**Applied in**: Both `trade_osmium_market_making()` (line 221-227) and `trade_pepper_trend_following()` (line 281-287)

**Expected benefit**: Smoother returns, reduced drawdown, fewer large swings

---

## Alternative Strategy Enhancements (Optional Advanced Options)

After testing A/B/C in the simulator, you can consider these **additional** enhancements:

---

### **Option 2: Mean Reversion Enhancement** (Osmium only)
**What it does**: Detect extreme price overshoots and counter-trade aggressively
- Normal price movement: standard market-making
- Extreme overshoot (>3 std dev): aggressive counter-trade

**Implementation**: ~45-60 minutes
- Calculate rolling std dev
- Detect extremes
- Place larger orders at extremes
- Add safety checks to prevent over-trading

**Expected benefit**: +5-15% on Osmium profits (catches reversals)

---

### **Option 3: Adaptive EMA Alpha** (Pepper only)
**What it does**: Change trend sensitivity based on market conditions
- Trending market: slower EMA (catch longer trends)
- Choppy market: faster EMA (reduce false signals)

**Implementation**: ~20-30 minutes
- Measure trend strength (price consistently above/below EMA)
- Adjust alpha accordingly
- Test in simulator

**Expected benefit**: +3-8% on Pepper profits (fewer whipsaws)

---

### **Option 4: Pairs Trading / Correlation Hedge**
**What it does**: If Osmium and Pepper are correlated, hedge one with the other
- Reduces portfolio variance
- Allows taking more risk in each

**Implementation**: ~1-2 hours
- Analyze correlation in simulator data
- Set up hedge ratios
- Complex implementation

**Expected benefit**: Unknown (depends on correlation - probably low)

---

### **Quick Decision Matrix**

| Option | Status | Benefit | Risk | Action |
| --- | --- | --- | --- | --- |
| Volatility-Based Scaling | ✅ **INCLUDED** | Already active | Low | Monitor in Round 1 |
| Mean Reversion Enhancement | Optional | +5-15% | Low-Medium | Consider if time allows |
| Adaptive EMA Alpha | Optional | +3-8% | Low | Consider if time allows |
| Pairs Trading | Optional | Unknown | Medium-High | Skip (too complex) |

---

## Next Steps After Simulator

1. **If Test C wins**: Deploy as-is to Round 1 (high confidence)
2. **If Test B wins**: Consider adding Volatility-Based Scaling
3. **If Test A wins**: Something unusual in simulator data (investigate)
4. **Optional**: Add other enhancements if time permits
5. **General**: Expect Round 1 profits ~100x higher than simulator (larger market, more participants)

---

**Goal**: Complete all 3 tests before Round 1 begins (Apr 14).  
**Status**: Ready to begin - pick which config to test first!
