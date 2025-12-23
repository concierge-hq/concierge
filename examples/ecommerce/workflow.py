from concierge.core import workflow, stage, task, State


@stage(name="discovery")
class DiscoveryStage:
    @task(description="Search for products by keyword")
    def search_products(self, state: State, query: str) -> dict:
        return {"results": []}
    
    @task(description="Filter by price range")
    def filter_by_price(self, state: State, min_price: float, max_price: float) -> dict:
        return {"filtered_count": 0}


@stage(name="product")
class ProductStage:
    @task(description="View product details")
    def view_details(self, state: State, product_id: str) -> dict:
        return {"product": {}}
    
    @task(description="Read customer reviews")
    def read_reviews(self, state: State, product_id: str) -> dict:
        return {"reviews": []}


@stage(name="cart")
class CartStage:
    @task(description="Add item to cart")
    def add_to_cart(self, state: State, product_id: str, quantity: int) -> dict:
        return {"cart_size": 1}
    
    @task(description="Update quantity")
    def update_quantity(self, state: State, product_id: str, quantity: int) -> dict:
        return {"updated": True}
    
    @task(description="Remove item from cart")
    def remove_item(self, state: State, product_id: str) -> dict:
        return {"removed": True}


@stage(name="checkout", prerequisites=["cart.items"])
class CheckoutStage:
    @task(description="Apply coupon code")
    def apply_coupon(self, state: State, code: str) -> dict:
        return {"discount": 0}
    
    @task(description="Complete purchase")
    def complete_purchase(self, state: State) -> dict:
        return {"order_id": "ORD123"}


@workflow(name="ecommerce_shopping")
class EcommerceWorkflow:
    discovery = DiscoveryStage
    product = ProductStage
    cart = CartStage
    checkout = CheckoutStage
    
    transitions = {
        discovery: [product, cart],
        product: [cart, discovery],
        cart: [checkout, discovery],
        checkout: []
    }

