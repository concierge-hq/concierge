# Concierge SDK — Skills Reference

Please read this file for complete reference for building next gen MCP servers with Concierge.

## Install & Scaffold

```bash
pip install concierge-sdk
concierge init my-project
cd my-project
python main.py
```

## Minimal Setup

  transport_security=_no_dns — Disable DNS rebinding protection. Required when deploying behind a reverse proxy (e.g. concierge deploy, Kubernetes, Docker).
   The MCP SDK validates the HTTP Host header against the bind address; behind a proxy, the Host header is the proxy's address, not 127.0.0.1, so validation
   fails with HTTP 421.host="0.0.0.0" is a separate concern:
  it binds the server to all network interfaces so the reverse proxy can reach it over TCP. Without it, the server only accepts connections from 127.0.0.1
  and the proxy's connection is refused. Both are needed for any deployed/proxied environment; neither is needed for local-only dev.
```python
import os
from concierge import Concierge
from mcp.server.transport_security import TransportSecuritySettings

_no_dns = TransportSecuritySettings(enable_dns_rebinding_protection=False)
```

Two modes of operation:

```python
# Stateless — independent tools, no shared state between calls: The stateless mode does not support upstream servers, and does not support using Concierge provided state and does not support tool dependency for multi turn conversations.
app = Concierge("my-server", stateless_http=True, host="0.0.0.0", transport_security=_no_dns)

# Stateful — tools share state via get_state/set_state, required for staged workflows: The stateful nature support tool dependency and shared state in multi-turn conversations. With session id, the server "remembers" past tool changes, and state updates by tools in previous turns of the conversation. Much more powerful but certain clients dont support this. Fallback to stateless if you see client seeing issues when connecting to server.
app = Concierge("my-server", host="0.0.0.0", transport_security=_no_dns)
```

`host="0.0.0.0"` and `transport_security=_no_dns` are required for deployed environments. Without them, DNS rebinding protection blocks requests behind reverse proxies. Ensure these are set when using Concierge deploy

## Wrapping an Existing MCP Server

```python
from mcp.server.fastmcp import FastMCP
from concierge import Concierge

existing = FastMCP("my-server")
app = Concierge(existing)
# All existing @existing.tool() decorators continue to work.
# Optionally add app.stages and app.transitions.
```

## Tools

```python
@app.tool()
async def search(query: str, limit: int = 10) -> dict:
    """Search items by query"""  # docstring becomes the MCP tool description
    return {"results": [...], "query": query}
```

- Type hints on all parameters (required).
- Docstring on every tool (becomes the description agents see).
- Return a dict — this becomes the tool's structured output.

## State

Per-session key-value storage. Only available in stateful mode (no `stateless_http=True`).

```python
@app.tool()
def add_to_cart(product_id: str) -> dict:
    """Add product to cart"""
    cart = app.get_state("cart", [])
    cart.append(product_id)
    app.set_state("cart", cart)
    return {"cart": cart}
```

State persists across stage transitions within a session. Cleared on `terminate_session()`.

**Backends:**
- **In-memory** (default) — single-process, no persistence
- **Postgres** — distributed, persistent: not NON Concierge deployments, the server needs to provide `CONCIERGE_STATE_URL=postgresql://user:pass@host/db`

## Provider Modes

Modes control how tools are exposed to the AI agent. Four modes, each a different trade-off.

### Plain (default)

All tools exposed directly — no wrapping. Agent sees every tool and calls them by name.

```python
app = Concierge("my-server", stateless_http=True, host="0.0.0.0", transport_security=_no_dns)
```

Use for: small APIs (<20 tools), any app where all tools are relevant at once.

### Search

Two meta-tools: `search_tools(query)` and `call_tool(tool_name, arguments)`. Agent discovers tools via semantic search, then calls them by name.

```python
from concierge import Concierge, Config, ProviderType

app = Concierge(
    "my-server",
    config=Config(provider_type=ProviderType.SEARCH, max_results=5),
    stateless_http=True, host="0.0.0.0", transport_security=_no_dns,
)
```

Uses `sentence-transformers` for embeddings (`BAAI/bge-large-en-v1.5` by default). Requires `sentence-transformers` in requirements.txt.

Config: `max_results` (default 5), `model` (custom SentenceTransformer instance).

Use for: large APIs with 100+ generic tools where the agent shouldn't see everything at once, broad/unpredictable use cases.

### Plan

One meta-tool: `execute_plan(steps)`. Agent submits a JSON plan — sequential steps that reference each other's outputs.

```python
from concierge import Concierge, Config, ProviderType

app = Concierge(
    "my-server",
    config=Config(provider_type=ProviderType.PLAN),
    stateless_http=True, host="0.0.0.0", transport_security=_no_dns,
)
```

Steps pass data forward using `output_by_reference`. Only parameters annotated with `Sharable()` accept references:

```python
from typing import Annotated
from concierge.core.sharable import Sharable

@app.tool()
def create_backup(database: str) -> dict:
    """Create a database backup"""
    return {"backup_id": "bk-123"}

@app.tool()
def validate_backup(backup_id: Annotated[str, Sharable()]) -> dict:
    """Validate a backup"""
    return {"valid": True}
```

What the agent sends:
```json
{
  "steps": [
    {"id": "backup", "tool": "create_backup", "args": {"database": "prod"}},
    {"id": "validate", "tool": "validate_backup", "args": {
      "backup_id": {"output_by_reference": {"backup": ["backup_id"]}}
    }}
  ]
}
```

The reference `{"output_by_reference": {"backup": ["backup_id"]}}` resolves to `results["backup"]["backup_id"]`. Only backward references — no cycles, no self-references.

Use for: multi-step workflows with explicit data dependencies between tools.

### Code

One meta-tool: `execute_code(code, timeout)`. Agent writes async Python that calls tools directly.

```python
from concierge import Concierge, Config, ProviderType

app = Concierge(
    "my-server",
    config=Config(provider_type=ProviderType.CODE),
    stateless_http=True, host="0.0.0.0", transport_security=_no_dns,
)
```

Two modules injected into the sandbox:
- `tools` — every registered tool as an async callable
- `runtime` — discovery: `list_tools()`, `get_tool_info(name)`, `search_tools(query)`

What the agent writes:
```python
# Discovery
print(runtime.list_tools())
print(runtime.get_tool_info("create_backup"))
print(runtime.search_tools("backup"))

# Call tools — output of one feeds into another
backup = await tools.create_backup(database="prod")
result = await tools.validate_backup(backup_id=backup["backup_id"])
print(result)
```

Sandbox restricts imports, `eval`, `exec`, `open`, and other unsafe builtins. Default timeout: 30 seconds.

Use for: 200+ tools, complex scenarios where output of one tool feeds into another, iteration, conditionals, branching logic.

### Decision Guide — Which Mode to Use

| Scenario | Mode | Why |
|----------|------|-----|
| <20 tools, all relevant at once | **Plain** | Simple, direct, no overhead |
| 100+ generic tools, broad/unpredictable use cases | **Search** | Agent discovers what it needs via semantic search |
| Strict ordered workflow, predictable steps | **Staged Workflows** + Plain | Progressive disclosure controls the flow |
| Multi-step with explicit data dependencies | **Plan** | Steps reference each other's outputs cleanly |
| 200+ tools, output-to-input chaining, complex logic | **Code** | Agent writes Python with full control flow |

**Default to Plain.** Only reach for other modes when the use case clearly demands it:
- If you have too many tools for the agent to reason about → Search
- If there's a strict order that must be enforced and the steps are predictable → Stages
- If tools need to pipe data between each other in a defined sequence → Plan
- If the agent needs iteration, conditionals, or complex orchestration → Code

## Staged Workflows (Progressive Disclosure)

Stages control which tools the agent sees at each step. This is **not a mode** — it's orthogonal and works with any provider mode. Use when there is a strict order of operations and the use cases can be fuzzily predicted beforehand. Do not use for generic usecases.

### Defining Stages

Map stage names to tool lists. First stage defined is the starting stage:

```python
app.stages = {
    "browse": ["search_products", "view_product"],
    "cart": ["add_to_cart", "remove_from_cart", "view_cart"],
    "checkout": ["apply_coupon", "complete_purchase"],
}
```

### Defining Transitions

Map each stage to its allowed next stages. Empty list = terminal stage:

```python
app.transitions = {
    "browse": ["cart"],
    "cart": ["browse", "checkout"],
    "checkout": [],  # terminal
}
```

### Auto-Generated Tools

When stages are defined, Concierge automatically adds:
- **`proceed_to_next_stage(target_stage)`** — moves to a new stage. Only accepts stages in current stage's transitions. Triggers a tool list refresh so the agent sees new tools.
- **`terminate_session()`** — clears all session state, resets to initial stage.

### Session Flow

```
Session starts → agent sees "browse" tools + proceed_to_next_stage
  → agent calls search_products, view_product
  → agent calls proceed_to_next_stage("cart")
  → tool list refreshes → agent now sees "cart" tools
  → agent calls add_to_cart
  → agent calls proceed_to_next_stage("checkout")
  → agent calls complete_purchase
  → agent calls terminate_session → session resets
```

### Workflow Instructions

Concierge auto-injects instructions telling the agent to follow the workflow, not skip stages, and only ask the user when specific input is needed. You can override:

```python
app = Concierge("my-server", workflow_instructions="Custom instructions here", ...)
```

### Combining Stages with Provider Modes

Stages wrap whatever the provider mode exposes. With Plan mode, the agent sees `execute_plan` but can only reference tools in the current stage:

```python
from concierge import Concierge, Config, ProviderType

app = Concierge(
    "my-server",
    config=Config(provider_type=ProviderType.PLAN),
    host="0.0.0.0", transport_security=_no_dns,
)

app.stages = {"browse": ["search"], "checkout": ["pay"]}
app.transitions = {"browse": ["checkout"], "checkout": []}
```

**IMPORTANT:** Staged workflows require stateful mode (no `stateless_http=True`). The current stage is tracked in session state.

### Complete Staged Example

```python
from concierge import Concierge
from mcp.server.transport_security import TransportSecuritySettings

_no_dns = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = Concierge("shopping", host="0.0.0.0", transport_security=_no_dns)

@app.tool()
def search_products(query: str) -> dict:
    """Search the product catalog"""
    return {"products": [{"id": "p1", "name": "Laptop", "price": 999}]}

@app.tool()
def add_to_cart(product_id: str) -> dict:
    """Add a product to the cart"""
    cart = app.get_state("cart", [])
    cart.append(product_id)
    app.set_state("cart", cart)
    return {"cart": cart}

@app.tool()
def checkout(payment_method: str) -> dict:
    """Complete the purchase"""
    cart = app.get_state("cart", [])
    return {"order_id": "ORD-123", "items": len(cart), "status": "confirmed"}

app.stages = {
    "browse": ["search_products"],
    "cart": ["add_to_cart"],
    "checkout": ["checkout"],
}

app.transitions = {
    "browse": ["cart"],
    "cart": ["browse", "checkout"],
    "checkout": [],
}
```

## Widgets

Widgets render rich UI in ChatGPT via the `text/html+skybridge` MIME type. Four modes (mutually exclusive):

### Mode 1 — Dynamic HTML (preferred, no build step)

Best for most widgets. A lambda/function generates HTML from the tool's return dict:

```python
@app.widget(
    uri="ui://widget/results",
    html_fn=lambda args: f'''
    <div style="font-family:sans-serif;padding:20px">
        <h2>{args.get("title","")}</h2>
        <p>{args.get("message","")}</p>
    </div>''',
    title="Show Results",
    invoking="Loading...",
    invoked="Done",
)
async def show_results(title: str, message: str) -> dict:
    """Display results in a card"""
    return {"title": title, "message": message}
```

`html_fn` receives the dict returned by the tool function. Return an HTML string.

### Mode 2 — Inline HTML

Static HTML string, doesn't depend on tool output:

```python
@app.widget(
    uri="ui://widget/info",
    html='<div style="padding:20px"><h1>Welcome</h1></div>',
    title="Info Card",
)
async def info() -> dict:
    """Show info card"""
    return {"shown": True}
```

### Mode 3 — Entrypoint (React/JS, for complex interactive UIs)

For widgets that need interactivity, state management, or complex rendering:

```python
@app.widget(
    uri="ui://widget/pizza-map",
    entrypoint="pizzaz.html",
    title="Show Pizza Map",
    invoking="Hand-tossing a map",
    invoked="Served a fresh map",
)
async def pizza_map(pizzaTopping: str) -> dict:
    """Show a map of pizza spots for a given topping"""
    return {"pizzaTopping": pizzaTopping}
```

Requires files:
- `assets/entrypoints/pizzaz.html` — HTML entry point
- `assets/src/pizzaz/index.jsx` — React component

On startup, Concierge runs `npm run build` in the `assets/` directory to compile widgets.

### Mode 4 — External URL

Wraps an external URL in an iframe:

```python
@app.widget(
    uri="ui://widget/external",
    url="https://example.com/dashboard",
    title="External Dashboard",
)
async def external_dash(query: str) -> dict:
    """Show external dashboard"""
    return {"query": query}
```

### Widget Decorator Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `uri` | str | required | Unique resource URI (e.g. `ui://widget/name`) |
| `html` | str | None | Mode 2: inline HTML string |
| `url` | str | None | Mode 4: external URL for iframe |
| `entrypoint` | str | None | Mode 3: filename in `assets/entrypoints/` |
| `html_fn` | callable | None | Mode 1: function `(args: dict) -> str` |
| `name` | str | function name | Tool name |
| `title` | str | None | Display title in ChatGPT |
| `description` | str | docstring | Tool description |
| `invoking` | str | "Loading..." | Text shown while tool is running |
| `invoked` | str | "Done" | Text shown when tool completes |
| `annotations` | dict | `{readOnlyHint: True, ...}` | MCP tool annotations |

### Widget Runtime — `window.openai` Globals

ChatGPT injects these globals into widget iframes:

| Global | Type | Description |
|--------|------|-------------|
| `toolOutput` | object | Dict returned by your tool function |
| `toolInput` | object | Args passed to the tool by the agent |
| `theme` | string | `"light"` or `"dark"` |
| `displayMode` | string | `"pip"`, `"inline"`, or `"fullscreen"` |
| `maxHeight` | number | Available pixel height for the widget |
| `callTool(name, args)` | function | Call another MCP tool from within the widget |
| `setWidgetState(state)` | function | Persist widget UI state across invocations |

**Data flow:** tool returns dict → `structuredContent` → `window.openai.toolOutput` → widget reads it.

In React entrypoints, use `useOpenAiGlobal("toolOutput")` to access the data reactively.

In `html_fn` widgets, the HTML is generated server-side from the return dict — no client-side JS needed.

## Server Boilerplate

Always include this at the bottom of `main.py`:

```python
http_app = app.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware
    http_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )
    uvicorn.run(http_app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

For stdio transport (CLI clients):
```python
app.run()
```

## requirements.txt

Always include:
```
concierge-sdk
uvicorn
```

Add `sentence-transformers` if using Search mode.

## Deployment

```bash
concierge deploy
```

Deploys to Concierge cloud. The server runs on port 8000 (read from `PORT` env var). The MCP endpoint is available at `https://getconcierge.app/mcp-servers/{project-id}/mcp`.

## Complete Examples

### Simple Stateless API (Plain mode)

```python
import os
from concierge import Concierge
from mcp.server.transport_security import TransportSecuritySettings

_no_dns = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = Concierge("calculator", stateless_http=True, host="0.0.0.0", transport_security=_no_dns)

@app.tool()
async def add(a: float, b: float) -> dict:
    """Add two numbers"""
    return {"result": a + b}

@app.tool()
async def multiply(a: float, b: float) -> dict:
    """Multiply two numbers"""
    return {"result": a * b}

http_app = app.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware
    http_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["mcp-session-id"])
    uvicorn.run(http_app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

### Widget App with Dynamic HTML

```python
import os
from concierge import Concierge
from mcp.server.transport_security import TransportSecuritySettings

_no_dns = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = Concierge("weather", stateless_http=True, host="0.0.0.0", transport_security=_no_dns)

@app.tool()
async def get_weather(city: str) -> dict:
    """Get current weather for a city"""
    return {"city": city, "temp": 72, "condition": "Sunny"}

@app.widget(
    uri="ui://widget/weather-card",
    html_fn=lambda args: f'''
    <div style="font-family:sans-serif;padding:24px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border-radius:12px">
        <h2 style="margin:0 0 8px">{args.get("city","")}</h2>
        <div style="font-size:48px;font-weight:bold">{args.get("temp","")}&#176;F</div>
        <div style="opacity:0.8">{args.get("condition","")}</div>
    </div>''',
    title="Weather Card",
    invoking="Checking weather...",
    invoked="Weather loaded",
)
async def show_weather(city: str, temp: int, condition: str) -> dict:
    """Display weather in a visual card"""
    return {"city": city, "temp": temp, "condition": condition}

http_app = app.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware
    http_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["mcp-session-id"])
    uvicorn.run(http_app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

### E-Commerce with Staged Workflow

```python
import os
from concierge import Concierge
from mcp.server.transport_security import TransportSecuritySettings

_no_dns = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = Concierge("shop", host="0.0.0.0", transport_security=_no_dns)

@app.tool()
def search_products(query: str) -> dict:
    """Search the product catalog"""
    return {"products": [{"id": "p1", "name": "Laptop", "price": 999}]}

@app.tool()
def view_product(product_id: str) -> dict:
    """View product details"""
    return {"id": product_id, "name": "Laptop", "price": 999, "in_stock": True}

@app.tool()
def add_to_cart(product_id: str) -> dict:
    """Add a product to the shopping cart"""
    cart = app.get_state("cart", [])
    cart.append(product_id)
    app.set_state("cart", cart)
    return {"cart": cart}

@app.tool()
def remove_from_cart(product_id: str) -> dict:
    """Remove a product from the cart"""
    cart = app.get_state("cart", [])
    cart = [item for item in cart if item != product_id]
    app.set_state("cart", cart)
    return {"cart": cart}

@app.tool()
def checkout(payment_method: str) -> dict:
    """Complete the purchase"""
    cart = app.get_state("cart", [])
    return {"order_id": "ORD-123", "items": len(cart), "status": "confirmed"}

app.stages = {
    "browse": ["search_products", "view_product"],
    "cart": ["add_to_cart", "remove_from_cart"],
    "checkout": ["checkout"],
}

app.transitions = {
    "browse": ["cart"],
    "cart": ["browse", "checkout"],
    "checkout": [],
}

http_app = app.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware
    http_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["mcp-session-id"])
    uvicorn.run(http_app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

### Large API with Search Mode

```python
import os
from concierge import Concierge, Config, ProviderType
from mcp.server.transport_security import TransportSecuritySettings

_no_dns = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = Concierge(
    "admin-api",
    config=Config(provider_type=ProviderType.SEARCH, max_results=5),
    stateless_http=True, host="0.0.0.0", transport_security=_no_dns,
)

# Register 100+ tools — agent discovers them via search_tools()
@app.tool()
async def list_users(page: int = 1) -> dict:
    """List all users with pagination"""
    return {"users": [...]}

@app.tool()
async def create_user(name: str, email: str) -> dict:
    """Create a new user account"""
    return {"id": "u-1", "name": name, "email": email}

# ... many more tools

http_app = app.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware
    http_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["mcp-session-id"])
    uvicorn.run(http_app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

## Common Pitfalls

- **DNS rebinding errors (421):** Forgot `host="0.0.0.0"` and `transport_security=_no_dns`.
- **State not persisting:** Used `stateless_http=True` with `get_state`/`set_state`. Remove `stateless_http=True` for stateful apps.
- **Stage tools not appearing:** Didn't define `app.transitions` — both `stages` and `transitions` are required.
- **Widget not rendering:** Missing `structuredContent` — the tool must return a dict, and the widget decorator wraps it into `structuredContent` automatically.
- **Unicode errors on deploy:** Used emoji in Python strings. Use HTML entities instead (`&#128230;` not the emoji character).
- **Port mismatch on deploy:** Hardcoded a port other than 8000. Always use `int(os.getenv("PORT", 8000))`.

For any other issues related to Concierge SDK, please report the issue and open an issue at https://github.com/concierge-hq/concierge with error logs.