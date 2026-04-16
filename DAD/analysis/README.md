# Analysis & Development (Reference Only)

## Purpose
Development scripts used to build and optimize the trading strategies. These are **not needed for Round 1 competition**, but kept for reference and future optimization.

## Data Loading

### `load_data.py`
Utility for loading historical market data from CSV files.

**Data sources**: 
- 3 days of historical data (Day -2, -1, 0)
- OSMIUM and PEPPER trading data
- Order book snapshots (bid/ask prices)

**Used by**: All analysis scripts

## Statistical Analysis

### `analyze_prices.py`
Analyzes historical trading patterns to inform strategy selection.

**Findings**:
- **OSMIUM**: Mean-reverting (autocorrelation -0.509) → Market-making optimal
- **PEPPER**: Trending upward (+9-10% daily) → Trend-following optimal
- Bid-ask spreads: Osmium ~16, Pepper ~13

### `visualize.py`
Creates charts of market data.

**Outputs** (in this folder):
- `price_timeseries.png` - Price evolution over 3 days
- `price_momentum.png` - Up/down move analysis
- `price_comparison.png` - Osmium vs Pepper comparison
- `bid_ask_spreads.png` - Spread width analysis
- `price_distributions.png` - Price histograms
- `volume_analysis.png` - Trading volume patterns

### `time_block_analysis.py`
Breaks each day into 50 time blocks to find intraday patterns.

**Outputs**:
- `time_block_analysis.txt` - Detailed intraday breakdown

## Parameter Optimization

### `grid_search_backtest.py`
Basic grid search (768 combinations). ⚠️ **Obsolete** - superseded by realistic version.

### `grid_search_realistic.py`
Realistic grid search (2,304 combinations) simulating actual trader.py logic.
Result: +161,186 XIRECs (Phase 1 optimal)

### `grid_search_scaled.py`
Extended grid search (1,025+ combinations tested).
Result: +161,186 XIRECs (Phase 2 plateau confirmed - no improvement)

**Final Phase 2 Parameters** (now in `../continuous_trading/trader.py`):
- Osmium: EMA_Alpha=0.15, Inventory_Bias=0.7, VWAP_Window=15, Vol_Base=20
- Pepper: EMA_Alpha=0.3, Vol_Base=300
- Enhancements: Adaptive EMA Alpha + Mean Reversion detection (1.5x scaling)
- Result: +340,091 XIRECs (170% of target) via backtest_v2.py

## Reference Files

### `trader_original.py`
Your son's original trader.py (before optimization). Kept for reference.

## How These Were Used

1. **analyze_prices.py** → Discovered Osmium/Pepper patterns
2. **visualize.py** → Created charts for manual review
3. **grid_search_realistic.py** → Found optimal parameters
4. **Results** → Parameters incorporated into trader.py for Round 1

## If You Want to Optimize Further

Run during off-season:
```bash
# New grid search with different parameters
python grid_search_realistic.py

# Analyze new market data
python analyze_prices.py
python visualize.py
```

But for **Round 1 (Apr 14-17)**: Use trader.py as-is. It's validated and ready.
