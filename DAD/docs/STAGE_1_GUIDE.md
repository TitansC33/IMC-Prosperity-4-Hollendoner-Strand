# Round 1 Stage 1 Challenge - Phase-by-Phase Guide

## Overview

Round 1 has **three distinct phases**. This guide maps files and strategy to each phase.

---

## Phase 1: Continuous Trading (72 hours, automatic)

**Timeline**: Apr 14-17, 2026 | Runs automatically every minute

**What happens**: Your algorithm trades ASH_COATED_OSMIUM and INTARIAN_PEPPER_ROOT automatically

### Files Needed
- **`trader.py`** ← **SUBMIT THIS TO COMPETITION**
  - Dual-commodity trading algorithm
  - Market-making for Osmium, Trend-following for Pepper
  - Optimized parameters from grid search
  - Expected profit: +340,091 XIRECs (170% of 200k target)

### Reference Documentation
- `HOW_IT_WORKS.md` - Complete algorithm explanation
- `IMPLEMENTATION_SUMMARY.md` - Results and validation
- `README.md` - System overview

### Validation Scripts (for verification only)
- `scripts/backtest_v2.py` - Validates baseline strategy on historical data
  - Run: `python scripts/backtest_v2.py`
  - Shows: +340k expected profit with ±80 position limits

### What You Don't Control
- Algorithm runs automatically (you just submitted trader.py)
- Market feeds provided by competition
- Positions tracked and enforced by platform (±80 limit per commodity)

---

## Phase 2: Manual Challenge - Auction Bidding

**Timeline**: During Round 1 (date/time announced in competition)

**What happens**: Two separate auctions where you submit last (after seeing all other bids/asks)
- **DRYLAND_FLAX**: Buyback @30 XIRECs (no fees)
- **EMBER_MUSHROOM**: Buyback @20 XIRECs (0.10 fee per unit traded)

### Files Needed
- **`MANUAL_CHALLENGE_STRATEGY.md`** ← **READ THIS BEFORE AUCTION**
  - Step-by-step bidding algorithm
  - How to estimate clearing price
  - Quantity scaling based on profit
  - Bid price strategy (beat best bid by 1)

### Validation/Reference Scripts
- `scripts/auction_backtest.py` - Validates bidding strategy
  - Run before auction to build confidence: `python scripts/auction_backtest.py`
  - Results: 100% success rate on both products
  - Expected auction profit: +4,934 XIRECs (bonus on top of +340k)

### What You Need to Do
1. When auction time announced, be ready to submit a bid
2. Read `MANUAL_CHALLENGE_STRATEGY.md` for the algorithm
3. When you see the market order book:
   - Estimate clearing price from existing bids/asks
   - Calculate profit per unit (30 - estimate for FLAX, 20 - estimate - 0.10 for MUSHROOM)
   - If profit > 0, bid aggressively
   - Bid price = (best_bid_in_market + 1) to frontrun

---

## Phase 3: Analysis & Development (Behind the Scenes)

**Timeline**: Used to build Phases 1 and 2

**Not needed for competition**, but useful for understanding how we optimized everything:

### Data Analysis Scripts
- `scripts/load_data.py` - Parses historical market data
- `scripts/analyze_prices.py` - Statistical pattern discovery (found that Osmium mean-reverts, Pepper trends)
- `scripts/visualize.py` - Creates charts of price movements
- `scripts/time_block_analysis.py` - Intraday pattern analysis

### Parameter Optimization
- `scripts/grid_search_backtest.py` - ⚠️ **REMOVE** (superseded)
- `scripts/grid_search_realistic.py` - ⚠️ **REMOVE** (already analyzed)
- `scripts/grid_search_scaled.py` - ⚠️ **REMOVE AFTER COMPLETION** (currently running, finding better parameters)

### Data Files (Analysis)
- `scripts/grid_search_results.csv` - ⚠️ **REMOVE** (basic results, already extracted)
- `scripts/grid_search_realistic_results.csv` - ⚠️ **REMOVE** (already extracted best params)
- `scripts/grid_search_scaled_results.csv` - ⚠️ **REMOVE AFTER RUNNING** (in progress)

---

## File Organization Summary

### KEEP (Essential for Round 1)
```
DAD/
├── trader.py                          ← SUBMIT THIS
├── HOW_IT_WORKS.md
├── IMPLEMENTATION_SUMMARY.md
├── MANUAL_CHALLENGE_STRATEGY.md
├── ROUND1_STRATEGY.md
├── RULES_COMPLIANCE.md
├── COMPETITION_READINESS.md
├── README.md
├── STAGE_1_GUIDE.md (this file)
└── scripts/
    ├── backtest_v2.py                ← Validation
    ├── auction_backtest.py           ← Validation
    ├── load_data.py                  ← Development (reference)
    ├── analyze_prices.py             ← Development (reference)
    ├── visualize.py                  ← Development (reference)
    └── time_block_analysis.py        ← Development (reference)
```

### REMOVE (After validation)
```
DAD/scripts/
├── grid_search_backtest.py           ✗ Delete
├── grid_search_results.csv           ✗ Delete
├── grid_search_realistic.py          ✗ Delete
├── grid_search_realistic_results.csv ✗ Delete
└── (After grid_search_scaled completes)
    ├── grid_search_scaled.py         ✗ Delete
    └── grid_search_scaled_results.csv ✗ Delete
```

### OPTIONAL (Depends on your preference)
```
DAD/
└── trader_original.py                ? Keep for backup or delete
```

---

## Execution Checklist for Round 1

### Before Round 1 Starts (Apr 14)
- [ ] Read `HOW_IT_WORKS.md` to understand the system
- [ ] Review `IMPLEMENTATION_SUMMARY.md` for validation results
- [ ] Read `RULES_COMPLIANCE.md` to verify legality
- [ ] Copy `trader.py` to competition submission platform

### During Continuous Trading (Apr 14-17)
- [ ] Algorithm runs automatically
- [ ] Monitor balance growth (target: +340k XIRECs)
- [ ] Keep `MANUAL_CHALLENGE_STRATEGY.md` nearby for auction phase

### During Manual Challenge - Auction
- [ ] Watch for auction announcement (date/time)
- [ ] Read `MANUAL_CHALLENGE_STRATEGY.md` for bidding algorithm
- [ ] When market opens, see all existing bids/asks
- [ ] Execute bidding strategy (estimate clearing → calculate profit → bid aggressively if profitable)
- [ ] Expected auction profit: +4,934 XIRECs

### After Round 1
- [ ] Collect results (final balance, P&L breakdown)
- [ ] Compare actual vs. predicted performance
- [ ] Document lessons learned for Round 2

---

## Quick Reference: Phase 1 vs Phase 2

| Aspect | Phase 1 (Continuous) | Phase 2 (Auction) |
|--------|----------------------|-------------------|
| **Control** | Automatic (submitted) | Manual (you bid) |
| **File** | trader.py | MANUAL_CHALLENGE_STRATEGY.md |
| **Effort** | Zero (runs on own) | High (you submit bids) |
| **Expected Profit** | +340,091 XIRECs | +4,934 XIRECs (bonus) |
| **Duration** | 72 hours | One-time event |
| **Products** | OSMIUM, PEPPER | FLAX, MUSHROOM |

---

## Notes

- **Phases run sequentially**: Continuous first (72 hrs), then Auction happens sometime during
- **Independent**: If Continuous Trading loses money, Auction is separate opportunity to profit
- **Risk**: If you don't bid in Auction, you just miss +4,934k bonus (Continuous still runs)
- **Scoring**: Total = Continuous Trading P&L + Auction P&L (if you bid)

---

**Last Updated**: Apr 15, 2026
**Status**: Ready for Round 1 Submission ✅
