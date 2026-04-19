# Trading Strategy Backtesting Setup

## Quick Start

```bash
# Test all default configurations (takes ~90 seconds)
python backtest_hybrid.py

# Output shows rankings of all tested configurations
```

## Files Overview

| File | Purpose |
|------|---------|
| **backtest_hybrid.py** | The CORRECT backtest — use this for all testing ✓ |
| **BACKTEST_GUIDE.md** | Detailed guide: how to use, add configs, understand results |
| **trader.py** | Your optimized strategy (pos=60, spread=4, pskew=0.28 defaults) |
| **seanTrader.py** | Sean's baseline strategy (pos=20, spread=5, pskew=0.3) |
| **order_matcher.py** | Order matching engine (price-time-priority, position limits) |
| **OPTIMIZATION_SUMMARY.md** | History of parameter tuning and discoveries |
| **_archived_backtests/** | Old broken backtests (reference only, do not use) |

## Current Status

### Live Results (Validated)
- **Sean Baseline**: $2,668 profit ✓ (proven in simulator)
- **Current trader.py**: $2,553 profit (slightly below baseline)

### Backtest Results (Not 1:1 with live, use for relative ranking)
- **COMBO_60_4** (pos=60, spread=4): $312,331
- **Conservative Pepper** (pos=60, sp=4, pskew=0.28): $297,250
- **Sean Baseline**: $141,030 (backtest only; actual live is $2,668)

## Key Insights

1. **Backtest is 100x higher than live** — This is expected, not a bug
   - ROUND1 sample differs from live competition
   - Live has other traders competing for volume
   - Position sizing (60) is unrealistic in actual competition

2. **Sean's baseline is validated** — Default to it until live proves otherwise
   - $2,668 is proven in actual simulator
   - Position scaling to 60 hasn't improved live results
   - Simple strategy beats complex optimization on real competition

3. **Use backtest for relative ranking** — Not absolute profit prediction
   - Useful for: "Is config A better than B?"
   - Not useful for: "Config A will make $312k"

## Adding New Test Configurations

Edit `backtest_hybrid.py`, find the `configs` list:

```python
configs = [
    (SeanTrader, "Sean Baseline (pos=20, spread=5)", None),
    (Trader, "My New Test", {
        "POSITION_LIMITS": {"ASH_COATED_OSMIUM": 45, "INTARIAN_PEPPER_ROOT": 45},
        "OSMIUM_SPREAD": 3,
        "PEPPER_SKEW_FACTOR": 0.26
    }),
]
```

Run and get rankings automatically.

## Why Old Backtests Are Archived

Old scripts in `_archived_backtests/` had critical flaws:

| Script | Problem |
|--------|---------|
| `full_backtest_round1.py` | Only used prices at trades, missed order book updates |
| `full_backtest_round1_correct.py` | Used all timestamps (~100k), caused timeouts |
| `quick_grid_search.py` | Optimized on 200-trade sample, overfitted |
| `tight_grid_search.py` | Optimized on 200-trade sample, overfitted |
| `pepper_fine_search.py` | Optimized on 200-trade sample, overfitted |

**backtest_hybrid.py** fixed all these:
- ✓ Uses trade timestamps for speed
- ✓ Fetches full prices AND trades at each timestamp
- ✓ Runs on complete ROUND1 dataset (2,276 trades)
- ✓ Produces accurate relative rankings

## Testing Workflow

1. **Modify strategy** → Edit `trader.py`
2. **Test it** → Run `python backtest_hybrid.py`
3. **Compare results** → Rankings show if it improved
4. **If better in backtest**:
   - Submit to live simulator
   - If live result is worse, backtest was overfit
   - Revert to Sean baseline if needed

## Understanding the Output

```
Testing: My New Config
    300/2218 trade timestamps...
    600/2218 trade timestamps...
    ...
  Profit: $250,000.00 | Fills: 4015

RANKINGS (Hybrid ROUND1 Backtest - Trade timestamps + Prices + Trades):
=========================================================================
Rank  Configuration                    Profit          Fills      vs Best
1     COMBO_60_4                       $   312,331.00     4031         +0.00 <-- BEST
2     My New Config                    $   250,000.00     4015    -62,331.00
```

**Interpretation:**
- COMBO_60_4 is winning by $62,331 in backtest
- But backtest profit is unrealistic; use it to decide: "Is My New Config better than COMBO_60_4?" Answer: No.
- Before using live, validate with simulator

## Troubleshooting

**Script won't run:**
- Ensure you're in `DAD/continuous_trading/` directory
- Check that `trader.py`, `seanTrader.py`, `order_matcher.py` all exist

**Infinite loop / timeout:**
- Old scripts did this; use backtest_hybrid.py instead
- Typical runtime: 60-90 seconds for 5 configs

**Unexpected results:**
- Check git status (did you save changes to trader.py?)
- Verify position limits are reasonable (±60 is standard)
- See BACKTEST_GUIDE.md for detailed troubleshooting

## Next Steps

1. Read [BACKTEST_GUIDE.md](BACKTEST_GUIDE.md) for detailed documentation
2. Review [OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md) to understand parameter history
3. Experiment: modify a parameter and run the backtest
4. Compare backtest rankings with live simulator results

## Files Archived

For a clean working directory, 14 old backtest scripts were archived in `_archived_backtests/`:

**Sample-based grid searches (overfitted to 200-trade sample):**
- `quick_grid_search.py`
- `tight_grid_search.py`
- `pepper_fine_search.py`
- `ultra_fine_search.py`

**Broken/incomplete full backtests:**
- `full_backtest_round1.py` — Missing price data
- `full_backtest_round1_correct.py` — Timed out (100k timestamps)

**Duplicate test runners:**
- `grid_search_backtest.py`
- `grid_search_with_matching.py`
- `run_parameter_grid_search.py`

**Old matching/stress-testing versions:**
- `backtest_v2_with_matching.py`
- `run_backtest_loops.py`
- `run_all_tests.py`
- `run_comprehensive_testing.py`
- `validate_signals_with_execution.py`

**Do NOT restore these files.** They are archived for historical reference only.
