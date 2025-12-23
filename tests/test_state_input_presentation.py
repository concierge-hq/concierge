"""Tests for StateInputPresentation - state input flow"""
import json
import pytest
from concierge.core.workflow import workflow
from concierge.core.stage import stage
from concierge.core.task import task
from concierge.core.state import State
from concierge.core.construct import construct
from concierge.presentations import StateInputPresentation
from concierge.engine import LanguageEngine
from pydantic import BaseModel


# Define prerequisites construct
@construct()
class CheckoutPrerequisites(BaseModel):
    """Prerequisites for checkout stage"""
    user_email: str
    payment_method: str


@stage(name="shopping")
class ShoppingStage:
    """Shopping stage"""
    
    @task(description="Add item to cart")
    def add_to_cart(self, state: State, product_id: str) -> dict:
        return {"success": True}


@stage(name="checkout", prerequisites=[CheckoutPrerequisites])
class CheckoutStage:
    """Checkout stage with prerequisites"""
    
    @task(description="Complete purchase")
    def complete_purchase(self, state: State) -> dict:
        return {"order_id": "12345"}


@workflow(name="test_state_input")
class TestStateInputWorkflow:
    """Test workflow with prerequisites"""
    shopping = ShoppingStage
    checkout = CheckoutStage
    transitions = {
        shopping: [checkout],
        checkout: []
    }


class TestStateInputPresentation:
    """Test StateInputPresentation behavior"""
    
    def test_state_input_presentation_render_json(self):
        """Test that StateInputPresentation only shows provide_state tool"""
        engine = LanguageEngine(
            workflow=TestStateInputWorkflow._workflow,
            session_id="test-state-input",
            output_format="json"
        )
        
        engine.orchestrator.required_state_fields = ["user_email", "payment_method"]
        
        presentation = StateInputPresentation("Please provide missing information")
        result = presentation.render_json(engine.orchestrator)
        
        expected = {
            "content": "Please provide missing information",
            "tools": [{
                "name": "provide_state",
                "description": "Provide required the following state information to continue with the workflow",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_email": {
                            "type": "string",
                            "description": "Value for user_email"
                        },
                        "payment_method": {
                            "type": "string",
                            "description": "Value for payment_method"
                        }
                    },
                    "required": ["user_email", "payment_method"]
                }
            }]
        }
        
        # Assert exact match
        assert result == expected
    
    def test_state_input_presentation_text_format(self):
        """Test StateInputPresentation text format"""
        import uuid
        engine = LanguageEngine(
            workflow=TestStateInputWorkflow._workflow,
            session_id=f"test-text-{uuid.uuid4().hex[:8]}",
            output_format="text"
        )
        
        engine.orchestrator.required_state_fields = ["user_email"]
        
        presentation = StateInputPresentation("Please provide user_email")
        result = presentation.render_text(engine.orchestrator)
        
        assert result == "Please provide user_email"
    
    def test_state_input_with_empty_fields(self):
        """Test StateInputPresentation with no required fields"""
        engine = LanguageEngine(
            workflow=TestStateInputWorkflow._workflow,
            session_id="test-empty",
            output_format="json"
        )
        
        engine.orchestrator.required_state_fields = []
        
        presentation = StateInputPresentation("State satisfied")
        result = presentation.render_json(engine.orchestrator)
        
        expected = {
            "content": "State satisfied",
            "tools": [{
                "name": "provide_state",
                "description": "Provide required the following state information to continue with the workflow",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }]
        }
        
        assert result == expected
    
    @pytest.mark.anyio
    async def test_transition_triggers_state_input(self):
        """Test that attempting transition with missing prerequisites triggers StateInputPresentation"""
        import uuid
        engine = LanguageEngine(
            workflow=TestStateInputWorkflow._workflow,
            session_id=f"test-transition-{uuid.uuid4().hex[:8]}",
            output_format="json"
        )
        
        result = await engine.process({
            "action": "stage_transition",
            "stage": "checkout"
        })
        
        assert isinstance(result, str)
        result_json = json.loads(result)
        assert "content" in result_json
        assert "tools" in result_json
        
        # Only one tool: provide state
        assert len(result_json["tools"]) == 1
        assert result_json["tools"][0]["name"] == "provide_state"
        
        props = result_json["tools"][0]["input_schema"]["properties"]
        assert "user_email" in props
        assert "payment_method" in props
        
        assert engine.orchestrator.required_state_fields == ["user_email", "payment_method"]
    
    @pytest.mark.anyio
    async def test_state_cleared_after_providing(self):
        """Test that required_state_fields is cleared after providing state"""
        engine = LanguageEngine(
            workflow=TestStateInputWorkflow._workflow,
            session_id="test-clear",
            output_format="json"
        )
        
        engine.orchestrator.required_state_fields = ["user_email", "payment_method"]
        
        await engine.process({
            "action": "state_input",
            "state_updates": {
                "user_email": "test@example.com",
                "payment_method": "visa"
            }
        })
        
        assert engine.orchestrator.required_state_fields == []

