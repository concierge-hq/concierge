"""
Simple stock exchange example - demonstrates Concierge basics.
Focus is on showing the framework, not real stock logic.
"""
import asyncio
from pydantic import BaseModel, Field
from concierge.core import construct, State, tool, stage, Workflow


# Define constructs
@construct()
class Stock(BaseModel):
    """Stock selection"""
    symbol: str = Field(description="Stock symbol like AAPL, GOOGL")
    quantity: int = Field(ge=1, description="Number of shares")


@construct()
class Transaction(BaseModel):
    """Transaction result"""
    order_id: str = Field(description="Order ID")
    status: str = Field(description="Transaction status")


# Stage 1: Browse stocks
@stage(name="browse", prerequisites=[])
class BrowseStage:
    """Browse and search stocks"""
    
    @tool()
    def search(self, state: State, symbol: str) -> dict:
        """Search for a stock"""
        return {"result": f"Found {symbol}: $150.00", "symbol": symbol, "price": 150.00}
    
    @tool()
    def add_to_cart(self, state: State, symbol: str, quantity: int) -> dict:
        """Add stock to cart (updates state directly)"""
        state.set("symbol", symbol)
        state.set("quantity", quantity)
        return {"result": f"Added {quantity} shares of {symbol}"}
    
    @tool()
    def view_history(self, state: State, symbol: str) -> dict:
        """View stock price history"""
        return {"result": f"{symbol} history: [100, 120, 150]"}


# Stage 2: Transact (buy/sell)
@stage(name="transact", prerequisites=[Stock])
class TransactStage:
    """Buy or sell stocks"""
    
    @tool(output=Transaction)
    def buy(self, state: State) -> dict:
        """Buy the selected stock"""
        stock = state.get("symbol")
        qty = state.get("quantity")
        return {"order_id": "ORD123", "status": f"Bought {qty} shares of {stock}"}
    
    @tool(output=Transaction)
    def sell(self, state: State) -> dict:
        """Sell the selected stock"""
        stock = state.get("symbol")
        qty = state.get("quantity")
        return {"order_id": "ORD456", "status": f"Sold {qty} shares of {stock}"}


# Stage 3: Portfolio
@stage(name="portfolio", prerequisites=[])
class PortfolioStage:
    """View portfolio and profits"""
    
    @tool()
    def view_holdings(self, state: State) -> dict:
        """View current holdings"""
        return {"result": "Holdings: AAPL: 10 shares, GOOGL: 5 shares"}
    
    @tool()
    def view_profit(self, state: State) -> dict:
        """View profit/loss"""
        return {"result": "Total profit: +$1,234.56"}


# Build workflow
def build_workflow() -> Workflow:
    workflow = Workflow("stock_exchange", "Simple stock trading")
    
    # Add stages
    browse = BrowseStage._stage
    browse.transitions = ["transact", "portfolio"]
    
    transact = TransactStage._stage
    transact.transitions = ["portfolio", "browse"]
    
    portfolio = PortfolioStage._stage
    portfolio.transitions = ["browse"]
    
    workflow.add_stage(browse, initial=True)
    workflow.add_stage(transact)
    workflow.add_stage(portfolio)
    
    return workflow


# Demo
async def main():
    print("=== Simple Stock Exchange ===\n")
    
    workflow = build_workflow()
    session = workflow.create_session()
    
    print(f"Current stage: {session.current_stage}\n")
    
    # 1. Search for stock
    print("1. Searching for stock...")
    result = await session.process_action({
        "action": "tool",
        "tool": "search",
        "args": {"symbol": "AAPL"}
    })
    print(f"   {result}\n")
    
    # 2. Add stock to cart (updates Browse stage's local state)
    print("2. Adding stock to cart...")
    result = await session.process_action({
        "action": "tool",
        "tool": "add_to_cart",
        "args": {"symbol": "AAPL", "quantity": 10}
    })
    print(f"   {result}\n")
    
    # 3. Check that other tools in Browse stage can see the state
    print("3. Viewing history (should see state from add_to_cart)...")
    result = await session.process_action({
        "action": "tool",
        "tool": "view_history",
        "args": {"symbol": "AAPL"}
    })
    print(f"   {result}\n")
    
    # 4. For now, let's skip prerequisites and go to portfolio (no prerequisites)
    print("4. Transitioning to 'portfolio'...")
    result = await session.process_action({
        "action": "transition",
        "stage": "portfolio"
    })
    print(f"   {result['type']}: {result.get('from', '')} → {result.get('to', '')}")
    print(f"   Note: Portfolio stage has fresh, isolated state\n")
    
    # 5. View holdings in portfolio stage
    print("5. Viewing holdings in portfolio stage...")
    result = await session.process_action({
        "action": "tool",
        "tool": "view_holdings",
        "args": {}
    })
    print(f"   {result}\n")
    
    print("\nSummary:")
    print("✓ Each stage has its own isolated local state")
    print("✓ Tools within a stage share that stage's local state")
    print("✗ Stage transitions create fresh state (data doesn't transfer)")
    print("→ Later: We'll add global state via Context for cross-stage data sharing")


if __name__ == "__main__":
    asyncio.run(main())

