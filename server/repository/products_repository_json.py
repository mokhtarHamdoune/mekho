
import json
import pathlib

from ..interfaces.products_repository import Product, ProductRepository as IProductRepository

_CATALOG_PATH = pathlib.Path(__file__).parent / "products.json"

class JsonProductsRepository(IProductRepository):
    
    def __init__(self):
        self.products = self._load_products()

    def get_product(self, product_id: str) -> Product:
        """Return the product details for the given product ID."""
        return self.products.get(product_id, {})

    def search_products(self, query: str) -> list[Product]:
        """Return a list of products matching the search query."""
        query_lower = query.lower()
        return [
            product
            for product in self.products.values()
            if query_lower in product["name"].lower()
        ]

    def _load_products(self) -> dict[str, Product]:
        """Load products.json and index them by product ID."""
        with _CATALOG_PATH.open() as f:
            products_list: list[Product] = json.load(f)
        return {p["id"]: p for p in products_list}

