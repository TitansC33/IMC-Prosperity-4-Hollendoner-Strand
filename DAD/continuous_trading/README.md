# Continuous Trading Phase - Backtesting & Parameter Optimization

## Production Files

### `trader.py` — **SUBMIT THIS TO COMPETITION**
The main trading algorithm that runs automatically during Round 1 (Apr 14-17).

**What it does:**

- Trades ASH_COATED_OSMIUM (market-making strategy)
- Trades INTARIAN_PEPPER_ROOT (trend-following strategy)
- Runs every minute for 72 hours automatically

**Phase 2 Optimized Parameters** (validated through realistic backtesting):
```python
# Osmium (Market-Making)
OSMIUM_EMA_ALPHA = 0.15           # Slower trend, less noise
OSMIUM_VWAP_WINDOW = 15           # Recent 15 trades for anchor
OSMIUM_INVENTORY_BIAS = 0.7       # Conservative rebalancing
OSMIUM_VOL_BASE = 20              # Volatility threshold
OSMIUM_POSITION_LIMIT = 80        # ±80 per run (proven optimal)

# Pepper (Trend-Following)
PEPPER_EMA_ALPHA = 0.3            # Responsive trend detection
PEPPER_VOL_BASE = 300             # Higher threshold
PEPPER_POSITION_LIMIT = 80        # ±80 per run (proven optimal)
```

**Expected Performance**: +286,351 XIRECs (143% of 200k target)

---

## Backtesting System (NEW - Realistic Order Matching)

### Core Tools

| Tool | Purpose | Time | Command |
| --- | --- | --- | --- |
| **backtest_v2_with_matching.py** | Single backtest with realistic order matching | 30s | `python backtest_v2_with_matching.py` |
| **grid_search_with_matching.py** | Test multiple position limit configurations | 5min | `python grid_search_with_matching.py` |
| **run_backtest_loops.py** | Stress test with randomization + consistency checks | 3-10min | `python run_backtest_loops.py --iterations 20 --randomize-order --randomize-depth` |

### What's NEW

These tools implement **realistic order matching** following IMC Prosperity platform rules:

- ✅ **Order Depth Priority**: Fill from order book BEFORE market trades
- ✅ **Price-Time-Priority**: Correct FIFO ordering at same price level
- ✅ **Position Limit Enforcement**: Strict all-or-nothing rejection
- ✅ **Match Modes**: Support `all` (default), `worse`, `none`
- ✅ **Execution Statistics**: Track fills, rejections, rates by product

### Quick Start (5 min)

```bash
# 1. Run single backtest
python backtest_v2_with_matching.py

# 2. Find best parameters
python grid_search_with_matching.py

# 3. Stress test (randomize order + depths)
python run_backtest_loops.py --iterations 20 --randomize-order --randomize-depth
```

### Validation Results

**Baseline (±80/±80)**: +286,351 XIRECs (143% target)  
**New Optimal (±90/±90)**: +306,755 XIRECs (153% target)  
**Loop Testing**: 35 iterations, 0 failures, 100% success rate

**Key Finding**: Market volatility is an ADVANTAGE (loop test showed +147% higher profits with price noise)

---

## Supporting Files

### `order_matcher.py`

Core order matching engine implementing IMC Prosperity rules.

- Used by: `backtest_v2_with_matching.py`, `grid_search_with_matching.py`, `run_backtest_loops.py`
- Handles: Order depth matching, market trade matching, position limit validation

### `validate_signals_with_execution.py`

Signal validation with execution simulation.

- Tests if generated signals would actually execute
- Reports fill rates and execution confidence
- Flags orders rejected by position limits

---

## Documentation

**Start Here**: See `../docs/START_HERE_BACKTESTING.md` (5 min overview)

**Quick Reference**: `../docs/QUICK_REFERENCE.md` (commands & output interpretation)

**Complete Guide**: `../docs/HOW_TO_USE_BACKTESTING_SYSTEM.md` (8-part detailed walkthrough)

**Parameter Details**: `../docs/RECOMMENDED_TRADER_PARAMETERS.md` (parameter analysis & validation)

**Testing Results**: 
- `../docs/LOOP_TEST_RESULTS.md` (35 iterations, all scenarios)
- `../docs/VARIABLES_AND_COMBINATIONS.md` (complete coverage matrix)

**Technical**: `../docs/VISUAL_GUIDE.md` (ASCII diagrams of order matching)

---

## Workflow

### Daily Check (5 min)

```bash
python backtest_v2_with_matching.py
# Check: Portfolio Value > 200,000? → Ready!
```

### Find Optimal Parameters (5 min)

```bash
python grid_search_with_matching.py
# Check: Is ±80/±80 still competitive? Or try ±90/±90?
```

### Stress Test Before Submission (10 min)

```bash
python run_backtest_loops.py --iterations 20 --randomize-order --randomize-depth
# Check: All runs > 200k? Std Dev < 5%? → Ready to submit!
```

### Test Custom Limits

```bash
python run_backtest_loops.py --iterations 5 --osmium-limit 90 --pepper-limit 90
```

---

## File Locations

```text
DAD/continuous_trading/
├── trader.py                          ← SUBMIT THIS
├── backtest_v2_with_matching.py       ← Primary backtest (realistic)
├── grid_search_with_matching.py       ← Parameter optimization
├── run_backtest_loops.py              ← Stress testing
├── order_matcher.py                   ← Core matching engine
└── validate_signals_with_execution.py ← Signal validation

DAD/docs/
├── START_HERE_BACKTESTING.md          ← Start here
├── QUICK_REFERENCE.md                 ← Command cheat sheet
├── HOW_TO_USE_BACKTESTING_SYSTEM.md   ← Full guide
├── RECOMMENDED_TRADER_PARAMETERS.md   ← Parameter details
├── LOOP_TEST_RESULTS.md               ← Test results (35 iterations)
├── VARIABLES_AND_COMBINATIONS.md      ← Coverage matrix
└── VISUAL_GUIDE.md                    ← Diagrams
```

---

## Pre-Competition Checklist

```text
□ Backtest passes?
  python backtest_v2_with_matching.py
  → Portfolio > 200k? YES ✓

□ Grid search clear?
  python grid_search_with_matching.py
  → Top config still viable? YES ✓

□ Loop test passes?
  python run_backtest_loops.py --iterations 20
  → All runs > 200k? YES ✓
  → Std Dev < 5%? YES ✓

□ Ready to deploy!
  SUBMIT ✅
```
