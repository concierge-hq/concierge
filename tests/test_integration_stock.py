"""Integration tests for stock workflow with message exchanges."""
import asyncio
from concierge.core import State, task, stage, workflow
from concierge.engine.language_engine import LanguageEngine
from concierge.external.contracts import ACTION_METHOD_CALL, ACTION_STAGE_TRANSITION


# Define simple stock workflow for testing
@stage(name="browse")
class Browse:
    """Browse stocks"""
    
    @task()
    def search(self, state: State, symbol: str):
        """Search for stock"""
        state.set("last_search", symbol)
        return {"result": f"Found {symbol}: $150.00", "price": 150.0}
    
    @task()
    def add_to_cart(self, state: State, symbol: str, quantity: int):
        """Add stock to cart"""
        state.set("cart", {"symbol": symbol, "quantity": quantity})
        return {"result": f"Added {quantity} shares of {symbol}"}


@stage(name="portfolio")
class Portfolio:
    """View portfolio"""
    
    @task()
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
        engine = LanguageEngine(wf, session_id="test-1")
        orch = engine.orchestrator
        
        response = await engine.process({
            "action": "method_call",
            "task": "search",
            "args": {"symbol": "AAPL"}
        })
        
        expected = """================================================================================
RESPONSE:
Task 'search' executed successfully.

Result:
{'result': 'Found AAPL: $150.00', 'price': 150.0}

================================================================================
ADDITIONAL CONTEXT:

WORKFLOW: stock_test
Description: Test stock workflow

STRUCTURE:
  - browse
  - portfolio

CURRENT POSITION: browse

CURRENT STATE:
{
  "last_search": "AAPL"
}

YOU MAY CHOOSE THE FOLLOWING ACTIONS:

1. ACTION CALLS (Tasks):
  Task: search
    Description: Search for stock
    Call Format:
      {
      "action": "method_call",
      "task": "search",
      "args": {
            "symbol": "<symbol>"
      }
}

  Task: add_to_cart
    Description: Add stock to cart
    Call Format:
      {
      "action": "method_call",
      "task": "add_to_cart",
      "args": {
            "symbol": "<symbol>",
            "quantity": 0
      }
}


2. STAGE CALLS (Transitions):
  Transition to: portfolio
    {"action": "stage_transition", "stage": "portfolio"}


You must ONLY respond with a single JSON. Do not add comments or extra text.
================================================================================"""
        
        assert response == expected
        
        # Verify state was updated via state_manager
        from concierge.core.state_manager import get_state_manager
        state_mgr = get_state_manager()
        stage_state = await state_mgr.get_stage_state("test-1", "browse")
        assert stage_state.get("last_search") == "AAPL"
    
    asyncio.run(run())


def test_stock_workflow_add_to_cart():
    """Test adding stock to cart"""
    async def run():
        wf = StockWorkflow._workflow
        engine = LanguageEngine(wf, session_id="test-2")
        orch = engine.orchestrator
        
        response = await engine.process({
            "action": "method_call",
            "task": "add_to_cart",
            "args": {"symbol": "GOOGL", "quantity": 5}
        })
        
        expected = """================================================================================
RESPONSE:
Task 'add_to_cart' executed successfully.

Result:
{'result': 'Added 5 shares of GOOGL'}

================================================================================
ADDITIONAL CONTEXT:

WORKFLOW: stock_test
Description: Test stock workflow

STRUCTURE:
  - browse
  - portfolio

CURRENT POSITION: browse

CURRENT STATE:
{
  "cart": {
    "symbol": "GOOGL",
    "quantity": 5
  }
}

YOU MAY CHOOSE THE FOLLOWING ACTIONS:

1. ACTION CALLS (Tasks):
  Task: search
    Description: Search for stock
    Call Format:
      {
      "action": "method_call",
      "task": "search",
      "args": {
            "symbol": "<symbol>"
      }
}

  Task: add_to_cart
    Description: Add stock to cart
    Call Format:
      {
      "action": "method_call",
      "task": "add_to_cart",
      "args": {
            "symbol": "<symbol>",
            "quantity": 0
      }
}


2. STAGE CALLS (Transitions):
  Transition to: portfolio
    {"action": "stage_transition", "stage": "portfolio"}


You must ONLY respond with a single JSON. Do not add comments or extra text.
================================================================================"""
        
        assert response == expected
        
        # Verify state via state_manager
        from concierge.core.state_manager import get_state_manager
        state_mgr = get_state_manager()
        stage_state = await state_mgr.get_stage_state("test-2", "browse")
        cart = stage_state.get("cart")
        assert cart["symbol"] == "GOOGL"
        assert cart["quantity"] == 5
    
    asyncio.run(run())


def test_stock_workflow_transition():
    """Test transitioning between stages"""
    async def run():
        wf = StockWorkflow._workflow
        engine = LanguageEngine(wf, session_id="test-3")
        orch = engine.orchestrator
        
        assert orch.get_current_stage().name == "browse"
        
        response = await engine.process({
            "action": "stage_transition",
            "stage": "portfolio"
        })
        
        expected = """================================================================================
RESPONSE:
Successfully transitioned from 'browse' to 'portfolio'.

================================================================================
ADDITIONAL CONTEXT:

WORKFLOW: stock_test
Description: Test stock workflow

STRUCTURE:
  - browse
  - portfolio

CURRENT POSITION: portfolio

CURRENT STATE:
{}

YOU MAY CHOOSE THE FOLLOWING ACTIONS:

1. ACTION CALLS (Tasks):
  Task: view_holdings
    Description: View current holdings
    Call Format:
      {
      "action": "method_call",
      "task": "view_holdings",
      "args": {}
}


2. STAGE CALLS (Transitions):
  Transition to: browse
    {"action": "stage_transition", "stage": "browse"}


You must ONLY respond with a single JSON. Do not add comments or extra text.
================================================================================"""
        
        assert response == expected
        assert orch.get_current_stage().name == "portfolio"
    
    asyncio.run(run())


def test_stock_workflow_full_conversation():
    """Test a full conversation flow"""
    async def run():
        wf = StockWorkflow._workflow
        engine = LanguageEngine(wf, session_id="test-4")
        orch = engine.orchestrator
        
        response1 = await engine.process({
            "action": "method_call",
            "task": "search",
            "args": {"symbol": "AAPL"}
        })
        assert "Task 'search' executed successfully." in response1
        assert "Found AAPL: $150.00" in response1
        assert orch.get_current_stage().name == "browse"
        
        response2 = await engine.process({
            "action": "method_call",
            "task": "add_to_cart",
            "args": {"symbol": "AAPL", "quantity": 10}
        })
        assert "Task 'add_to_cart' executed successfully." in response2
        assert "Added 10 shares of AAPL" in response2
        
        # Verify state via state_manager
        from concierge.core.state_manager import get_state_manager
        state_mgr = get_state_manager()
        stage_state = await state_mgr.get_stage_state("test-4", "browse")
        assert stage_state.get("cart") is not None
        
        response3 = await engine.process({
            "action": "stage_transition",
            "stage": "portfolio"
        })
        assert "Successfully transitioned from 'browse' to 'portfolio'." in response3
        assert orch.get_current_stage().name == "portfolio"
        
        response4 = await engine.process({
            "action": "method_call",
            "task": "view_holdings",
            "args": {}
        })
        assert "Task 'view_holdings' executed successfully." in response4
        assert "Holdings: AAPL: 10 shares" in response4
        
        assert len(orch.history) == 4
        assert orch.history[0]["action"] == ACTION_METHOD_CALL
        assert orch.history[1]["action"] == ACTION_METHOD_CALL
        assert orch.history[2]["action"] == ACTION_STAGE_TRANSITION
        assert orch.history[3]["action"] == ACTION_METHOD_CALL
    
    asyncio.run(run())


def test_stock_workflow_invalid_action():
    """Test handling of invalid action"""
    async def run():
        wf = StockWorkflow._workflow
        engine = LanguageEngine(wf, session_id="test-5")
        
        response = await engine.process({
            "action": "invalid_action",
            "data": "whatever"
        })
        
        expected = """================================================================================
RESPONSE:
Error: Unknown action type: invalid_action

================================================================================
ADDITIONAL CONTEXT:

WORKFLOW: stock_test
Description: Test stock workflow

STRUCTURE:
  - browse
  - portfolio

CURRENT POSITION: browse

CURRENT STATE:
{}

YOU MAY CHOOSE THE FOLLOWING ACTIONS:

1. ACTION CALLS (Tasks):
  Task: search
    Description: Search for stock
    Call Format:
      {
      "action": "method_call",
      "task": "search",
      "args": {
            "symbol": "<symbol>"
      }
}

  Task: add_to_cart
    Description: Add stock to cart
    Call Format:
      {
      "action": "method_call",
      "task": "add_to_cart",
      "args": {
            "symbol": "<symbol>",
            "quantity": 0
      }
}


2. STAGE CALLS (Transitions):
  Transition to: portfolio
    {"action": "stage_transition", "stage": "portfolio"}


You must ONLY respond with a single JSON. Do not add comments or extra text.
================================================================================"""
        
        assert response == expected
    
    asyncio.run(run())


def test_stock_workflow_invalid_task():
    """Test calling non-existent task"""
    async def run():
        wf = StockWorkflow._workflow
        engine = LanguageEngine(wf, session_id="test-6")
        
        response = await engine.process({
            "action": "method_call",
            "task": "nonexistent_task",
            "args": {}
        })
        
        expected = """================================================================================
RESPONSE:
Error: Task 'nonexistent_task' not found in stage 'browse'

================================================================================
ADDITIONAL CONTEXT:

WORKFLOW: stock_test
Description: Test stock workflow

STRUCTURE:
  - browse
  - portfolio

CURRENT POSITION: browse

CURRENT STATE:
{}

YOU MAY CHOOSE THE FOLLOWING ACTIONS:

1. ACTION CALLS (Tasks):
  Task: search
    Description: Search for stock
    Call Format:
      {
      "action": "method_call",
      "task": "search",
      "args": {
            "symbol": "<symbol>"
      }
}

  Task: add_to_cart
    Description: Add stock to cart
    Call Format:
      {
      "action": "method_call",
      "task": "add_to_cart",
      "args": {
            "symbol": "<symbol>",
            "quantity": 0
      }
}


2. STAGE CALLS (Transitions):
  Transition to: portfolio
    {"action": "stage_transition", "stage": "portfolio"}


You must ONLY respond with a single JSON. Do not add comments or extra text.
================================================================================"""
        
        assert response == expected
    
    asyncio.run(run())


def test_stock_workflow_invalid_transition():
    """Test invalid stage transition"""
    async def run():
        wf = StockWorkflow._workflow
        engine = LanguageEngine(wf, session_id="test-7")
        
        response = await engine.process({
            "action": "stage_transition",
            "stage": "nonexistent_stage"
        })
        
        assert isinstance(response, str)
        assert "Error: " in response
        assert "nonexistent_stage" in response
    
    asyncio.run(run())
