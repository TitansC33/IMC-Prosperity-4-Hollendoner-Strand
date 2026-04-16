# Round 1 Strategy & Analysis

## Current Status
- **Algorithmic Target**: ≥200,000 XIRECs profit
- **Data Available**: 3 days historical (day -2, -1, 0)
- **Commodities**: ASH_COATED_OSMIUM, INTARIAN_PEPPER_ROOT

## Trader.py Current Implementation

### What's Working
- ✅ VWAP-based pricing (anchoring)
- ✅ Pennying logic (undercut by 1)
- ✅ Inventory leaning (reduces position bias)
- ✅ Safety checks (avoid extreme moves)
- ✅ Memory/history tracking

### Critical Issues
- ❌ **Position limit wrong**: Code uses ±20, should be ±80 (4x too conservative)
- ❌ **Only trades ASH_COATED_OSMIUM** — ignoring INTARIAN_PEPPER_ROOT
- ⚠️ **No directional strategy** for ASH_COATED_OSMIUM's "hidden pattern"

## Baseline Statistics (from load_data.py)

### Total Dataset
- **Total trades**: 2,276
- **Total price snapshots**: 60,000 (order book observations)

### ASH_COATED_OSMIUM
- Trades: 1,265
- Price range: 9,979 - 10,026 (spread: 47 units)
- **Interpretation**: Very tight cluster around 10,000 → stable, low volatility
- Suitable for: Market-making (current strategy)

### INTARIAN_PEPPER_ROOT
- Trades: 1,011
- Price range: 9,995 - 13,005 (spread: 3,010 units)
- **Interpretation**: HUGE range! Much more volatile than Osmium
- ⚠️ Either drifts/trends over time OR genuinely volatile
- May need directional strategy, not just market-making

## Pattern Analysis Results (from time_block_analysis.py + analyze_prices.py)

### 🎯 CRITICAL DISCOVERY: TWO COMPLETELY DIFFERENT COMMODITIES

## ASH_COATED_OSMIUM: STABLE MEAN-REVERSION ✅

**Across all 3 days (consistent pattern):**
- Day -2: 9979-10018 (range: 39 units), VWAP: 9998.26, +0.11% change
- Day -1: 9982-10019 (range: 37 units), VWAP: 10000.85, +0.09% change
- Day 0:  9981-10026 (range: 45 units), VWAP: 10001.64, -0.10% change

**Intraday pattern (50 blocks per day):**
- Each block: 1-14 trades, mostly +/- 0.3% change or less
- Momentum: Balanced (mix of ups/downs, ~50/50)
- **Price oscillates tightly around 10,000**

**Strategic Implication:**
- ✅ **PURE MARKET-MAKING** is optimal
- Buy at 9990-9995, sell at 10005-10010
- Capture 15-20 unit spread repeatedly
- Your current VWAP strategy is PERFECT for this
- Position limit of ±80 lets you scale this aggressively

---

## INTARIAN_PEPPER_ROOT: STRONG UPTREND ⚠️

**Across all 3 days (DRIFTING UPWARD):**
- Day -2: 9995-10994 (range: ~1,000 units!), VWAP: 10490.48, **+9.97% change**
- Day -1: 10995-12005 (range: ~1,010 units), VWAP: 11496.66, **+9.15% change**
- Day 0:  11998-13005 (range: ~1,007 units), VWAP: 12519.79, **+8.31% change**

**Intraday pattern (50 blocks per day - Day -2 example):**
- Block 1: Price ~10000 → 10026 (+0.31%)
- Block 5: Price ~10083 → 10101 (+0.18%)
- Block 10: Price ~10190 → 10199 (+0.09%)
- Block 15: Price ~10277 → 10291 (+0.14%)
- Block 20: Price ~10388 → 10390 (+0.02%)
- Block 25: Price ~10490 → 10486 (-0.04%)
- **Price drifts monotonically upward throughout each day**
- **Then each day starts ~500 units higher than previous day ended**

**Strategic Implication:**
- ❌ Market-making alone will NOT work here
- ✅ **TREND-FOLLOWING is optimal**
- Buy early in the day (catch the drift up)
- Hold through the intraday momentum
- Sell at end of day or next morning
- This is a **strong directional trend** across 3 days + intraday drift

---

## COMBINED STRATEGY FOR ROUND 1

| Commodity | Strategy | Rationale | Profit Potential |
|-----------|----------|-----------|-----------------|
| **ASH_COATED_OSMIUM** | Market-making (penny + VWAP) | Oscillates tightly, mean-reverting | Consistent small spreads × high volume |
| **INTARIAN_PEPPER_ROOT** | Trend-following (directional) | Drifts 9% per day, strong uptrend | Large directional moves × volume |

**Action Items:**
1. Keep ASH_COATED_OSMIUM logic as-is (market-making works)
2. Add trend detection to INTARIAN_PEPPER_ROOT (use EMA or simple momentum)
3. Buy PEPPER_ROOT early, hold through drift, sell at highs
4. Increase position limits to ±80 for both
5. This should hit the 200,000 XIREC target

### 2. INTARIAN_PEPPER_ROOT Behavior
- [ ] Verify it's truly "steady" as described
- [ ] Analyze bid-ask spread consistency
- [ ] Confirm market-making is the right approach

### 3. Correlation Analysis
- [ ] Are the two products correlated?
- [ ] Opportunities for arbitrage or hedging?

### 4. Manual Challenge Prep (Exchange Auction)
- [ ] Research typical clearing prices for DRYLAND_FLAX and EMBER_MUSHROOM
- [ ] Develop bidding strategy
- [ ] Calculate profit curves by clearing price

## Strategic Decisions

### Algorithmic Strategy (Draft)
- **ASH_COATED_OSMIUM**: 
  - If pattern detected: trend-follow or mean-revert (TBD after analysis)
  - If no pattern: market-make with wider margins
- **INTARIAN_PEPPER_ROOT**: 
  - Market-make with penny logic
  - Use full ±80 position limit

### Manual Strategy (TBD)
- Estimate clearing price distribution for each product
- Submit aggressive bids to win volume
- Capture arbitrage: (Buyback Price - Clearing Price) × Quantity

## Implementation Status ✅

### Algorithmic Trading - COMPLETE
1. ✅ Fixed position limits: **±80 for both commodities**
2. ✅ Refactored memory structure: separate tracking per commodity
3. ✅ ASH_COATED_OSMIUM: Market-making (VWAP + pennying + inventory leaning)
4. ✅ INTARIAN_PEPPER_ROOT: Trend-following (EMA + momentum + inventory mgmt)
5. ✅ Helper functions: `calculate_vwap()`, `calculate_ema()`
6. ✅ Dual commodity support in `run()` method

### Backtest Results ✅

**Recommended Configuration: Aggressive (±80)**
- Expected Portfolio Value: **+340,091 XIRECs**
- Target: 200,000 XIRECs
- **Result: 170% of target** ✅
- Exceeds by: +140,091 XIRECs

**Strategy Validation:**
- ✅ All 5 tested configurations exceed 200k target
- ✅ Margin of safety: 70% buffer
- ✅ Market-making + trend-following combination validated
- ✅ Ready for production

### Files
- `trader.py`: Dual-commodity strategy (production ready)
- `scripts/backtest_v2.py`: Validated strategy on historical data
- `ROUND1_STRATEGY.md`: This document

### Next: Manual Challenge Auction Strategy
Need to develop bidding for:
- **DRYLAND_FLAX**: Buyback at 30 per unit (no fees)
- **EMBER_MUSHROOM**: Buyback at 20 per unit (fee: 0.10/unit = 19.90 net)
