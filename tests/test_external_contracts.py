"""Test external contracts - formal JSON schemas."""
from concierge.external.contracts import (
    ToolCall,
    StageTransition,
    TerminateSession,
    TOOL_CALL_EXAMPLE,
    STAGE_TRANSITION_EXAMPLE,
    TERMINATE_SESSION_EXAMPLE,
    _auto_example
)


def test_tool_call_schema():
    """Test ToolCall schema definition"""
    schema = ToolCall.model_json_schema()
    
    assert schema["properties"]["action"]["const"] == "method_call"
    
    assert "examples" in schema["properties"]["tool"]
    assert "search" in schema["properties"]["tool"]["examples"]
    
    assert "examples" in schema["properties"]["args"]


def test_stage_transition_schema():
    """Test StageTransition schema definition"""
    schema = StageTransition.model_json_schema()
    
    assert schema["properties"]["action"]["const"] == "stage_transition"
    
    assert "examples" in schema["properties"]["stage"]
    assert "portfolio" in schema["properties"]["stage"]["examples"]


def test_terminate_session_schema():
    """Test TerminateSession schema definition"""
    schema = TerminateSession.model_json_schema()
    
    assert schema["properties"]["action"]["const"] == "terminate_session"
    
    assert "examples" in schema["properties"]["reason"]
    assert "completed" in schema["properties"]["reason"]["examples"]


def test_auto_example_tool_call():
    """Test auto-generation of ToolCall example"""
    assert TOOL_CALL_EXAMPLE.action == "method_call"
    assert TOOL_CALL_EXAMPLE.tool == "search"
    assert TOOL_CALL_EXAMPLE.args == {"symbol": "AAPL"}


def test_auto_example_stage_transition():
    """Test auto-generation of StageTransition example"""
    assert STAGE_TRANSITION_EXAMPLE.action == "stage_transition"
    assert STAGE_TRANSITION_EXAMPLE.stage == "portfolio"


def test_auto_example_terminate_session():
    """Test auto-generation of TerminateSession example"""
    assert TERMINATE_SESSION_EXAMPLE.action == "terminate_session"
    assert TERMINATE_SESSION_EXAMPLE.reason == "completed"


def test_example_serialization():
    """Test that examples serialize to valid JSON"""
    tool_json = TOOL_CALL_EXAMPLE.model_dump()
    assert tool_json["action"] == "method_call"
    assert tool_json["tool"] == "search"
    assert tool_json["args"] == {"symbol": "AAPL"}
    
    stage_json = STAGE_TRANSITION_EXAMPLE.model_dump()
    assert stage_json["action"] == "stage_transition"
    assert stage_json["stage"] == "portfolio"
    
    term_json = TERMINATE_SESSION_EXAMPLE.model_dump()
    assert term_json["action"] == "terminate_session"
    assert term_json["reason"] == "completed"


def test_example_json_strings():
    """Test JSON string formatting"""
    import json
    
    tool_str = TOOL_CALL_EXAMPLE.model_dump_json()
    stage_str = STAGE_TRANSITION_EXAMPLE.model_dump_json()
    term_str = TERMINATE_SESSION_EXAMPLE.model_dump_json()
    
    assert json.loads(tool_str)["action"] == "method_call"
    assert json.loads(stage_str)["action"] == "stage_transition"
    assert json.loads(term_str)["action"] == "terminate_session"


def test_contract_validation():
    """Test that contracts validate correctly"""
    valid_tool = ToolCall(
        action="method_call",
        tool="search",
        args={"symbol": "AAPL"}
    )
    assert valid_tool.action == "method_call"
    
    valid_stage = StageTransition(
        action="stage_transition",
        stage="portfolio"
    )
    assert valid_stage.stage == "portfolio"
    
    valid_term = TerminateSession(
        action="terminate_session",
        reason="user_request"
    )
    assert valid_term.reason == "user_request"
    
    valid_term_no_reason = TerminateSession(
        action="terminate_session"
    )
    assert valid_term_no_reason.reason is None


def test_auto_example_uses_field_metadata():
    """Test that _auto_example correctly extracts from Field metadata"""
    from pydantic import BaseModel, Field
    from typing import Literal
    
    class TestModel(BaseModel):
        action: Literal["test_action"]
        name: str = Field(examples=["first", "second", "third"])
        count: int = Field(examples=[10, 20, 30])
    
    example = _auto_example(TestModel)
    
    assert example.action == "test_action"
    
    assert example.name == "first"
    assert example.count == 10

