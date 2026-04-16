"""
SCALED GRID SEARCH: 20,000+ parameter combinations
Can run in background. Saves progress to CSV (resumes if interrupted).
Run: python grid_search_scaled.py &
"""

import pandas as pd
import numpy as np
import sys
import csv
from pathlib import Path
from itertools import product
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from load_data import load_all_trades

OUTPUT_DIR = Path(__file__).parent
RESULTS_FILE = OUTPUT_DIR / "grid_search_scaled_results.csv"


class TraderSimulator:
    """Simulates trader.py logic with configurable parameters"""

    def __init__(self, config):
        self.config = config
        self.osmium_history = []
        self.pepper_history = []
        self.positions = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
        self.balance = config.get("initial_balance", 100000)
        self.trades_executed = 0

    def calculate_vwap(self, prices, volumes):
        if len(prices) == 0:
            return None
        return np.average(prices, weights=volumes)

    def calculate_ema(self, prices, alpha):
        if len(prices) < 2:
            return prices[0] if len(prices) > 0 else None
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema

    def calculate_volatility(self, prices):
        if len(prices) < 2:
            return 0
        return np.std(prices[-20:])

    def get_position_scale(self, volatility, base_volatility):
        if volatility < base_volatility * 0.7:
            return 1.0
        elif volatility > base_volatility * 1.3:
            return 0.6
        else:
            return 0.8

    def process_trade(self, trade):
        symbol = trade["symbol"]
        price = trade["price"]
        quantity = trade["quantity"]

        if symbol == "ASH_COATED_OSMIUM":
            self.osmium_history.append([price, quantity])
            self.osmium_history = self.osmium_history[-self.config["osmium_vwap_window"]:]

            if len(self.osmium_history) > 0:
                prices = np.array([x[0] for x in self.osmium_history])
                volumes = np.array([x[1] for x in self.osmium_history])
                vwap = self.calculate_vwap(prices, volumes)
            else:
                vwap = 10000.0

            current_pos = self.positions[symbol]
            inventory_bias = current_pos * self.config["osmium_inventory_bias"]

            if len(self.osmium_history) > 0:
                recent_prices = np.array([x[0] for x in self.osmium_history])
                volatility = self.calculate_volatility(recent_prices)
                vol_scale = self.get_position_scale(volatility, self.config["osmium_vol_base"])
            else:
                vol_scale = 1.0

            room_to_buy = self.config["osmium_pos_limit"] - current_pos
            room_to_sell = -self.config["osmium_pos_limit"] - current_pos

            scaled_buy = int(room_to_buy * vol_scale)
            scaled_sell = int(room_to_sell * vol_scale)

            if price < vwap - 5 and scaled_buy > 0:
                buy_qty = min(5, scaled_buy)
                self.balance -= buy_qty * price
                self.positions[symbol] += buy_qty
                self.trades_executed += 1
            elif price > vwap + 5 and scaled_sell < 0:
                sell_qty = min(5, -scaled_sell)
                self.balance += sell_qty * price
                self.positions[symbol] -= sell_qty
                self.trades_executed += 1

        elif symbol == "INTARIAN_PEPPER_ROOT":
            self.pepper_history.append([price, quantity])
            self.pepper_history = self.pepper_history[-50:]

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

            if len(self.pepper_history) > 0:
                recent_prices = np.array([x[0] for x in self.pepper_history])
                volatility = self.calculate_volatility(recent_prices)
                vol_scale = self.get_position_scale(volatility, self.config["pepper_vol_base"])
            else:
                vol_scale = 1.0

            current_pos = self.positions[symbol]
            room_to_buy = self.config["pepper_pos_limit"] - current_pos
            room_to_sell = -self.config["pepper_pos_limit"] - current_pos

            scaled_buy = int(room_to_buy * vol_scale)
            scaled_sell = int(room_to_sell * vol_scale)

            if is_uptrend and scaled_buy > 0 and price < vwap + 20:
                buy_qty = min(3, scaled_buy)
                self.balance -= buy_qty * price
                self.positions[symbol] += buy_qty
                self.trades_executed += 1
            elif not is_uptrend and scaled_sell < 0 and price > vwap - 20:
                sell_qty = min(3, -scaled_sell)
                self.balance += sell_qty * price
                self.positions[symbol] -= sell_qty
                self.trades_executed += 1


def load_existing_results():
    if RESULTS_FILE.exists():
        return set(pd.read_csv(RESULTS_FILE)["combination_id"].unique())
    return set()


def save_result(row):
    file_exists = RESULTS_FILE.exists()
    with open(RESULTS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def run_scaled_grid_search():
    print("\n" + "="*80)
    print("SCALED GRID SEARCH - 20,000+ COMBINATIONS")
    print("="*80)

    print("\n[Loading historical data...]")
    trades_df = load_all_trades()
    print(f"Loaded {len(trades_df)} trades")

    # EXPANDED PARAMETER GRID
    param_grid = {
        # Osmium parameters (expanded around best values)
        "osmium_ema_alpha": [0.12, 0.15, 0.18, 0.2, 0.22, 0.25],
        "osmium_inventory_bias": [0.6, 0.65, 0.7, 0.75, 0.8],
        "osmium_vwap_window": [12, 15, 18, 20, 22],
        "osmium_pos_limit": [60, 70, 80],
        "osmium_vol_base": [12, 15, 18, 20],
        # Pepper parameters (expanded)
        "pepper_ema_alpha": [0.2, 0.22, 0.25, 0.28, 0.3],
        "pepper_pos_limit": [60, 70, 80],
        "pepper_vol_base": [250, 300, 350, 400],
    }

    # Calculate total
    total_combos = 1
    for values in param_grid.values():
        total_combos *= len(values)
    print(f"\n[Total combinations: {total_combos}]")

    tested = load_existing_results()
    print(f"[Already tested: {len(tested)}]")
    print(f"[New tests: {total_combos - len(tested)}]")

    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]
    all_combos = list(product(*param_values))

    results = []
    tested_count = 0

    print(f"\n[Starting... this will take ~60-90 minutes]\n")
    start_time = datetime.now()

    for combo_idx, combo_values in enumerate(all_combos):
        combo_dict = dict(zip(param_names, combo_values))
        combo_id = "_".join(f"{k}={v}" for k, v in sorted(combo_dict.items()))

        if combo_id in tested:
            continue

        config = {"initial_balance": 100000, **combo_dict}
        simulator = TraderSimulator(config)

        trades_sorted = trades_df.sort_values(["day", "timestamp"])
        for idx, trade in trades_sorted.iterrows():
            simulator.process_trade(trade)

        profit = simulator.balance - 100000

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

        save_result(output_row)
        results.append(output_row)
        tested_count += 1

        # Print every 50 tests
        if tested_count % 50 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / tested_count
            remaining = (total_combos - len(tested) - tested_count) * avg_time

            print(f"[{tested_count:,}/{total_combos - len(tested):,}] "
                  f"Best profit: {max([r['profit'] for r in results]):+,.0f} | "
                  f"Avg: {avg_time:.1f}s/test | "
                  f"Est. remaining: {remaining/3600:.1f} hours")

    # Final summary
    print(f"\n{'='*80}")
    print("COMPLETED")
    print(f"{'='*80}")
    all_results = pd.read_csv(RESULTS_FILE)
    top_result = all_results.nlargest(1, 'profit').iloc[0]

    print(f"\n✅ BEST RESULT FOUND:")
    print(f"   Profit: {top_result['profit']:+,.0f} ({top_result['target_progress']})")
    print(f"   Osmium: EMA={top_result['osmium_ema_alpha']}, Bias={top_result['osmium_inventory_bias']}, "
          f"Window={top_result['osmium_vwap_window']:.0f}, Limit={top_result['osmium_pos_limit']:.0f}, VolBase={top_result['osmium_vol_base']:.0f}")
    print(f"   Pepper: EMA={top_result['pepper_ema_alpha']}, Limit={top_result['pepper_pos_limit']:.0f}, VolBase={top_result['pepper_vol_base']:.0f}")

    print(f"\n📊 SUMMARY:")
    print(f"   Total tests: {len(all_results):,}")
    print(f"   Total time: {(datetime.now() - start_time).total_seconds()/3600:.1f} hours")
    print(f"   Results file: {RESULTS_FILE}")


if __name__ == "__main__":
    run_scaled_grid_search()
