<p align="center">
  <img
    src="https://raw.githubusercontent.com/concierge-hq/concierge/main/assets/logo.svg"
    alt="Concierge"
  />
</p>


<p align="center">
  <a href="https://github.com/concierge-hq/concierge-sdk" target="_blank">
    <img src="https://img.shields.io/badge/GitHub-concierge--sdk-8B5CF6?style=flat&logo=github&logoColor=white&labelColor=000000" alt="GitHub"/>
  </a>
  &nbsp;
  <a href="https://discord.gg/bfT3VkhF" target="_blank">
    <img src="https://img.shields.io/badge/Discord-Join_Community-5865F2?style=flat&logo=discord&logoColor=white&labelColor=000000" alt="Discord"/>
  </a>
  &nbsp;
  <a href="https://calendly.com/arnavbalyan1/new-meeting" target="_blank">
    <img src="https://img.shields.io/badge/Book_Demo-Calendly-00A2FF?style=flat&logo=calendly&logoColor=white&labelColor=000000" alt="Book Demo"/>
  </a>
  &nbsp;
  <a href="https://calendar.google.com/calendar/u/0?cid=MWRiNjA2YjEzODU5MjM4MGE0ZWU1ODJkZTc1ZDhhOGUxMmZiNWYzM2FkNTYwMDdhNTg5ODUzNDU5OWM1MWM0YkBncm91cC5jYWxlbmRhci5nb29nbGUuY29t" target="_blank">
    <img src="https://img.shields.io/badge/Community_Sync-Calendar-34A853?style=flat&logo=googlecalendar&logoColor=white&labelColor=000000" alt="Community Sync"/>
  </a>
</p>
<p align="center">
  <img src="https://img.shields.io/badge/build-passing-brightgreen?style=flat&labelColor=000000" alt="Build Status"/>
  &nbsp;
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat&labelColor=000000" alt="License"/>
  &nbsp;
  <img src="https://img.shields.io/badge/python-3.9+-8B5CF6?style=flat&logo=python&logoColor=white&labelColor=000000" alt="Python"/>
</p>

<p align="center"><b>Declarative framework to convert MCP servers into production grade apps with workflows, state management, semantic search, and more.</b></p>

Concierge is a framework for building production agentic apps. Using protocols like MCP as the transport layer, Concierge adds the missing primitives like: *stages*, *transitions*, and *state*. Define invocation order and guardrails so agents reliably navigate, interact, and transact with your services. 
Ensuring your agent cannot call `checkout()` before calling `add_to_cart()`.

<p align="center">
  <img src="assets/token_usage.png" alt="Token Usage" width="48%"/>
  <img src="assets/error_rate.png" alt="Error Rate" width="48%"/>
</p>

<p align="center"><i>Concierge reduces token usage by 78% and error rates by 65% compared to flat tool lists</i></p>


## Quick Start

```bash
pip install concierge-sdk    # Install the SDK
concierge init my-store      # Scaffold a new project
cd my-store                  # Enter the project
python main.py               # Start the server
```

**Or convert an existing MCP server:**

```python
# Before
from mcp.server.fastmcp import FastMCP
app = FastMCP("my-server")

# After
from concierge import Concierge
app = Concierge("my-server")
```

Your `@app.tool()` decorators are unchanged. But you get superpowers.

## Why Concierge?

When you expose tools as a flat list, agents can invoke them in any order, semantic loss creeps in as tool count grows, and context windows fill up before the real work begins.

Concierge provides several primitives that you can annotate your tools to convert them into structured workflows that an agent can reliably navigate and interact with:

- **Stages**: Group of several tools, expose only what's relevant.
- **Transitions**: Define legal paths to the next stage that an agent can transition to.  
- **State**: Shared distributed memory available on a stage local and a global workflow level.

Declare your workflow. Concierge enforces it.

<br>
<p align="center">
  <img src="assets/concierge_example.svg" alt="Concierge Workflow" width="87%"/>
</p>
<br>

## Core Concepts

### **Tools**

Tools are your business logic. Define them exactly like FastMCP:

```python
@app.tool()
def add_to_cart(product_id: str, quantity: int) -> dict:
    """Add a product to the shopping cart."""
    cart = app.get_state("cart", [])
    cart.append({"product_id": product_id, "quantity": quantity})
    app.set_state("cart", cart)
    return {"success": True, "cart_size": len(cart)}
```

### **Stages**

A stage groups related tools that should be available together. Only tools within the current stage are visible to the agent.

```python
app.stages = {
    "browse": ["search_products", "view_product"],
    "cart": ["add_to_cart", "remove_from_cart", "view_cart"],
    "checkout": ["apply_coupon", "complete_purchase"],
}
```

### **Transitions**

Transitions define legal moves between stages. Enforce certain stages or guarentee tool invocation order:

```python
app.transitions = {
    "browse": ["cart"],              # Can only go to cart
    "cart": ["browse", "checkout"],  # Can go back or proceed
    "checkout": [],                  # Terminal stage
}
```

### **State**

State can be scoped to a stage or available globally across a session. For stateful servers, state is atomic and consistent across distributed replicas. Each session is isolated:

```python
# Set state (scoped to current session)
app.set_state("cart", [{"product_id": "123", "quantity": 2}])
app.set_state("user.email", "user@example.com")

# Get state
cart = app.get_state("cart", [])
email = app.get_state("user.email")
```


## Example

```python
from concierge import Concierge

app = Concierge("shopping")

@app.tool()
def search_products(query: str) -> dict:
    return {"products": [{"id": "p1", "name": "Laptop", "price": 999}]}

@app.tool()
def add_to_cart(product_id: str) -> dict:
    cart = app.get_state("cart", [])
    cart.append(product_id)
    app.set_state("cart", cart)
    return {"cart": cart}

@app.tool()
def checkout(payment_method: str) -> dict:
    return {"order_id": "ORD-123", "status": "confirmed"}

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

## Semantic Tool Search

When you have 100+ tools, even staged workflows aren't enough. Enable semantic search to collapse all tools into just two (search and invoke):

```python
from concierge import Concierge, Config, ProviderType

app = Concierge("large-api", config=Config(
    provider_type=ProviderType.SEARCH,
    max_results=5
))

# Register hundreds of tools...
@app.tool()
def search_users(query: str): ...
@app.tool()
def get_user_by_id(user_id: int): ...
# ... hundreds more
```

**What the agent sees:**

```
search_tools(query: str)              → Find tools by description
call_tool(tool_name: str, args: dict) → Execute a discovered tool
```

## API Reference

```python
from concierge import Concierge, Config, ProviderType

# Initialize
app = Concierge("name", config=Config(
    provider_type=ProviderType.PLAIN,  # or SEARCH
    max_results=5,
))

# Tools
@app.tool()
def my_tool(): ...

# State
app.get_state(key, default=None)
app.set_state(key, value)

# Workflow
app.stages = {"stage": ["tool1", "tool2"]}
app.transitions = {"stage": ["next_stage"]}
app.enforce_completion = True

# Run
app.run()                      # stdio
app.streamable_http_app()      # HTTP
```


**We are building the agentic web. Come join us.**

Interested in contributing or building with Concierge? [Reach out](mailto:arnavbalyan1@gmail.com).

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

<p align="center">
  <a href="https://github.com/concierge-hq/concierge-sdk/discussions" target="_blank">
    <img src="https://img.shields.io/badge/Discussions-Ask_Questions-blue?style=flat&logo=github&logoColor=white&labelColor=000000" alt="Discussions"/>
  </a>
  &nbsp;
  <a href="https://github.com/concierge-hq/concierge-sdk/issues" target="_blank">
    <img src="https://img.shields.io/badge/Issues-Report_Bugs-red?style=flat&logo=github&logoColor=white&labelColor=000000" alt="Issues"/>
  </a>
  &nbsp;
  <a href="https://discord.gg/bfT3VkhF" target="_blank">
    <img src="https://img.shields.io/badge/Discord-Chat-5865F2?style=flat&logo=discord&logoColor=white&labelColor=000000" alt="Discord"/>
  </a>
</p>
