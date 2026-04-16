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
    
    def run(self, state: TradingState):
        import jsonpickle
        result = {}
        symbol = "ASH_COATED_OSMIUM"

        # Phase A
        # 1. Initialize memory safely
        try:
            if state.traderData:
                memory = jsonpickle.decode(state.traderData)
            else:
                memory = {"history": []}
        except Exception:
            memory = {"history": []}

        # 2. Update History with Market Trades
        # market_trades contains the actual transactions from other bots
        m_trades = state.market_trades.get(symbol, [])
        for t in m_trades:
            memory["history"].append([t.price, t.quantity])

        # Keep the window to the last 20 trade events to keep calculations fresh
        # and stay under the character limit for traderData
        memory["history"] = memory["history"][-20:]

        # 3. Calculate VWAP (The Anchor)
        if len(memory["history"]) > 0:
            # Extract prices and quantities for the weighted average
            prices = np.array([x[0] for x in memory["history"]])
            volumes = np.array([x[1] for x in memory["history"]])
            
            # VWAP = Sum(Price * Volume) / Sum(Volume)
            vwap = np.average(prices, weights=volumes)
        else:
            # Default value for Osmium if no trades have happened yet
            vwap = 10000.0

        # 4. Safety Check: MAX_DISTANCE
        # We define a safety buffer to avoid buying at a peak or selling at a floor
        max_distance = 20 
        too_high = False
        too_low = False

        depth = state.order_depths.get(symbol)
        if depth and depth.buy_orders:
            best_bid = max(depth.buy_orders.keys())
            if best_bid > vwap + max_distance:
                too_high = True # Market is trending up too fast, stay cautious
                
        if depth and depth.sell_orders:
            best_ask = min(depth.sell_orders.keys())
            if best_ask < vwap - max_distance:
                too_low = True # Market is crashing, don't catch the falling knife

        # Phase B - Pennying
        # We look at the top of the order book for ASH_COATED_OSMIUM
        depth = state.order_depths.get(symbol)

        # Default prices in case the book is empty (using our VWAP anchor)
        best_bid = max(depth.buy_orders.keys()) if (depth and depth.buy_orders) else int(vwap - 1)
        best_ask = min(depth.sell_orders.keys()) if (depth and depth.sell_orders) else int(vwap + 1)

        # The "Penny" logic: 
        # We want to be 1 unit better than the current best bots.
        # This puts our order at the very front of the queue.
        penny_buy_price = best_bid + 1
        penny_sell_price = best_ask - 1

        # Phase 3 - Leaning
        # We retrieve our current position (e.g., +15 or -5)
        current_pos = state.position.get(symbol, 0)

        # Logic: If we are long (+), we want to be less likely to buy more 
        # and more likely to sell. We achieve this by lowering our prices.
        # If we are short (-), the negative value will raise our prices.

        inventory_bias = current_pos * 0.9  # The '0.75' determines how aggressive the lean is

        # We apply the bias to our penny prices
        # Use int() because the exchange does not accept float prices
        final_buy_price = int(round(penny_buy_price - inventory_bias))
        final_sell_price = int(round(penny_sell_price - inventory_bias))

        # Phase 4 - Placing Orders
        orders: List[Order] = []
        
        # 1. Calculate how much we can actually trade
        # Position limit for Osmium is 20
        room_to_buy = 20 - current_pos
        room_to_sell = -20 - current_pos # This will be a negative number (e.g., -20 - 5 = -25)

        # 2. Execute Buy Side
        if room_to_buy > 0 and not too_high:
            # Final Guardrail: Don't buy if our price is higher than the best available seller
            # (Otherwise, we are 'taking' rather than 'making')
            actual_buy_price = min(final_buy_price, best_ask - 1)
            
            orders.append(Order(symbol, actual_buy_price, room_to_buy))

        # 3. Execute Sell Side
        if room_to_sell < 0 and not too_low:
            # Final Guardrail: Don't sell if our price is lower than the best available buyer
            actual_sell_price = max(final_sell_price, best_bid + 1)
            
            orders.append(Order(symbol, actual_sell_price, room_to_sell))

        # 4. Finalize and Store State
        result[symbol] = orders
        
        # Re-encode our memory with jsonpickle for the next timestamp
        traderData = jsonpickle.encode(memory)
        
        return result, 0, traderData