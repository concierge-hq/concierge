"""Integration tests for stock workflow with message exchanges."""
import asyncio
from concierge.core import State, tool, stage, workflow
from concierge.engine import Orchestrator
from concierge.engine.language_engine import LanguageEngine


# Define simple stock workflow for testing
@stage(name="browse")
class Browse:
    """Browse stocks"""
    
    @tool()
    def search(self, state: State, symbol: str):
        """Search for stock"""
        state.set("last_search", symbol)
        return {"result": f"Found {symbol}: $150.00", "price": 150.0}
    
    @tool()
    def add_to_cart(self, state: State, symbol: str, quantity: int):
        """Add stock to cart"""
        state.set("cart", {"symbol": symbol, "quantity": quantity})
        return {"result": f"Added {quantity} shares of {symbol}"}


@stage(name="portfolio")
class Portfolio:
    """View portfolio"""
    
    @tool()
    def view_holdings(self, state: State):
        """View current holdings"""
        return {"result": "Holdings: AAPL: 10 shares"}


@workflow(name="stock_test")
class StockWorkflow:
    """Test stock workflow"""
    browse = Browse
    portfolio = Portfolio
    
    transitions = {
        browse: [portfolio],
        portfolio: [browse]
    }


def test_stock_workflow_search():
    """Test searching for a stock"""
    async def run():
        wf = StockWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-1")
        engine = LanguageEngine(orch)
        
        response = await engine.process({
            "action": "method_call",
            "tool": "search",
            "args": {"symbol": "AAPL"}
        })
        
        expected = """Tool 'search' executed successfully.

Result:
{
  "result": "Found AAPL: $150.00",
  "price": 150.0
}

Workflow: stock_test
Stage: browse (step 1 of 2)
Description: Browse stocks

Available tools: search, add_to_cart
Next stages: portfolio
Previous stages: 

Current state:
{
  "last_search": "AAPL"
}

What would you like to do?

1. Call a tool
Format: {"action": "method_call", "tool": "<tool>", "args": "{...}"}
Example: {"action":"method_call","tool":"search","args":{"symbol":"AAPL"}}

2. Transition to another stage
Format: {"action": "stage_transition", "stage": "<stage>"}
Example: {"action":"stage_transition","stage":"portfolio"}

3. End session
Format: {"action": "terminate_session", "reason": "<reason>"}
Example: {"action":"terminate_session","reason":"completed"}"""
        
        assert response == expected
        
        assert orch.get_current_stage().local_state.get("last_search") == "AAPL"
    
    asyncio.run(run())


def test_stock_workflow_add_to_cart():
    """Test adding stock to cart"""
    async def run():
        wf = StockWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-2")
        engine = LanguageEngine(orch)
        
        response = await engine.process({
            "action": "method_call",
            "tool": "add_to_cart",
            "args": {"symbol": "GOOGL", "quantity": 5}
        })
        
        expected = """Tool 'add_to_cart' executed successfully.

Result:
{
  "result": "Added 5 shares of GOOGL"
}

Workflow: stock_test
Stage: browse (step 1 of 2)
Description: Browse stocks

Available tools: search, add_to_cart
Next stages: portfolio
Previous stages: 

Current state:
{
  "cart": {
    "symbol": "GOOGL",
    "quantity": 5
  }
}

What would you like to do?

1. Call a tool
Format: {"action": "method_call", "tool": "<tool>", "args": "{...}"}
Example: {"action":"method_call","tool":"search","args":{"symbol":"AAPL"}}

2. Transition to another stage
Format: {"action": "stage_transition", "stage": "<stage>"}
Example: {"action":"stage_transition","stage":"portfolio"}

3. End session
Format: {"action": "terminate_session", "reason": "<reason>"}
Example: {"action":"terminate_session","reason":"completed"}"""
        
        assert response == expected
        
        cart = orch.get_current_stage().local_state.get("cart")
        assert cart["symbol"] == "GOOGL"
        assert cart["quantity"] == 5
    
    asyncio.run(run())


def test_stock_workflow_transition():
    """Test transitioning between stages"""
    async def run():
        wf = StockWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-3")
        engine = LanguageEngine(orch)
        
        assert orch.get_current_stage().name == "browse"
        
        response = await engine.process({
            "action": "stage_transition",
            "stage": "portfolio"
        })
        
        expected = """Successfully transitioned from 'browse' to 'portfolio'.

Workflow: stock_test
Stage: portfolio (step 2 of 2)
Description: View portfolio

Available tools: view_holdings
Next stages: browse
Previous stages: 

Current state:
{}

What would you like to do?

1. Call a tool
Format: {"action": "method_call", "tool": "<tool>", "args": "{...}"}
Example: {"action":"method_call","tool":"search","args":{"symbol":"AAPL"}}

2. Transition to another stage
Format: {"action": "stage_transition", "stage": "<stage>"}
Example: {"action":"stage_transition","stage":"portfolio"}

3. End session
Format: {"action": "terminate_session", "reason": "<reason>"}
Example: {"action":"terminate_session","reason":"completed"}"""
        
        assert response == expected
        
        assert orch.get_current_stage().name == "portfolio"
    
    asyncio.run(run())


def test_stock_workflow_full_conversation():
    """Test a full conversation flow"""
    async def run():
        wf = StockWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-4")
        engine = LanguageEngine(orch)
        
        response1 = await engine.process({
            "action": "method_call",
            "tool": "search",
            "args": {"symbol": "AAPL"}
        })
        assert "Tool 'search' executed successfully." in response1
        assert "Found AAPL: $150.00" in response1
        assert orch.get_current_stage().name == "browse"
        
        response2 = await engine.process({
            "action": "method_call",
            "tool": "add_to_cart",
            "args": {"symbol": "AAPL", "quantity": 10}
        })
        assert "Tool 'add_to_cart' executed successfully." in response2
        assert "Added 10 shares of AAPL" in response2
        assert orch.get_current_stage().local_state.get("cart") is not None
        
        response3 = await engine.process({
            "action": "stage_transition",
            "stage": "portfolio"
        })
        assert "Successfully transitioned from 'browse' to 'portfolio'." in response3
        assert orch.get_current_stage().name == "portfolio"
        
        response4 = await engine.process({
            "action": "method_call",
            "tool": "view_holdings",
            "args": {}
        })
        assert "Tool 'view_holdings' executed successfully." in response4
        assert "Holdings: AAPL: 10 shares" in response4
        
        assert len(orch.history) == 4
        assert orch.history[0]["action"] == "method_call"
        assert orch.history[1]["action"] == "method_call"
        assert orch.history[2]["action"] == "stage_transition"
        assert orch.history[3]["action"] == "method_call"
    
    asyncio.run(run())


def test_stock_workflow_invalid_action():
    """Test handling of invalid action"""
    async def run():
        wf = StockWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-5")
        engine = LanguageEngine(orch)
        
        response = await engine.process({
            "action": "invalid_action",
            "data": "whatever"
        })
        
        # Assert exact error format
        expected = """Error: Unknown action type: invalid_action

"""
        
        assert response == expected
    
    asyncio.run(run())


def test_stock_workflow_invalid_tool():
    """Test calling non-existent tool"""
    async def run():
        wf = StockWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-6")
        engine = LanguageEngine(orch)
        
        response = await engine.process({
            "action": "method_call",
            "tool": "nonexistent_tool",
            "args": {}
        })
        
        expected = """Error: Tool 'nonexistent_tool' not found in stage 'browse'

"""
        
        assert response == expected
    
    asyncio.run(run())


def test_stock_workflow_invalid_transition():
    """Test invalid stage transition"""
    async def run():
        wf = StockWorkflow._workflow
        orch = Orchestrator(wf, session_id="test-7")
        engine = LanguageEngine(orch)
        
        response = await engine.process({
            "action": "stage_transition",
            "stage": "nonexistent_stage"
        })
        
        assert isinstance(response, str)
        assert "Error: " in response
        assert "nonexistent_stage" in response
    
    asyncio.run(run())
