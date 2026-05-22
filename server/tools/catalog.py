from typing import Any

from ..interfaces import BaseTool, ToolGroup
from ..services import CatalogService
from ..repository import JsonProductsRepository
from .registry import registry
import logging

logger = logging.getLogger(__name__)


class SearchProductTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_product"

    @property
    def description(self) -> str:
        return (
            "Search for products in the catalog. Call this whenever the customer "
            "says something that indicates they are looking for a product, e.g. "
            "'I'm looking for headphones' or 'Do you have any laptops?'. Always "
            "returns a list of matching product names and prices."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The customer's search query, e.g. 'headphones' or 'laptops'",
                },
            },
            "required": ["query"],
        }

    def run(self, state: Any, **kwargs: Any) -> dict:
        query: str = kwargs["query"]
        results = CatalogService(JsonProductsRepository()).search_products(query)
        logger.info("Search query: %s, Results: %s", query, results)
        return {"results": results}


class GetProductDetailTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_product_detail"

    @property
    def description(self) -> str:
        return (
            "Retrieve full details for a specific product by its ID. Call this "
            "when the customer wants to add a product to the cart or asks for more "
            "information about a specific product (price, description, availability). "
            "Use the product ID returned by search_product."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The unique product ID, e.g. 'P001'",
                },
            },
            "required": ["product_id"],
        }

    def run(self, state: Any, **kwargs: Any) -> dict:
        product_id: str = kwargs["product_id"]
        product = CatalogService(JsonProductsRepository()).get_product_details(product_id)
        if not product:
            logger.warning("Product not found: %s", product_id)
            return {"error": f"Product '{product_id}' not found."}
        logger.info("Product detail fetched: %s", product_id)
        return {"product": product}


class CatalogGroup(ToolGroup):

    @property
    def name(self) -> str:
        return "catalog"

    @property
    def tools(self) -> list[BaseTool]:
        return [SearchProductTool(), GetProductDetailTool()]

    def new_session_state(self) -> None:
        return None


registry.register_group(CatalogGroup())