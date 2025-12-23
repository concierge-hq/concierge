"""
Test state transfer between stages during transitions.
This test file was created to catch the state transfer bug.
"""
import asyncio
import pytest
from pydantic import BaseModel, Field
from concierge.core import State, task, stage, workflow, construct, StateTransfer
from concierge.engine import Orchestrator
from concierge.core.actions import MethodCallAction, StageTransitionAction
from concierge.core.state_manager import get_state_manager


@construct()
class Product(BaseModel):
    """Product construct"""
    symbol: str = Field(description="Product symbol")
    quantity: int = Field(ge=1, description="Quantity")


@stage(name="cart")
class CartStage:
    """Shopping cart stage"""
    
    @task()
    def add_item(self, state: State, symbol: str, quantity: int) -> dict:
        state.set("symbol", symbol)
        state.set("quantity", quantity)
        return {"result": f"Added {quantity} of {symbol}"}


@stage(name="checkout", prerequisites=[Product])
class CheckoutStage:
    """Checkout stage - requires product info"""
    
    @task()
    def place_order(self, state: State) -> dict:
        symbol = state.get("symbol")
        quantity = state.get("quantity")
        return {"order_id": "ORD123", "status": f"Ordered {quantity} of {symbol}"}


@stage(name="review")
class ReviewStage:
    """Review stage - no prerequisites"""
    
    @task()
    def view_order(self, state: State) -> dict:
        symbol = state.get("symbol", "Unknown")
        quantity = state.get("quantity", 0)
        return {"result": f"Order: {quantity} of {symbol}"}


@workflow(name="shopping")
class ShoppingWorkflow:
    cart = CartStage
    checkout = CheckoutStage
    review = ReviewStage
    
    transitions = {
        CartStage: [CheckoutStage, ReviewStage],
        CheckoutStage: [ReviewStage],
        ReviewStage: [CartStage]
    }
    
    state_management = [
        (CartStage, CheckoutStage, ["symbol", "quantity"]),  # Copy specific fields
        (CartStage, ReviewStage, StateTransfer.ALL),          # Copy all fields
        (CheckoutStage, ReviewStage, StateTransfer.NONE),     # Copy nothing
    ]


def test_state_transfer_specific_fields():
    """Test that specific fields are transferred from cart to checkout"""
    async def run():
        wf = ShoppingWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-transfer-1")
        
        # Add item to cart
        action = MethodCallAction(task_name="add_item", args={"symbol": "WIDGET", "quantity": 5})
        result = await orch.execute_method_call(action)
        assert result.result["result"] == "Added 5 of WIDGET"
        
        # Verify cart stage has the data
        state_mgr = get_state_manager()
        cart_state = await state_mgr.get_stage_state("test-transfer-1", "cart")
        assert cart_state["symbol"] == "WIDGET"
        assert cart_state["quantity"] == 5
        
        # Transition to checkout (should transfer symbol and quantity)
        transition_action = StageTransitionAction(target_stage="checkout")
        transition_result = await orch.execute_stage_transition(transition_action)
        assert transition_result.to_stage == "checkout"
        
        # Verify checkout stage received the transferred data
        checkout_state = await state_mgr.get_stage_state("test-transfer-1", "checkout")
        assert checkout_state["symbol"] == "WIDGET", "symbol should be transferred to checkout"
        assert checkout_state["quantity"] == 5, "quantity should be transferred to checkout"
        
        # Place order (should work because state was transferred)
        order_action = MethodCallAction(task_name="place_order", args={})
        order_result = await orch.execute_method_call(order_action)
        assert "Ordered 5 of WIDGET" in order_result.result["status"]
    
    asyncio.run(run())


def test_state_transfer_all():
    """Test that ALL fields are transferred from cart to review"""
    async def run():
        wf = ShoppingWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-transfer-2")
        
        # Add item to cart
        action = MethodCallAction(task_name="add_item", args={"symbol": "GADGET", "quantity": 10})
        await orch.execute_method_call(action)
        
        # Verify cart state
        state_mgr = get_state_manager()
        cart_state = await state_mgr.get_stage_state("test-transfer-2", "cart")
        assert cart_state["symbol"] == "GADGET"
        assert cart_state["quantity"] == 10
        
        # Transition to review (should transfer ALL fields)
        transition_action = StageTransitionAction(target_stage="review")
        await orch.execute_stage_transition(transition_action)
        
        # Verify review stage received ALL data
        review_state = await state_mgr.get_stage_state("test-transfer-2", "review")
        assert review_state["symbol"] == "GADGET", "ALL fields should be transferred to review"
        assert review_state["quantity"] == 10, "ALL fields should be transferred to review"
        
        # View order (should work with transferred data)
        view_action = MethodCallAction(task_name="view_order", args={})
        view_result = await orch.execute_method_call(view_action)
        assert "Order: 10 of GADGET" in view_result.result["result"]
    
    asyncio.run(run())


def test_state_transfer_none():
    """Test that NO fields are transferred when StateTransfer.NONE is specified"""
    async def run():
        wf = ShoppingWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-transfer-3")
        
        # Add item and go to checkout
        action = MethodCallAction(task_name="add_item", args={"symbol": "THING", "quantity": 3})
        await orch.execute_method_call(action)
        
        transition = StageTransitionAction(target_stage="checkout")
        await orch.execute_stage_transition(transition)
        
        # Place order in checkout (this adds order_id to checkout state)
        order_action = MethodCallAction(task_name="place_order", args={})
        await orch.execute_method_call(order_action)
        
        state_mgr = get_state_manager()
        checkout_state = await state_mgr.get_stage_state("test-transfer-3", "checkout")
        assert "symbol" in checkout_state
        
        # Transition to review with NONE config (should not transfer anything)
        transition2 = StageTransitionAction(target_stage="review")
        await orch.execute_stage_transition(transition2)
        
        # Verify review stage has NO transferred data
        review_state = await state_mgr.get_stage_state("test-transfer-3", "review")
        assert review_state == {}, "No fields should be transferred with StateTransfer.NONE"
    
    asyncio.run(run())


def test_state_transfer_missing_prerequisites_blocks_transition():
    """Test that transitions are blocked if prerequisites aren't satisfied"""
    async def run():
        wf = ShoppingWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-prereq-1")
        
        # Try to transition to checkout without adding item first
        # (checkout requires Product which has symbol and quantity)
        transition_action = StageTransitionAction(target_stage="checkout")
        result = await orch.execute_stage_transition(transition_action)
        
        # Should fail because prerequisites aren't met
        from concierge.core.results import StateInputRequiredResult
        assert isinstance(result, StateInputRequiredResult), "Should require state input"
        assert "symbol" in result.required_fields
        assert "quantity" in result.required_fields
    
    asyncio.run(run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

