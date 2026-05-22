from abc import ABC, abstractmethod
from typing import TypedDict

class Product(TypedDict):
    id: str
    name: str
    description: str
    price: float
    qty: int

class ProductRepository(ABC):

    @abstractmethod
    def get_product(self, product_id: str) -> Product:
        """Return the product details for the given product ID."""
        pass

    @abstractmethod
    def search_products(self, query: str) -> list[Product]:
        """Return a list of products matching the search query."""
        pass