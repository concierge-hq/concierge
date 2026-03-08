"""MySQL Migration — Flat: all 9 tools exposed at once, model picks the order."""

import os
import json
from concierge import Concierge
from concierge.examples.tools import register_tools

upstream = json.loads(os.getenv("UPSTREAM_SERVERS", '["https://mcp.exa.ai/mcp"]'))

app = Concierge("mysql-migration-flat", host="0.0.0.0", upstream_servers=upstream)
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
