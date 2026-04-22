"""MySQL Migration — Code: all tools wrapped into a single execute_code tool."""

import os
from concierge import Concierge, Config, ProviderType
from concierge.examples.tools import register_tools

app = Concierge(
    "mysql-migration-code",
    config=Config(provider_type=ProviderType.CODE),
    host="0.0.0.0",
)
register_tools(app)


http_app = app.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    from starlette.middleware.cors import CORSMiddleware

    http_app = CORSMiddleware(
        http_app,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(http_app, host="0.0.0.0", port=port)
