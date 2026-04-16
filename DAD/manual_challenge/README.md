# Manual Challenge - Auction Bidding Phase

## Files in This Folder

### `auction_backtest.py`
Validates the auction bidding strategy using market microstructure patterns.

**To run:**
```bash
python auction_backtest.py
```

**What it does:**
- Simulates 200 auction scenarios for each product
- Uses bid-ask patterns from continuous trading data
- Tests bidding algorithm for profitability
- Results: 100% viable on both products

**Output:**
- DRYLAND_FLAX: avg +2,372 XIRECs per scenario
- EMBER_MUSHROOM: avg +95 XIRECs per scenario
- Total auction expected: +4,934 XIRECs (bonus)

## Bidding Strategy

During Round 1, you'll be notified of the auction. Two separate auctions:

### DRYLAND_FLAX
- **Fair value**: ~25 XIRECs (estimated from bid/ask)
- **Buyback price**: 30 XIRECs (guaranteed after auction, no fees)
- **Profit target**: 30 - estimated_clearing_price
- **Expected profit**: +2,372 XIRECs

### EMBER_MUSHROOM
- **Fair value**: ~18 XIRECs
- **Buyback price**: 20 XIRECs (guaranteed after auction, 0.10 fee)
- **Profit target**: (20 - 0.10) - estimated_clearing_price
- **Expected profit**: +95 XIRECs

## How to Use During Round 1

1. **Before auction**: Read `../docs/MANUAL_CHALLENGE_STRATEGY.md` for algorithm
2. **When auction opens**:
   - See all existing bids/asks on the order book
   - Estimate clearing price (median of bid/ask prices)
   - Calculate profit: buyback_price - estimated_clearing
   - If profit > 0, bid aggressively to maximize quantity
   - Bid price = best_bid_in_market + 1 (frontrun by 1 unit)
   - Submit before auction closes

3. **After auction**: Trading executes at clearing price, you can sell at buyback

## Documentation

See `../docs/MANUAL_CHALLENGE_STRATEGY.md` for complete bidding algorithm
See `../docs/STAGE_1_GUIDE.md` for Phase 2 execution checklist
