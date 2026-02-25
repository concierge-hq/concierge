"""Plan backend: exposes a single execute_plan tool for multi-step tool invocation."""

from __future__ import annotations

import json
from typing import Any, Annotated, get_type_hints, get_args, get_origin

from concierge.backends.base_provider import BaseProvider
from concierge.core.sharable import Sharable

REF_KEY = "output_by_reference"


def _is_ref(value: Any) -> bool:
    """A reference is a dict with an 'output_by_reference' key."""
    return isinstance(value, dict) and REF_KEY in value


def _parse_ref(ref: dict) -> tuple[str, list[str]]:
    """Extract (step_id, path) from an output_by_reference.

    The value of "output_by_reference" is a dict with one key:
      - key   = step id
      - value = path array (list of keys to traverse), or [] for entire output
    """
    payload = ref[REF_KEY]
    if not isinstance(payload, dict) or len(payload) != 1:
        raise ValueError(
            f"output_by_reference must be an object with exactly one key "
            f"(the step id), got: {payload}"
        )
    step_id = next(iter(payload))
    path_value = payload[step_id]
    if not isinstance(path_value, list):
        raise ValueError(
            f"output_by_reference path for step '{step_id}' must be an array, "
            f"got: {type(path_value).__name__}"
        )
    return step_id, [str(p) for p in path_value]


def _detect_sharable_params(tool) -> set[str]:
    """Detect which params have the Sharable() annotation on the original function."""
    fn = getattr(tool, "fn", None)
    if fn is None:
        return set()
    try:
        hints = get_type_hints(fn, include_extras=True)
    except Exception:
        return set()
    sharable = set()
    for name, hint in hints.items():
        if get_origin(hint) is Annotated:
            if any(isinstance(a, Sharable) for a in get_args(hint)):
                sharable.add(name)
    return sharable


def _build_tool_description(tool, sharable_params: set[str]) -> str:
    """Build a human-readable description of a tool for the execute_plan prompt."""
    schema = tool.parameters
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    params = []
    for pname, pdef in props.items():
        ptype = pdef.get("type", "any")
        tag = " [sharable]" if pname in sharable_params else ""
        opt = "" if pname in required else "?"
        params.append(f"{pname}{opt}: {ptype}{tag}")

    sig = f"  {tool.name}({', '.join(params)})"
    desc = f"    {tool.description}" if tool.description else ""
    output = ""
    if getattr(tool, "output_schema", None):
        output = (
            f"\n    returns: {json.dumps(tool.output_schema, separators=(',', ':'))}"
        )
    return f"{sig}\n{desc}{output}"


def _resolve_ref(ref: dict, results: dict[str, Any]) -> Any:
    """Resolve an output_by_reference from completed step results."""
    step_id, path = _parse_ref(ref)

    obj = results[step_id]
    for key in path:
        if isinstance(obj, list):
            try:
                obj = obj[int(key)]
            except (ValueError, IndexError) as e:
                raise ValueError(
                    f"Cannot resolve output_by_reference "
                    f"[{step_id}, {', '.join(repr(k) for k in path)}]: {e}"
                ) from e
        elif isinstance(obj, dict):
            if key not in obj:
                raise ValueError(
                    f"Cannot resolve output_by_reference: "
                    f"key '{key}' not found in step '{step_id}'"
                )
            obj = obj[key]
        else:
            raise ValueError(
                f"Cannot resolve output_by_reference: "
                f"cannot traverse into {type(obj).__name__} "
                f"at key '{key}' in step '{step_id}'"
            )
    return obj


def _resolve_args(
    args: dict[str, Any],
    results: dict[str, Any],
    sharable_params: set[str],
) -> dict[str, Any]:
    """Resolve all output_by_reference values in a step's args dict."""
    resolved = {}
    for key, value in args.items():
        if _is_ref(value):
            if key not in sharable_params:
                raise ValueError(
                    f"Parameter '{key}' is not sharable and cannot use references"
                )
            resolved[key] = _resolve_ref(value, results)
        else:
            resolved[key] = value
    return resolved


def _validate_references(steps: list[dict]) -> str | None:
    """Validate that all references point to earlier steps (no cycles, no self-refs, no dangling refs)."""
    seen: set[str] = set()
    for step in steps:
        sid = step["id"]
        for value in step.get("args", {}).values():
            if _is_ref(value):
                ref_id, _ = _parse_ref(value)
                if ref_id == sid:
                    return f"Step '{sid}' references itself"
                if ref_id not in seen:
                    return (
                        f"Step '{sid}' references step '{ref_id}' which "
                        f"either does not exist or comes later in the plan"
                    )
        seen.add(sid)
    return None


class PlanBackend(BaseProvider):
    def initialize(self, config):
        self._tools = []
        self._sharable_map: dict[str, set[str]] = {}

    def index_tools(self, tools):
        self._tools = list(tools)
        for tool in self._tools:
            self._sharable_map[tool.name] = _detect_sharable_params(tool)

    def serve_tools(self):
        tools_ref = self._tools
        sharable_map = self._sharable_map

        tool_descriptions = "\n\n".join(
            _build_tool_description(t, sharable_map.get(t.name, set()))
            for t in tools_ref
        )

        description = (
            "Execute a plan of one or more tool calls on this server.\n\n"
            'INPUT: A JSON object with a "steps" array. Each step has:\n'
            "  - id: unique name for this step (other steps can reference its output)\n"
            "  - tool: name of the tool to call\n"
            "  - args: arguments for the tool\n\n"
            "REFERENCING OUTPUTS:\n"
            "  The server holds the JSON output of every completed step. For parameters\n"
            "  marked [sharable], instead of a literal value you can pass a reference\n"
            '  object with an "output_by_reference" key. The value is an object where\n'
            "  the key is the step id and the value is the path (array of keys to traverse):\n\n"
            '    {"output_by_reference": {"step_id": []}}                  -> entire output\n'
            '    {"output_by_reference": {"step_id": ["field"]}}           -> output.field\n'
            '    {"output_by_reference": {"step_id": ["items", "0"]}}      -> output.items[0]\n'
            '    {"output_by_reference": {"step_id": ["a", "b", "c"]}}    -> output.a.b.c\n\n'
            "  Non-sharable parameters must always be literal values.\n"
            "  You can mix references and literals in the same step — use a reference\n"
            "  when you want to pass an earlier step's output directly, and a literal\n"
            "  when you want to provide your own value.\n\n"
            "EXECUTION:\n"
            "  Steps run sequentially in the order listed.\n"
            "  A step can reference any earlier step's output.\n"
            "  You do not need to solve everything in a single plan. If you are\n"
            "  unsure about something, execute a plan with the steps you are\n"
            "  confident about, inspect the outputs, and then issue follow-up\n"
            "  plans to continue. Each conversation turn can be a new plan that\n"
            "  builds on previous results to achieve the user's objective.\n\n"
            "EXAMPLE:\n"
            "  {\n"
            '    "steps": [\n'
            "      {\n"
            '        "id": "locs",\n'
            '        "tool": "search_locations",\n'
            '        "args": { "base_city": "Chicago" }\n'
            "      },\n"
            "      {\n"
            '        "id": "wx",\n'
            '        "tool": "get_weather",\n'
            '        "args": {\n'
            '          "lat": {"output_by_reference": {"locs": ["lat"]}},\n'
            '          "lon": {"output_by_reference": {"locs": ["lon"]}},\n'
            '          "start_date": "2025-06-21"\n'
            "        }\n"
            "      }\n"
            "    ]\n"
            "  }\n\n"
            "AVAILABLE TOOLS:\n\n" + tool_descriptions
        )

        execute_plan_params = {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["id", "tool", "args"],
                        "properties": {
                            "id": {"type": "string"},
                            "tool": {"type": "string"},
                            "args": {"type": "object", "additionalProperties": True},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["steps"],
        }

        async def execute_plan(steps: list[dict]) -> dict:
            tool_by_name = {t.name: t for t in tools_ref}
            step_ids: set[str] = set()

            for step in steps:
                sid = step.get("id")
                if not sid:
                    return {"error": "Every step must have an 'id'"}
                if sid in step_ids:
                    return {"error": f"Duplicate step id: '{sid}'"}
                step_ids.add(sid)

                tool_name = step.get("tool")
                if tool_name not in tool_by_name:
                    available = ", ".join(sorted(tool_by_name.keys()))
                    return {
                        "error": f"Unknown tool: '{tool_name}'. Available: {available}"
                    }

            ref_error = _validate_references(steps)
            if ref_error:
                return {"error": ref_error}

            results: dict[str, Any] = {}
            response: dict[str, Any] = {}

            for step in steps:
                sid = step["id"]
                tool = tool_by_name[step["tool"]]
                sharable = sharable_map.get(step["tool"], set())
                try:
                    resolved = _resolve_args(step.get("args", {}), results, sharable)
                    result = await tool.run(resolved)
                    results[sid] = result
                    response[sid] = {"status": "ok", "result": result}
                except Exception as e:
                    response[sid] = {"status": "error", "error": str(e)}
                    break

            has_errors = any(e["status"] != "ok" for e in response.values())
            return {
                "status": "partial" if has_errors else "completed",
                "steps": response,
            }

        class PlanExecutionTool:
            def __init__(self, name, tool_description, parameters, func):
                self.name = name
                self.title = "Plan Execution"
                self.description = tool_description
                self.parameters = parameters
                self.output_schema = None
                self.annotations = {}
                self.meta = {}
                self.icons = None
                self._func = func

            async def run(self, arguments, **kwargs):
                return await self._func(**arguments)

        return [
            PlanExecutionTool(
                name="execute_plan",
                tool_description=description,
                parameters=execute_plan_params,
                func=execute_plan,
            ),
        ]
