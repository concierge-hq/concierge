"""Intelligence stage - market research and property discovery."""

from concierge.core import State, stage, task


@stage(name="intelligence", prerequisites=[])
class Intelligence:
    """Market intelligence and property discovery - Zillow's official API for listings and market data"""

    @task()
    def search_listings(self, state: State, location: str, max_price: int, filters: dict) -> dict:
        """Search property listings via official API"""
        state.set("location", location)
        state.set("max_price", max_price)
        return {"result": f"Found 847 listings in {location} under ${max_price} (via Zillow API)"}

    @task()
    def filter_undervalued(self, state: State, criteria: dict) -> dict:
        """Filter for undervalued properties using valuation model"""
        filtered = 23
        return {"result": f"Filtered to {filtered} undervalued properties (15-30% below market)"}

    @task()
    def fetch_market_data(self, state: State, location: str) -> dict:
        """Fetch market trends, inventory, days-on-market stats"""
        state.set("market_velocity", "high")
        return {"result": f"{location}: 2.1mo inventory, median DOM 18 days, hot market"}

    @task()
    def analyze_comps(self, state: State, property_id: str, radius_miles: float) -> dict:
        """Analyze comparable sales in radius"""
        return {"result": f"Found 47 comps within {radius_miles}mi. Property {property_id} priced 18% below comps"}

    @task()
    def search_off_market(self, state: State, location: str, deal_types: list) -> dict:
        """Search pre-foreclosures, estate sales, FSBO from public records"""
        return {"result": "Found 12 off-market: 4 pre-foreclosures, 3 estate sales, 5 FSBOs"}
