"""
Unit tests for build_search_text - unstructured format for better embeddings.
"""

import pytest
from openmcp.search_backend import build_search_text, extract_param_text


class MockTool:
    def __init__(self, name, description, parameters):
        self.name = name
        self.description = description
        self.parameters = parameters


class TestBuildSearchText:

    def test_basic_tool(self):
        tool = MockTool("search_users", "Find users", {"properties": {}})
        text = build_search_text(tool)
        assert text == "search_users search users Find users"

    def test_tool_with_param(self):
        tool = MockTool("tool", "desc", {
            "properties": {
                "query": {},
            }
        })
        text = build_search_text(tool)
        assert text == "tool tool desc query query"

    def test_tool_with_param_title(self):
        tool = MockTool("tool", "desc", {
            "properties": {
                "query": {"title": "Search Query"},
            }
        })
        text = build_search_text(tool)
        assert text == "tool tool desc query query Search Query"

    def test_tool_with_param_description(self):
        tool = MockTool("tool", "desc", {
            "properties": {
                "query": {"description": "The search term"},
            }
        })
        text = build_search_text(tool)
        assert text == "tool tool desc query query The search term"

    def test_tool_with_param_format(self):
        tool = MockTool("tool", "desc", {
            "properties": {
                "email": {"format": "email"},
            }
        })
        text = build_search_text(tool)
        assert text == "tool tool desc email email email"

    def test_tool_with_param_examples(self):
        tool = MockTool("tool", "desc", {
            "properties": {
                "query": {"examples": ["john@test.com", "jane"]},
            }
        })
        text = build_search_text(tool)
        assert text == "tool tool desc query query john@test.com jane"

    def test_tool_with_inline_enum(self):
        tool = MockTool("tool", "desc", {
            "properties": {
                "status": {"enum": ["pending", "active"]},
            }
        })
        text = build_search_text(tool)
        assert text == "tool tool desc status status pending active"

    def test_tool_with_ref_enum(self):
        tool = MockTool("tool", "desc", {
            "$defs": {
                "Status": {"enum": ["on", "off"]}
            },
            "properties": {
                "status": {"$ref": "#/$defs/Status"},
            }
        })
        text = build_search_text(tool)
        assert text == "tool tool desc status status on off"

    def test_tool_with_multiple_params(self):
        tool = MockTool("get_user", "Get user details", {
            "properties": {
                "user_id": {"title": "User ID", "description": "The user identifier"},
                "include_email": {"title": "Include Email"},
            }
        })
        text = build_search_text(tool)
        assert text == "get_user get user Get user details user_id user id User ID The user identifier include_email include email Include Email"

    def test_complete_tool(self):
        tool = MockTool(
            name="get_payment_errors",
            description="Retrieve payment errors",
            parameters={
                "$defs": {
                    "Env": {"enum": ["prod", "dev"]}
                },
                "properties": {
                    "service": {
                        "title": "Service Name",
                        "description": "The service",
                        "format": "string",
                        "examples": ["stripe"],
                    },
                    "env": {"$ref": "#/$defs/Env"},
                    "codes": {"enum": ["E001", "E002"]},
                }
            }
        )
        text = build_search_text(tool)
        assert text == "get_payment_errors get payment errors Retrieve payment errors service service Service Name The service string stripe env env prod dev codes codes E001 E002"


class TestExtractParamText:

    def test_empty_param(self):
        parts = extract_param_text({}, {})
        assert parts == []

    def test_with_title(self):
        parts = extract_param_text({"title": "Search Query"}, {})
        assert parts == ["Search Query"]

    def test_with_description(self):
        parts = extract_param_text({"description": "The search term"}, {})
        assert parts == ["The search term"]

    def test_with_format(self):
        parts = extract_param_text({"format": "email"}, {})
        assert parts == ["email"]

    def test_with_examples(self):
        parts = extract_param_text({"examples": ["a", "b"]}, {})
        assert parts == ["a", "b"]

    def test_with_enum(self):
        parts = extract_param_text({"enum": ["x", "y"]}, {})
        assert parts == ["x", "y"]

    def test_with_ref(self):
        defs = {"Status": {"enum": ["on", "off"]}}
        parts = extract_param_text({"$ref": "#/$defs/Status"}, defs)
        assert parts == ["on", "off"]

    def test_with_all_fields(self):
        parts = extract_param_text({
            "title": "Query",
            "description": "Search term",
            "format": "string",
            "examples": ["test"],
            "enum": ["a", "b"],
        }, {})
        assert parts == ["Query", "Search term", "string", "test", "a", "b"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
