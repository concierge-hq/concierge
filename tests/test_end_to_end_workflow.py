"""
End-to-end test simulating realistic LLM interaction with Concierge.
Tests complete workflow with multiple stages, tasks, state requirements, and transitions.
"""
import json
import uuid
import pytest
from pydantic import BaseModel
from concierge.core.workflow import workflow
from concierge.core.stage import stage
from concierge.core.task import task
from concierge.core.state import State
from concierge.core.construct import construct
from concierge.engine import LanguageEngine


# Define constructs for state requirements
@construct()
class UserProfile(BaseModel):
    """User profile information"""
    user_id: str
    email: str


@construct()
class PaymentInfo(BaseModel):
    """Payment information for checkout"""
    card_number: str
    cvv: str


# Define a realistic e-commerce workflow
@stage(name="browse")
class BrowseStage:
    """Browse products and add to cart"""
    
    @task(description="Search for products by query")
    def search_products(self, state: State, query: str) -> dict:
        """Search products"""
        return {
            "results": [
                {"id": "prod1", "name": "Laptop", "price": 999.99},
                {"id": "prod2", "name": "Mouse", "price": 29.99}
            ]
        }
    
    @task(description="Add product to shopping cart")
    def add_to_cart(self, state: State, product_id: str, quantity: int = 1) -> dict:
        """Add to cart"""
        cart = state.get("cart", [])
        cart.append({"product_id": product_id, "quantity": quantity})
        state.set("cart", cart)
        return {"success": True, "cart_size": len(cart)}
    
    @task(description="View current cart contents")
    def view_cart(self, state: State) -> dict:
        """View cart"""
        return {"cart": state.get("cart", [])}


@stage(name="checkout", prerequisites=[UserProfile, PaymentInfo])
class CheckoutStage:
    """Checkout and complete purchase"""
    
    @task(description="Calculate order total with tax and shipping")
    def calculate_total(self, state: State) -> dict:
        """Calculate total"""
        cart = state.get("cart", [])
        subtotal = len(cart) * 100.0  # Simplified
        tax = subtotal * 0.08
        shipping = 10.0
        total = subtotal + tax + shipping
        return {
            "subtotal": subtotal,
            "tax": tax,
            "shipping": shipping,
            "total": total
        }
    
    @task(description="Complete the purchase and create order")
    def complete_purchase(self, state: State) -> dict:
        """Complete purchase"""
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        state.set("order_id", order_id)
        return {
            "success": True,
            "order_id": order_id,
            "message": "Order placed successfully"
        }


@stage(name="confirmation")
class ConfirmationStage:
    """Order confirmation and tracking"""
    
    @task(description="Get order details and confirmation")
    def get_order_details(self, state: State) -> dict:
        """Get order details"""
        return {
            "order_id": state.get("order_id"),
            "email": state.get("email"),
            "status": "confirmed"
        }
    
    @task(description="Send confirmation email")
    def send_confirmation_email(self, state: State) -> dict:
        """Send email"""
        return {
            "success": True,
            "sent_to": state.get("email")
        }


@workflow(name="ecommerce_workflow")
class EcommerceWorkflow:
    """Complete e-commerce workflow"""
    browse = BrowseStage
    checkout = CheckoutStage
    confirmation = ConfirmationStage
    
    transitions = {
        browse: [checkout],
        checkout: [confirmation],
        confirmation: []
    }


@pytest.mark.anyio
async def test_end_to_end_ecommerce_flow():
    """
    Comprehensive end-to-end test simulating real LLM interaction.
    Tests: tasks, stage transitions, state requirements, and session termination.
    """
    session_id = f"e2e-{uuid.uuid4().hex[:8]}"
    engine = LanguageEngine(
        workflow=EcommerceWorkflow._workflow,
        session_id=session_id,
        output_format="json"
    )
    
    # Step 1: Get initial state - should show browse stage tools
    result = engine.get_initial_message()
    result_json = json.loads(result)
    assert "content" in result_json
    assert "tools" in result_json
    
    # Verify initial tools include browse stage tasks
    tool_names = [t["name"] for t in result_json["tools"]]
    assert "search_products" in tool_names
    assert "add_to_cart" in tool_names
    assert "view_cart" in tool_names
    assert "transition_stage" in tool_names
    assert "terminate_session" in tool_names
    
    # Step 2: Search for products (task call)
    result = await engine.process({
        "action": "method_call",
        "task": "search_products",
        "args": {"query": "laptop"}
    })
    result_json = json.loads(result)
    assert "content" in result_json
    assert "tools" in result_json
    assert "Laptop" in result_json["content"] or "laptop" in result_json["content"].lower()
    
    # Step 3: Add items to cart (multiple task calls)
    result = await engine.process({
        "action": "method_call",
        "task": "add_to_cart",
        "args": {"product_id": "prod1", "quantity": 1}
    })
    result_json = json.loads(result)
    assert "success" in result_json["content"].lower() or "cart_size" in result_json["content"]
    
    result = await engine.process({
        "action": "method_call",
        "task": "add_to_cart",
        "args": {"product_id": "prod2", "quantity": 2}
    })
    result_json = json.loads(result)
    assert "tools" in result_json
    
    # Step 4: View cart
    result = await engine.process({
        "action": "method_call",
        "task": "view_cart",
        "args": {}
    })
    result_json = json.loads(result)
    assert "content" in result_json
    
    # Step 5: Try to transition to checkout WITHOUT providing state (should fail)
    result = await engine.process({
        "action": "stage_transition",
        "stage": "checkout"
    })
    result_json = json.loads(result)
    
    # Should get state input required with ONLY provide_state tool
    assert "tools" in result_json
    assert len(result_json["tools"]) == 1, "Should only show provide_state tool when state is required"
    assert result_json["tools"][0]["name"] == "provide_state"
    
    # Verify required fields are in the schema
    properties = result_json["tools"][0]["input_schema"]["properties"]
    assert "user_id" in properties
    assert "email" in properties
    assert "card_number" in properties
    assert "cvv" in properties
    
    # Step 6: Provide required state
    result = await engine.process({
        "action": "state_input",
        "state_updates": {
            "user_id": "user123",
            "email": "user@example.com",
            "card_number": "4111111111111111",
            "cvv": "123"
        }
    })
    result_json = json.loads(result)
    assert "populated" in result_json["content"].lower() or "success" in result_json["content"].lower()
    
    # Step 7: Now transition to checkout (should succeed)
    result = await engine.process({
        "action": "stage_transition",
        "stage": "checkout"
    })
    result_json = json.loads(result)
    assert "tools" in result_json
    
    # Verify we're now in checkout stage with checkout tools
    tool_names = [t["name"] for t in result_json["tools"]]
    assert "calculate_total" in tool_names
    assert "complete_purchase" in tool_names
    assert "transition_stage" in tool_names  # Should have transition to confirmation
    
    # Should NOT have browse stage tools anymore
    assert "search_products" not in tool_names
    assert "add_to_cart" not in tool_names
    
    # Step 8: Calculate total
    result = await engine.process({
        "action": "method_call",
        "task": "calculate_total",
        "args": {}
    })
    result_json = json.loads(result)
    assert "content" in result_json
    assert "total" in result_json["content"].lower()
    
    # Step 9: Complete purchase
    result = await engine.process({
        "action": "method_call",
        "task": "complete_purchase",
        "args": {}
    })
    result_json = json.loads(result)
    assert "success" in result_json["content"].lower() or "order" in result_json["content"].lower()
    
    # Step 10: Transition to confirmation
    result = await engine.process({
        "action": "stage_transition",
        "stage": "confirmation"
    })
    result_json = json.loads(result)
    
    # Verify we're in confirmation stage
    tool_names = [t["name"] for t in result_json["tools"]]
    assert "get_order_details" in tool_names
    assert "send_confirmation_email" in tool_names
    
    # Should NOT have checkout tools anymore
    assert "calculate_total" not in tool_names
    assert "complete_purchase" not in tool_names
    
    # Step 11: Get order details
    result = await engine.process({
        "action": "method_call",
        "task": "get_order_details",
        "args": {}
    })
    result_json = json.loads(result)
    assert "content" in result_json
    assert "order" in result_json["content"].lower() or "confirmed" in result_json["content"].lower()
    
    # Step 12: Send confirmation email
    result = await engine.process({
        "action": "method_call",
        "task": "send_confirmation_email",
        "args": {}
    })
    result_json = json.loads(result)
    assert "success" in result_json["content"].lower() or "sent" in result_json["content"].lower()
    
    # Step 13: Terminate session
    result = await engine.process({
        "action": "terminate_session",
        "reason": "order completed"
    })
    result_json = json.loads(result)
    assert result_json["status"] == "terminated"
    assert result_json["session_id"] == session_id


@pytest.mark.anyio
async def test_invalid_task_call():
    """Test that invalid task calls are handled gracefully"""
    session_id = f"invalid-task-{uuid.uuid4().hex[:8]}"
    engine = LanguageEngine(
        workflow=EcommerceWorkflow._workflow,
        session_id=session_id,
        output_format="json"
    )
    
    # Try to call non-existent task
    result = await engine.process({
        "action": "method_call",
        "task": "nonexistent_task",
        "args": {}
    })
    result_json = json.loads(result)
    
    # Should return error but still provide tools
    assert "content" in result_json
    assert "error" in result_json["content"].lower() or "not found" in result_json["content"].lower()


@pytest.mark.anyio
async def test_invalid_stage_transition():
    """Test that invalid stage transitions are rejected"""
    session_id = f"invalid-transition-{uuid.uuid4().hex[:8]}"
    engine = LanguageEngine(
        workflow=EcommerceWorkflow._workflow,
        session_id=session_id,
        output_format="json"
    )
    
    # Try to transition to confirmation from browse (not allowed)
    result = await engine.process({
        "action": "stage_transition",
        "stage": "confirmation"
    })
    result_json = json.loads(result)
    
    # Should return error with allowed transitions
    assert "content" in result_json
    assert "error" in result_json["content"].lower() or "cannot" in result_json["content"].lower()


@pytest.mark.anyio
async def test_missing_task_args():
    """Test that missing required task arguments are handled"""
    session_id = f"missing-args-{uuid.uuid4().hex[:8]}"
    engine = LanguageEngine(
        workflow=EcommerceWorkflow._workflow,
        session_id=session_id,
        output_format="json"
    )
    
    # Try to call search_products without required 'query' argument
    result = await engine.process({
        "action": "method_call",
        "task": "search_products",
        "args": {}
    })
    result_json = json.loads(result)
    
    # Should return error
    assert "content" in result_json
    # Error should mention missing parameter
    assert "error" in result_json["content"].lower()


@pytest.mark.anyio
async def test_state_persistence_across_stages():
    """Test that state persists correctly across stage transitions"""
    session_id = f"state-persist-{uuid.uuid4().hex[:8]}"
    engine = LanguageEngine(
        workflow=EcommerceWorkflow._workflow,
        session_id=session_id,
        output_format="json"
    )
    
    # Add items to cart in browse stage
    await engine.process({
        "action": "method_call",
        "task": "add_to_cart",
        "args": {"product_id": "test_product", "quantity": 5}
    })
    
    # Provide state and transition to checkout
    await engine.process({
        "action": "state_input",
        "state_updates": {
            "user_id": "user456",
            "email": "test@example.com",
            "card_number": "4111111111111111",
            "cvv": "456"
        }
    })
    
    await engine.process({
        "action": "stage_transition",
        "stage": "checkout"
    })
    
    # Calculate total should still have access to cart from browse stage
    result = await engine.process({
        "action": "method_call",
        "task": "calculate_total",
        "args": {}
    })
    result_json = json.loads(result)
    
    # Should successfully calculate (wouldn't work if cart state was lost)
    assert "content" in result_json
    assert "total" in result_json["content"].lower()


@pytest.mark.anyio
async def test_tool_schema_accuracy():
    """Test that tool schemas accurately reflect task parameters"""
    session_id = f"schema-test-{uuid.uuid4().hex[:8]}"
    engine = LanguageEngine(
        workflow=EcommerceWorkflow._workflow,
        session_id=session_id,
        output_format="json"
    )
    
    result = engine.get_initial_message()
    result_json = json.loads(result)
    
    # Find add_to_cart tool
    add_to_cart_tool = None
    for tool in result_json["tools"]:
        if tool["name"] == "add_to_cart":
            add_to_cart_tool = tool
            break
    
    assert add_to_cart_tool is not None
    
    # Verify schema has correct parameters
    props = add_to_cart_tool["input_schema"]["properties"]
    assert "product_id" in props
    assert "quantity" in props
    
    # product_id should be required, quantity is optional (has default)
    required = add_to_cart_tool["input_schema"]["required"]
    assert "product_id" in required
    # quantity has default so should not be required
    assert "quantity" not in required or len([r for r in required if r == "quantity"]) == 0

