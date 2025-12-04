from typing import Any, Dict, List, Optional
from openai import OpenAI
from .base import LLMProvider

class OpenAIProvider(LLMProvider):
    def __init__(self, api_base: str, api_key: str, model: str = "gpt-5"):
        self.client = OpenAI(base_url=api_base, api_key=api_key)
        self.model = model

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self.client.chat.completions.create(**kwargs)

    def convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # OpenAI expects tools in the format: {"type": "function", "function": {...}}
        # Assuming input tools are already in or close to this format, or need wrapping.
        # Based on client_tool_calling.py, it seems we might receive Concierge tools and need to convert them.
        # Let's reuse the logic from client_tool_calling.py if possible, or reimplement it here.

        openai_tools = []
        for tool in tools:
            # Check if it's already in OpenAI format
            if "type" in tool and tool["type"] == "function":
                openai_tools.append(tool)
            else:
                # Convert from Concierge format
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"]
                    }
                })
        return openai_tools

    def parse_response(self, response: Any) -> Dict[str, Any]:
        message = response.choices[0].message
        result = {
            "content": message.content,
            "tool_calls": []
        }

        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]

        return result
