"""Mini Store Checkout workflow (UAIP demo)."""
from uaip.core import workflow, stage, task, State


@stage(name="browse")
class Browse:
    @task()
    def search_items(self, state: State, query: str = "widget") -> dict:
        return {
            "items": [
                {"id": "sku-1", "name": "Widget", "price": 19.99},
                {"id": "sku-2", "name": "Gadget", "price": 24.99},
            ]
        }

    @task()
    def select_item(self, state: State, item_id: str) -> dict:
        state.set("item_id", item_id)
        return {"selected": item_id}


@stage(name="checkout")
class Checkout:
    @task()
    def set_quantity(self, state: State, quantity: int = 1) -> dict:
        state.set("quantity", quantity)
        return {"quantity": quantity}

    @task()
    def set_shipping(self, state: State, address: str) -> dict:
        state.set("shipping", address)
        return {"shipping": address}


@stage(name="payment")
class Payment:
    @task()
    def pay(self, state: State, method: str = "card") -> dict:
        item_id = state.get("item_id")
        quantity = state.get("quantity", 1)
        shipping = state.get("shipping", "not provided")
        return {
            "status": "paid",
            "item_id": item_id,
            "quantity": quantity,
            "shipping": shipping,
            "payment_method": method,
            "order_id": "order-123",
        }


@workflow(name="mini_store", description="Minimal store checkout flow")
class MiniStoreWorkflow:
    browse = Browse
    checkout = Checkout
    payment = Payment

    transitions = {
        browse: [checkout],
        checkout: [payment],
        payment: [browse],
    }


if __name__ == "__main__":
    MiniStoreWorkflow.run(port=8000)
