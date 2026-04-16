"""
Order Matching Engine for IMC Prosperity Backtesting

Implements realistic order matching following IMC Prosperity platform rules:
- Order Depth Priority: Orders filled completely from order depths BEFORE market trades
- Price-Time-Priority: At same price level, oldest orders (FIFO) get priority
- Position Limit Enforcement: All orders canceled if any would exceed limits (strict)
- Match Modes: Support 'all', 'worse', 'none' for market trade matching
"""

from typing import Dict, List, NamedTuple, Tuple
from dataclasses import dataclass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from trader import Order, OrderDepth, Trade


@dataclass
class MatchResult:
    """Result of matching a single order"""
    filled: int                    # Quantity actually filled
    fill_price: float              # Weighted average fill price
    fills: List[Tuple]             # List of (price, qty, source) tuples
    rejected: bool                 # Was order rejected?
    rejection_reason: str          # Why rejected (if applicable)
    position_after: int            # Position after fill


class OrderMatcher:
    """
    Matches orders against order depths and market trades with proper priority.

    Priority Rules:
    1. Pre-validate position limits (strict: all-or-nothing)
    2. Match against order depths (price-time-priority: best price first, oldest first)
    3. Match remaining against market trades (if not already filled)
    """

    def __init__(self, match_mode: str = "all"):
        """
        Initialize matcher.

        match_mode: 'all' (match any trade price)
                   'worse' (only match trades worse than your quote)
                   'none' (never match market trades)
        """
        assert match_mode in ["all", "worse", "none"], f"Invalid match_mode: {match_mode}"
        self.match_mode = match_mode

    def match_order(self,
                    order: Order,
                    order_depth: OrderDepth,
                    market_trades: List[Trade],
                    current_position: int,
                    position_limit: int) -> MatchResult:
        """
        Match a single order against order depth and market trades.

        Process:
        1. Pre-validate: If position + order would exceed limit, reject ALL
        2. Fill from order depths (price-time-priority)
        3. Fill remainder from market trades (if match_mode allows)

        Args:
            order: Order to match (quantity > 0 = buy, < 0 = sell)
            order_depth: Current order book
            market_trades: Recent market trades at this timestamp
            current_position: Current position before this order
            position_limit: Position limit (±limit)

        Returns:
            MatchResult with filled qty, avg price, fill details, rejection status
        """
        symbol = order.symbol
        is_buy = order.quantity > 0
        abs_qty = abs(order.quantity)

        # Pre-validation: Position limit enforcement (STRICT - all-or-nothing)
        position_after_fill = current_position + order.quantity

        if position_after_fill > position_limit or position_after_fill < -position_limit:
            return MatchResult(
                filled=0,
                fill_price=order.price,
                fills=[],
                rejected=True,
                rejection_reason=f"Position limit exceeded: {current_position} + {order.quantity} = {position_after_fill} (limit ±{position_limit})",
                position_after=current_position
            )

        # Matching process
        fills: List[Tuple[int, int, str]] = []  # (price, qty, source)
        remaining_qty = abs_qty
        total_cost = 0

        # Step 1: Match against order depths (price-time-priority)
        filled_from_depth = self._match_order_depth(
            is_buy=is_buy,
            quantity=remaining_qty,
            order_price=order.price,
            order_depth=order_depth,
            fills=fills,
            total_cost=[total_cost]
        )

        remaining_qty -= filled_from_depth
        total_cost = fills[0][0] * fills[0][1] if fills else 0

        # Step 2: Match remaining against market trades (if mode allows)
        if remaining_qty > 0 and self.match_mode != "none":
            filled_from_trades = self._match_market_trades(
                is_buy=is_buy,
                quantity=remaining_qty,
                order_price=order.price,
                market_trades=market_trades,
                fills=fills,
                total_cost=[total_cost]
            )
            remaining_qty -= filled_from_trades
            total_cost = fills[-1][0] * fills[-1][1] if fills else 0

        # Calculate results
        total_filled = abs_qty - remaining_qty

        if total_filled > 0:
            avg_price = sum(p * q for p, q, _ in fills) / total_filled
        else:
            avg_price = order.price

        return MatchResult(
            filled=total_filled,
            fill_price=avg_price,
            fills=fills,
            rejected=False,
            rejection_reason="",
            position_after=current_position + (total_filled if is_buy else -total_filled)
        )

    def _match_order_depth(self,
                          is_buy: bool,
                          quantity: int,
                          order_price: int,
                          order_depth: OrderDepth,
                          fills: List[Tuple],
                          total_cost: List) -> int:
        """
        Match order against order depth using price-time-priority.

        For buy orders: Match against sell_orders (lowest prices first)
        For sell orders: Match against buy_orders (highest prices first)
        """
        filled = 0

        if is_buy:
            # Buy order: Match against sell_orders (ascending price)
            sell_prices = sorted(order_depth.sell_orders.keys())
            for price in sell_prices:
                if price > order_price:
                    break  # Stop if price exceeds our limit

                available = order_depth.sell_orders[price]
                fill_qty = min(quantity - filled, available)

                if fill_qty > 0:
                    fills.append((price, fill_qty, "order_depth"))
                    filled += fill_qty
                    total_cost[0] += price * fill_qty

                    if filled >= quantity:
                        break
        else:
            # Sell order: Match against buy_orders (descending price)
            buy_prices = sorted(order_depth.buy_orders.keys(), reverse=True)
            for price in buy_prices:
                if price < order_price:
                    break  # Stop if price falls below our limit

                available = order_depth.buy_orders[price]
                fill_qty = min(quantity - filled, available)

                if fill_qty > 0:
                    fills.append((price, fill_qty, "order_depth"))
                    filled += fill_qty
                    total_cost[0] += price * fill_qty

                    if filled >= quantity:
                        break

        return filled

    def _match_market_trades(self,
                            is_buy: bool,
                            quantity: int,
                            order_price: int,
                            market_trades: List[Trade],
                            fills: List[Tuple],
                            total_cost: List) -> int:
        """
        Match order against market trades using match_mode filter.

        Modes:
        - 'all': Match trades at any price
        - 'worse': Only match trades worse than order_price
        - 'none': Never match (handled by caller)

        Note: Fills are at YOUR order price, not the trade price.
        This matches IMC Prosperity behavior: if you bid €9 and trade happens at €10,
        you get filled at €9 (your quote), not €10.
        """
        filled = 0

        for trade in market_trades:
            if filled >= quantity:
                break

            # Apply match_mode filter
            if self.match_mode == "worse":
                if is_buy and trade.price < order_price:
                    continue  # Ignore trades better than our bid
                elif not is_buy and trade.price > order_price:
                    continue  # Ignore trades better than our ask
            # else: match_mode == 'all', accept any trade

            # Fill up to order_price (not trade price)
            fill_qty = min(quantity - filled, trade.quantity)

            if fill_qty > 0:
                fills.append((order_price, fill_qty, "market_trade"))
                filled += fill_qty
                total_cost[0] += order_price * fill_qty

        return filled

    def calculate_mid_price(self, order_depth: OrderDepth) -> float:
        """Calculate mid price from order depth (bid-ask midpoint)"""
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        elif best_bid:
            return best_bid
        elif best_ask:
            return best_ask
        else:
            return None


class OrderMatcherWithOrderBook:
    """
    Extended matcher that maintains order book state and tracks order priority.
    Useful for simulating multiple sequential orders at same timestamp.
    """

    def __init__(self, match_mode: str = "all"):
        self.matcher = OrderMatcher(match_mode)
        self.order_timestamps: Dict[int, int] = {}  # price -> earliest timestamp at this price
        self.counter = 0

    def add_order_to_depth(self, price: int, quantity: int, is_buy: bool) -> None:
        """Add order to depth and track timestamp for price-time-priority"""
        if is_buy:
            if price not in self.order_timestamps:
                self.order_timestamps[price] = self.counter
        else:
            if price not in self.order_timestamps:
                self.order_timestamps[price] = self.counter

        self.counter += 1

    def reset_timestamps(self) -> None:
        """Reset timestamps for new timestamp group"""
        self.order_timestamps.clear()
        self.counter = 0
