"""Zillow workflow - composes stages into workflow graph."""

from concierge.core import StateTransfer, workflow
from examples.zillow.stages import (
    Analytics,
    Inspection,
    Intelligence,
    Negotiation,
    Portfolio,
)


@workflow(name="zillow", description="Real estate investment automation")
class ZillowWorkflow:
    """
    Real estate investment workflow implementing Concierge for agentic transcations
    """

    intelligence = Intelligence
    analytics = Analytics
    inspection = Inspection
    negotiation = Negotiation
    portfolio = Portfolio

    transitions = {
        intelligence: [analytics, inspection, portfolio],
        analytics: [intelligence, inspection, negotiation],
        inspection: [negotiation, analytics],
        negotiation: [intelligence, portfolio],
        portfolio: [intelligence, analytics],
    }

    state_management = [
        (intelligence, analytics, StateTransfer.ALL),
        (analytics, inspection, StateTransfer.ALL),
        (inspection, negotiation, StateTransfer.ALL),
        (negotiation, portfolio, StateTransfer.ALL),
    ]
