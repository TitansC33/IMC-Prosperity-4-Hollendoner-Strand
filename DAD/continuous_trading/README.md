# Continuous Trading Phase (72 hours - Automatic)

## Files in This Folder

### `trader.py` ← **SUBMIT THIS TO COMPETITION**
The main trading algorithm that runs automatically during Round 1 (Apr 14-17).

**What it does:**
- Trades ASH_COATED_OSMIUM (market-making strategy)
- Trades INTARIAN_PEPPER_ROOT (trend-following strategy)
- Runs every minute for 72 hours automatically
- Expected profit: +340,091 XIRECs (170% of 200k target)

**Phase 2 Optimized Parameters** (grid search plateau validated):
- Osmium: EMA_Alpha=0.15, Inventory_Bias=0.7, VWAP_Window=15, Vol_Base=20
- Pepper: EMA_Alpha=0.3, Vol_Base=300
- Enhancements: Adaptive EMA + Mean Reversion detection (1.5x scaling)

### `backtest_v2.py`
Validates the trading strategy on historical data.

**To run:**
```bash
python backtest_v2.py
```

**Output:**
- Tests 5 position limit configurations
- Best result: +340,091 XIRECs with ±80 limits
- Confirms strategy is profitable

## How to Use

1. **Before Round 1**: Run `backtest_v2.py` to validate
2. **Submit**: Copy `trader.py` to competition platform
3. **During Round 1**: Let it run automatically

## Documentation

See `../docs/HOW_IT_WORKS.md` for complete algorithm explanation
See `../docs/IMPLEMENTATION_SUMMARY.md` for validation results
