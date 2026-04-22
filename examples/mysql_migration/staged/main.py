"""MySQL Migration — Staged: progressive tool disclosure via stages + transitions."""

import os
from concierge import Concierge
from concierge.examples.tools import register_tools

app = Concierge("mysql-migration-staged", host="0.0.0.0")
register_tools(app)

app.stages = {
    "preflight": ["preflight_check"],
    "drain": ["drain_connections"],
    "backup": ["create_backup", "validate_backup"],
    "migrate": ["apply_migration"],
    "verify": ["run_smoke_tests"],
    "release": ["undrain_connections", "notify_stakeholders"],
    "finalize": ["finalize_migration"],
}

app.transitions = {
    "preflight": ["drain"],
    "drain": ["backup"],
    "backup": ["migrate"],
    "migrate": ["verify"],
    "verify": ["release"],
    "release": ["finalize"],
    "finalize": [],
}


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
