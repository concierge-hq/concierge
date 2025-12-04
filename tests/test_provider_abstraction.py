import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Mock openai and requests before importing modules that use them
sys.modules["openai"] = MagicMock()
sys.modules["requests"] = MagicMock()
sys.modules["yaml"] = MagicMock()

# Mock pydantic with a real class for BaseModel so issubclass works
class MockBaseModel:
    pass
mock_pydantic = MagicMock()
mock_pydantic.BaseModel = MockBaseModel
sys.modules["pydantic"] = mock_pydantic
sys.modules["pydantic_core"] = MagicMock()

# Mock concierge package to avoid importing dependencies
mock_concierge = MagicMock()
mock_config = MagicMock()
mock_config.SERVER_HOST = "localhost"
mock_config.SERVER_PORT = 8080
mock_concierge.config = mock_config
sys.modules["concierge"] = mock_concierge
sys.modules["concierge.config"] = mock_config

from concierge_clients.providers.factory import get_provider
from concierge_clients.providers.openai_provider import OpenAIProvider
from concierge_clients.providers.anthropic_provider import AnthropicProvider
from concierge_clients.client_tool_calling import ToolCallingClient

def test_factory():
    openai_provider = get_provider("openai", api_base="http://test", api_key="test")
    assert isinstance(openai_provider, OpenAIProvider)

    # Mock Anthropic import for test environment where it might not be installed
    with patch("concierge_clients.providers.anthropic_provider.Anthropic") as mock_anthropic:
        anthropic_provider = get_provider("anthropic", api_key="test")
        assert isinstance(anthropic_provider, AnthropicProvider)

def test_client_initialization():
    # Test OpenAI initialization
    client_openai = ToolCallingClient(api_base="http://test", api_key="test", provider_name="openai")
    assert isinstance(client_openai.llm_provider, OpenAIProvider)

    # Test Anthropic initialization
    with patch("concierge_clients.providers.anthropic_provider.Anthropic") as mock_anthropic:
        client_anthropic = ToolCallingClient(api_base="http://test", api_key="test", provider_name="anthropic")
        assert isinstance(client_anthropic.llm_provider, AnthropicProvider)

def test_openai_provider_conversion():
    provider = OpenAIProvider(api_base="http://test", api_key="test")
    tools = [{"name": "test_tool", "description": "test", "input_schema": {"type": "object"}}]
    converted = provider.convert_tools(tools)
    assert converted[0]["type"] == "function"
    assert converted[0]["function"]["name"] == "test_tool"

def test_anthropic_provider_conversion():
    with patch("concierge_clients.providers.anthropic_provider.Anthropic") as mock_anthropic:
        provider = AnthropicProvider(api_key="test")
        tools = [{"name": "test_tool", "description": "test", "input_schema": {"type": "object"}}]
        converted = provider.convert_tools(tools)
        assert converted[0]["name"] == "test_tool"
        assert "input_schema" in converted[0]

if __name__ == "__main__":
    test_factory()
    test_client_initialization()
    test_openai_provider_conversion()
    test_anthropic_provider_conversion()
    print("All tests passed!")
