# Deprecated Documentation Files - Archive

**Date Cleaned**: April 16, 2026  
**Reason**: Removed old backtesting files and consolidated documentation now that the new realistic order matching system is in place and Round 1 parameters are locked.

---

## Removed Files

### 1. `START_HERE.md`

**Status**: ❌ REMOVED  
**Reason**: Referenced old `scripts/` folder structure that no longer exists

**What it was**:
- Entry point document pointing to old folder structure
- Listed `scripts/` folder with analysis tools
- Referenced old backtesting approaches

**Why removed**:
- All `scripts/` folder tools have been superseded by new backtesting system
- New entry point is `README.md` and `START_HERE_BACKTESTING.md`
- Old folder structure no longer maintained

---

### 2. `STAGE_1_GUIDE.md`

**Status**: ❌ REMOVED  
**Reason**: Referenced `backtest_v2.py` (old simplified backtesting system)

**What it was**:
- Phase-by-phase guide for Round 1
- Mapped files to different phases (continuous trading, manual challenge)
- Referenced old validation script

**Why removed**:
- Referenced `continuous_trading/backtest_v2.py` which has been removed
- New system uses `backtest_v2_with_matching.py` instead
- Outdated guidance superseded by updated README.md and continuous_trading/README.md

---

### 3. `COMPETITION_READINESS.md`

**Status**: ❌ REMOVED  
**Reason**: Referenced missing `scripts/auction_backtest.py`

**What it was**:
- Pre-competition verification checklist
- Auction strategy validation results
- Risk mitigation confirmation

**Why removed**:
- Referenced `scripts/auction_backtest.py` (missing file)
- Manual challenge strategy is now in `MANUAL_CHALLENGE_STRATEGY.md`
- Outdated pre-Round 1 checklist (Round 1 already occurred)

---

### 4. `OUTPUTS.md`

**Status**: ❌ REMOVED  
**Reason**: Documented outputs from `DAD/scripts/` folder which no longer exists

**What it was**:
- Listed all output files from data visualization scripts
- Documented `visualize.py`, `time_block_analysis.py` outputs
- Referenced analysis scripts location

**Why removed**:
- All `DAD/scripts/` folder tools have been removed
- Analysis tools are no longer part of the active system
- Documentation for non-existent folder and tools

---

## Archived Files

### 5. `SIMULATOR_TEST_PLAN.md`

**Status**: 📦 ARCHIVED (kept for reference, not actively used)  
**Reason**: Tutorial Round testing plan is no longer needed (parameters already optimized)

**What it was**:
- Comprehensive testing framework for Simulator Tutorial Round
- Three test configurations (Conservative A, Aggressive B, Balanced C)
- Parameter tuning guidance for trader.py

**Why archived**:
- Round 1 parameters have already been optimized through grid search (Phase 2)
- ±80/±80 position limits validated as optimal (or ±90/±90 for enhanced performance)
- EMA, VWAP, and other parameters already locked and loop-tested
- Simulator round (if run again) would use these already-optimized parameters
- Kept as reference for future optimization workflows

**When to use**:
- For understanding parameter tuning methodology
- For future rounds with new products/markets
- As framework for systematic parameter optimization

---

## Current Active Documentation

### Essential (Read First)
- ✅ `README.md` — Master documentation index
- ✅ `START_HERE_BACKTESTING.md` — Quick entry point (5 min)
- ✅ `QUICK_REFERENCE.md` — Command cheat sheet

### Backtesting System (New)
- ✅ `HOW_TO_USE_BACKTESTING_SYSTEM.md` — Complete 8-part guide
- ✅ `LOOP_TEST_RESULTS.md` — Validation results (35 iterations)
- ✅ `RECOMMENDED_TRADER_PARAMETERS.md` — Parameter analysis
- ✅ `VARIABLES_AND_COMBINATIONS.md` — Coverage matrix

### Technical Reference
- ✅ `VISUAL_GUIDE.md` — ASCII diagrams of order matching
- ✅ `MARKET_RULES.md` — IMC Prosperity market mechanics
- ✅ `TRADING_GLOSSARY_AND_ORDER_MATCHING.md` — Order matching implementation

### Strategy & Implementation
- ✅ `HOW_IT_WORKS.md` — Trading strategy explanation
- ✅ `IMPLEMENTATION_SUMMARY.md` — Implementation details
- ✅ `ROUND1_STRATEGY.md` — Strategy analysis
- ✅ `RULES_COMPLIANCE.md` — trader.py compliance verification
- ✅ `MANUAL_CHALLENGE_STRATEGY.md` — Auction bidding strategy
- ✅ `CHANGES.md` — What changed vs original trader.py

---

## Migration Guide

### If You Looked for `COMPETITION_READINESS.md`:
**Use**: `continuous_trading/README.md` + `../docs/QUICK_REFERENCE.md`

Pre-competition checklist is now in the README.md at the bottom.

---

### If You Looked for `START_HERE.md`:
**Use**: `README.md` or `START_HERE_BACKTESTING.md`

The new starting point clearly outlines the current backtesting system structure.

---

### If You Looked for `STAGE_1_GUIDE.md`:
**Use**: `HOW_TO_USE_BACKTESTING_SYSTEM.md` + `continuous_trading/README.md`

Complete workflows are now documented there, updated for the new system.

---

### If You Looked for `SIMULATOR_TEST_PLAN.md`:
**Use**: For Simulator Tutorial Round testing (if doing it)

The file is archived but still available if needed. However, Round 1 parameters are already locked, so reference `RECOMMENDED_TRADER_PARAMETERS.md` instead for current parameters.

---

## Files Removed from Code

### Scripts Folder (Removed)
```
DAD/scripts/ (entire folder removed - no longer used)
├── load_data.py           → moved to analysis/load_data.py
├── analyze_prices.py      → not needed (data analysis complete)
├── time_block_analysis.py → archived (historical analysis only)
├── visualize.py           → archived (charts generated)
├── backtest_v2.py         → REPLACED by backtest_v2_with_matching.py
└── auction_backtest.py    → REMOVED (auction strategy documented in MANUAL_CHALLENGE_STRATEGY.md)
```

### Continuous Trading Folder (Simplified)
```
DAD/continuous_trading/ (old files removed)
├── backtest_v2.py          ❌ REMOVED → use backtest_v2_with_matching.py
└── validate_signals.py     ❌ REMOVED → use validate_signals_with_execution.py
```

---

## Key Improvements Made

### 1. **Realistic Order Matching**
- Old: `backtest_v2.py` used simplified mock matching with hardcoded thresholds
- New: `backtest_v2_with_matching.py` implements actual IMC Prosperity order matching rules
  - ✅ Order depth priority
  - ✅ Price-time-priority (FIFO)
  - ✅ Position limit pre-validation
  - ✅ Match mode configuration (all/worse/none)

### 2. **Comprehensive Testing**
- Old: Single backtest, basic validation
- New: Three tools covering different testing needs
  - Single backtest (30s)
  - Grid search optimization (5 min)
  - Loop stress testing (3-10 min)

### 3. **Better Documentation**
- Old: Scattered across 21 files (many outdated)
- New: Consolidated and organized
  - Clear navigation in `README.md`
  - Dedicated backtesting guide
  - Technical references separate from strategies

### 4. **Validation Results**
- Phase 2 Parameters: ±80/±80 → +286,351 XIRECs (143% of target)
- Grid Search Best: ±90/±90 → +306,755 XIRECs (153% of target)
- Loop Testing: 35 iterations, 0 failures, 100% success rate
- Worst Case (Stress Test): +409,671 XIRECs (205% of target)

---

## Archive Location

All removed files are preserved in git history:

```bash
# View old files
git log --follow -- DAD/docs/START_HERE.md
git log --follow -- DAD/continuous_trading/backtest_v2.py
git log --follow -- DAD/continuous_trading/validate_signals.py

# Restore if needed
git checkout HEAD~1 -- DAD/docs/START_HERE.md
```

---

## Questions?

**Backtesting system**: See `HOW_TO_USE_BACKTESTING_SYSTEM.md`

**Parameter details**: See `RECOMMENDED_TRADER_PARAMETERS.md`

**Order matching rules**: See `TRADING_GLOSSARY_AND_ORDER_MATCHING.md`

**Quick commands**: See `QUICK_REFERENCE.md`

---

**Status**: All cleanup complete. Documentation is now streamlined and current. ✅

