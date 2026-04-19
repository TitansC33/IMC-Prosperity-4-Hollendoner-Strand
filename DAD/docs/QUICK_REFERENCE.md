# Quick Reference Guide - Backtesting System

## 30-Second Quick Start

```bash
cd DAD/continuous_trading
python backtest_v2_with_matching.py
```

**Look for**: `Portfolio Value: +286,351` and `Target: VIABLE`  
✅ If > 200,000 XIRECs → Your strategy works!

---

## The 3 Tools

| Tool | Command | Purpose | Time |
|------|---------|---------|------|
| **Backtest** | `python backtest_v2_with_matching.py` | Test current strategy | 30s |
| **Grid Search** | `python grid_search_with_matching.py` | Find best parameters | 5min |
| **Loop Test** | `python run_backtest_loops.py --iterations 10` | Validate robustness | 3min |

---

## Common Commands

### Daily Check (5 min)
```bash
python backtest_v2_with_matching.py
# Check: Portfolio Value > 200,000? YES → Good day!
```

### Find Best Parameters (5 min)
```bash
python grid_search_with_matching.py
# Check: Ranking - which config is #1?
# Compare with Phase 2 (±80/±80) - is it still strong?
```

### Stress Test Before Competition (10 min)
```bash
python run_backtest_loops.py --iterations 20 --randomize-order --randomize-depth
# Check: All runs > 200k? Std Dev < 5%? → Ready to deploy!
```

### Test Custom Position Limits
```bash
python run_backtest_loops.py --iterations 5 --osmium-limit 90 --pepper-limit 90
```

### Test Different Matching Mode
```bash
python run_backtest_loops.py --iterations 5 --match-mode worse
```

---

## Output Interpretation (30 seconds)

### Backtest Output
```
Final Portfolio Value: +286,351     ← Should be > 200,000
Final Positions: Osmium= -57        ← Final inventory
Trades executed: 1271               ← Number of orders
Osmium - Filled: 734, Rejected: 0   ← Execution quality
```

**✅ Good Signs**:
- Portfolio Value > 200,000
- Rejected = 0
- Fill rate > 50%

**❌ Bad Signs**:
- Portfolio Value < 200,000
- High rejections
- Very low fill rate

### Grid Search Output
```
1. Very Aggressive (90/90)          ← Best performing
   Portfolio Value: +306,755
2. Aggressive (80/80)               ← Phase 2 optimal
   Portfolio Value: +286,351
```

**Decision**:
- If #1 is significantly better AND std dev acceptable → Switch to #1
- If #2 is safe/proven → Keep Phase 2 (±80/±80)

### Loop Test Output
```
Mean:              286,150
Std Dev:            226      ← Should be < 5% of mean (14,300)
Runs above target:  20/20    ← Should be 100%
```

**✅ If**:
- Mean > 200,000
- Std Dev < 5% of mean
- All runs > 200,000

**Then**: Ready for competition!

---

## Decision Tree

```
START
  │
  ├─ Want quick check?
  │  └─ Run: backtest_v2_with_matching.py → 30 seconds
  │     └─ Portfolio > 200k? 
  │        ├─ YES → Continue
  │        └─ NO → Investigate strategy
  │
  ├─ Want to find better parameters?
  │  └─ Run: grid_search_with_matching.py → 5 minutes
  │     └─ New best config found?
  │        ├─ YES → Test with loop runner
  │        └─ NO → Keep Phase 2 (±80/±80)
  │
  └─ Ready to compete?
     └─ Run: loop_test 20 iterations → 3 minutes
        └─ All checks pass?
           ├─ YES → READY FOR COMPETITION ✅
           └─ NO → Fix and retest
```

---

## Position Limit Quick Guide

| Config | Risk | Profit | Recommendation |
|--------|------|--------|-----------------|
| ±40/±40 | Low | +203k (102%) | Very safe |
| ±60/±60 | Med-Low | +245k (123%) | Conservative |
| ±80/±80 | Medium | +438k (219%) | Phase 2 Proven |
| ±90/±90 | Medium | +439k (220%) | **← Current Optimal** |
| ±100/±100 | High | ~450k (225%) | Risky |

**Our Recommendation**: ±80/±80 (proven baseline) or ±90/±90 (current optimal with clearing-level sizing)

---

## Matching Modes Explained

```
match-trades all    (DEFAULT)
├─ Match trades at ANY price
├─ More fills → Higher profit
└─ Result: +286,351 XIRECs

match-trades worse
├─ Only match trades worse than your quote
├─ Conservative → Lower profit
└─ Result: ~260,000 XIRECs (estimate)

match-trades none
├─ Never match market trades
├─ Order depth only
└─ Result: Lower than both above
```

**Use**: Default `all` for best results

---

## File Locations

```
DAD/
├── continuous_trading/
│   ├── backtest_v2_with_matching.py      ← Main backtest
│   ├── grid_search_with_matching.py      ← Parameter optimization
│   ├── run_backtest_loops.py             ← Stress testing
│   ├── order_matcher.py                  ← Matching engine (core)
│   ├── trader.py                         ← Your trading strategy
│   └── validate_signals.py               ← Old signal validator
│
├── docs/
│   ├── TRADING_GLOSSARY_AND_ORDER_MATCHING.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── HOW_TO_USE_BACKTESTING_SYSTEM.md  ← You are here
│   └── QUICK_REFERENCE.md                ← This file
│
analysis/
└── load_data.py                          ← Data loader
```

---

## Troubleshooting (30 seconds)

| Problem | Quick Fix |
|---------|-----------|
| "ModuleNotFoundError" | Run from `DAD/continuous_trading/` not parent |
| "Portfolio Value too low" | Test with higher position limits (±100) |
| "Fill rate very low" | Check if match-trades mode is too strict |
| "Rejected orders high" | Position limits too small - increase them |
| "Portfolio negative" | Fair values or strategy logic issue - debug trader.py |

---

## Pre-Competition Checklist (5 min)

```
□ Backtest passes?
  python backtest_v2_with_matching.py
  → Portfolio > 200k? YES ✓

□ Grid search clear?
  python grid_search_with_matching.py
  → Found good config? YES ✓

□ Loop test passes?
  python run_backtest_loops.py --iterations 20
  → All runs > 200k? YES ✓
  → Std Dev < 5%? YES ✓

□ Ready to deploy!
  SUBMIT ✅
```

---

## Performance Benchmarks

**Expected baseline (±90/±90 with clearing-level sizing)**:
- Portfolio Value: 438,650 XIRECs (219% of target)
- Fill Rate: 65-75%
- Position Limit Rejections: 0
- Consistency: 1.47% CoV (very tight)

**If you see**:
- Portfolio > 430,000 → Excellent! On target ✅
- Portfolio 200,000-250,000 → Good, but below optimal ✓
- Portfolio < 200,000 → Investigate ⚠️

---

## One-Page Workflow

**Morning (Competition Day)**:
```bash
# 1. Quick validation (30s)
cd DAD/continuous_trading && python backtest_v2_with_matching.py

# 2. Check output
grep "Portfolio Value" <output>
# If > 200,000 → Deploy! ✅
# If < 200,000 → Hold, investigate
```

**Before Final Submission**:
```bash
# 1. Run full validation (15 min)
python backtest_v2_with_matching.py
python grid_search_with_matching.py
python run_backtest_loops.py --iterations 20

# 2. Review all outputs
# 3. If all green → Submit! ✅
```

---

## Key Numbers to Remember

- **Target**: 200,000 XIRECs
- **Phase 2 Baseline**: 286,351 XIRECs (±80/±80)
- **New Optimal**: 306,755 XIRECs (±90/±90)
- **Minimum Acceptable**: 200,000 XIRECs (at any position limit)
- **Acceptable Fill Rate**: > 50%
- **Maximum Rejections**: 0 (should never happen)
- **Good Consistency**: Std Dev < 5% of mean

---

## Clearing-Level Order Sizing

**What Is It?**

Orders are sized based on **cumulative order book depth**, not position room:
- Analyze: "How much volume to nudge the book to my target price?"
- Place: Exactly that volume (+ 10% safety buffer)
- Result: Capital-efficient execution, graceful thin-market handling

**Example**:
- Position: -35, Room to buy: 125 units (old approach places 100)
- Order book cumulative depth shows: 45 units to clear through best_ask
- New approach: Place 50 units (45 + 10% buffer)
- Benefit: 50% smaller order, better fills, less market impact

**Why It Matters**:
- Less capital needed per trade
- Better execution in thin markets (auto right-sizes down)
- Principles-based (market microstructure) instead of heuristic (position room)

**See Also**: `CLEARING_LEVEL_ARCHITECTURE.md` for technical details

---

## Support

### Need more detail?
→ See `HOW_TO_USE_BACKTESTING_SYSTEM.md`

### Need technical info?
→ See `IMPLEMENTATION_SUMMARY.md`

### Need order matching rules?
→ See `TRADING_GLOSSARY_AND_ORDER_MATCHING.md`

---

**TL;DR**:
1. Run backtest → Check > 200k ✅
2. Run grid search → Check ranking ✅  
3. Run loop test → Check consistency ✅
4. Deploy! 🚀

---

*Last updated: April 16, 2026*
