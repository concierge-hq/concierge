from concierge.core import workflow, stage, task, State


@stage(name="restaurants")
class RestaurantsStage:
    @task(description="Search restaurants by cuisine")
    def search_restaurants(self, state: State, cuisine: str, location: str) -> dict:
        return {"restaurants": []}
    
    @task(description="Filter by rating or delivery time")
    def filter_restaurants(self, state: State, min_rating: float) -> dict:
        return {"filtered": []}


@stage(name="menu")
class MenuStage:
    @task(description="View restaurant menu")
    def view_menu(self, state: State, restaurant_id: str) -> dict:
        return {"menu_items": []}
    
    @task(description="Add item to order")
    def add_item(self, state: State, item_id: str, quantity: int) -> dict:
        return {"order_size": 1}
    
    @task(description="Customize item")
    def customize_item(self, state: State, item_id: str, modifications: list) -> dict:
        return {"customized": True}


@stage(name="cart")
class CartStage:
    @task(description="Review order and total")
    def review_order(self, state: State) -> dict:
        return {"total": 0, "items": []}
    
    @task(description="Apply promo code")
    def apply_promo(self, state: State, code: str) -> dict:
        return {"discount": 0}


@stage(name="checkout", prerequisites=["cart.items", "delivery_address"])
class CheckoutStage:
    @task(description="Set delivery instructions")
    def set_instructions(self, state: State, instructions: str) -> dict:
        return {"saved": True}
    
    @task(description="Place order")
    def place_order(self, state: State) -> dict:
        return {"order_id": "DD123", "eta": 30}


@workflow(name="food_delivery")
class FoodDeliveryWorkflow:
    restaurants = RestaurantsStage
    menu = MenuStage
    cart = CartStage
    checkout = CheckoutStage
    
    transitions = {
        restaurants: [menu],
        menu: [cart, restaurants],
        cart: [checkout, menu],
        checkout: []
    }

