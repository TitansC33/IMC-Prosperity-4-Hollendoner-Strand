from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Tuple, Optional
import json

class Trader:
    
    def __init__(self):
        self.POSITION_LIMITS = {
            'ASH_COATED_OSMIUM': 20,
            'INTARIAN_PEPPER_ROOT': 20
        }
        
        # Osmium - unchanged, working perfectly
        self.OSMIUM_FAIR_VALUE = 10000
        self.OSMIUM_SPREAD = 8
        
        # Pepper Root - NEW strategy based on Kelp insight
        self.PEPPER_LARGE_ORDER_THRESHOLD = 18  # 75th percentile
        self.PEPPER_QUOTE_IMPROVEMENT = 1  # Overbid/undercut by 1
        self.PEPPER_MAX_INVENTORY = 15  # Neutralize above this
        
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
    
    def trade_osmium(self, state: TradingState) -> List[Order]:
        """Osmium strategy - unchanged, working great"""
        product = 'ASH_COATED_OSMIUM'
        orders = []
        
        if product not in state.order_depths:
            return orders
        
        order_depth = state.order_depths[product]
        position = state.position.get(product, 0)
        position_limit = self.POSITION_LIMITS[product]
        
        buy_capacity = position_limit - position
        sell_capacity = position_limit + position
        
        fair_value = self.OSMIUM_FAIR_VALUE
        
        # TAKE: Aggressive taking when profitable
        if order_depth.sell_orders and buy_capacity > 0:
            asks = sorted(order_depth.sell_orders.items())
            for ask_price, ask_volume in asks:
                ask_volume = abs(ask_volume)
                if ask_price < fair_value - 2:
                    buy_quantity = min(ask_volume, buy_capacity)
                    if buy_quantity > 0:
                        orders.append(Order(product, ask_price, buy_quantity))
                        buy_capacity -= buy_quantity
                        position += buy_quantity
        
        if order_depth.buy_orders and sell_capacity > 0:
            bids = sorted(order_depth.buy_orders.items(), reverse=True)
            for bid_price, bid_volume in bids:
                if bid_price > fair_value + 2:
                    sell_quantity = min(bid_volume, sell_capacity)
                    if sell_quantity > 0:
                        orders.append(Order(product, bid_price, -sell_quantity))
                        sell_capacity -= sell_quantity
                        position -= sell_quantity
        
        # POST: Passive market making
        if buy_capacity > 0:
            our_bid_price = fair_value - self.OSMIUM_SPREAD
            if not order_depth.sell_orders or our_bid_price < min(order_depth.sell_orders.keys()):
                bid_quantity = min(10, buy_capacity)
                orders.append(Order(product, int(our_bid_price), bid_quantity))
        
        if sell_capacity > 0:
            our_ask_price = fair_value + self.OSMIUM_SPREAD
            if not order_depth.buy_orders or our_ask_price > max(order_depth.buy_orders.keys()):
                ask_quantity = min(10, sell_capacity)
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
        
        # STEP 1: TAKE - Any order that crosses fair value
        
        if order_depth.sell_orders and buy_capacity > 0:
            asks = sorted(order_depth.sell_orders.items())
            for ask_price, ask_volume in asks:
                ask_volume = abs(ask_volume)
                
                # Take if below or at fair value
                if ask_price <= fair_value:
                    buy_quantity = min(ask_volume, buy_capacity)
                    
                    if buy_quantity > 0:
                        orders.append(Order(product, ask_price, buy_quantity))
                        buy_capacity -= buy_quantity
                        position += buy_quantity
        
        if order_depth.buy_orders and sell_capacity > 0:
            bids = sorted(order_depth.buy_orders.items(), reverse=True)
            for bid_price, bid_volume in bids:
                
                # Take if above or at fair value
                if bid_price >= fair_value:
                    sell_quantity = min(bid_volume, sell_capacity)
                    
                    if sell_quantity > 0:
                        orders.append(Order(product, bid_price, -sell_quantity))
                        sell_capacity -= sell_quantity
                        position -= sell_quantity
        
        # STEP 2: INVENTORY NEUTRALIZATION
        # If inventory too large, neutralize at current price
        
        if abs(position) > self.PEPPER_MAX_INVENTORY:
            if position > 0 and order_depth.buy_orders:
                # Too long, sell at best bid
                best_bid = max(order_depth.buy_orders.keys())
                excess = position - self.PEPPER_MAX_INVENTORY
                neutralize_qty = min(excess, order_depth.buy_orders[best_bid], sell_capacity)
                
                if neutralize_qty > 0:
                    orders.append(Order(product, best_bid, -neutralize_qty))
                    position -= neutralize_qty
                    sell_capacity -= neutralize_qty
            
            elif position < 0 and order_depth.sell_orders:
                # Too short, buy at best ask
                best_ask = min(order_depth.sell_orders.keys())
                excess = abs(position) - self.PEPPER_MAX_INVENTORY
                neutralize_qty = min(excess, abs(order_depth.sell_orders[best_ask]), buy_capacity)
                
                if neutralize_qty > 0:
                    orders.append(Order(product, best_ask, neutralize_qty))
                    position += neutralize_qty
                    buy_capacity -= neutralize_qty
        
        # STEP 3: POST - Quote just inside the large market makers
        # Only if inventory is reasonable
        
        if abs(position) < self.PEPPER_MAX_INVENTORY:
            
            # Overbid the large market maker by 1
            if buy_capacity > 0 and large_bid:
                our_bid = large_bid + self.PEPPER_QUOTE_IMPROVEMENT
                
                # Don't cross the book
                if not order_depth.sell_orders or our_bid < min(order_depth.sell_orders.keys()):
                    bid_quantity = min(10, buy_capacity)
                    orders.append(Order(product, int(our_bid), bid_quantity))
            
            # Undercut the large market maker by 1
            if sell_capacity > 0 and large_ask:
                our_ask = large_ask - self.PEPPER_QUOTE_IMPROVEMENT
                
                # Don't cross the book
                if not order_depth.buy_orders or our_ask > max(order_depth.buy_orders.keys()):
                    ask_quantity = min(10, sell_capacity)
                    orders.append(Order(product, int(our_ask), -ask_quantity))
        
        return orders
    
    def run(self, state: TradingState):
        """Main trading loop"""
        result = {}
        
        # Trade Osmium (the money maker)
        if 'ASH_COATED_OSMIUM' in state.order_depths:
            result['ASH_COATED_OSMIUM'] = self.trade_osmium(state)
        
        # Trade Pepper Root (filtered strategy)
        if 'INTARIAN_PEPPER_ROOT' in state.order_depths:
            result['INTARIAN_PEPPER_ROOT'] = self.trade_pepper_filtered(state)
        
        conversions = 0
        traderData = ""
        
        return result, conversions, traderData
