"""
Shop Workflow - Real e-commerce workflow using FakeStore API.

5 stages, 15 tasks, complex transitions.
"""
import requests
from concierge.core import workflow, stage, task, State

_carts = {}

def _cart(sid: str) -> dict:
    if sid not in _carts:
        _carts[sid] = {"items": [], "total": 0}
    return _carts[sid]


@stage(name="browse")
class BrowseStage:
    @task(description="Search products by keyword")
    def search(self, state: State, query: str) -> dict:
        r = requests.get("https://fakestoreapi.com/products")
        products = [p for p in r.json() if query.lower() in p["title"].lower()]
        return {"products": [{"id": p["id"], "title": p["title"], "price": p["price"]} for p in products[:5]], "count": len(products)}

    @task(description="Get products by category: electronics, jewelery, men's clothing, women's clothing")
    def by_category(self, state: State, category: str) -> dict:
        r = requests.get(f"https://fakestoreapi.com/products/category/{category}")
        return {"products": [{"id": p["id"], "title": p["title"], "price": p["price"]} for p in r.json()]}

    @task(description="List all categories")
    def categories(self, state: State) -> dict:
        return {"categories": requests.get("https://fakestoreapi.com/products/categories").json()}


@stage(name="product")
class ProductStage:
    @task(description="Get product details by ID")
    def details(self, state: State, product_id: int) -> dict:
        r = requests.get(f"https://fakestoreapi.com/products/{product_id}")
        p = r.json()
        return {"id": p["id"], "title": p["title"], "price": p["price"], "description": p["description"], "rating": p["rating"]}

    @task(description="Get similar products")
    def similar(self, state: State, product_id: int) -> dict:
        r = requests.get(f"https://fakestoreapi.com/products/{product_id}")
        cat = r.json()["category"]
        r2 = requests.get(f"https://fakestoreapi.com/products/category/{cat}")
        return {"similar": [{"id": p["id"], "title": p["title"], "price": p["price"]} for p in r2.json() if p["id"] != product_id][:3]}


@stage(name="cart")
class CartStage:
    @task(description="Add product to cart")
    def add(self, state: State, product_id: int, quantity: int = 1) -> dict:
        r = requests.get(f"https://fakestoreapi.com/products/{product_id}")
        p = r.json()
        cart = _cart(getattr(state, 'session_id', 'default'))
        cart["items"].append({"id": p["id"], "title": p["title"], "price": p["price"], "qty": quantity})
        cart["total"] = sum(i["price"] * i["qty"] for i in cart["items"])
        return {"added": p["title"], "cart_total": round(cart["total"], 2), "item_count": len(cart["items"])}

    @task(description="View cart")
    def view(self, state: State) -> dict:
        cart = _cart(getattr(state, 'session_id', 'default'))
        return {"items": cart["items"], "total": round(cart["total"], 2)}

    @task(description="Remove item from cart")
    def remove(self, state: State, product_id: int) -> dict:
        cart = _cart(getattr(state, 'session_id', 'default'))
        cart["items"] = [i for i in cart["items"] if i["id"] != product_id]
        cart["total"] = sum(i["price"] * i["qty"] for i in cart["items"])
        return {"removed": True, "cart_total": round(cart["total"], 2)}

    @task(description="Apply coupon code")
    def coupon(self, state: State, code: str) -> dict:
        cart = _cart(getattr(state, 'session_id', 'default'))
        discount = 0.1 if code.upper() == "SAVE10" else 0
        return {"code": code, "discount": f"{discount*100}%", "new_total": round(cart["total"] * (1 - discount), 2)}


@stage(name="shipping")
class ShippingStage:
    @task(description="Set shipping address")
    def set_address(self, state: State, name: str, street: str, city: str, zip_code: str) -> dict:
        return {"address": {"name": name, "street": street, "city": city, "zip": zip_code}, "saved": True}

    @task(description="Get shipping options")
    def options(self, state: State) -> dict:
        cart = _cart(getattr(state, 'session_id', 'default'))
        free = cart["total"] >= 50
        return {"options": [
            {"method": "standard", "days": "5-7", "cost": 0 if free else 5.99},
            {"method": "express", "days": "2-3", "cost": 12.99},
        ]}


@stage(name="checkout")
class CheckoutStage:
    @task(description="Get order summary")
    def summary(self, state: State) -> dict:
        cart = _cart(getattr(state, 'session_id', 'default'))
        tax = round(cart["total"] * 0.08, 2)
        return {"items": len(cart["items"]), "subtotal": cart["total"], "tax": tax, "total": round(cart["total"] + tax, 2)}

    @task(description="Complete purchase")
    def complete(self, state: State) -> dict:
        import random
        cart = _cart(getattr(state, 'session_id', 'default'))
        if not cart["items"]:
            return {"error": "Cart empty"}
        order_id = f"ORD-{random.randint(10000,99999)}"
        total = round(cart["total"] * 1.08, 2)
        cart["items"], cart["total"] = [], 0
        return {"order_id": order_id, "status": "confirmed", "total": total}


@workflow(name="shop", description="E-commerce shopping workflow")
class ShopWorkflow:
    browse = BrowseStage
    product = ProductStage
    cart = CartStage
    shipping = ShippingStage
    checkout = CheckoutStage

    transitions = {
        browse: [product, cart],
        product: [browse, cart],
        cart: [browse, product, shipping, checkout],
        shipping: [cart, checkout],
        checkout: [],
    }

