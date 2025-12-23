#!/usr/bin/env python3
"""OpenMCP CLI - Deploy MCP servers in seconds"""
import os
import sys
import json
import time
from pathlib import Path

API = os.getenv("OPENMCP_API", "https://api.openmcp-free.app")
CREDS = Path.home() / ".openmcp" / "credentials.json"

# Colors
def dim(s): return f"\033[2m{s}\033[0m"
def green(s): return f"\033[32m{s}\033[0m"
def cyan(s): return f"\033[36m{s}\033[0m"
def bold(s): return f"\033[1m{s}\033[0m"


def load_credentials():
    if CREDS.exists():
        return json.loads(CREDS.read_text())
    return None


def save_credentials(creds):
    CREDS.parent.mkdir(parents=True, exist_ok=True)
    CREDS.write_text(json.dumps(creds, indent=2))


def spinner(duration=0.5):
    """Simple spinner animation"""
    frames = ["◐", "◓", "◑", "◒"]
    end = time.time() + duration
    i = 0
    while time.time() < end:
        print(f"\r  {frames[i % 4]}", end="", flush=True)
        time.sleep(0.1)
        i += 1
    print("\r  ", end="", flush=True)


def login():
    """Authenticate with OpenMCP"""
    import webbrowser
    from secrets import token_urlsafe
    import httpx
    
    creds = load_credentials()
    if creds and creds.get("api_key"):
        print(f"\n  {green('✓')} Already authenticated\n")
        return creds["api_key"]

    session = token_urlsafe(16)
    url = f"{API}/login?session={session}"
    
    print(f"\n  {bold('☁  OpenMCP')}\n")
    print(f"  Opening browser to authenticate...\n")
    
    webbrowser.open(url)
    print(f"  {dim('If browser does not open, visit:')}")
    print(f"  {dim(url)}\n")
    
    print(f"  Waiting for authentication ", end="", flush=True)
    
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
    
    print(f"\r  Timeout. Please try again.        \n")
    sys.exit(1)


def deploy(project_path=".", project_id=None):
    """Deploy an MCP server"""
    import tarfile
    import tempfile
    import httpx
    
    start_total = time.time()
    
    creds = load_credentials()
    if not creds or not creds.get("api_key"):
        api_key = login()
    else:
        api_key = creds["api_key"]
    
    path = Path(project_path).resolve()
    
    if not project_id:
        project_id = path.name.lower().replace("_", "-").replace(" ", "-")
    
    print(f"\n  {bold('☁  Deploying')} {cyan(project_id)}\n")
    
    # Package
    start_pack = time.time()
    print(f"  Packaging...", end="", flush=True)
    
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        with tarfile.open(tmp.name, "w:gz") as tar:
            for item in path.iterdir():
                if item.name.startswith(".") or item.name in ("__pycache__", "node_modules", ".venv", "venv"):
                    continue
                tar.add(item, arcname=item.name)
        tmp_path = tmp.name
    
    size = os.path.getsize(tmp_path) / 1024
    pack_time = time.time() - start_pack
    print(f"\r  Packaged {dim(f'{size:.1f}KB')} {dim(f'({pack_time:.1f}s)')} {green('✓')}")
    
    # Upload
    start_upload = time.time()
    print(f"  Uploading...", end="", flush=True)
    
    try:
        with open(tmp_path, "rb") as f:
            r = httpx.post(
                f"{API}/deploy",
                params={"project_id": project_id},
                files={"file": ("project.tar.gz", f, "application/gzip")},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60
            )
        os.unlink(tmp_path)
        
        if r.status_code == 401:
            print(f"\r  {dim('○')} Session expired. Run: {cyan('openmcp login')}\n")
            sys.exit(1)
        
        if r.status_code != 200:
            print(f"\r  {dim('○')} Error: {r.text}\n")
            sys.exit(1)
        
        upload_time = time.time() - start_upload
        print(f"\r  Uploaded {dim(f'({upload_time:.1f}s)')} {green('✓')}         ")
        
        # Success
        data = r.json()
        total_time = time.time() - start_total
        
        print(f"\n  {green('●')} Live at {bold(data['url'])}")
        print(f"  ⚡ {dim(f'Deployed in {total_time:.1f}s')}")
        
        return project_id, api_key, data['url']
        
    except KeyboardInterrupt:
        print(f"\n\n  {dim('Cancelled')}\n")
        sys.exit(0)
    except httpx.TimeoutException:
        print(f"\r  {dim('○')} Timeout. Try again.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\r  {dim('○')} Error: {e}\n")
        sys.exit(1)


def stream_logs(project_id: str, api_key: str, url: str):
    """Stream logs from deployed project in a 4-line scrolling window"""
    import httpx
    
    # Gradient styles: oldest → newest (faded → bright)
    def fade0(s): return f"\033[38;5;239m{s}\033[0m"
    def fade1(s): return f"\033[38;5;244m{s}\033[0m"
    def fade2(s): return f"\033[38;5;250m{s}\033[0m"
    def fade3(s): return f"\033[38;5;255m{s}\033[0m"
    fades = [fade0, fade1, fade2, fade3]
    
    print(f"  {dim('╶───')}")
    print()
    print()
    print()
    print()
    sys.stdout.flush()
    
    lines = ["", "", "", ""]
    pulse = 0
    start_time = time.time()
    log_count = 0
    
    try:
        with httpx.stream(
            "GET",
            f"{API}/logs/{project_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=None
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
                        pulse = (pulse + 1) % 4
                        log_count += 1
                        indicators = ["◜", "◝", "◞", "◟"]
                        
                        print(f"\033[4A", end="")
                        for i, l in enumerate(lines):
                            prefix = indicators[pulse] if i == 3 else " "
                            styled = fades[i](l) if l else ""
                            print(f"\033[2K  {dim(prefix)} {styled}")
                        sys.stdout.flush()
    except KeyboardInterrupt:
        elapsed = int(time.time() - start_time)
        import random
        farewells = [
            "Ship it! 🚀", 
            "You're live. Now make history. ✨",
            "Go break the internet. 🔥",
            "You just leveled up. 🎮",
            "You shipped. The world noticed. 🌍",
            "That was fast. You're faster. ⚡",
            "You built this. Now watch it fly. 🚀",
            "You're unstoppable. Keep going. 💫",
            "Your code is live. Own it. 💪",
            "You did that. Legend. ✨",
        ]
        msg = random.choice(farewells)
        print(f"\033[4A", end="")  
        print(f"\033[J", end="")   
        print(f"  {dim(f'{log_count} logs · {elapsed}s')}")
        print(f"  {msg}\n")
    except Exception:
        pass


def logout():
    """Clear stored credentials"""
    if CREDS.exists():
        CREDS.unlink()
    print(f"\n  {green('✓')} Logged out\n")


def main():
    args = sys.argv[1:]
    
    if not args or args[0] in ("-h", "--help", "help"):
        print(f"""
  {bold('☁  OpenMCP')} {dim('— Deploy MCP servers in seconds')}

  {bold('Commands')}
    {cyan('login')}                    Authenticate with OpenMCP
    {cyan('deploy')} [path] [id]        Deploy current directory
    {cyan('deploy')} --logs [path] [id] Deploy and stream logs
    {cyan('logout')}                   Clear stored credentials

  {bold('Examples')}
    openmcp deploy
    openmcp deploy --logs
    openmcp deploy ./my-mcp custom-name
""")
        return
    
    cmd = args[0]
    
    if cmd == "login":
        login()
    elif cmd == "deploy":
        # Parse --logs flag
        show_logs = "--logs" in args
        remaining = [a for a in args[1:] if a != "--logs"]
        
        path = remaining[0] if len(remaining) > 0 else "."
        project_id = remaining[1] if len(remaining) > 1 else None
        
        result = deploy(path, project_id)
        
        if show_logs and result:
            proj_id, api_key, url = result
            stream_logs(proj_id, api_key, url)
    elif cmd == "logout":
        logout()
    else:
        print(f"\n  Unknown command: {cmd}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
