from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        """
        Send a chat request to the provider.

        Args:
            messages: List of message dictionaries (role, content).
            tools: Optional list of tools in the provider's format (or generic format to be converted).

        Returns:
            The raw response object from the provider.
        """
        pass

    @abstractmethod
    def convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert generic tools to the provider-specific format.

        Args:
            tools: List of generic tool definitions.

        Returns:
            List of tools in the provider's format.
        """
        pass

    @abstractmethod
    def parse_response(self, response: Any) -> Dict[str, Any]:
        """
        Parse the provider's response into a standard format.

        Args:
            response: The raw response from the provider.

        Returns:
            A dictionary containing:
            - content: The text content of the response.
            - tool_calls: A list of tool calls (if any).
        """
        pass
