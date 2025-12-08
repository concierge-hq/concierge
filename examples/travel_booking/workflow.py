from concierge.core import State, stage, task, workflow


@stage(name="search")
class SearchStage:
    @task(description="Search flights")
    def search_flights(self, state: State, origin: str, destination: str, date: str) -> dict:
        return {"flights": []}

    @task(description="Search hotels")
    def search_hotels(self, state: State, location: str, checkin: str, checkout: str) -> dict:
        return {"hotels": []}

    @task(description="Filter by price or amenities")
    def filter_results(self, state: State, max_price: float) -> dict:
        return {"filtered": []}


@stage(name="details")
class DetailsStage:
    @task(description="View flight details")
    def view_flight_details(self, state: State, flight_id: str) -> dict:
        return {"flight": {}}

    @task(description="View hotel details")
    def view_hotel_details(self, state: State, hotel_id: str) -> dict:
        return {"hotel": {}}


@stage(name="booking")
class BookingStage:
    @task(description="Add flight to itinerary")
    def add_flight(self, state: State, flight_id: str) -> dict:
        return {"added": True}

    @task(description="Add hotel to itinerary")
    def add_hotel(self, state: State, hotel_id: str, rooms: int) -> dict:
        return {"added": True}

    @task(description="Review itinerary")
    def review_itinerary(self, state: State) -> dict:
        return {"total_cost": 0}


@stage(name="checkout", prerequisites=["itinerary.items"])
class CheckoutStage:
    @task(description="Add traveler information")
    def add_travelers(self, state: State, travelers: list) -> dict:
        return {"saved": True}

    @task(description="Complete booking")
    def complete_booking(self, state: State) -> dict:
        return {"booking_id": "EXP123"}


@workflow(name="travel_booking")
class TravelBookingWorkflow:
    search = SearchStage
    details = DetailsStage
    booking = BookingStage
    checkout = CheckoutStage

    transitions = {search: [details], details: [booking, search], booking: [checkout, search], checkout: []}
