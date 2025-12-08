from concierge.core import State, stage, task, workflow


@stage(name="location")
class LocationStage:
    @task(description="Set pickup location")
    def set_pickup(self, state: State, address: str) -> dict:
        return {"pickup": address}

    @task(description="Set destination")
    def set_destination(self, state: State, address: str) -> dict:
        return {"destination": address}


@stage(name="selection", prerequisites=["pickup", "destination"])
class SelectionStage:
    @task(description="View available ride options")
    def view_options(self, state: State) -> dict:
        return {"options": []}

    @task(description="Select ride type")
    def select_ride(self, state: State, ride_type: str) -> dict:
        return {"selected": ride_type, "price": 15.99}


@stage(name="booking", prerequisites=["ride_type"])
class BookingStage:
    @task(description="Confirm and request ride")
    def request_ride(self, state: State) -> dict:
        return {"ride_id": "RIDE123", "eta": 5}

    @task(description="Cancel ride request")
    def cancel_ride(self, state: State) -> dict:
        return {"cancelled": True}


@stage(name="tracking")
class TrackingStage:
    @task(description="Track driver location")
    def track_driver(self, state: State, ride_id: str) -> dict:
        return {"driver_location": {}, "eta": 3}

    @task(description="Contact driver")
    def contact_driver(self, state: State, ride_id: str) -> dict:
        return {"contacted": True}


@workflow(name="ride_sharing")
class RideSharingWorkflow:
    location = LocationStage
    selection = SelectionStage
    booking = BookingStage
    tracking = TrackingStage

    transitions = {location: [selection], selection: [booking, location], booking: [tracking], tracking: []}
