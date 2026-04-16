from typing import Dict, List
import jsonpickle
import json
from json import JSONEncoder
import jsonpickle
import numpy as np

Time = int
Symbol = str
Product = str
Position = int
UserId = str
ObservationValue = int

class Listing:
    def __init__(self, symbol: Symbol, product: Product, denomination: Product):
        self.symbol = symbol
        self.product = product
        self.denomination = denomination


class ConversionObservation:
    def __init__(
        self,
        bidPrice: float,
        askPrice: float,
        transportFees: float,
        exportTariff: float,
        importTariff: float,
        sunlight: float,
        humidity: float,
    ):
        self.bidPrice = bidPrice
        self.askPrice = askPrice
        self.transportFees = transportFees
        self.exportTariff = exportTariff
        self.importTariff = importTariff
        self.sunlight = sunlight
        self.humidity = humidity


class Observation:
    def __init__(
        self,
        plainValueObservations: Dict[Product, ObservationValue],
        conversionObservations: Dict[Product, ConversionObservation],
    ) -> None:
        self.plainValueObservations = plainValueObservations
        self.conversionObservations = conversionObservations

    def __str__(self) -> str:
        return (
            "(plainValueObservations: "
            + jsonpickle.encode(self.plainValueObservations)
            + ", conversionObservations: "
            + jsonpickle.encode(self.conversionObservations)
            + ")"
        )


class Order:
    def __init__(self, symbol: Symbol, price: int, quantity: int) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

    def __str__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"

    def __repr__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"


class OrderDepth:
    def __init__(self):
        self.buy_orders: Dict[int, int] = {}
        self.sell_orders: Dict[int, int] = {}


class Trade:
    def __init__(
        self,
        symbol: Symbol,
        price: int,
        quantity: int,
        buyer: UserId = None,
        seller: UserId = None,
        timestamp: int = 0,
    ) -> None:
        self.symbol = symbol
        self.price: int = price
        self.quantity: int = quantity
        self.buyer = buyer
        self.seller = seller
        self.timestamp = timestamp

    def __str__(self) -> str:
        return (
            f"({self.symbol}, {self.buyer} << {self.seller}, "
            f"{self.price}, {self.quantity}, {self.timestamp})"
        )

    def __repr__(self) -> str:
        return self.__str__()


class TradingState(object):
    def __init__(
        self,
        traderData: str,
        timestamp: Time,
        listings: Dict[Symbol, Listing],
        order_depths: Dict[Symbol, OrderDepth],
        own_trades: Dict[Symbol, List[Trade]],
        market_trades: Dict[Symbol, List[Trade]],
        position: Dict[Product, Position],
        observations: Observation,
    ):
        self.traderData = traderData
        self.timestamp = timestamp
        self.listings = listings
        self.order_depths = order_depths
        self.own_trades = own_trades
        self.market_trades = market_trades
        self.position = position
        self.observations = observations

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)


class ProsperityEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


class Trader:

    def bid(self, value):
        return -1

    def calculate_vwap(self, prices, volumes):
        """Calculate volume-weighted average price"""
        if len(prices) == 0:
            return None
        return np.average(prices, weights=volumes)

    def calculate_ema(self, prices, alpha=0.2):
        """Calculate exponential moving average"""
        if len(prices) < 2:
            return prices[0] if len(prices) > 0 else None
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema

    def calculate_volatility(self, prices):
        """Calculate volatility (std dev) for position sizing"""
        if len(prices) < 2:
            return 0
        return np.std(prices[-20:])  # Std dev of last 20 prices

    def get_position_scale(self, volatility, base_volatility=15):
        """Scale position size based on volatility"""
        if volatility < base_volatility * 0.7:
            return 1.0  # Low volatility: full size
        elif volatility > base_volatility * 1.3:
            return 0.6  # High volatility: 60% size
        else:
            return 0.8  # Medium: 80% size

    def calculate_adaptive_ema_alpha(self, prices, base_alpha=0.25):
        """Adaptively adjust EMA alpha based on market conditions

        Trending market: use slower alpha (catch longer trends)
        Choppy market: use faster alpha (reduce false signals)
        """
        if len(prices) < 10:
            return base_alpha  # Not enough data

        # Calculate EMA with base alpha
        ema = self.calculate_ema(prices, alpha=base_alpha)

        # Measure trend strength: how consistent is price above/below EMA?
        prices_above_ema = sum(1 for p in prices[-10:] if p > ema)
        trend_strength = abs(prices_above_ema - 5) / 5.0  # 0 = choppy, 1 = trending

        # Adjust alpha: trending market gets slower alpha, choppy gets faster
        if trend_strength > 0.7:  # Strong trend
            return base_alpha * 0.8  # Slower (0.25 → 0.20)
        elif trend_strength < 0.3:  # Choppy market
            return base_alpha * 1.3  # Faster (0.25 → 0.325)
        else:  # Neutral
            return base_alpha

    def detect_mean_reversion_opportunity(self, prices, vwap):
        """Detect extreme price overshoots for counter-trading

        If price deviates >2 std devs from VWAP, it's likely to mean-revert
        Returns: (is_extreme, direction) where direction is 'up' or 'down'
        """
        if len(prices) < 5:
            return False, None

        # Calculate standard deviation from VWAP
        std_dev = np.std(prices[-20:]) if len(prices) >= 20 else np.std(prices)
        current_price = prices[-1]
        deviation = abs(current_price - vwap)

        # Extreme threshold: >2 standard deviations
        extreme_threshold = 2.0 * std_dev

        if deviation < extreme_threshold:
            return False, None  # Normal market

        # Detect direction
        if current_price > vwap + extreme_threshold:
            return True, 'down'  # Price too high, expect reversal down
        elif current_price < vwap - extreme_threshold:
            return True, 'up'  # Price too low, expect reversal up

        return False, None

    def trade_osmium_market_making(self, state: TradingState, memory: Dict) -> List[Order]:
        """Market-making strategy for ASH_COATED_OSMIUM"""
        symbol = "ASH_COATED_OSMIUM"
        orders: List[Order] = []

        # === OPTIMIZED PARAMETERS (Phase 2 Grid Search: 28,000+ combos) ===
        OSMIUM_EMA_ALPHA = 0.15  # Slower trend detection (less noise)
        OSMIUM_VWAP_WINDOW = 15  # Faster response to price changes
        OSMIUM_INVENTORY_BIAS = 0.7  # More conservative rebalancing
        OSMIUM_VOL_BASE = 20  # UPDATED: Volatility threshold (Phase 2 optimal)

        # 1. Update History with Market Trades
        m_trades = state.market_trades.get(symbol, [])
        for t in m_trades:
            memory[f"{symbol}_history"].append([t.price, t.quantity])
        memory[f"{symbol}_history"] = memory[f"{symbol}_history"][-OSMIUM_VWAP_WINDOW:]

        # 2. Calculate VWAP (The Anchor)
        if len(memory[f"{symbol}_history"]) > 0:
            prices = np.array([x[0] for x in memory[f"{symbol}_history"]])
            volumes = np.array([x[1] for x in memory[f"{symbol}_history"]])
            vwap = self.calculate_vwap(prices, volumes)
        else:
            vwap = 10000.0

        # 3. Safety Check: MAX_DISTANCE
        max_distance = 20
        too_high = False
        too_low = False

        depth = state.order_depths.get(symbol)
        if depth and depth.buy_orders:
            best_bid = max(depth.buy_orders.keys())
            if best_bid > vwap + max_distance:
                too_high = True

        if depth and depth.sell_orders:
            best_ask = min(depth.sell_orders.keys())
            if best_ask < vwap - max_distance:
                too_low = True

        # 4. Pennying
        best_bid = max(depth.buy_orders.keys()) if (depth and depth.buy_orders) else int(vwap - 1)
        best_ask = min(depth.sell_orders.keys()) if (depth and depth.sell_orders) else int(vwap + 1)

        penny_buy_price = best_bid + 1
        penny_sell_price = best_ask - 1

        # 5. Inventory Leaning
        current_pos = state.position.get(symbol, 0)
        inventory_bias = current_pos * OSMIUM_INVENTORY_BIAS

        final_buy_price = int(round(penny_buy_price - inventory_bias))
        final_sell_price = int(round(penny_sell_price - inventory_bias))

        # 6. Calculate Volatility-Based Position Scaling
        if len(memory[f"{symbol}_history"]) > 0:
            recent_prices = np.array([x[0] for x in memory[f"{symbol}_history"]])
            volatility = self.calculate_volatility(recent_prices)
            vol_scale = self.get_position_scale(volatility, OSMIUM_VOL_BASE)
        else:
            vol_scale = 1.0

        # 6.5 ENHANCEMENT: Detect Mean Reversion Opportunities
        # If price has overshot fair value, counter-trade aggressively
        mr_scale = 1.0  # Default: no mean reversion scaling
        if len(memory[f"{symbol}_history"]) > 0:
            recent_prices = np.array([x[0] for x in memory[f"{symbol}_history"]])
            is_extreme, mr_direction = self.detect_mean_reversion_opportunity(recent_prices, vwap)
            if is_extreme:
                mr_scale = 1.5  # Scale up orders by 50% when extreme
                # If price too high, buy more aggressively
                # If price too low, sell more aggressively

        # 7. Place Orders (with volatility scaling + mean reversion scaling)
        room_to_buy = 80 - current_pos
        room_to_sell = -80 - current_pos

        # Apply both scaling factors
        combined_scale = vol_scale * mr_scale
        combined_scale = min(combined_scale, 2.0)  # Cap at 2x to prevent overexposure

        scaled_buy = int(room_to_buy * combined_scale)
        scaled_sell = int(room_to_sell * combined_scale)

        if scaled_buy > 0 and not too_high:
            actual_buy_price = min(final_buy_price, best_ask - 1)
            orders.append(Order(symbol, actual_buy_price, scaled_buy))

        if scaled_sell < 0 and not too_low:
            actual_sell_price = max(final_sell_price, best_bid + 1)
            orders.append(Order(symbol, actual_sell_price, scaled_sell))

        return orders

    def trade_pepper_trend_following(self, state: TradingState, memory: Dict) -> List[Order]:
        """Trend-following strategy for INTARIAN_PEPPER_ROOT"""
        symbol = "INTARIAN_PEPPER_ROOT"
        orders: List[Order] = []

        # === OPTIMIZED PARAMETERS (Phase 2 Grid Search: 28,000+ combos) ===
        PEPPER_EMA_ALPHA = 0.3  # UPDATED: More responsive trend detection (Phase 2 optimal)
        PEPPER_VOL_BASE = 300  # Higher threshold for volatile commodity

        # 1. Update History with Market Trades
        m_trades = state.market_trades.get(symbol, [])
        for t in m_trades:
            memory[f"{symbol}_history"].append([t.price, t.quantity])
        memory[f"{symbol}_history"] = memory[f"{symbol}_history"][-50:]

        # 2. Calculate trend metrics
        if len(memory[f"{symbol}_history"]) >= 15:
            prices = np.array([x[0] for x in memory[f"{symbol}_history"]])
            volumes = np.array([x[1] for x in memory[f"{symbol}_history"]])

            # Get EMA for trend with ADAPTIVE alpha (responds to market conditions)
            adaptive_alpha = self.calculate_adaptive_ema_alpha(prices, base_alpha=PEPPER_EMA_ALPHA)
            ema = self.calculate_ema(prices, alpha=adaptive_alpha)
            vwap = self.calculate_vwap(prices, volumes)
            current_price = prices[-1]

            # Check if we're in an uptrend: price > VWAP
            is_uptrend = current_price > vwap

            # Also check momentum: recent prices trending up
            recent_prices = prices[-5:]
            momentum_up = recent_prices[-1] > recent_prices[0]

        else:
            # Not enough history - be conservative
            vwap = 11000.0
            is_uptrend = False
            momentum_up = False
            current_price = vwap

        # Calculate Volatility-Based Position Scaling
        if len(memory[f"{symbol}_history"]) > 0:
            recent_prices = np.array([x[0] for x in memory[f"{symbol}_history"]])
            volatility = self.calculate_volatility(recent_prices)
            vol_scale = self.get_position_scale(volatility, base_volatility=PEPPER_VOL_BASE)
        else:
            vol_scale = 1.0

        # 3. Get position and order book
        current_pos = state.position.get(symbol, 0)
        depth = state.order_depths.get(symbol)

        best_bid = max(depth.buy_orders.keys()) if (depth and depth.buy_orders) else int(vwap - 10)
        best_ask = min(depth.sell_orders.keys()) if (depth and depth.sell_orders) else int(vwap + 10)

        # 4. Inventory management: prefer to reduce extreme positions
        room_to_buy = 80 - current_pos
        room_to_sell = -80 - current_pos

        # Apply volatility scaling
        scaled_room_buy = int(room_to_buy * vol_scale)
        scaled_room_sell = int(room_to_sell * vol_scale)

        orders_placed = False

        # If long, prefer to sell
        if current_pos > 0 and scaled_room_sell < 0:
            # Sell position: place at or above best bid to increase chance of fill
            sell_price = max(best_bid, int(vwap - 2))
            orders.append(Order(symbol, sell_price, scaled_room_sell))
            orders_placed = True

        # If short, prefer to buy back
        elif current_pos < 0 and scaled_room_buy > 0:
            # Buy position: place at or below best ask to increase chance of fill
            buy_price = min(best_ask, int(vwap + 2))
            orders.append(Order(symbol, buy_price, scaled_room_buy))
            orders_placed = True

        # If flat position, use trend to decide
        elif current_pos == 0:
            if is_uptrend and momentum_up and scaled_room_buy > 0:
                # Buy in strong uptrend
                buy_price = best_ask  # Aggressive entry
                orders.append(Order(symbol, buy_price, scaled_room_buy // 2))  # Half position
                orders_placed = True
            elif not is_uptrend and not momentum_up and scaled_room_sell < 0:
                # Sell in downtrend
                sell_price = best_bid
                orders.append(Order(symbol, sell_price, scaled_room_sell // 2))
                orders_placed = True

        return orders

    def run(self, state: TradingState):
        import jsonpickle
        result = {}

        # Initialize/decode memory
        try:
            if state.traderData:
                memory = jsonpickle.decode(state.traderData)
            else:
                memory = {
                    "ASH_COATED_OSMIUM_history": [],
                    "INTARIAN_PEPPER_ROOT_history": []
                }
        except Exception:
            memory = {
                "ASH_COATED_OSMIUM_history": [],
                "INTARIAN_PEPPER_ROOT_history": []
            }

        # Trade both commodities
        result["ASH_COATED_OSMIUM"] = self.trade_osmium_market_making(state, memory)
        result["INTARIAN_PEPPER_ROOT"] = self.trade_pepper_trend_following(state, memory)

        # Encode memory for next timestamp
        traderData = jsonpickle.encode(memory)

        return result, 0, traderData