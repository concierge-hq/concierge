"""MySQL Migration — Plan: all tools wrapped into a single execute_plan tool."""

import os
from concierge import Concierge, Config, ProviderType
from concierge.examples.tools import register_tools

app = Concierge(
    "mysql-migration-plan",
    config=Config(provider_type=ProviderType.PLAN),
    host="0.0.0.0",
)
register_tools(app)


http_app = app.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware

    http_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(http_app, host="0.0.0.0", port=port)
