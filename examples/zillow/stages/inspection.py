"""Inspection stage - property due diligence and repair estimation."""
from pydantic import BaseModel, Field
from concierge.core import construct, State, task, stage


@construct()
class PropertyCriteria(BaseModel):
    """Search criteria"""
    location: str = Field(description="City or zip code")
    max_price: int = Field(description="Maximum price")


@stage(name="inspection", prerequisites=[PropertyCriteria])
class Inspection:
    """Property inspection orchestration - schedules inspectors, estimates repairs"""
    
    @task()
    def schedule_inspectors(self, state: State, property_id: str, inspection_types: list) -> dict:
        """Schedule general, structural, pest, radon inspectors"""
        state.set("inspection_date", "2024-11-02")
        return {"result": f"Scheduled {len(inspection_types)} inspectors for Sat 10am: general, structural, pest"}
    
    @task()
    def get_contractor_quotes(self, state: State, property_id: str, repairs: list) -> dict:
        """Get contractor quotes for identified repairs"""
        return {"result": f"Quotes received: Roof $12k, HVAC $5.2k, Foundation $8.1k. Total: $25.3k"}
    
    @task()
    def generate_repair_matrix(self, state: State, property_id: str) -> dict:
        """Generate repair priority: safety, structural, cosmetic"""
        return {"result": "Priority: Safety (0), Structural ($8.1k), Cosmetic ($5k). Critical: $8.1k"}
    
    @task()
    def calculate_leverage(self, state: State, property_id: str, repair_cost: int) -> dict:
        """Calculate negotiation leverage from inspection"""
        state.set("negotiation_amount", repair_cost)
        return {"result": f"Leverage: Request ${repair_cost} credit (or 5% price reduction)"}



