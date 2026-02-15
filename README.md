<div align="center">

<!-- omit in toc -->

<picture>
  <img width="900" alt="Concierge Banner" src="assets/concierge-banner.png" />
</picture>

# Concierge AI 🚀

<strong>The fabric for reliable MCP servers and AI applications.</strong>

[![Docs](https://img.shields.io/badge/docs-getconcierge.app-blue)](https://docs.getconcierge.app)
[![Discord](https://img.shields.io/badge/community-discord-5865F2?logo=discord&logoColor=white)](https://discord.gg/bfT3VkhF)
[![PyPI - Version](https://img.shields.io/pypi/v/concierge-sdk.svg)](https://pypi.org/project/concierge-sdk)
[![Python](https://img.shields.io/badge/python-3.9+-8B5CF6?logo=python&logoColor=white)](https://pypi.org/project/concierge-sdk)

</div>

The [Model Context Protocol](https://modelcontextprotocol.io) (MCP) is a standardized way to connect AI agents to tools. Instead of exposing a flat list of every tool on every request, Concierge progressively discloses only what's relevant. Concierge guarantees deterministic results and reliable tool invocation.

## Getting Started

> [!NOTE]
> Concierge requires Python 3.9+. We recommend installing with [uv](https://docs.astral.sh/uv/) for faster dependency resolution, but pip works just as well.

```bash
pip install concierge-sdk
```

**Scaffold a new project:**

```bash
concierge init my-store    # Generate a ready to run project
cd my-store                # Enter project
python main.py             # Start the MCP server
```

**Or wrap an existing MCP server** two lines, nothing else changes:

```python
# Before
from mcp.server.fastmcp import FastMCP
app = FastMCP("my-server")

# After: just wrap it
from concierge import Concierge
app = Concierge(FastMCP("my-server"))
```

> [!TIP]
> Concierge works at the MCP protocol level. It dynamically changes which tools are returned by `tools/list` based on the current workflow step. The agent and client don't need to know Concierge exists, they just see fewer, more relevant tools at each point.

<br />

```python
from concierge import Concierge
from mcp.server.fastmcp import FastMCP

app = Concierge(FastMCP("my-server"))

# Your @app.tool() decorators stay exactly the same.
# You can additionally add app.stages and app.transitions.
```

> [!NOTE]
> The wrap and go gives you progressive tool disclosure immediately. Add `app.stages` and `app.transitions` when you want full workflow control, no code changes required.

<br />

## Usage

### Group tools into steps

Instead of exposing everything at once, group related tools together. Only the current step's tools are visible to the agent:

```python
app.stages = {
    "browse":   ["search_products", "view_product"],
    "cart":     ["add_to_cart", "remove_from_cart", "view_cart"],
    "checkout": ["apply_coupon", "complete_purchase"],
}
```

### Define transitions

Control which steps can follow which. The agent moves forward (or backward) only along paths you allow:

```python
app.transitions = {
    "browse":   ["cart"],               # Can only move to cart
    "cart":     ["browse", "checkout"], # Can go back or proceed
    "checkout": [],                     # Terminal step
}
```

<details>
<summary><b>Share state between steps</b></summary>
<br>

Pass data between workflow steps without round-tripping through the LLM. State is session-scoped and works across distributed replicas:

```python
# In the "browse" step - save a selection
app.set_state("selected_product", {"id": "p1", "name": "Laptop"})

# In the "cart" step retrieve it directly
product = app.get_state("selected_product")
```
</details>

<details>
<summary><b>Scale with semantic search</b></summary>
<br>

When you have hundreds of tools, enable semantic search to collapse your entire API behind two meta-tools:

```python
from concierge import Concierge, Config, ProviderType

app = Concierge("large-api", config=Config(
    provider_type=ProviderType.SEARCH,
    max_results=5,
))
```

No matter how many tools you register, the agent only ever sees:

```
search_tools(query: str)              → Find tools by description
call_tool(tool_name: str, args: dict) → Execute a discovered tool
```
</details>

### Run over HTTP

Concierge supports multiple transports. Use streamable HTTP for web deployments:

```python
# Streamable HTTP (recommended for web)
http_app = app.streamable_http_app()

# Or run over stdio (default, for CLI-based clients)
app.run()
```

> [!TIP]
> All of the above: stages, transitions, state, semantic search are optional and independent. Use any combination. Start simple and add structure as your workflow grows.

## Features
| | |
|:--|:--|
| **Progressive Disclosure**: Only expose the tools that matter right now. Fewer tools in context means less confusion and lower cost. | **Enforced Tool Ordering**: Define which tools unlock which. The agent follows your business logic, not its own guesses. |
| **Shared State**: Pass data between workflow steps server-side. No tool-call chaining through the LLM, no re-injecting data into prompts. | **Semantic Search**: For large APIs (100+ tools), collapse everything behind two meta-tools. The agent searches by description, then invokes. |
| **Protocol Compatible**: Wraps any MCP server. Your existing `@app.tool()` decorators, resources, and prompts work unchanged. | **Session Isolation**: Each conversation gets its own workflow state. Atomic, consistent, works across distributed replicas. |
| **Multiple Transports**: Run over stdio, streamable HTTP, or SSE. Deploy anywhere: serverless, containers, bare metal. | **Scaffolding CLI**: `concierge init` generates a ready to run project with tools, stages, and transitions wired up ready to go. |

## Example Concierge Application

A complete e-commerce workflow in under 30 lines:

```python
from concierge import Concierge

app = Concierge("shopping")

@app.tool()
def search_products(query: str) -> dict:
    """Search the product catalog."""
    return {"products": [{"id": "p1", "name": "Laptop", "price": 999}]}

@app.tool()
def add_to_cart(product_id: str) -> dict:
    """Add a product to the cart."""
    cart = app.get_state("cart", [])
    cart.append(product_id)
    app.set_state("cart", cart)
    return {"cart": cart}

@app.tool()
def checkout(payment_method: str) -> dict:
    """Complete the purchase."""
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

app.run()  # Start over stdio
```

The agent starts at `browse`. It can move to `cart`, then to `checkout`. It cannot call `checkout` from `browse`. Concierge enforces this at the protocol level, no prompt engineering required.
<br />

## Documentation

Full guides, API reference, and deployment patterns are available at **[docs.getconcierge.app](https://docs.getconcierge.app)**.
<br />

## Community

- [Discord](https://discord.gg/bfT3VkhF): Ask questions, share what you're building, get help.
- [Issues](https://github.com/concierge-hq/concierge/issues): Report bugs or request features.
- [Discussions](https://github.com/concierge-hq/concierge/discussions): Longer form discussions and RFCs.

---

<p align="left">
  We are building the agentic web. Come <a href="mailto:arnav@getconcierge.app">join us</a>.
</p>
