# Round 1 Stage 1 Challenge - Phase-by-Phase Guide

## Overview

Round 1 has **three distinct phases**. This guide maps files and strategy to each phase.

---

## Phase 1: Continuous Trading (72 hours, automatic)

**Timeline**: Apr 14-17, 2026 | Runs automatically every minute

**What happens**: Your algorithm trades ASH_COATED_OSMIUM and INTARIAN_PEPPER_ROOT automatically

### Files Needed
- **`continuous_trading/trader.py`** ← **SUBMIT THIS TO COMPETITION**
  - Dual-commodity trading algorithm
  - Market-making for Osmium, Trend-following for Pepper
  - Optimized parameters from grid search
  - Expected profit: +340,091 XIRECs (170% of 200k target)

### Reference Documentation
- `docs/HOW_IT_WORKS.md` - Complete algorithm explanation
- `docs/IMPLEMENTATION_SUMMARY.md` - Results and validation
- `docs/README.md` - System overview

### Validation Scripts (for verification only)
- `continuous_trading/backtest_v2.py` - Validates baseline strategy on historical data
  - Run: `python continuous_trading/backtest_v2.py`
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
- **`docs/MANUAL_CHALLENGE_STRATEGY.md`** ← **READ THIS BEFORE AUCTION**
  - Step-by-step bidding algorithm
  - How to estimate clearing price
  - Quantity scaling based on profit
  - Bid price strategy (beat best bid by 1)

### Validation/Reference Scripts
- `manual_challenge/auction_backtest.py` - Validates bidding strategy
  - Run before auction to build confidence: `python manual_challenge/auction_backtest.py`
  - Results: 100% success rate on both products
  - Expected auction profit: +4,934 XIRECs (bonus on top of +340k)

### What You Need to Do
1. When auction time announced, be ready to submit a bid
2. Read `docs/MANUAL_CHALLENGE_STRATEGY.md` for the algorithm
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
- `analysis/load_data.py` - Parses historical market data
- `analysis/analyze_prices.py` - Statistical pattern discovery (found that Osmium mean-reverts, Pepper trends)
- `analysis/visualize.py` - Creates charts of price movements
- `analysis/time_block_analysis.py` - Intraday pattern analysis

### Parameter Optimization (Archive)
- `analysis/grid_search_backtest.py` - Basic grid search (768 combinations, superseded)
- `analysis/grid_search_realistic.py` - Realistic search (2,304 combinations, produced best parameters)
- `scripts/grid_search_scaled.py` - Extended search (20,736 combinations, completed ~25%, no improvement found)

### Data Files (Completed Analysis)
- `analysis/analysis_output.txt` - Pattern discovery results
- `scripts/grid_search_scaled_results.csv` - Completed scaled search results

---

## File Organization Summary

### KEEP (Essential for Round 1)

```
DAD/
├── continuous_trading/
│   ├── trader.py                     ← SUBMIT THIS
│   ├── backtest_v2.py                ← Validation
│   └── README.md
├── manual_challenge/
│   ├── auction_backtest.py           ← Validation
│   └── README.md
├── analysis/
│   ├── load_data.py                  ← Development (reference)
│   ├── analyze_prices.py             ← Development (reference)
│   ├── visualize.py                  ← Development (reference)
│   ├── time_block_analysis.py        ← Development (reference)
│   └── README.md
├── docs/
│   ├── HOW_IT_WORKS.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── MANUAL_CHALLENGE_STRATEGY.md
│   ├── ROUND1_STRATEGY.md
│   ├── RULES_COMPLIANCE.md
│   ├── COMPETITION_READINESS.md
│   ├── README.md
│   ├── STAGE_1_GUIDE.md (this file)
│   └── ...
└── scripts/ (keeping for now)
    ├── grid_search_scaled.py         ⚠️ Delete after use
    └── grid_search_scaled_results.csv ⚠️ Delete after use
```

### OPTIONAL (Depends on your preference)

```
DAD/analysis/
├── trader_original.py                ? Keep for backup or delete
└── grid_search_realistic.py           ? Already analyzed, can delete
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
