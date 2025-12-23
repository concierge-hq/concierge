"""Test to verify input_schema generation from function signatures"""
from typing import Optional, List
from concierge.core.task import task
from concierge.core.stage import stage
from concierge.core.state import State


class TestSchemaGeneration:
    """Test that to_schema correctly captures types and arguments"""
    
    def test_basic_types(self):
        """Test basic Python types are correctly converted"""
        @stage(name="test")
        class TestStage:
            @task(description="Test basic types")
            def test_func(self, state: State, name: str, age: int, score: float, active: bool) -> dict:
                return {}
        
        task_obj = TestStage.tasks["test_func"]
        schema = task_obj.to_schema()
        props = schema["input_schema"]["properties"]
        
        # Verify types
        assert props["name"]["type"] == "string"
        assert props["age"]["type"] == "integer"
        assert props["score"]["type"] == "number"
        assert props["active"]["type"] == "boolean"
        
        # Verify all are required (no defaults)
        assert set(schema["input_schema"]["required"]) == {"name", "age", "score", "active"}
    
    def test_optional_parameters(self):
        """Test optional parameters with defaults"""
        @stage(name="test")
        class TestStage:
            @task(description="Test optional params")
            def test_func(self, state: State, required: str, optional: int = 10) -> dict:
                return {}
        
        task_obj = TestStage.tasks["test_func"]
        schema = task_obj.to_schema()
        
        # Only required param is in required list
        assert schema["input_schema"]["required"] == ["required"]
        
        # Optional param has default
        assert "optional" in schema["input_schema"]["properties"]
        assert schema["input_schema"]["properties"]["optional"]["type"] == "integer"
    
    def test_complex_types(self):
        """Test complex types like List and Optional"""
        @stage(name="test")
        class TestStage:
            @task(description="Test complex types")
            def test_func(self, state: State, items: List[str], maybe_value: Optional[str] = None) -> dict:
                return {}
        
        task_obj = TestStage.tasks["test_func"]
        schema = task_obj.to_schema()
        props = schema["input_schema"]["properties"]
        
        # List[str] becomes array of strings
        assert props["items"]["type"] == "array"
        assert props["items"]["items"]["type"] == "string"
        
        # Optional[str] becomes anyOf with null
        assert "anyOf" in props["maybe_value"] or "type" in props["maybe_value"]
    
    def test_state_filtered_out(self):
        """Test that State parameter is filtered out"""
        @stage(name="test")
        class TestStage:
            @task(description="Test state filtering")
            def test_func(self, state: State, user_id: str) -> dict:
                return {}
        
        task_obj = TestStage.tasks["test_func"]
        schema = task_obj.to_schema()
        props = schema["input_schema"]["properties"]
        
        # State should NOT be in properties
        assert "state" not in props
        
        # Only user_id should be present
        assert "user_id" in props
        assert len(props) == 1
    
    def test_title_generation(self):
        """Test that titles are generated from param names"""
        @stage(name="test")
        class TestStage:
            @task(description="Test title generation")
            def test_func(self, state: State, product_id: str, user_name: str) -> dict:
                return {}
        
        task_obj = TestStage.tasks["test_func"]
        schema = task_obj.to_schema()
        props = schema["input_schema"]["properties"]
        
        # snake_case → Title Case
        assert props["product_id"]["title"] == "Product Id"
        assert props["user_name"]["title"] == "User Name"
    
    def test_complete_schema_structure(self):
        """Test the complete schema structure matches expectations"""
        @stage(name="test")
        class TestStage:
            @task(description="Add item to shopping cart")
            def add_to_cart(self, state: State, product_id: str, quantity: int) -> dict:
                return {}
        
        task_obj = TestStage.tasks["add_to_cart"]
        schema = task_obj.to_schema()
        
        # Check top-level structure
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema
        
        # Check name and description
        assert schema["name"] == "add_to_cart"
        assert schema["description"] == "Add item to shopping cart"
        
        # Check input_schema structure
        input_schema = schema["input_schema"]
        assert input_schema["type"] == "object"
        assert "properties" in input_schema
        assert "required" in input_schema
        assert "title" in input_schema
        
        # Check properties
        props = input_schema["properties"]
        assert "product_id" in props
        assert "quantity" in props
        
        # Check each property has required fields
        for prop_name, prop_schema in props.items():
            assert "type" in prop_schema
            assert "title" in prop_schema
        
        # Verify exact match with expected
        expected = {
            "name": "add_to_cart",
            "description": "Add item to shopping cart",
            "input_schema": {
                "properties": {
                    "product_id": {"title": "Product Id", "type": "string"},
                    "quantity": {"title": "Quantity", "type": "integer"}
                },
                "required": ["product_id", "quantity"],
                "title": "add_to_cartInput",
                "type": "object"
            }
        }
        
        assert schema == expected

