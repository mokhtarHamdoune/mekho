"""
Catalog helpers — load product data from products.json.
"""

import json
import pathlib
from typing import TypedDict

_CATALOG_PATH = pathlib.Path(__file__).parent / "products.json"


class Product(TypedDict):
    id: str
    name: str
    description: str
    price: float
    qty: int


def load_catalog() -> list[Product]:
    """Return the full product list from products.json."""
    with _CATALOG_PATH.open() as f:
        return json.load(f)


def catalog_as_prompt_text() -> str:
    """Format the catalog as a short, spoken-friendly paragraph for the system prompt."""
    products = load_catalog()
    lines = []
    for p in products:
        lines.append(
            f"{p['name']} (ID: {p['id']}): {p['description']}. "
            f"Price: ${p['price']:.2f}. In stock: {p['qty']} units."
        )
    return "Available products:\n" + "\n".join(lines)


def find_product(product_id: str) -> Product | None:
    """Look up a product by its ID (case-insensitive)."""
    for p in load_catalog():
        if p["id"].upper() == product_id.upper():
            return p
    return None
