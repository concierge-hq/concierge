import asyncio
import contextlib
import io
import textwrap
import types as pytypes

import mcp.types as mcp_types

from concierge.backends.base_provider import BaseProvider

_PRIMITIVE_TYPE_MAP = {
    "string": "str",
    "number": "float",
    "integer": "int",
    "boolean": "bool",
    "null": "None",
}


def _schema_to_python_type(schema):
    if not schema or not isinstance(schema, dict):
        return "Any"

    t = schema.get("type")

    if t == "object":
        return "dict"

    if t == "array":
        return f"list[{_schema_to_python_type(schema.get('items'))}]"

    if isinstance(t, list):
        mapped = [_PRIMITIVE_TYPE_MAP.get(x, "Any") for x in t if x != "null"]
        has_null = "null" in t
        if not mapped:
            return "None" if has_null else "Any"
        base = " | ".join(mapped) if len(mapped) > 1 else mapped[0]
        return f"{base} | None" if has_null else base

    if "anyOf" in schema or "oneOf" in schema:
        variants = schema.get("anyOf") or schema.get("oneOf", [])
        mapped = [_schema_to_python_type(v) for v in variants if v.get("type") != "null"]
        has_null = any(v.get("type") == "null" for v in variants)
        if not mapped:
            return "None" if has_null else "Any"
        base = " | ".join(mapped) if len(mapped) > 1 else mapped[0]
        return f"{base} | None" if has_null else base

    return _PRIMITIVE_TYPE_MAP.get(t, "Any")


def _describe_schema(schema, depth=0):
    if not schema or not isinstance(schema, dict):
        return ""
    t = schema.get("type")
    pad = "            " + "    " * depth
    if t == "object" and schema.get("properties"):
        required = set(schema.get("required") or [])
        lines = []
        for k, v in schema["properties"].items():
            opt = "" if k in required else " (optional)"
            desc = v.get("description", "")
            s = f"{pad}{k}: {_schema_to_python_type(v)}{opt}"
            if desc:
                s += f" — {desc}"
            lines.append(s)
            sub = _describe_schema(v, depth + 1)
            if sub:
                lines.append(sub)
        return "\n".join(lines)
    if t == "array" and schema.get("items", {}).get("type") == "object":
        return _describe_schema(schema["items"], depth)
    return ""


def _build_stub(tool):
    schema = tool.parameters or {}
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    params = []
    for name, prop in properties.items():
        type_str = _schema_to_python_type(prop)
        params.append(f"{name}: {type_str}" if name in required else f"{name}: {type_str} = None")

    req = [p for p in params if "= None" not in p]
    opt = [p for p in params if "= None" in p]
    all_params = req + opt

    sig = f"async def {tool.name}(*, {', '.join(all_params)})" if all_params else f"async def {tool.name}()"
    sig += " -> dict:"

    doc_lines = []
    if tool.description:
        doc_lines.append(tool.description)

    param_descs = []
    for name, prop in properties.items():
        desc = prop.get("description", "")
        schema_desc = _describe_schema(prop, depth=3)
        if desc and schema_desc:
            param_descs.append(f"        {name}: {desc}\n{schema_desc}")
        elif desc:
            param_descs.append(f"        {name}: {desc}")
        elif schema_desc:
            param_descs.append(f"        {name}:\n{schema_desc}")

    if param_descs:
        doc_lines.append("")
        doc_lines.append("    Args:")
        doc_lines.extend(param_descs)

    if doc_lines:
        docstring = '    """' + doc_lines[0] + "\n"
        for line in doc_lines[1:]:
            docstring += line + "\n" if line else "\n"
        docstring += '    """'
        return f"{sig}\n{docstring}"

    return sig


EXECUTE_CODE_DESCRIPTION = (
    "Execute Python code in a sandboxed environment with access to MCP tool APIs. "
    "Code runs inside an async function — use `await` for tool calls, `print()` for output. "
    "1. DISCOVER: `runtime.list_tools()`, `runtime.get_tool_info(name)`, `runtime.search_tools(query)`. "
    "2. CALL: `await tools.<tool_name>(param=value)` — tools are available on the `tools` module. "
    "Run `print(runtime.list_tools())` to see available tools."
)

RESOURCE_URI = "resource://concierge/code-backend/capabilities"

CAPABILITY_RESOURCE_TEXT = """\
# Code Execution Sandbox

Execute Python code via `execute_code`. Code runs inside an async function.
Use `await` for all tool calls. Use `print()` to return output.

## Discovery Helpers

All discovery helpers are available on the `runtime` module.

```python
# List all available tool names
print(runtime.list_tools())

# Get full schema and typed stub for a specific tool
print(runtime.get_tool_info("tool_name"))

# Search tools by keyword in name/description
print(runtime.search_tools("query"))
```

## Calling Tools

Tools are available on the `tools` module. Use keyword arguments.

```python
result = await tools.tool_name(param="value")
print(result)
```

## Composing Multiple Tools

```python
items = await tools.list_items(query="search term")
for item in items.get("items", []):
    detail = await tools.get_item(id=item["id"])
    print(detail)
```
"""


class CodeBackend(BaseProvider):

    def initialize(self, config):
        self._config = config
        self._tools = []
        self._tool_index = {}
        self._tools_module = None
        self._runtime_module = None

    def index_tools(self, tools):
        self._tools = list(tools)
        self._tool_index = {}
        for tool in self._tools:
            self._tool_index[tool.name] = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "stub": _build_stub(tool),
            }
        self._tools_module = self._build_tools_module()
        self._runtime_module = self._build_runtime_module()

    def _build_tools_module(self):
        tool_map = {t.name: t for t in self._tools}

        async def call_tool(tool_name, arguments):
            tool = tool_map.get(tool_name)
            if not tool:
                raise ValueError(f"Unknown tool: {tool_name}")
            return await tool.run(arguments)

        module = pytypes.ModuleType("tools")

        for tool in self._tools:
            def _make_stub(t):
                async def stub(**kwargs):
                    return await call_tool(t.name, kwargs)
                stub.__name__ = t.name
                stub.__doc__ = t.description
                return stub
            setattr(module, tool.name, _make_stub(tool))

        return module

    def _build_runtime_module(self):
        tool_index = self._tool_index

        module = pytypes.ModuleType("runtime")

        def list_tools():
            return list(tool_index.keys())

        def get_tool_info(name):
            info = tool_index.get(name)
            if not info:
                return f"Tool '{name}' not found. Use runtime.list_tools() to see available tools."
            return {
                "name": info["name"],
                "description": info["description"],
                "parameters": info["parameters"],
                "stub": info["stub"],
            }

        def search_tools(query):
            query_lower = query.lower()
            results = []
            for info in tool_index.values():
                text = f"{info['name']} {info['description'] or ''}".lower()
                if query_lower in text:
                    results.append({"name": info["name"], "description": info["description"]})
            return results

        module.list_tools = list_tools
        module.get_tool_info = get_tool_info
        module.search_tools = search_tools

        return module

    def serve_tools(self):

        class SyntheticTool:
            def __init__(self, name, description, parameters, func):
                self.name = name
                self.title = name.replace("_", " ")
                self.description = description
                self.parameters = parameters
                self.output_schema = None
                self.annotations = {}
                self.meta = {}
                self.icons = None
                self._func = func

            async def run(self, arguments, **kwargs):
                """Run the tool. Accepts context/convert_result from MCP SDK and ignores them."""
                return await self._func(**arguments)

        async def execute_code(code: str, timeout: int = 30):
            return await self._execute_code(code, timeout)

        return [
            SyntheticTool(
                name="execute_code",
                description=EXECUTE_CODE_DESCRIPTION,
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute. Use `await` for tool calls, `print()` for output.",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Maximum execution time in seconds. Defaults to 30.",
                            "default": 30,
                        },
                    },
                    "required": ["code"],
                },
                func=execute_code,
            ),
        ]

    def serve_resources(self):
        resource = mcp_types.Resource(
            uri=RESOURCE_URI,
            name="code-backend-capabilities",
            title="Code Execution Sandbox Helpers",
            description="Sandbox usage guide and discovery helper reference.",
            mimeType="text/markdown",
        )

        read_result = mcp_types.ServerResult(
            mcp_types.ReadResourceResult(
                contents=[
                    mcp_types.TextResourceContents(
                        uri=RESOURCE_URI,
                        mimeType="text/markdown",
                        text=CAPABILITY_RESOURCE_TEXT,
                    )
                ]
            )
        )

        return [(resource, read_result)]

    async def _execute_code(self, code: str, timeout: int = 30) -> dict:
        _safe_builtins = {k: v for k, v in __builtins__.items() if k not in (
            "__import__", "exec", "eval", "compile", "open",
            "breakpoint", "exit", "quit", "globals", "locals",
            "getattr", "setattr", "delattr", "vars", "dir",
            "memoryview", "type", "__build_class__",
        )} if isinstance(__builtins__, dict) else {k: getattr(__builtins__, k) for k in (
            "print", "len", "range", "enumerate", "zip", "map", "filter",
            "sorted", "reversed", "list", "dict", "set", "tuple", "str",
            "int", "float", "bool", "bytes", "bytearray",
            "min", "max", "sum", "abs", "round", "pow", "divmod",
            "any", "all", "isinstance", "issubclass", "hasattr",
            "repr", "format", "hash", "id", "callable",
            "iter", "next", "slice", "frozenset", "complex",
            "chr", "ord", "hex", "oct", "bin",
            "ValueError", "TypeError", "KeyError", "IndexError",
            "AttributeError", "RuntimeError", "StopIteration",
            "Exception", "BaseException", "True", "False", "None",
        ) if hasattr(__builtins__, k)}
        namespace = {"__builtins__": _safe_builtins}

        # Inject modules — user code calls tools.X(), runtime.Y()
        # No real tool implementations are exposed in the namespace.
        # tools module contains stubs that dispatch through call_tool.
        namespace["tools"] = self._tools_module
        namespace["runtime"] = self._runtime_module


        indented = textwrap.indent(code, "    ")
        wrapped = f"async def __user_main__():\n{indented}\n"

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            compiled = compile(wrapped, "<user_code>", "exec")
            exec(compiled, namespace)

            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                await asyncio.wait_for(
                    namespace["__user_main__"](),
                    timeout=timeout,
                )

            return {
                "stdout": stdout_capture.getvalue(),
                "stderr": stderr_capture.getvalue(),
                "exit_code": 0,
            }
        except asyncio.TimeoutError:
            return {
                "stdout": stdout_capture.getvalue(),
                "stderr": "Execution timed out",
                "exit_code": 1,
            }
        except Exception as e:
            return {
                "stdout": stdout_capture.getvalue(),
                "stderr": f"{type(e).__name__}: {e}",
                "exit_code": 1,
            }
