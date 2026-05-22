import logging
from decimal import Decimal
from typing import Any

from .interfaces import BaseTool, ToolGroup
from .registry import registry

logger = logging.getLogger(__name__)


# ── Per-session state ────────────────────────────────────────────────────────

class CartState:
    """Owns the shopping cart for one user session."""

    def __init__(self) -> None:
        self.items: dict[str, Decimal] = {}

    def add(self, item: str, quantity: Decimal) -> None:
        self.items[item] = self.items.get(item, Decimal(0)) + quantity

    def remove(self, item: str, quantity: Decimal | None = None) -> bool:
        """Subtract quantity (or remove entirely if quantity is None).
        Returns False if the item was not in the cart."""
        if item not in self.items:
            return False
        if quantity is None or quantity >= self.items[item]:
            del self.items[item]
        else:
            self.items[item] -= quantity
        return True

    def snapshot(self) -> dict[str, str]:
        """Return a JSON-serializable copy of the cart."""
        return {k: str(v) for k, v in self.items.items()}


# ── Tools ────────────────────────────────────────────────────────────────────

class AddToCartTool(BaseTool):

    @property
    def name(self) -> str:
        return "add_to_cart"

    @property
    def description(self) -> str:
        return (
            "Add a product to the customer's shopping cart. "
            "Call this whenever the customer says they want to buy or add an item. "
            "Always returns the full updated cart so you know its exact contents."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "description": "The exact product name to add.",
                },
                "quantity": {
                    "type": "number",
                    "description": "Number of units to add.",
                },
            },
            "required": ["item", "quantity"],
        }

    def run(self, state: CartState, **kwargs: Any) -> dict:
        item: str = kwargs["item"]
        quantity = Decimal(str(kwargs["quantity"]))
        state.add(item, quantity)
        logger.info("Cart add: %s × %s | cart=%s", quantity, item, state.snapshot())
        return {
            "status": "added",
            "item": item,
            "quantity": str(quantity),
            "cart": state.snapshot(),
        }

class RemoveFromCartTool(BaseTool):

    @property
    def name(self) -> str:
        return "remove_from_cart"

    @property
    def description(self) -> str:
        return (
            "Remove a product (or reduce its quantity) from the customer's shopping cart. "
            "Call this whenever the customer says they want to remove or delete an item. "
            "Omit 'quantity' or set it to None to remove all units of that product at once. "
            "Always returns the full updated cart so you know its exact contents."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "description": "The exact product name to remove.",
                },
                "quantity": {
                    "type": "number",
                    "description": "Units to remove. Omit to remove all units of this product.",
                },
            },
            "required": ["item"],
        }

    def run(self, state: CartState, **kwargs: Any) -> dict:
        item: str = kwargs["item"]
        quantity = Decimal(str(kwargs["quantity"])) if "quantity" in kwargs else None
        found = state.remove(item, quantity)
        logger.info("Cart remove: %s × %s | cart=%s", quantity, item, state.snapshot())
        if not found:
            return {"status": "not_found", "item": item, "cart": state.snapshot()}
        return {
            "status": "removed",
            "item": item,
            "quantity": str(quantity) if quantity is not None else "all",
            "cart": state.snapshot(),
        }


# ── Group ────────────────────────────────────────────────────────────────────

class CartGroup(ToolGroup):

    @property
    def name(self) -> str:
        return "cart"

    @property
    def tools(self) -> list[BaseTool]:
        return [AddToCartTool(), RemoveFromCartTool()]

    def new_session_state(self) -> CartState:
        return CartState()


registry.register_group(CartGroup())
