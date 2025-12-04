from typing import Any, Dict, List, Optional
import json
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from .base import LLMProvider

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        if Anthropic is None:
            raise ImportError("anthropic package is required for AnthropicProvider")
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Any:
        # Convert OpenAI-style messages to Anthropic format if necessary
        # Anthropic expects 'user' and 'assistant' roles. 'system' message is a separate parameter.

        system_prompt = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg["role"] == "tool":
                # Anthropic tool results
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": msg["content"]
                        }
                    ]
                })
            elif "tool_calls" in msg and msg["tool_calls"]:
                 # Assistant message with tool calls
                content = []
                if msg["content"]:
                    content.append({"type": "text", "text": msg["content"]})

                for tc in msg["tool_calls"]:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"])
                    })
                anthropic_messages.append({"role": "assistant", "content": content})
            else:
                anthropic_messages.append(msg)

        kwargs = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if tools:
            kwargs["tools"] = tools

        return self.client.messages.create(**kwargs)

    def convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        anthropic_tools = []
        for tool in tools:
             # Check if it's already in OpenAI format (which we might receive) and convert to Anthropic
            if "type" in tool and tool["type"] == "function":
                 func = tool["function"]
                 anthropic_tools.append({
                    "name": func["name"],
                    "description": func["description"],
                    "input_schema": func["parameters"]
                })
            else:
                # Assume Concierge format which is close to Anthropic's
                anthropic_tools.append({
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["input_schema"]
                })
        return anthropic_tools

    def parse_response(self, response: Any) -> Dict[str, Any]:
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input)
                    }
                })

        return {
            "content": content,
            "tool_calls": tool_calls
        }
