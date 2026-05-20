import logging
from decimal import Decimal
from typing import Any

from .base_tool import BaseTool
from .registry import registry

logger = logging.getLogger(__name__)


class CartTool(BaseTool):

    @property
    def name(self) -> str:
        return "add_to_cart"

    @property
    def description(self) -> str:
        return "Add an item to the shopping cart."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "description": "The name of the product to add.",
                },
                "quantity": {
                    "type": "number",
                    "description": "How many units to add.",
                },
            },
            "required": ["item", "quantity"],
        }

    def run(self, **kwargs: Any) -> Any:
        item: str = kwargs["item"]
        quantity: Decimal = Decimal(str(kwargs["quantity"]))
        logger.info(f"LLM Call Adding to cart: {quantity} of {item}")
        return {"item": item, "quantity": str(quantity), "status": "added"}


registry.register(CartTool())
