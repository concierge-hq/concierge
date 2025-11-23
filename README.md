<br>
<p align="center">
  <img src="assets/logo.svg" alt="Concierge Logo" width="2000"/>
</p>
<br>

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]() [![License: MIT](https://img.shields.io/badge/License-MIT-blue)]() [![Python 3.10+](https://img.shields.io/badge/python-3.10+-lightgrey)]()

# Concierge Agentic Web Interfaces

**Expose your service to Agents**
<br>

Concierge is a declerative framework that allows LLMs to interact with your applications, and navigate through complex service heirarchies. With Concierge, you can built applications for AI/LLM use exposed over the web to guide agents towards domain specific goals. (Example: Agents browsing, selecting, transcating for online shopping interface).

<h2 id="updates">🚀 Updates</h2>

 - **Nov 16, 2025**: Concierge x <a href="https://www.useblock.tech/">Block</a> unite. Concierge now powers conversational booking agents for beauty and wellness appointments across platforms.
 - **Nov 10, 2025**: Concierge x <a href="https://topfunnel.io/">Funnel</a> unite. Concierge powers your AI Staff Member That Never Sleeps.
 - **Nov 5, 2025**: Concierge x <a href="https://usearistotle.com/">Aristotle</a>. Concierge now powers Aristotle's conversational AI for reliable, high-stakes production deployments.

## Quick Start

```bash
# 1. Install Concierge
pip install concierge_awi

# 2. Start the AWI
concierge serve --config your_workflow.yaml

# 3. Chat with your service!
concierge chat --config your_workflow.yaml --api-base https://api.openai.com/v1 --api-key $OPENAI_API_KEY
```

## 🌐 Protocols Supported

| Protocol | Status | Description |
|-----------|---------|-------------|
| **AWIP (Agentic Web Interactive Protocol)** | ✅ Supported | Concierge natively implements the Agentic Web Interactive Protocol (AWIP) for connecting agents to web-exposed services. Tools are maintained **server-side**, preventing model context bloat and significantly reducing cost and latency. |
| **MCP (Model Context Protocol)** | 🚧 Coming Soon | Now express Concierge workflows through MCP, support comming soon. |

## Core Concepts

Developers define workflows with explicit rules and prerequisites. You control agent autonomy by specifying legal tasks at each stage and valid transitions between stages. For example: agents cannot checkout before adding items to cart. Concierge enforces these rules, validates prerequisites before task execution, and ensures agents follow your defined path through the application.

<br>
<p align="center">
  <img src="assets/concierge_example.svg" alt="Concierge Example" width="100%"/>
</p>
<br>

### **Tasks**
Tasks are the smallest granularity of callable business logic. Several tasks can be defined within 1 stage. Ensuring these tasks are avialable or callable at the stage. 
```python
@task(description="Add product to shopping cart")
def add_to_cart(self, state: State, product_id: str, quantity: int) -> dict:
    """Adds item to cart and updates state"""
    cart_items = state.get("cart.items", [])
    cart_items.append({"product_id": product_id, "quantity": quantity})
    state.set("cart.items", cart_items)
    return {"success": True, "cart_size": len(cart_items)}
```

### **Stages**
A stage is a logical sub-step towards a goal, Stage can have several tasks grouped together, that an agent can call at a given point. 
```python
@stage(name="product")
class ProductStage:
    @task(description="Add product to shopping cart")
    def add_to_cart(self, state: State, product_id: str, quantity: int) -> dict:
        """Adds item to cart"""
        
    @task(description="Save product to wishlist")
    def add_to_wishlist(self, state: State, product_id: str) -> dict:
        """Saves item for later"""
        
```

### **State**
A state is a global context that is maintained by Concierge, parts of which can get propagated to other stages as the agent transitions and navigates through stages. 
```python
# State persists across stages and tasks
state.set("cart.items", [{"product_id": "123", "quantity": 2}])
state.set("user.email", "user@example.com")
state.set("cart.total", 99.99)

# Retrieve state values
items = state.get("cart.items", [])
user_email = state.get("user.email")
```

### **Workflow**
A workflow is a logic grouping of several stages, you can define graphs of stages which represent legal moves to other stages within workflow.
```python
@workflow(name="shopping")
class ShoppingWorkflow:
    discovery = DiscoveryStage      # Search and filter products
    product = ProductStage          # View product details
    selection = SelectionStage      # Add to cart/wishlist
    cart = CartStage                # Manage cart items
    checkout = CheckoutStage        # Complete purchase
    
    transitions = {
        discovery: [product, selection],
        product: [selection, discovery],
        selection: [cart, discovery, product],
        cart: [checkout, selection, discovery],
        checkout: []
    }
```

**Dashboard**
<br>
<p align="center">
  <img src="assets/Concierge WF.png" alt="Concierge Workflow" width="100%"/>
  <br/>  
</p>
<br>


## Examples

### Multi-Stage Workflow

```python
@workflow(name="amazon_shopping")
class AmazonShoppingWorkflow:
    browse = BrowseStage         # Search and filter products
    select = SelectStage         # Add items to cart
    checkout = CheckoutStage     # Complete transaction
    
    transitions = {
        browse: [select],
        select: [browse, checkout],
        checkout: []
    }
```

### Stage with Tasks

```python
@stage(name="browse")
class BrowseStage:
    @task(description="Search for products by keyword")
    def search_products(self, state: State, query: str) -> dict:
        """Returns matching products"""
        
    @task(description="Filter products by price range")
    def filter_by_price(self, state: State, min_price: float, max_price: float) -> dict:
        """Filters current results by price"""
        
    @task(description="Sort products by rating or price")
    def sort_products(self, state: State, sort_by: str) -> dict:
        """Sorts: 'rating', 'price_low', 'price_high'"""

@stage(name="select")
class SelectStage:
    @task(description="Add product to shopping cart")
    def add_to_cart(self, state: State, product_id: str, quantity: int) -> dict:
        """Adds item to cart"""
        
    @task(description="Save product to wishlist")
    def add_to_wishlist(self, state: State, product_id: str) -> dict:
        """Saves item for later"""
        
    @task(description="Star product for quick access")
    def star_product(self, state: State, product_id: str) -> dict:
        """Stars item as favorite"""
        
    @task(description="View product details")
    def view_details(self, state: State, product_id: str) -> dict:
        """Shows full product information"""
```

### Prerequisites

```python
@stage(name="checkout", prerequisites=["cart.items", "user.payment_method"])
class CheckoutStage:
    @task(description="Apply discount code")
    def apply_discount(self, state: State, code: str) -> dict:
        """Validates and applies discount"""
        
    @task(description="Complete purchase")
    def complete_purchase(self, state: State) -> dict:
        """Processes payment and creates order"""
```

**We are building the agentic web. Come join us.**

Interested in contributing or building with Concierge? [Reach out](mailto:arnavbalyan1@gmail.com).

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

