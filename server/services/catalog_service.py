from ..interfaces import ProductRepository
class CatalogService:

    def __init__(self, products_repository: ProductRepository):
        self.products_repository = products_repository

    def get_product_details(self, product_id: str):
        """Return the product details for the given product ID."""
        return self.products_repository.get_product(product_id)
    

    def search_products(self, query: str):
        """Return a list of products matching the search query."""
        return self.products_repository.search_products(query)