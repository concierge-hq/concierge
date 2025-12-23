import numpy as np
from typing import Annotated
from pydantic import Field
from sentence_transformers import SentenceTransformer
from mcp.types import Tool as MCPTool
from openmcp.backends.base_provider import BaseProvider


def to_mcp_tool(tool) -> dict:
    return MCPTool(
        name=tool.name,
        title=tool.title,
        description=tool.description,
        inputSchema=tool.parameters,
        outputSchema=tool.output_schema,
        annotations=tool.annotations,
        icons=tool.icons,
        _meta=tool.meta,
    ).model_dump(exclude_none=True)

DEFAULT_MODEL = SentenceTransformer("BAAI/bge-large-en-v1.5")

TEXT_FIELDS = ("title", "description", "format")
LIST_FIELDS = ("examples", "enum")


def extract_param_text(param_def: dict, defs: dict) -> list[str]:
    parts = []

    for field in TEXT_FIELDS:
        if field in param_def:
            parts.append(str(param_def[field]))

    for field in LIST_FIELDS:
        if field in param_def:
            parts.extend(str(v) for v in param_def[field])

    if "$ref" in param_def:
        ref_name = param_def["$ref"].split("/")[-1]
        ref_def = defs.get(ref_name, {})
        if "enum" in ref_def:
            parts.extend(str(v) for v in ref_def["enum"])

    return parts


def build_search_text(tool) -> str:
    parts = [
        tool.name,
        tool.name.replace("_", " "),
        tool.description or "",
    ]

    schema = tool.parameters
    defs = schema.get("$defs", {})

    for param_name, param_def in schema.get("properties", {}).items():
        parts.append(param_name)
        parts.append(param_name.replace("_", " "))
        parts.extend(extract_param_text(param_def, defs))

    return " ".join(parts)


class SearchBackend(BaseProvider):

    def initialize(self, config):
        self._max_results = config.max_results
        self._tools = []
        self._embeddings = None
        self._model = config.model or DEFAULT_MODEL

    def index_tools(self, tools):
        self._tools = list(tools)
        texts = [build_search_text(t) for t in self._tools]
        self._embeddings = self._model.encode(texts, normalize_embeddings=True)

    def serve_tools(self):
        max_k = self._max_results
        tools_ref = self._tools

        async def search_tools(
            query: Annotated[str, Field(
                description="Natural language description of what you want to do. Returns relevant tools you can call with call_tool.",
                examples=["find user by email", "process payment refund", "lookup order status"]
            )],
        ):
            results = self._search(query, max_k)
            return [to_mcp_tool(t) for t in results]

        async def call_tool(
            tool_name: Annotated[str, Field(
                description="Exact name of the tool to execute, as returned by search_tools.",
                examples=["search_users", "get_payment_errors"]
            )],
            arguments: Annotated[dict, Field(
                description="Arguments to pass to the tool, matching the inputSchema from search_tools.",
                examples=[{"query": "john@example.com"}, {"user_id": 123}]
            )],
        ):
            tool = next((t for t in tools_ref if t.name == tool_name), None)
            if not tool:
                return {"error": f"Tool '{tool_name}' not found."}
            return await tool.run(arguments)

        return [search_tools, call_tool]

    def _search(self, query: str, top_k: int):

        query_embedding = self._model.encode(query, normalize_embeddings=True)
        similarities = self._embeddings @ query_embedding
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [self._tools[i] for i in top_indices]
