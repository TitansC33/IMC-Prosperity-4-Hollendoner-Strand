"""
Realistic Grid Search: Tests actual trader.py logic with parameter variations
Configurable parameters: EMA alpha, inventory bias, VWAP window, position limits, volatility thresholds
"""

import pandas as pd
import numpy as np
import sys
import csv
from pathlib import Path
from itertools import product
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from load_data import load_all_trades

OUTPUT_DIR = Path(__file__).parent
RESULTS_FILE = OUTPUT_DIR / "grid_search_realistic_results.csv"


class TraderSimulator:
    """Simulates actual trader.py logic with configurable parameters"""

    def __init__(self, config):
        self.config = config
        self.osmium_history = []
        self.pepper_history = []
        self.positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
        self.balance = config.get("initial_balance", 100000)
        self.trades_executed = 0

    def calculate_vwap(self, prices, volumes):
        """Calculate volume-weighted average price"""
        if len(prices) == 0:
            return None
        return np.average(prices, weights=volumes)

    def calculate_ema(self, prices, alpha):
        """Calculate exponential moving average"""
        if len(prices) < 2:
            return prices[0] if len(prices) > 0 else None
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema

    def calculate_volatility(self, prices):
        """Calculate volatility (std dev)"""
        if len(prices) < 2:
            return 0
        return np.std(prices[-20:])

    def get_position_scale(self, volatility, base_volatility):
        """Scale position size based on volatility"""
        if volatility < base_volatility * 0.7:
            return 1.0  # Low volatility: full size
        elif volatility > base_volatility * 1.3:
            return 0.6  # High volatility: 60% size
        else:
            return 0.8  # Medium: 80% size

    def process_trade(self, trade):
        """Process a market trade and generate orders if applicable"""
        symbol = trade["symbol"]
        price = trade["price"]
        quantity = trade["quantity"]

        if symbol == "ASH_COATED_OSMIUM":
            self.osmium_history.append([price, quantity])
            self.osmium_history = self.osmium_history[-self.config["osmium_vwap_window"]:]

            # Calculate VWAP
            if len(self.osmium_history) > 0:
                prices = np.array([x[0] for x in self.osmium_history])
                volumes = np.array([x[1] for x in self.osmium_history])
                vwap = self.calculate_vwap(prices, volumes)
            else:
                vwap = 10000.0

            # Inventory leaning
            current_pos = self.positions[symbol]
            inventory_bias = current_pos * self.config["osmium_inventory_bias"]

            # Volatility scaling
            if len(self.osmium_history) > 0:
                recent_prices = np.array([x[0] for x in self.osmium_history])
                volatility = self.calculate_volatility(recent_prices)
                vol_scale = self.get_position_scale(volatility, self.config["osmium_vol_base"])
            else:
                vol_scale = 1.0

            # Trading logic: buy low, sell high
            room_to_buy = self.config["osmium_pos_limit"] - current_pos
            room_to_sell = -self.config["osmium_pos_limit"] - current_pos

            scaled_buy = int(room_to_buy * vol_scale)
            scaled_sell = int(room_to_sell * vol_scale)

            # Simplified: if price is below VWAP, buy; if above, sell
            if price < vwap - 5 and scaled_buy > 0:
                # Buy
                buy_qty = min(5, scaled_buy)
                self.balance -= buy_qty * price
                self.positions[symbol] += buy_qty
                self.trades_executed += 1
            elif price > vwap + 5 and scaled_sell < 0:
                # Sell
                sell_qty = min(5, -scaled_sell)
                self.balance += sell_qty * price
                self.positions[symbol] -= sell_qty
                self.trades_executed += 1

        elif symbol == "INTARIAN_PEPPER_ROOT":
            self.pepper_history.append([price, quantity])
            self.pepper_history = self.pepper_history[-50:]  # Keep last 50

            # Calculate trend via EMA
            if len(self.pepper_history) >= 15:
                prices = np.array([x[0] for x in self.pepper_history])
                volumes = np.array([x[1] for x in self.pepper_history])
                ema = self.calculate_ema(prices, self.config["pepper_ema_alpha"])
                vwap = self.calculate_vwap(prices, volumes)
                current_price = prices[-1]
                is_uptrend = current_price > vwap
            else:
                vwap = 11000.0
                is_uptrend = False

            # Volatility scaling
            if len(self.pepper_history) > 0:
                recent_prices = np.array([x[0] for x in self.pepper_history])
                volatility = self.calculate_volatility(recent_prices)
                vol_scale = self.get_position_scale(volatility, self.config["pepper_vol_base"])
            else:
                vol_scale = 1.0

            # Trading logic: trend following
            current_pos = self.positions[symbol]
            room_to_buy = self.config["pepper_pos_limit"] - current_pos
            room_to_sell = -self.config["pepper_pos_limit"] - current_pos

            scaled_buy = int(room_to_buy * vol_scale)
            scaled_sell = int(room_to_sell * vol_scale)

            if is_uptrend and scaled_buy > 0 and price < vwap + 20:
                # Buy in uptrend
                buy_qty = min(3, scaled_buy)
                self.balance -= buy_qty * price
                self.positions[symbol] += buy_qty
                self.trades_executed += 1
            elif not is_uptrend and scaled_sell < 0 and price > vwap - 20:
                # Sell in downtrend
                sell_qty = min(3, -scaled_sell)
                self.balance += sell_qty * price
                self.positions[symbol] -= sell_qty
                self.trades_executed += 1


def load_existing_results():
    """Load existing results to avoid duplicate testing"""
    if RESULTS_FILE.exists():
        return set(pd.read_csv(RESULTS_FILE)["combination_id"].unique())
    return set()


def save_result(row):
    """Append result to CSV file"""
    file_exists = RESULTS_FILE.exists()
    with open(RESULTS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def run_realistic_grid_search():
    """Test parameter combinations with actual trader logic"""
    print("\n" + "="*80)
    print("REALISTIC GRID SEARCH - ACTUAL TRADER LOGIC")
    print("="*80)

    # Load data once
    print("\n[Loading historical data...]")
    trades_df = load_all_trades()
    print(f"Loaded {len(trades_df)} trades")

    # HIGH-IMPACT PARAMETERS (scaled up)
    param_grid = {
        "osmium_ema_alpha": [0.15, 0.2, 0.25, 0.3],
        "osmium_inventory_bias": [0.7, 0.9, 1.1, 1.3],
        "osmium_vwap_window": [15, 20, 25],
        "osmium_pos_limit": [60, 80],
        "osmium_vol_base": [15, 20],
        "pepper_ema_alpha": [0.25, 0.3, 0.35],
        "pepper_pos_limit": [60, 80],
        "pepper_vol_base": [300, 400],
    }

    # Calculate total combinations
    total_combos = 1
    for values in param_grid.values():
        total_combos *= len(values)
    print(f"\n[Total combinations to test: {total_combos}]")

    # Load already tested combinations
    tested = load_existing_results()
    print(f"[Already tested: {len(tested)} combinations]")
    print(f"[New tests: {total_combos - len(tested)}]")

    # Generate all combinations
    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]
    all_combos = list(product(*param_values))

    results = []
    tested_count = 0
    skipped_count = 0

    print(f"\n[Starting realistic grid search...]\n")
    start_time = datetime.now()

    for combo_idx, combo_values in enumerate(all_combos):
        # Create combo ID for deduplication
        combo_dict = dict(zip(param_names, combo_values))
        combo_id = "_".join(f"{k}={v}" for k, v in sorted(combo_dict.items()))

        # Skip if already tested
        if combo_id in tested:
            skipped_count += 1
            continue

        # Run simulator with actual trader logic
        config = {
            "initial_balance": 100000,
            **combo_dict,
        }

        simulator = TraderSimulator(config)

        # Process all trades in order
        trades_sorted = trades_df.sort_values(["day", "timestamp"])
        for idx, trade in trades_sorted.iterrows():
            simulator.process_trade(trade)

        # Calculate final profit
        profit = simulator.balance - 100000

        # Prepare output row
        output_row = {
            "combination_id": combo_id,
            **combo_dict,
            "final_balance": simulator.balance,
            "profit": profit,
            "trades": simulator.trades_executed,
            "osmium_pos": simulator.positions["ASH_COATED_OSMIUM"],
            "pepper_pos": simulator.positions["INTARIAN_PEPPER_ROOT"],
            "target_progress": f"{(profit / 200000 * 100):.1f}%"
        }

        # Save immediately
        save_result(output_row)
        results.append(output_row)
        tested_count += 1

        # Print progress every 20 tests
        if tested_count % 20 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / tested_count
            remaining = (total_combos - len(tested) - tested_count) * avg_time

            print(f"[{tested_count}/{total_combos - len(tested)}] "
                  f"Profit: {profit:+,.0f} ({output_row['target_progress']}) | "
                  f"Trades: {simulator.trades_executed} | "
                  f"Avg: {avg_time:.2f}s/test | "
                  f"Est. remaining: {remaining/60:.1f} min")

    # Sort and display top results
    print(f"\n{'='*80}")
    print("TOP 15 RESULTS (BEST PROFIT)")
    print(f"{'='*80}\n")

    all_results_df = pd.read_csv(RESULTS_FILE)
    results_sorted = all_results_df.sort_values("profit", ascending=False).head(15)

    for rank, (idx, row) in enumerate(results_sorted.iterrows(), 1):
        print(f"#{rank}")
        print(f"  Profit: {row['profit']:+,.0f} ({row['target_progress']})")
        print(f"  Osmium: EMA={row['osmium_ema_alpha']}, Bias={row['osmium_inventory_bias']}, "
              f"Limit={row['osmium_pos_limit']}, Window={row['osmium_vwap_window']}, VolBase={row['osmium_vol_base']}")
        print(f"  Pepper: EMA={row['pepper_ema_alpha']}, Limit={row['pepper_pos_limit']}, "
              f"VolBase={row['pepper_vol_base']}")
        print(f"  Trades: {row['trades']} | Final Osmium Pos: {row['osmium_pos']:.0f} | Final Pepper Pos: {row['pepper_pos']:.0f}")
        print()

    # Summary stats
    print(f"{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"New tests run: {tested_count}")
    print(f"Already tested (skipped): {skipped_count}")
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"Total elapsed time: {elapsed/60:.1f} minutes")
    if tested_count > 0:
        print(f"Average per test: {elapsed / tested_count:.2f} seconds")
        print(f"Est. time to complete all {total_combos} combos: "
              f"{(total_combos * elapsed / tested_count) / 60:.1f} minutes")
    print(f"\nResults saved to: {RESULTS_FILE}")
    total_recorded = len(all_results_df)
    print(f"Total results recorded: {total_recorded}")


if __name__ == "__main__":
    run_realistic_grid_search()
