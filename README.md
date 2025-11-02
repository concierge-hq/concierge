<br>
<p align="center">
  <img src="assets/logo.svg" alt="Concierge Logo" width="2000"/>
</p>
<br>

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]() [![License: MIT](https://img.shields.io/badge/License-MIT-blue)]() [![Python 3.10+](https://img.shields.io/badge/python-3.10+-lightgrey)]()

# Concierge

**A server-centric state machine framework for building intelligent LLM workflows.**
<br>

Concierge flips the traditional MCP model: instead of clients managing everything, the **server** handles prompt generation, state management, and flow control. The client becomes a simple messenger.

## Core Concepts

### 🔤 **Primitives**
Basic typed variables that form the foundation of state:
```python
email = String("email", required=True, pattern=r".*@.*")
age = Integer("age", min_value=0, max_value=120)  
cart_items = List("items", default_factory=list)
```

### 🏗️ **Constructs**
Collections of related primitives forming logical units:
```python
user_construct = Construct("user", {
    "id": String("id", required=True),
    "email": String("email", pattern=r".*@.*"),
    "name": String("name")
})
```

### 📦 **State**
Immutable container organizing data by constructs (inspired by Burr):
```python
state = State()
state = state.update("user", {"id": "123", "email": "user@example.com"})
state = state.update("cart", {"items": ["laptop"], "total": 999.99})
```

### 🔧 **Tasks**
Actions that read and write state with automatic validation:
```python
@task("Search for products")
def search(state: State, query: str) -> tuple:
    results = db.search(query)
    return results, {
        "state_updates": {
            "search.results": results,
            "search.query": query
        }
    }
```

### 📄 **Stages**
Logical groupings of tasks and state (like pages in a web app):
```python
browse_stage = Stage(
    name="browse",
    description="Browse products", 
    tasks=[search_task, add_to_cart_task],
    transitions=["cart", "checkout"]
)
```

### 🔄 **Workflows**
Complete state machines orchestrating stages:
```python
workflow = Workflow("amazon_shopping")
workflow.add_stage(browse_stage, initial=True)
workflow.add_stage(checkout_stage)
```

## Key Differences from MCP

| Feature | MCP | Concierge |
|---------|-----|-----------|
| **Control** | Client-centric | Server-centric |
| **Prompts** | Client generates | Server generates |
| **State** | Client manages | Server manages |
| **Tools** | Flat list | Organized by stages |
| **Flow** | No concept | Built-in transitions |
| **Validation** | Manual | Automatic |

## Quick Start

```python
from concierge.core import (
    Workflow, Stage, Task, 
    String, Integer, List,
    Construct, State
)

# 1. Define constructs (state shape)
cart = Construct("cart", {
    "items": List("items"),
    "total": Float("total", min_value=0)
})

# 2. Define tasks (business logic)
def add_to_cart(state: State, item_id: str) -> tuple:
    items = state.get("cart", "items", [])
    items.append(item_id)
    return {"added": item_id}, {
        "state_updates": {"cart.items": items}
    }

add_task = Task("add_to_cart", "Add item", add_to_cart)

# 3. Create stages
browse = Stage("browse", "Browse products")
browse.add_task(add_task)
browse.transitions = ["checkout"]

# 4. Build workflow
workflow = Workflow("shopping")
workflow.add_stage(browse)

# 5. Run session
session = workflow.create_session()
result = await session.process_action({
    "action": "method_call",
    "task": "add_to_cart", 
    "args": {"item_id": "laptop"}
})
```

## Architecture

```
User Input
    ↓
Thin Client (just forwards)
    ↓
Smart Server
    ├── Workflow Engine
    ├── State Manager  
    ├── Prompt Generator
    └── Task Executor
    ↓
LLM (via client)
    ↓
Server processes response
    ↓
Client displays to user
```

## Comparison with Burr and LangGraph

- **Burr**: We adopt Burr's immutable state pattern but add constructs and server-side orchestration
- **LangGraph**: Similar DAG concept but server-controlled rather than agent-controlled  
- **MCP**: Complete inversion - server does the heavy lifting, not the client

## Philosophy

1. **Servers should be smart, clients should be dumb**
2. **State should be structured (constructs), not flat keys**
3. **Stages provide natural boundaries (like web pages)**
4. **Auto-generate everything possible (prompts, validation, elicitation)**
5. **Developers define business logic, framework handles LLM interaction**

## Status

This is a **minimal proof-of-concept** showing the core ideas. Key features demonstrated:
- ✅ Primitive → Construct → State hierarchy
- ✅ Immutable state management  
- ✅ Task execution with state updates
- ✅ Stage-based organization
- ✅ Auto-prompt generation
- ✅ Session management

## Next Steps

1. **Transport Layer**: HTTP/WebSocket server implementation
2. **Client Library**: Thin JavaScript/Python clients  
3. **LLM Integration**: Direct Claude/GPT integration
4. **Persistence**: State saving/loading
5. **UI Builder**: Drag-and-drop workflow designer
6. **Registry**: Package and share workflows

## Inspiration

Built after analyzing:
- **MCP** (Model Context Protocol) - Task definitions
- **Burr** - Immutable state patterns
- **5ire** - Client implementation patterns
- **LangGraph** - DAG workflows

## License

MIT
