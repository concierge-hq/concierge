<h1 align="center">Universal Agent Interactive Framework (UAIF)</h1>

<p align="center">
  <a href="https://github.com/concierge-hq/UAIP" target="_blank">
    <img src="https://img.shields.io/badge/GitHub-UAIP-8B5CF6?style=flat&logo=github&logoColor=white&labelColor=000000" alt="GitHub"/>
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
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue?style=flat&labelColor=000000" alt="License"/>
  &nbsp;
  <img src="https://img.shields.io/badge/python-3.9+-yellow?style=flat&logo=python&logoColor=white&labelColor=000000" alt="Python"/>
</p>

<p align="center"><b>An open protocol for interoperability between autonomous agents and application services.</b></p>

UAIP defines how autonomous agents interact with applications through explicit stages, workflows, and tasks. It guarantees invocation order and reliable execution, replacing ad-hoc prompting with verifiable contracts. UAIP is 78% more token efficient than existing protocols, eliminating context overflow and semantic loss.


<p align="center">
  <img src="assets/token_usage.png" alt="Token Usage" width="48%"/>
  <img src="assets/error_rate.png" alt="Error Rate" width="48%"/>
</p>

<p align="center"><i>UAIP token efficiency across benchmarks</i></p>


## Quick Start

```bash
# Install UAIP SDK
pip install uaip

# Initialize a new workflow project
uaip init my-store

# Run the workflow server
cd my-store
python main.py
```

This starts a UAIP server at `http://localhost:8000` that agents can interact with via `/initialize` and `/execute`.

## Universal Agent Interactive Protocol

You control agent autonomy by specifying legal tasks at each stage and valid transitions between stages. For example: agents cannot checkout before adding items to cart. UAIP enforces these rules, validates prerequisites before task execution, and ensures agents follow your defined path through the application.

<br>
<p align="center">
  <img src="assets/concierge_example.svg" alt="UAIP Example" width="100%"/>
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
A state is a global context that is maintained by the protocol, parts of which can get propagated to other stages as the agent transitions and navigates through stages. 
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

Interested in contributing or building with UAIP? [Reach out](mailto:arnavbalyan1@gmail.com).

Interested in building apps that render in ChatGPT? Check out [Concierge AI](https://github.com/concierge-hq/concierge-sdk).

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

