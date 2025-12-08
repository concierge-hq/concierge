"""
Test server layer with stock exchange workflow.
Demonstrates server managing sessions and routing to language engines.
"""

import asyncio

from pydantic import BaseModel, Field

from concierge import SessionManager, State, construct, stage, task, workflow


@construct()
class Stock(BaseModel):
    """Stock selection"""

    symbol: str = Field(description="Stock symbol like AAPL, GOOGL")
    quantity: int = Field(ge=1, description="Number of shares")


@stage(name="browse", prerequisites=[])
class BrowseStage:
    """Browse and search stocks"""

    @task()
    def search(self, state: State, symbol: str = Field(description="Stock ticker", examples=["AAPL"])) -> dict:
        """Search for a stock"""
        return {"result": f"Found {symbol}: $150.00", "symbol": symbol, "price": 150.00}

    @task()
    def add_to_cart(
        self,
        state: State,
        symbol: str = Field(description="Stock ticker", examples=["AAPL"]),
        quantity: int = Field(description="Number of shares", examples=[10]),
    ) -> dict:
        """Add stock to cart"""
        state.set("symbol", symbol)
        state.set("quantity", quantity)
        return {"result": f"Added {quantity} shares of {symbol}"}


@stage(name="portfolio", prerequisites=[])
class PortfolioStage:
    """View portfolio"""

    @task()
    def view_holdings(self, state: State) -> dict:
        """View current holdings"""
        return {"result": "Holdings: AAPL: 10 shares"}


@workflow(name="stock_exchange", description="Simple stock trading")
class StockWorkflow:
    """Stock exchange workflow"""

    browse = BrowseStage
    portfolio = PortfolioStage

    transitions = {browse: [portfolio], portfolio: [browse]}


def test_server_create_session():
    """Test creating a new session"""
    workflow = StockWorkflow._workflow
    session_manager = SessionManager(workflow)

    session_id = session_manager.create_session()

    # Should return a UUID string
    assert isinstance(session_id, str)
    assert len(session_id) > 0
    assert session_id in session_manager.get_active_sessions()


def test_server_handle_task_request():
    """Test handling task execution request"""
    workflow = StockWorkflow._workflow
    session_manager = SessionManager(workflow)

    session_id = session_manager.create_session()

    response = asyncio.run(
        session_manager.handle_request(
            session_id, {"action": "method_call", "task": "search", "args": {"symbol": "AAPL"}}
        )
    )

    assert "search" in response
    assert "AAPL" in response
    assert "150.00" in response


def test_server_handle_transition():
    """Test handling stage transition"""
    workflow = StockWorkflow._workflow
    session_manager = SessionManager(workflow)

    session_id = session_manager.create_session()

    response = asyncio.run(
        session_manager.handle_request(session_id, {"action": "stage_transition", "stage": "portfolio"})
    )

    assert "portfolio" in response
    assert "Successfully transitioned" in response


def test_server_multiple_sessions():
    """Test managing multiple concurrent sessions"""
    workflow = StockWorkflow._workflow
    session_manager = SessionManager(workflow)

    session_1 = session_manager.create_session()
    session_2 = session_manager.create_session()

    active = session_manager.get_active_sessions()
    assert session_1 in active
    assert session_2 in active
    assert len(active) == 2
    assert session_1 != session_2


def test_server_terminate_session():
    """Test terminating a session"""
    workflow = StockWorkflow._workflow
    session_manager = SessionManager(workflow)

    session_id = session_manager.create_session()

    session_manager.terminate_session(session_id)
    assert session_id not in session_manager.get_active_sessions()


def test_server_session_isolation():
    """Test that sessions are isolated from each other"""

    async def run_test():
        workflow = StockWorkflow._workflow
        session_manager = SessionManager(workflow)

        session_1 = session_manager.create_session()
        session_2 = session_manager.create_session()

        response_1 = await session_manager.handle_request(
            session_1, {"action": "method_call", "task": "add_to_cart", "args": {"symbol": "AAPL", "quantity": 10}}
        )

        assert '"symbol": "AAPL"' in response_1
        assert '"quantity": 10' in response_1

        response_2 = await session_manager.handle_request(
            session_2, {"action": "method_call", "task": "add_to_cart", "args": {"symbol": "GOOGL", "quantity": 5}}
        )

        assert '"symbol": "GOOGL"' in response_2
        assert '"quantity": 5' in response_2

        active = session_manager.get_active_sessions()
        assert session_1 in active
        assert session_2 in active
        assert len(active) == 2

    asyncio.run(run_test())


def test_server_invalid_session_handle_request():
    """Test that invalid session raises KeyError on handle_request"""

    async def run_test():
        workflow = StockWorkflow._workflow
        session_manager = SessionManager(workflow)

        try:
            await session_manager.handle_request(
                "invalid-session-id", {"action": "method_call", "task": "search", "args": {"symbol": "AAPL"}}
            )
            assert False, "Should have raised KeyError"
        except KeyError as e:
            assert "invalid-session-id" in str(e)

    asyncio.run(run_test())


def test_server_invalid_session_terminate():
    """Test that invalid session raises KeyError on terminate"""
    workflow = StockWorkflow._workflow
    session_manager = SessionManager(workflow)

    try:
        session_manager.terminate_session("invalid-session-id")
        assert False, "Should have raised KeyError"
    except KeyError as e:
        assert "invalid-session-id" in str(e)
