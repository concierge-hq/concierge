"""Test Zillow workflow."""

import asyncio

from concierge.engine import LanguageEngine
from examples.zillow.workflow import ZillowWorkflow


async def test_workflow_execution():
    """Test complete workflow: intelligence → analytics → inspection → negotiation"""
    workflow = ZillowWorkflow._workflow
    engine = LanguageEngine(workflow, session_id="test-001")

    result = await engine.process(
        {
            "action": "method_call",
            "task": "search_listings",
            "args": {"location": "Phoenix, AZ", "max_price": 450000, "filters": {}},
        }
    )
    assert "Phoenix, AZ" in result
    assert "Zillow API" in result

    await engine.process({"action": "stage_transition", "stage": "analytics"})
    result = await engine.process(
        {"action": "method_call", "task": "run_monte_carlo", "args": {"property_id": "prop-001", "simulations": 1000}}
    )
    assert "Monte Carlo" in result
    assert "IRR" in result

    await engine.process({"action": "stage_transition", "stage": "inspection"})
    result = await engine.process(
        {
            "action": "method_call",
            "task": "schedule_inspectors",
            "args": {"property_id": "prop-001", "inspection_types": ["general", "structural"]},
        }
    )
    assert "Scheduled" in result

    await engine.process({"action": "stage_transition", "stage": "negotiation"})
    result = await engine.process(
        {
            "action": "method_call",
            "task": "submit_offer",
            "args": {"property_id": "prop-001", "offer_price": 395000, "contingencies": ["inspection"]},
        }
    )
    assert "Offer submitted" in result
    assert "395000" in result

    print("All tests passed")


async def test_portfolio_tasks():
    """Test portfolio stage tasks"""
    workflow = ZillowWorkflow._workflow
    engine = LanguageEngine(workflow, session_id="test-002")

    await engine.process({"action": "stage_transition", "stage": "portfolio"})

    result = await engine.process({"action": "method_call", "task": "detect_refi_opportunities", "args": {}})
    assert "Refi opportunity" in result

    result = await engine.process(
        {"action": "method_call", "task": "simulate_rebalance", "args": {"constraints": {"max_sell": 1, "min_roi": 15}}}
    )
    assert "Rebalance" in result
    assert "1031" in result

    print("Portfolio tests passed")


if __name__ == "__main__":
    asyncio.run(test_workflow_execution())
    asyncio.run(test_portfolio_tasks())
