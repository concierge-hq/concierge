#!/usr/bin/env python3
"""Concierge CLI - Structured AI workflows with staged tool execution"""

import os
import sys
import json
import time
import shutil
from pathlib import Path

API = os.getenv("CONCIERGE_API", "https://getconcierge.app")
CREDS = Path.home() / ".concierge" / "credentials.json"
VERSION = "0.4.0"

# Basic MCP template (non-chatgpt) - Shopping workflow with 3 stages
TEMPLATE_MAIN = '''"""Shopping workflow with Concierge stages."""
import os
from concierge import Concierge

app = Concierge("{name}")


# ═══════════════════════════════════════════════════════════════════════════════
# Stage: browse — Search and discover products
# ═══════════════════════════════════════════════════════════════════════════════

@app.tool()
def search_products(query: str = "") -> dict:
    """Search for products in the catalog."""
    products = [
        {{"id": "p1", "name": "Laptop", "price": 999}},
        {{"id": "p2", "name": "Mouse", "price": 29}},
        {{"id": "p3", "name": "Keyboard", "price": 79}},
    ]
    if query:
        products = [p for p in products if query.lower() in p["name"].lower()]
    return {{"products": products}}


# ═══════════════════════════════════════════════════════════════════════════════
# Stage: cart — Manage shopping cart
# ═══════════════════════════════════════════════════════════════════════════════

@app.tool()
def add_to_cart(product_id: str, quantity: int = 1) -> dict:
    """Add a product to the shopping cart."""
    cart = app.get_state("cart", [])
    cart.append({{"product_id": product_id, "quantity": quantity}})
    app.set_state("cart", cart)
    return {{"status": "added", "cart": cart}}


@app.tool()
def view_cart() -> dict:
    """View the current shopping cart."""
    return {{"cart": app.get_state("cart", [])}}


# ═══════════════════════════════════════════════════════════════════════════════
# Stage: checkout — Complete the purchase
# ═══════════════════════════════════════════════════════════════════════════════

@app.tool()
def checkout(payment_method: str) -> dict:
    """Complete the checkout process."""
    cart = app.get_state("cart", [])
    if not cart:
        return {{"status": "error", "message": "Cart is empty"}}
    order_id = f"ORD-{{len(cart) * 1000}}"
    app.set_state("cart", [])
    return {{"order_id": order_id, "status": "confirmed"}}


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow: browse → cart → checkout
# ═══════════════════════════════════════════════════════════════════════════════

app.stages = {{
    "browse": ["search_products"],
    "cart": ["add_to_cart", "view_cart"],
    "checkout": ["checkout"],
}}

app.transitions = {{
    "browse": ["cart"],
    "cart": ["browse", "checkout"],
    "checkout": [],
}}


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
    print(f"Starting server on http://localhost:{{port}}/mcp", flush=True)
    uvicorn.run(http_app, host="0.0.0.0", port=port)
'''

TEMPLATE_README = """# {name}

Shopping workflow with Concierge stages: `browse` → `cart` → `checkout`

## Run locally

```bash
pip install -r requirements.txt
python main.py
```

Server starts at `http://localhost:8000/mcp`

## Deploy

```bash
concierge deploy
```

## Workflow

| Stage | Tools | Next |
|-------|-------|------|
| browse | `search_products` | cart |
| cart | `add_to_cart`, `view_cart` | browse, checkout |
| checkout | `checkout` | — |

Agents cannot call `checkout` before adding items to cart.
"""

TEMPLATE_REQUIREMENTS = """concierge-sdk
uvicorn
starlette
"""


# Colors
def dim(s):
    return f"\033[2m{s}\033[0m"


def green(s):
    return f"\033[32m{s}\033[0m"


def cyan(s):
    return f"\033[36m{s}\033[0m"


def bold(s):
    return f"\033[1m{s}\033[0m"


def generate_project_id(name):
    """Generate unique project ID: name + random suffix"""
    import random
    import string

    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    clean_name = name.lower().replace("_", "-").replace(" ", "-")[:20]
    return f"{clean_name}-{suffix}"


def get_settings_json(project_id):
    return json.dumps(
        {
            "command": "python main.py",
            "project_id": project_id,
            "state_backend": "postgres",
        },
        indent=2,
    )


def load_credentials():
    if CREDS.exists():
        return json.loads(CREDS.read_text())
    return None


def save_credentials(creds):
    CREDS.parent.mkdir(parents=True, exist_ok=True)
    CREDS.write_text(json.dumps(creds, indent=2))


def get_templates_dir():
    """Get path to bundled templates directory"""
    import importlib.resources

    return importlib.resources.files("concierge") / "templates"


def login():
    """Authenticate with Concierge"""
    from secrets import token_urlsafe
    import httpx

    creds = load_credentials()
    if creds and creds.get("api_key"):
        print(f"\n  {green('✓')} Already authenticated\n")
        return creds["api_key"]

    session = token_urlsafe(16)
    url = f"{API}/login?session={session}&mode=cli"

    print(f"\n  {bold('☁  Concierge')}\n")
    print("  Opening browser to authenticate...\n")

    # webbrowser.open(url)
    print(f"  {dim('If browser does not open, visit:')}")
    print(f"  {dim(url)}\n")

    print("  Waiting for authentication ", end="", flush=True)

    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    for _ in range(120):
        print(f"\r  Waiting for authentication {frames[i % 10]}", end="", flush=True)
        time.sleep(1)
        i += 1

        r = httpx.get(f"{API}/auth/status", params={"session": session}, timeout=5)
        data = r.json()
        if data.get("status") == "complete":
            api_key = data["api_key"]
            save_credentials({"api_key": api_key})
            print(f"\r  {green('✓')} Authenticated                    \n")
            return api_key

    print("\r  Timeout. Please try again.        \n")
    sys.exit(1)


def logout(quiet=False):
    """Clear stored credentials"""
    if CREDS.exists():
        CREDS.unlink()
    if not quiet:
        print(f"\n  {green('✓')} Logged out\n")


def deploy(project_path="."):
    """Deploy an MCP server"""
    import tarfile
    import tempfile
    import httpx

    start_total = time.time()
    path = Path(project_path).resolve()

    # settings.json is required
    settings_file = path / "settings.json"
    if not settings_file.exists():
        print(f"\n  {dim('Error:')} settings.json not found")
        print(f"  {dim('Run:')} concierge init\n")
        sys.exit(1)

    try:
        settings = json.loads(settings_file.read_text())
        project_id = settings.get("project_id")
        if not project_id:
            print(f"\n  {dim('Error:')} project_id missing in settings.json\n")
            sys.exit(1)
    except json.JSONDecodeError:
        print(f"\n  {dim('Error:')} Invalid settings.json\n")
        sys.exit(1)

    creds = load_credentials()
    if not creds or not creds.get("api_key"):
        api_key = login()
    else:
        api_key = creds["api_key"]

    print(f"\n  {bold('☁  Deploying')} {cyan(project_id)}\n")

    # Package (exclude node_modules, dist, venv, etc)
    time.time()
    print("  Packaging...", end="", flush=True)

    skip = {"__pycache__", "node_modules", "dist", ".venv", "venv", ".git"}

    def add_filtered(tar, item, arcname):
        if item.name.startswith(".") or item.name in skip:
            return
        if item.is_file():
            tar.add(item, arcname=arcname)
        elif item.is_dir():
            for sub in item.iterdir():
                add_filtered(tar, sub, f"{arcname}/{sub.name}")

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        with tarfile.open(tmp.name, "w:gz") as tar:
            for item in path.iterdir():
                add_filtered(tar, item, item.name)
        tmp_path = tmp.name

    size = os.path.getsize(tmp_path) / 1024
    print(f"\r  Packaged {dim(f'{size:.1f}KB')} {green('✓')}")

    # Upload
    print("  Uploading...", end="", flush=True)

    try:
        with open(tmp_path, "rb") as f:
            r = httpx.post(
                f"{API}/deploy",
                params={"project_id": project_id},
                files={"file": ("project.tar.gz", f, "application/gzip")},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60,
            )
        os.unlink(tmp_path)

        if r.status_code == 401:
            print(f"\r  {dim('○')} Session expired, re-authenticating...\n")
            logout(quiet=True)
            api_key = login()
            return deploy(project_path)

        if r.status_code != 200:
            print(f"\r  {dim('○')} Error: {r.text}\n")
            sys.exit(1)

        print(f"\r  Uploaded {green('✓')}              ")

        data = r.json()
        total_time = time.time() - start_total

        print(f"\n  {green('●')} Live at {bold(data['url'])}")
        print(f"  ⚡ {dim(f'Deployed in {total_time:.1f}s')}")

        return project_id, api_key, data["url"]

    except KeyboardInterrupt:
        print(f"\n\n  {dim('Cancelled')}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\r  {dim('○')} Error: {e}\n")
        sys.exit(1)


def stream_logs(project_id: str, api_key: str, url: str = None):
    """Stream logs from deployed project"""
    import httpx

    fade = [
        lambda s: f"\033[38;5;239m{s}\033[0m",
        lambda s: f"\033[38;5;244m{s}\033[0m",
        lambda s: f"\033[38;5;250m{s}\033[0m",
        lambda s: f"\033[38;5;255m{s}\033[0m",
    ]

    print(f"  {dim('╶───')}\n\n\n\n")
    lines = ["", "", "", ""]

    try:
        with httpx.stream(
            "GET",
            f"{API}/logs/{project_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(connect=30, read=300, write=30, pool=30),
        ) as r:
            if r.status_code != 200:
                print(f"\033[4A\033[2K  {dim('Could not connect')}")
                return

            buffer = ""
            for chunk in r.iter_bytes():
                buffer += chunk.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        lines = lines[1:] + [line[:72]]
                        print("\033[4A", end="")
                        for i, log_line in enumerate(lines):
                            print(f"\033[2K  {fade[i](log_line) if log_line else ''}")
    except KeyboardInterrupt:
        print(f"\033[4A\033[J  {dim('Done')}\n")
    except httpx.RemoteProtocolError:
        print(
            f"\033[4A\033[J  {dim('Connection closed (build may still be running)')}\n"
        )
        if url:
            print(f"  {dim('Check status:')} curl {url}\n")


def logs(project_id_arg: str = None):
    """Stream logs for a project. If no project_id provided, use current directory's settings.json"""

    # Get project_id
    if project_id_arg:
        project_id = project_id_arg
    else:
        # Try to read from current directory's settings.json
        settings_path = Path.cwd() / "settings.json"
        if not settings_path.exists():
            print(f"\n  {dim('Error:')} No settings.json in current directory.")
            print(f"  {dim('Usage:')} concierge logs <project_id>")
            print(f"  {dim('   or:')} cd into a project directory\n")
            sys.exit(1)

        try:
            settings = json.loads(settings_path.read_text())
            project_id = settings.get("project_id")
            if not project_id:
                print(f"\n  {dim('Error:')} No project_id in settings.json\n")
                sys.exit(1)
        except json.JSONDecodeError:
            print(f"\n  {dim('Error:')} Invalid settings.json\n")
            sys.exit(1)

    # Get credentials
    creds = load_credentials()
    if not creds or not creds.get("api_key"):
        api_key = login()
    else:
        api_key = creds["api_key"]

    print(f"\n  {bold('☁  Streaming logs')} {cyan(project_id)}\n")
    print(f"  {dim('Press Ctrl+C to stop')}\n")

    stream_logs(project_id, api_key)


def init(name="concierge-app", chatgpt=False):
    """Scaffold a new MCP server project"""
    project_dir = Path.cwd() / name

    if project_dir.exists():
        print(f"\n  {dim('Error:')} Directory {bold(name)} already exists\n")
        sys.exit(1)

    project_id = generate_project_id(name)

    print(f"\nConcierge CLI {VERSION}")
    print(f"Scaffolding project {green('✓')}")

    if chatgpt:
        # Copy entire chatgpt template
        templates_dir = get_templates_dir()
        chatgpt_template = templates_dir / "chatgpt"
        shutil.copytree(chatgpt_template, project_dir)
    else:
        # Basic MCP server
        project_dir.mkdir()
        (project_dir / "main.py").write_text(TEMPLATE_MAIN.format(name=name))
        (project_dir / "README.md").write_text(TEMPLATE_README.format(name=name))
        (project_dir / "requirements.txt").write_text(TEMPLATE_REQUIREMENTS)

    # Always write settings.json with unique project_id
    (project_dir / "settings.json").write_text(get_settings_json(project_id))

    print(f"> Success! Created {bold(name)}")
    print(f"\n  {dim('$')} cd {name}")
    print(f"  {dim('$')} concierge deploy\n")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(f"""
  {bold("☁  Concierge")} {dim("— Structured AI workflows with staged tool execution")}

  {bold("Commands")}
    {cyan("init")} [name]              Create a new MCP server project
    {cyan("init")} --chatgpt [name]    Create a ChatGPT widget app
    {cyan("deploy")} [path]             Deploy project
    {cyan("deploy")} --logs [path]      Deploy and stream logs
    {cyan("logs")} [project_id]        Stream logs (uses current dir if no id)
    {cyan("login")}                    Authenticate with Concierge
    {cyan("logout")}                   Clear stored credentials

  {bold("Quick Start")}
    concierge init
    cd concierge-app
    concierge deploy
""")
        return

    cmd = args[0]

    if cmd == "init":
        chatgpt = "--chatgpt" in args
        remaining = [a for a in args[1:] if not a.startswith("--")]
        name = remaining[0] if remaining else "concierge-app"
        init(name, chatgpt=chatgpt)
    elif cmd == "login":
        login()
    elif cmd == "deploy":
        show_logs = "--logs" in args
        remaining = [a for a in args[1:] if a != "--logs"]
        path = remaining[0] if remaining else "."
        result = deploy(path)
        if show_logs and result:
            stream_logs(*result)
    elif cmd == "logs":
        project_id_arg = args[1] if len(args) > 1 else None
        logs(project_id_arg)
    elif cmd == "logout":
        logout()
    else:
        print(f"\n  Unknown command: {cmd}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
