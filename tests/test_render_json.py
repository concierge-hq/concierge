"""Tests for render_json capability in presentations"""
import json
import pytest
from concierge.core.workflow import workflow
from concierge.core.stage import stage
from concierge.core.task import task
from concierge.core.state import State
from concierge.core.results import TaskResult
from concierge.presentations import ComprehensivePresentation, BriefPresentation
from concierge.communications import TaskResultMessage
from concierge.engine import LanguageEngine


@stage(name="shopping")
class ShoppingStage:
    """Shopping stage for testing"""
    
    @task(description="Add item to cart")
    def add_to_cart(self, state: State, product_id: str, quantity: int) -> dict:
        """Add product to shopping cart"""
        return {"success": True}
    
    @task(description="Search for products")
    def search_products(self, state: State, query: str) -> dict:
        """Search product catalog"""
        return {"results": []}


@stage(name="checkout")
class CheckoutStage:
    """Checkout stage for completing purchase"""
    
    @task(description="Complete purchase")
    def complete_purchase(self, state: State, payment_method: str) -> dict:
        """Process payment and complete order"""
        return {"order_id": "12345"}


@workflow(name="test_shopping")
class TestShoppingWorkflow:
    """Test workflow for render_json"""
    shopping = ShoppingStage
    checkout = CheckoutStage
    transitions = {
        shopping: [checkout],
        checkout: []
    }


class TestRenderJson:
    """Test render_json functionality"""
    
    def test_comprehensive_presentation_render_json(self):
        """Test ComprehensivePresentation.render_json returns correct structure"""
        engine = LanguageEngine(
            workflow=TestShoppingWorkflow._workflow,
            session_id="test-123",
            output_format="json"
        )
        
        task_result = TaskResult(
            task_name="add_to_cart",
            result={"success": True},
            presentation_type=ComprehensivePresentation
        )
        content = TaskResultMessage().render(task_result)
        
        presentation = ComprehensivePresentation(content)
        result = presentation.render_json(engine.orchestrator)
        
        expected = {
            "content": "Task 'add_to_cart' executed successfully.\n\nResult:\n{'success': True}",
            "tools": [
                {
                    "name": "add_to_cart",
                    "description": "Add item to cart",
                    "input_schema": {
                        "properties": {
                            "product_id": {"title": "Product Id", "type": "string"},
                            "quantity": {"title": "Quantity", "type": "integer"}
                        },
                        "required": ["product_id", "quantity"],
                        "title": "add_to_cartInput",
                        "type": "object"
                    }
                },
                {
                    "name": "search_products",
                    "description": "Search for products",
                    "input_schema": {
                        "properties": {
                            "query": {"title": "Query", "type": "string"}
                        },
                        "required": ["query"],
                        "title": "search_productsInput",
                        "type": "object"
                    }
                },
                {
                    "name": "transition_stage",
                    "description": "Move to a different stage in the workflow. Available stages: checkout",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "target_stage": {
                                "type": "string",
                                "enum": ["checkout"],
                                "description": "The stage to transition to. checkout: Checkout stage for completing purchase"
                            }
                        },
                        "required": ["target_stage"]
                    }
                },
                {
                    "name": "terminate_session",
                    "description": "End the current session",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Optional reason for ending the session"
                            }
                        },
                        "required": []
                    }
                }
            ]
        }
        
        assert result == expected
    
    def test_brief_presentation_render_json(self):
        """Test BriefPresentation.render_json returns correct structure"""
        engine = LanguageEngine(
            workflow=TestShoppingWorkflow._workflow,
            session_id="test-456",
            output_format="json"
        )
        
        task_result = TaskResult(
            task_name="search_products",
            result={"results": ["item1", "item2"]},
            presentation_type=BriefPresentation
        )
        content = TaskResultMessage().render(task_result)
        
        presentation = BriefPresentation(content)
        result = presentation.render_json(engine.orchestrator)
        
        expected = {
            "content": "Task 'search_products' executed successfully.\n\nResult:\n{'results': ['item1', 'item2']}",
            "tools": [
                {
                    "name": "add_to_cart",
                    "description": "Add item to cart",
                    "input_schema": {
                        "properties": {
                            "product_id": {"title": "Product Id", "type": "string"},
                            "quantity": {"title": "Quantity", "type": "integer"}
                        },
                        "required": ["product_id", "quantity"],
                        "title": "add_to_cartInput",
                        "type": "object"
                    }
                },
                {
                    "name": "search_products",
                    "description": "Search for products",
                    "input_schema": {
                        "properties": {
                            "query": {"title": "Query", "type": "string"}
                        },
                        "required": ["query"],
                        "title": "search_productsInput",
                        "type": "object"
                    }
                },
                {
                    "name": "transition_stage",
                    "description": "Move to a different stage in the workflow. Available stages: checkout",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "target_stage": {
                                "type": "string",
                                "enum": ["checkout"],
                                "description": "The stage to transition to. checkout: Checkout stage for completing purchase"
                            }
                        },
                        "required": ["target_stage"]
                    }
                },
                {
                    "name": "terminate_session",
                    "description": "End the current session",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Optional reason for ending the session"
                            }
                        },
                        "required": []
                    }
                }
            ]
        }
        
        assert result == expected
    
    def test_tool_schema_format(self):
        """Test that tools have the correct schema format (tasks + transitions)"""
        engine = LanguageEngine(
            workflow=TestShoppingWorkflow._workflow,
            session_id="test-789",
            output_format="json"
        )
        
        task_result = TaskResult(
            task_name="add_to_cart",
            result={"cart_size": 3},
            presentation_type=ComprehensivePresentation
        )
        content = TaskResultMessage().render(task_result)
        
        presentation = ComprehensivePresentation(content)
        result = presentation.render_json(engine.orchestrator)
        
        expected = {
            "content": "Task 'add_to_cart' executed successfully.\n\nResult:\n{'cart_size': 3}",
            "tools": [
                {
                    "name": "add_to_cart",
                    "description": "Add item to cart",
                    "input_schema": {
                        "properties": {
                            "product_id": {"title": "Product Id", "type": "string"},
                            "quantity": {"title": "Quantity", "type": "integer"}
                        },
                        "required": ["product_id", "quantity"],
                        "title": "add_to_cartInput",
                        "type": "object"
                    }
                },
                {
                    "name": "search_products",
                    "description": "Search for products",
                    "input_schema": {
                        "properties": {
                            "query": {"title": "Query", "type": "string"}
                        },
                        "required": ["query"],
                        "title": "search_productsInput",
                        "type": "object"
                    }
                },
                {
                    "name": "transition_stage",
                    "description": "Move to a different stage in the workflow. Available stages: checkout",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "target_stage": {
                                "type": "string",
                                "enum": ["checkout"],
                                "description": "The stage to transition to. checkout: Checkout stage for completing purchase"
                            }
                        },
                        "required": ["target_stage"]
                    }
                },
                {
                    "name": "terminate_session",
                    "description": "End the current session",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Optional reason for ending the session"
                            }
                        },
                        "required": []
                    }
                }
            ]
        }
        
        assert result == expected
    
    @pytest.mark.anyio
    async def test_language_engine_output_format_text(self):
        """Test LanguageEngine returns text when output_format='text'"""
        engine = LanguageEngine(
            workflow=TestShoppingWorkflow._workflow,
            session_id="test-text",
            output_format="text"
        )
        
        result = await engine.process({
            "action": "method_call",
            "task": "add_to_cart",
            "args": {"product_id": "123", "quantity": 2}
        })
        
        assert isinstance(result, str)
        assert "success" in result.lower() or "result" in result.lower()
    
    @pytest.mark.anyio
    async def test_language_engine_output_format_json(self):
        """Test LanguageEngine returns JSON string when output_format='json'"""
        engine = LanguageEngine(
            workflow=TestShoppingWorkflow._workflow,
            session_id="test-json",
            output_format="json"
        )
        
        result = await engine.process({
            "action": "method_call",
            "task": "add_to_cart",
            "args": {"product_id": "123", "quantity": 2}
        })
        
        assert isinstance(result, str)
        result_json = json.loads(result)
        
        expected = {
            "content": "Task 'add_to_cart' executed successfully.\n\nResult:\n{'success': True}",
            "tools": [
                {
                    "name": "add_to_cart",
                    "description": "Add item to cart",
                    "input_schema": {
                        "properties": {
                            "product_id": {"title": "Product Id", "type": "string"},
                            "quantity": {"title": "Quantity", "type": "integer"}
                        },
                        "required": ["product_id", "quantity"],
                        "title": "add_to_cartInput",
                        "type": "object"
                    }
                },
                {
                    "name": "search_products",
                    "description": "Search for products",
                    "input_schema": {
                        "properties": {
                            "query": {"title": "Query", "type": "string"}
                        },
                        "required": ["query"],
                        "title": "search_productsInput",
                        "type": "object"
                    }
                },
                {
                    "name": "transition_stage",
                    "description": "Move to a different stage in the workflow. Available stages: checkout",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "target_stage": {
                                "type": "string",
                                "enum": ["checkout"],
                                "description": "The stage to transition to. checkout: Checkout stage for completing purchase"
                            }
                        },
                        "required": ["target_stage"]
                    }
                },
                {
                    "name": "terminate_session",
                    "description": "End the current session",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Optional reason for ending the session"
                            }
                        },
                        "required": []
                    }
                }
            ]
        }
        
        assert result_json == expected
    
    @pytest.mark.anyio
    async def test_language_engine_default_format(self):
        """Test LanguageEngine defaults to text format"""
        engine = LanguageEngine(
            workflow=TestShoppingWorkflow._workflow,
            session_id="test-default"
        )
        
        result = await engine.process({
            "action": "method_call",
            "task": "search_products",
            "args": {"query": "laptop"}
        })
        
        assert isinstance(result, str)
    
    @pytest.mark.anyio
    async def test_terminate_session(self):
        """Test that terminate_session action works correctly"""
        import uuid
        engine = LanguageEngine(
            workflow=TestShoppingWorkflow._workflow,
            session_id=f"test-terminate-{uuid.uuid4().hex[:8]}",
            output_format="json"
        )
        
        result = await engine.process({
            "action": "terminate_session",
            "reason": "completed"
        })
        
        assert isinstance(result, str)
        result_json = json.loads(result)
        assert result_json["status"] == "terminated"
        assert "session_id" in result_json

