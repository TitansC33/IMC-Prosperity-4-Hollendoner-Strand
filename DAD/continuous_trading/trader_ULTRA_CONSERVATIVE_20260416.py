from typing import Dict, List, Tuple, Optional
import json
from json import JSONEncoder

import jsonpickle

# Global Variables
Time = int
Symbol = str
Product = str
Position = int
UserId = str
ObservationValue = int

# Class, constructors for each data type
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

# Core Trader Class | Algo
class Trader():

    def __init__(self):
        self.POSITION_LIMITS = {
            'ASH_COATED_OSMIUM': 10,           # ULTRA CONSERVATIVE: Smaller positions avoid catastrophic fills
            'INTARIAN_PEPPER_ROOT': 10         # Validated: +3/3 days profitable vs 1/3 for larger positions
        }

        # Osmium
        self.OSMIUM_FAIR_VALUE_SEED = 10000  # starting prior, replaced by EWM after first tick
        self.OSMIUM_EWM_ALPHA = 0.002        # half-life ~350 ticks (~3.5% of a day)
        self.OSMIUM_SPREAD = 2                # ULTRA CONSERVATIVE: Tighter spread for better fills
        self.OSMIUM_SKEW_FACTOR = 0.2        # shifts quotes 0.2 ticks per unit of inventory

        # Pepper Root
        self.PEPPER_LARGE_ORDER_THRESHOLD = 18  # Original
        self.PEPPER_QUOTE_IMPROVEMENT = 1        # overbid/undercut large MM by 1
        self.PEPPER_SKEW_FACTOR = 0.1            # ULTRA CONSERVATIVE: Much lower skew (from 0.28)
                                                 # Reduces aggressive rebalancing losses

    def get_large_order_mid(self, order_depth: OrderDepth, threshold: int) -> Optional[float]:
        """
        Get mid price from LARGE orders only (filtering noise from small orders)
        This identifies the consistent market makers' fair value
        """
        # Find largest bid
        large_bid = None
        if order_depth.buy_orders:
            for price, volume in order_depth.buy_orders.items():
                if volume >= threshold:
                    if large_bid is None or price > large_bid:
                        large_bid = price

        # Find largest ask
        large_ask = None
        if order_depth.sell_orders:
            for price, volume in order_depth.sell_orders.items():
                if abs(volume) >= threshold:
                    if large_ask is None or price < large_ask:
                        large_ask = price

        # Calculate mid from large orders
        if large_bid and large_ask:
            return (large_bid + large_ask) / 2
        elif large_bid:
            return large_bid + 10  # Estimate
        elif large_ask:
            return large_ask - 10  # Estimate

        # Fallback to regular mid
        if order_depth.buy_orders and order_depth.sell_orders:
            return (max(order_depth.buy_orders.keys()) + min(order_depth.sell_orders.keys())) / 2

        return None

    def get_large_order_levels(self, order_depth: OrderDepth, threshold: int) -> Tuple[Optional[int], Optional[int]]:
        """Get the price levels where large orders sit"""
        large_bid = None
        large_bid_vol = 0

        if order_depth.buy_orders:
            for price, volume in order_depth.buy_orders.items():
                if volume >= threshold and volume > large_bid_vol:
                    large_bid = price
                    large_bid_vol = volume

        large_ask = None
        large_ask_vol = 0

        if order_depth.sell_orders:
            for price, volume in order_depth.sell_orders.items():
                if abs(volume) >= threshold and abs(volume) > large_ask_vol:
                    large_ask = price
                    large_ask_vol = abs(volume)

        return large_bid, large_ask

    def trade_osmium(self, state: TradingState, state_data: dict) -> List[Order]:
        product = 'ASH_COATED_OSMIUM'
        orders = []

        if product not in state.order_depths:
            return orders

        order_depth = state.order_depths[product]
        position = state.position.get(product, 0)
        position_limit = self.POSITION_LIMITS[product]

        buy_capacity = position_limit - position
        sell_capacity = position_limit + position

        # Update EWM fair value from current mid-price
        fair_value = state_data.get('osmium_ewm', self.OSMIUM_FAIR_VALUE_SEED)
        if order_depth.buy_orders and order_depth.sell_orders:
            current_mid = (max(order_depth.buy_orders.keys()) + min(order_depth.sell_orders.keys())) / 2
            fair_value = self.OSMIUM_EWM_ALPHA * current_mid + (1 - self.OSMIUM_EWM_ALPHA) * fair_value
        state_data['osmium_ewm'] = fair_value

        skew = self.OSMIUM_SKEW_FACTOR * position

        # TAKE: skewed thresholds — less eager to buy when long, more eager to sell
        if order_depth.sell_orders and buy_capacity > 0:
            asks = sorted(order_depth.sell_orders.items())
            for ask_price, ask_volume in asks:
                ask_volume = abs(ask_volume)
                if ask_price < fair_value - 2 - skew:
                    buy_quantity = min(ask_volume, buy_capacity)
                    if buy_quantity > 0:
                        orders.append(Order(product, ask_price, buy_quantity))
                        buy_capacity -= buy_quantity
                        position += buy_quantity

        if order_depth.buy_orders and sell_capacity > 0:
            bids = sorted(order_depth.buy_orders.items(), reverse=True)
            for bid_price, bid_volume in bids:
                if bid_price > fair_value + 2 - skew:
                    sell_quantity = min(bid_volume, sell_capacity)
                    if sell_quantity > 0:
                        orders.append(Order(product, bid_price, -sell_quantity))
                        sell_capacity -= sell_quantity
                        position -= sell_quantity

        # POST: skewed passive quotes — long shifts both prices down (cheaper ask attracts
        # sellers); short shifts both prices up (higher bid attracts buyers)
        if buy_capacity > 0:
            our_bid_price = fair_value - self.OSMIUM_SPREAD - skew
            if not order_depth.sell_orders or our_bid_price < min(order_depth.sell_orders.keys()):
                #bid_quantity = min(10, buy_capacity)
                bid_quantity = buy_capacity
                orders.append(Order(product, int(our_bid_price), bid_quantity))

        if sell_capacity > 0:
            our_ask_price = fair_value + self.OSMIUM_SPREAD - skew
            if not order_depth.buy_orders or our_ask_price > max(order_depth.buy_orders.keys()):
                #ask_quantity = min(10, sell_capacity)
                ask_quantity = sell_capacity
                orders.append(Order(product, int(our_ask_price), -ask_quantity))

        return orders

    def trade_pepper_filtered(self, state: TradingState) -> List[Order]:
        """
        Pepper Root - Kelp-style strategy with large order filtering

        Key insight from top teams:
        1. Identify LARGE consistent market maker orders (volume >= threshold)
        2. Use THEIR mid price as fair value (ignore small noisy orders)
        3. Take anything that crosses this fair value
        4. Quote just inside the large market makers (overbid/undercut by 1)
        5. Aggressively neutralize inventory
        """
        product = 'INTARIAN_PEPPER_ROOT'
        orders = []

        if product not in state.order_depths:
            return orders

        order_depth = state.order_depths[product]
        position = state.position.get(product, 0)
        position_limit = self.POSITION_LIMITS[product]

        buy_capacity = position_limit - position
        sell_capacity = position_limit + position

        # Get fair value from LARGE orders only
        fair_value = self.get_large_order_mid(order_depth, self.PEPPER_LARGE_ORDER_THRESHOLD)

        if fair_value is None:
            return orders

        # Get the actual large order price levels
        large_bid, large_ask = self.get_large_order_levels(order_depth, self.PEPPER_LARGE_ORDER_THRESHOLD)

        target_position = 8
        skew = self.PEPPER_SKEW_FACTOR * (position - target_position)

        # TAKE: skewed thresholds — less eager to buy when long, more eager to sell
        if order_depth.sell_orders and buy_capacity > 0:
            asks = sorted(order_depth.sell_orders.items())
            for ask_price, ask_volume in asks:
                ask_volume = abs(ask_volume)
                if ask_price <= fair_value - skew:
                    buy_quantity = min(ask_volume, buy_capacity)
                    if buy_quantity > 0:
                        orders.append(Order(product, ask_price, buy_quantity))
                        buy_capacity -= buy_quantity
                        position += buy_quantity

        if order_depth.buy_orders and sell_capacity > 0:
            bids = sorted(order_depth.buy_orders.items(), reverse=True)
            for bid_price, bid_volume in bids:
                if bid_price >= fair_value - skew:
                    sell_quantity = min(bid_volume, sell_capacity)
                    if sell_quantity > 0:
                        orders.append(Order(product, bid_price, -sell_quantity))
                        sell_capacity -= sell_quantity
                        position -= sell_quantity

        # POST: skewed quotes just inside large market makers — no hard inventory cap;
        # skew naturally widens the side that would increase inventory, tightens the other
        if buy_capacity > 0 and large_bid:
            our_bid = large_bid + self.PEPPER_QUOTE_IMPROVEMENT - skew
            if not order_depth.sell_orders or our_bid < min(order_depth.sell_orders.keys()):
                #bid_quantity = min(10, buy_capacity)
                bid_quantity = buy_capacity
                orders.append(Order(product, int(our_bid), bid_quantity))

        if sell_capacity > 0 and large_ask:
            our_ask = large_ask - self.PEPPER_QUOTE_IMPROVEMENT - skew
            if not order_depth.buy_orders or our_ask > max(order_depth.buy_orders.keys()):
                #ask_quantity = min(10, sell_capacity)
                ask_quantity = sell_capacity
                orders.append(Order(product, int(our_ask), -ask_quantity))

        return orders

    def run(self, state: TradingState):
        result = {}

        state_data = json.loads(state.traderData) if state.traderData else {}

        if 'ASH_COATED_OSMIUM' in state.order_depths:
            result['ASH_COATED_OSMIUM'] = self.trade_osmium(state, state_data)

        if 'INTARIAN_PEPPER_ROOT' in state.order_depths:
            result['INTARIAN_PEPPER_ROOT'] = self.trade_pepper_filtered(state)

        conversions = 0
        traderData = json.dumps(state_data)

        return result, conversions, traderData
