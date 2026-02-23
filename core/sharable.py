"""Sharable annotation for tool parameters that can receive upstream step outputs."""


class Sharable:
    """Mark a tool parameter as sharable.

    When a parameter is annotated with Sharable(), the LLM can either provide
    a literal value or reference an upstream step's output using @step_id.field
    syntax in a plan.

    Usage:
        from typing import Annotated
        from concierge.core.sharable import Sharable

        @app.tool()
        def get_weather(
            lat: Annotated[float, Sharable()],
            lon: Annotated[float, Sharable()],
            start_date: str = None,
        ):
            ...
    """

    pass
