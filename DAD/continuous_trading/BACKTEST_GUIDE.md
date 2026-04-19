# Backtest Guide: backtest_hybrid.py

## Overview

`backtest_hybrid.py` is the **correct and only backtest** for evaluating trader strategies on ROUND1 data. It implements a **hybrid methodology** that processes trade timestamps while using both order depth (from prices) and market trades data—matching how the live simulator receives information.

## Why This Backtest Works

Previous backtests had critical flaws:
- **Trade-driven** (old `full_backtest_round1.py`): Only used price data at trade timestamps, missing order book updates
- **Timestamp-driven** (old `full_backtest_round1_correct.py`): Processed every price snapshot (~100k timestamps), causing timeouts
- **Sample-based** (old grid searches): Optimized on 200-trade samples, results didn't generalize to full dataset

**The hybrid approach:** Process only trade timestamps (~2,218) but fetch BOTH prices AND trades at each timestamp.

## Running the Backtest

### Basic Usage

```bash
python backtest_hybrid.py
```

This runs all default configurations (Sean baseline + 4 optimized variants) and outputs rankings.

### Output

```
==================================================================================================================================
HYBRID BACKTEST: Trade timestamps + both Prices AND Trades data
==================================================================================================================================

Testing: Sean Baseline (pos=20, spread=5)
    300/2218 trade timestamps...
    ...
  Profit: $141,030.00 | Fills: 4009

[more configs...]

==================================================================================================================================
RANKINGS (Hybrid ROUND1 Backtest - Trade timestamps + Prices + Trades):
==================================================================================================================================
Rank  Configuration                                      Profit          Fills      vs Best        
----------------------------------------------------------------------------------------------------------------------------------
1     COMBO_60_4 (pos=60, spread=4)                      $   312,331.00     4031         +0.00 <-- BEST
2     Conservative Pepper (pos=60, sp=4, pskew=0.28)     $   297,250.00     4023    -15,081.00
...
```

## Adding New Configurations

Edit the `configs` list near the end of the file:

```python
configs = [
    (SeanTrader, "Sean Baseline (pos=20, spread=5)", None),
    (Trader, "SPREAD_4 (pos=20, spread=4)", {"OSMIUM_SPREAD": 4}),
    (Trader, "My New Config", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 40, "INTARIAN_PEPPER_ROOT": 40},
        "OSMIUM_SPREAD": 3,
        "PEPPER_SKEW_FACTOR": 0.27
    }),
]
```

**Rules:**
- First element: `SeanTrader` for Sean's original trader, or `Trader` for your optimized trader
- Second element: Display name (for rankings table)
- Third element: Dictionary of parameter overrides, or `None` for defaults

## Key Parameters

### Osmium (ASH_COATED_OSMIUM)
- `POSITION_LIMITS`: How many units you can hold (default: 20, tested up to 60)
- `OSMIUM_SPREAD`: Bid-ask spread width (default: 5, tested down to 4)
- `OSMIUM_SKEW_FACTOR`: Inventory skew sensitivity (default: 0.2, typically not tuned)
- `OSMIUM_EWM_ALPHA`: Fair value smoothing (default: 0.002, rarely changed)

### Pepper Root (INTARIAN_PEPPER_ROOT)
- `POSITION_LIMITS`: How many units you can hold (default: 20, tested up to 60)
- `PEPPER_LARGE_ORDER_THRESHOLD`: Volume threshold for "large" order detection (default: 18, tested down to 10)
- `PEPPER_SKEW_FACTOR`: Inventory skew sensitivity (default: 0.3, tested 0.21-0.3)
- `PEPPER_QUOTE_IMPROVEMENT`: How much to beat large MM orders (default: 1, rarely changed)

## Understanding Results

### Backtest vs Live Performance Gap

**Important**: Backtest profits are ~100x higher than live results. This is expected and not a bug.

**Why the gap exists:**
1. ROUND1 data structure differs from live competition
2. Backtest assumes you're the only trader; live has competitors
3. Position sizing (60 units) works in backtest but may be unrealistic in live
4. Order matcher is generous with fills (price-time-priority); live execution is competitive

**Interpretation:**
- Backtest is useful for **relative ranking** (which config is better)
- Backtest profit is NOT a reliable predictor of live profit
- Live results are the ground truth for strategy validation

### Current Standings

| Config | Backtest | Live Simulator |
|--------|----------|---------|
| COMBO_60_4 | $312,331 | Unknown |
| Conservative Pepper | $297,250 | Unknown |
| Sean Baseline | $141,030 | $2,668 ✓ |

Sean's baseline is **validated live** and should be the default until live competition proves otherwise.

## Troubleshooting

### "No such file or directory: data/ROUND1/..."

The backtest must be run from the `continuous_trading/` directory:
```bash
cd DAD/continuous_trading
python backtest_hybrid.py
```

### Slow execution

Expected runtime: ~60-90 seconds for 5 configurations (processes 2,218 trade timestamps × 5 = 11,090 trader calls).

If it takes >5 minutes, check:
- Disk I/O (ROUND1 data files)
- CPU load (other processes)
- You haven't accidentally added a huge config list

### Negative profits or zeros

Check that:
- `trader.py` and `seanTrader.py` are in the same directory
- `order_matcher.py` hasn't been modified
- Position limits are reasonable (±60 is standard)

## When to Use This Backtest

✅ **DO use for:**
- Comparing strategy variants quickly
- Testing parameter sensitivities
- Verifying implementation changes don't break profitability
- Relative ranking of configurations

❌ **DON'T use for:**
- Predicting exact live profit (expect 100x scaling down)
- Validating live performance (run actual simulator for that)
- Machine learning / hyperparameter tuning (sample bias is high)

## Methodology Details

### Algorithm

1. Load all ROUND1 data (3 days, 2,276 trades, ~2,218 unique trade timestamps)
2. For each unique trade timestamp:
   - Fetch order depth at that timestamp (from prices data)
   - Fetch all market trades at that timestamp
   - Create TradingState with both
   - Call trader.run()
   - Match orders against order depth, then market trades
   - Update positions and balance
3. Output final P&L and rankings

### Why "Hybrid"

- **Hybrid source:** Data comes from two sources:
  - Trade timestamps (when to run trader)
  - Price snapshots (order book state)
  - Trade records (market activity)
  
- **Hybrid matching:** Orders matched against:
  1. Order depth (price-time-priority, like real markets)
  2. Market trades (fallback, like taking aggressive liquidity)

### Assumptions

1. Orders are filled instantly at matched prices (no latency)
2. You win against market makers at same prices (FIFO assumption)
3. You can always fill your posted quantity from market trades
4. No transaction costs, fees, or slippage
5. Competition doesn't adapt to your strategy

## Archived Backtests

Old backtest scripts that had flaws have been archived in `_archived_backtests/`:
- `quick_grid_search.py` — Sample-based, overfitted results
- `tight_grid_search.py` — Sample-based, overfitted results
- `pepper_fine_search.py` — Sample-based, overfitted results
- `full_backtest_round1.py` — Missing price data at trade timestamps
- `full_backtest_round1_correct.py` — Timeout due to 100k timestamps

**Do not use these.** They are kept for reference only.

## Example: Running a Grid Search

To test multiple parameter combinations:

```python
# In backtest_hybrid.py, replace configs with:
configs = [
    (Trader, f"pos={p}, spread={s}", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": p, "INTARIAN_PEPPER_ROOT": p},
        "OSMIUM_SPREAD": s
    })
    for p in [20, 40, 60]
    for s in [3, 4, 5]
]

# Then run: python backtest_hybrid.py
```

This generates 9 configurations and ranks them by profit automatically.

## Questions?

Refer to:
- [trader.py](trader.py) — Main strategy implementation
- [order_matcher.py](order_matcher.py) — Matching logic
- [OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md) — Parameter tuning history
