"""Negotiation stage - offer strategy and multi-round negotiation."""
from pydantic import BaseModel, Field
from concierge.core import construct, State, task, stage


@construct()
class PropertyCriteria(BaseModel):
    """Search criteria"""
    location: str = Field(description="City or zip code")
    max_price: int = Field(description="Maximum price")


@stage(name="negotiation", prerequisites=[PropertyCriteria])
class Negotiation:
    """Offer negotiation - game theory, multi-round strategy, contingency management"""
    
    @task()
    def analyze_seller_motivation(self, state: State, property_id: str) -> dict:
        """Analyze days-on-market, price reductions, seller situation"""
        state.set("seller_motivation", "high")
        return {"result": "Seller: 68 days on market, 2 price drops (-8%), estate sale. High motivation"}
    
    @task()
    def calculate_batna(self, state: State, property_id: str) -> dict:
        """Calculate best alternative to negotiated agreement"""
        return {"result": "BATNA: 3 comparable properties available. Walk-away price: $395k"}
    
    @task()
    def submit_offer(self, state: State, property_id: str, offer_price: int, contingencies: list) -> dict:
        """Submit initial offer with contingencies"""
        state.set("offer_price", offer_price)
        state.set("offer_contingencies", contingencies)
        return {"result": f"Offer submitted: ${offer_price} with contingencies: {', '.join(contingencies)}"}
    
    @task()
    def handle_counteroffer(self, state: State, counter_price: int, strategy: str) -> dict:
        """Handle seller counteroffer with game theory strategy"""
        return {"result": f"Counter at ${counter_price}. Strategy: Split difference, remove appraisal contingency"}
    
    @task()
    def negotiate_repairs(self, state: State, repair_amount: int) -> dict:
        """Negotiate repair credits post-inspection"""
        return {"result": f"Negotiated: ${repair_amount} seller credit for repairs. Closing proceeds"}



