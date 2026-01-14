"""
Simple stock exchange example - demonstrates a basic UAIP workflow.

Run directly with: python simple_stock.py
This starts an HTTP server at http://localhost:8000
"""
from pydantic import BaseModel, Field
from concierge.core import construct, State, task, stage, workflow, StateTransfer


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
    
    @task()
    def search(self, state: State, symbol: str) -> dict:
        """Search for a stock"""
        return {"result": f"Found {symbol}: $150.00", "symbol": symbol, "price": 150.00}
    
    @task()
    def add_to_cart(self, state: State, symbol: str, quantity: int) -> dict:
        """Add stock to cart (updates state directly)"""
        state.set("symbol", symbol)
        state.set("quantity", quantity)
        return {"result": f"Added {quantity} shares of {symbol}"}
    
    @task()
    def view_history(self, state: State, symbol: str) -> dict:
        """View stock price history"""
        return {"result": f"{symbol} history: [100, 120, 150]"}


# Stage 2: Transact (buy/sell)
@stage(name="transact", prerequisites=[Stock])
class TransactStage:
    """Buy or sell stocks"""
    
    @task(output=Transaction)
    def buy(self, state: State) -> dict:
        """Buy the selected stock"""
        stock = state.get("symbol")
        qty = state.get("quantity")
        return {"order_id": "ORD123", "status": f"Bought {qty} shares of {stock}"}
    
    @task(output=Transaction)
    def sell(self, state: State) -> dict:
        """Sell the selected stock"""
        stock = state.get("symbol")
        qty = state.get("quantity")
        return {"order_id": "ORD456", "status": f"Sold {qty} shares of {stock}"}


# Stage 3: Portfolio
@stage(name="portfolio", prerequisites=[])
class PortfolioStage:
    """View portfolio and profits"""
    
    @task()
    def view_holdings(self, state: State) -> dict:
        """View current holdings"""
        return {"result": "Holdings: AAPL: 10 shares, GOOGL: 5 shares"}
    
    @task()
    def view_profit(self, state: State) -> dict:
        """View profit/loss"""
        return {"result": "Total profit: +$1,234.56"}


@workflow(name="stock_exchange", description="Simple stock trading")
class StockWorkflow:
    """Stock exchange workflow"""
    
    # Define stages (first = initial)
    browse = BrowseStage
    transact = TransactStage
    portfolio = PortfolioStage
    
    transitions = {
        browse: [transact, portfolio],
        transact: [portfolio, browse],
        portfolio: [browse],
    }
    
    state_management = [
        (browse, transact, ["symbol", "quantity"]), 
        (browse, portfolio, StateTransfer.ALL),       
    ]


if __name__ == "__main__":
    StockWorkflow.run(port=8000)

