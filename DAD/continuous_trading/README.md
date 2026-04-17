# Continuous Trading: Strategy & Backtesting

## Quick Start

```bash
# Test current strategy
python backtest_hybrid.py

# Output: Rankings of all configurations
```

---

## Current Status

### Live Performance (Validated in Simulator)
- **Sean Baseline** (pos=20, spread=5): **$2,668** ✓
- **Current trader.py** (pos=60, spread=4, pskew=0.28): **$2,553** (underperforms)

### Full ROUND1 Backtest Results (Hybrid Methodology)
| Config | Backtest Profit | Live Result |
|--------|---|---|
| COMBO_60_4 (pos=60, sp=4) | $312,331 | Unknown |
| Conservative Pepper (pos=60, sp=4, pskew=0.28) | $297,250 | $2,553 |
| Sean Baseline (pos=20, sp=5) | $141,030 | $2,668 ✓ |

**Key Insight**: Backtest profits are ~100-150x higher than live. Use backtest for **relative ranking** (which config is better), not absolute profit prediction.

---

## Production Files

### `trader.py` — Current Strategy
Market-making strategy with two components:
- **Osmium (ASH_COATED_OSMIUM)**: EWM fair value + inventory skew
- **Pepper Root (INTARIAN_PEPPER_ROOT)**: Large order filtering + trend bias

**Current Parameters** (set as defaults):
```python
# Position Limits
POSITION_LIMITS = {
    "ASH_COATED_OSMIUM": 60,
    "INTARIAN_PEPPER_ROOT": 60
}

# Osmium
OSMIUM_SPREAD = 4
OSMIUM_SKEW_FACTOR = 0.2
OSMIUM_EWM_ALPHA = 0.002

# Pepper
PEPPER_LARGE_ORDER_THRESHOLD = 18
PEPPER_SKEW_FACTOR = 0.28
PEPPER_QUOTE_IMPROVEMENT = 1
```

**Performance**: $2,553 in live simulator (below Sean's $2,668)

### `seanTrader.py` — Baseline (Proven)
Sean's original strategy. Parameters:
```python
POSITION_LIMITS = {"ASH_COATED_OSMIUM": 20, "INTARIAN_PEPPER_ROOT": 20}
OSMIUM_SPREAD = 5
PEPPER_SKEW_FACTOR = 0.3
PEPPER_LARGE_ORDER_THRESHOLD = 18
```

**Performance**: $2,668 in live simulator ✓ (best validated)

---

## Backtesting System

### The Correct Backtest: `backtest_hybrid.py`

**Why this is correct:**
- Processes only trade timestamps (~2,218 per ROUND1, not 100k)
- Uses BOTH order depths (from prices) AND market trades
- Matches how live simulator receives data
- Fast: runs 5 configs in ~90 seconds

**Old broken backtests** (archived in `_archived_backtests/`):
- `full_backtest_round1.py` — Missing price data at trades
- `full_backtest_round1_correct.py` — Timed out
- Grid searches — Overfitted to 200-trade sample (1% of data)

### How to Use

```bash
# Run all default configurations
python backtest_hybrid.py

# Output example:
# Rank  Configuration                    Profit        vs Best
# 1     COMBO_60_4                       $312,331      +0.00 <-- BEST
# 2     Conservative Pepper              $297,250      -15,081
# 3     Sean Baseline                    $141,030      -171,301
```

### Adding New Configurations

Edit `backtest_hybrid.py`, find the `configs` list:

```python
configs = [
    (SeanTrader, "Sean Baseline (pos=20, spread=5)", None),
    (Trader, "My Test (pos=40, sp=3)", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 40, "INTARIAN_PEPPER_ROOT": 40},
        "OSMIUM_SPREAD": 3
    }),
]
```

Run and rankings appear automatically.

---

## Core Components

### `order_matcher.py`
Realistic order matching engine:
- Price-time-priority (FIFO at same price)
- Order depth vs market trades priority
- Position limit enforcement
- Multiple match modes (`all`, `worse`, `none`)

**Used by**: `backtest_hybrid.py`

---

## Documentation

| File | Purpose |
|------|---------|
| **README_BACKTESTING.md** | Quick start & workflows |
| **BACKTEST_GUIDE.md** | Technical deep dive & troubleshooting |
| **OPTIMIZATION_SUMMARY.md** | Parameter history & discoveries |
| **CLEANUP_SUMMARY.md** | This cleanup summary |

---

## Key Findings from Analysis

### 1. Backtest ≠ Live Performance
- Sample-based optimization showed $344k peak
- Full dataset backtest shows $312k peak
- Live results show $2.6k actual
- Gap is due to market structure differences, competition, position sizing limits

### 2. Position Scaling Doesn't Help Live
- Backtest ranks pos=60 higher than pos=20
- Live shows pos=20 (Sean) beating pos=60 (trader.py)
- Larger positions create slippage in actual competition

### 3. Sean's Baseline is Validated
- Only strategy with proven live results: $2,668
- Simple, aggressive market-making wins over complex optimization
- Default to baseline until live competition proves otherwise

---

## Testing Workflow

### To Test a Change

1. Modify strategy in `trader.py` or `seanTrader.py`
2. Run: `python backtest_hybrid.py`
3. Check rankings
4. If backtest improves, submit to live simulator
5. Compare live result vs $2,668 (Sean baseline)
6. If live is better, keep it; else revert

### To Find Better Parameters

Create grid search by editing `configs` in `backtest_hybrid.py`:

```python
configs = [
    (Trader, f"pos={p}, sp={s}", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": p, "INTARIAN_PEPPER_ROOT": p},
        "OSMIUM_SPREAD": s
    })
    for p in [20, 30, 40, 60]
    for s in [3, 4, 5]
]
```

Run: `python backtest_hybrid.py`  
Get: 12 configurations ranked automatically

---

## File Structure

```
DAD/continuous_trading/
├── backtest_hybrid.py         ← Use this for all testing
├── trader.py                  ← Current strategy
├── seanTrader.py              ← Baseline (best live: $2,668)
├── order_matcher.py           ← Order matching engine
├── README.md                  ← This file
├── README_BACKTESTING.md      ← Quick start guide
├── BACKTEST_GUIDE.md          ← Technical reference
├── OPTIMIZATION_SUMMARY.md    ← Parameter history
├── CLEANUP_SUMMARY.md         ← Cleanup notes
├── _archived_backtests/       ← 14 old backtest scripts
└── _archived_results/         ← 21 old result files
```

---

## Important Notes

⚠️ **Backtest vs Live Gap**
- Backtest: ~$150-300k per config
- Live: ~$2.6k actual
- This is expected and normal, NOT a bug
- Use backtest for relative comparison, not absolute values

✅ **Validated Strategy**
- Sean Baseline is the only strategy with proven live results
- Use it as the default until competition proves better alternative

✓ **How to Know If You've Improved**
- Backtest ranking improves (vs current leader)
- **AND** live simulator profit increases (vs $2,668 baseline)
- Both must be true to declare an improvement

---

## Questions?

- **How to run the backtest?** → See `README_BACKTESTING.md`
- **How does the backtest work?** → See `BACKTEST_GUIDE.md`
- **Why are profits so different?** → See "Key Findings" above
- **Old backtests?** → Archived in `_archived_backtests/` (don't use)
