#!/usr/bin/env python3
"""
Concierge Chat Client - CLI tool to chat with remote Concierge workflows via router
"""
import sys
import requests
from pathlib import Path

# Add parent directory to path to import ConciergeSession
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "router"))

from debug_session import ConciergeSession


def fetch_workflows_from_router(router_url: str) -> list:
    """Fetch available workflows from router"""
    try:
        response = requests.get(f"{router_url}/api/workflows", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Convert router format to ConciergeSession format
        workflows = []
        for wf in data.get("workflows", []):
            workflows.append({
                "name": wf.get("name", ""),
                "description": wf.get("description", ""),
                "url": wf.get("execute_url") or wf.get("url", ""),
                "execute_url": wf.get("execute_url"),
                "mcp_initialize_url": wf.get("mcp_initialize_url"),
                "mcp_tools_list_url": wf.get("mcp_tools_list_url"),
                "mcp_call_url": wf.get("mcp_call_url"),
            })
        return workflows
    except Exception as e:
        print(f"[ERROR] Failed to fetch workflows from router: {e}")
        return []


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Concierge Chat Client")
    parser.add_argument("--router-url", required=True, help="Router URL (e.g., http://localhost:8090)")
    parser.add_argument("--api-base", required=True, help="OpenAI API base URL")
    parser.add_argument("--api-key", required=True, help="OpenAI API key")
    parser.add_argument("--model", default="gpt-4-turbo", help="Model name")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--protocol",
        choices=["aip", "mcp"],
        default="aip",
        help="Protocol for workflow execution (default: aip)",
    )
    
    args = parser.parse_args()
    
    # Create ConciergeSession
    client = ConciergeSession(
        api_base=args.api_base,
        api_key=args.api_key,
        model=args.model or "gpt-4-turbo",
        verbose=args.verbose,
        protocol=args.protocol,
    )
    
    # Fetch workflows from router and set them
    print(f"[CONNECTING] Fetching workflows from {args.router_url}...")
    workflows = fetch_workflows_from_router(args.router_url)
    if workflows:
        client.set_available_workflows(workflows)
        print(f"[READY] Found {len(workflows)} workflow(s)")
        for wf in workflows:
            print(f"  - {wf['name']}: {wf.get('description', 'No description')}")
    else:
        print("[WARNING] No workflows found. You can still search manually.")
    
    print("\n" + "=" * 60)
    print("Concierge Chat Client")
    print(f"Router: {args.router_url}")
    print(f"Model: {args.model or 'gpt-4-turbo'}")
    print("=" * 60)
    print("Type 'exit' to quit\n")
    
    # Interactive chat loop
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                break
            
            # Refresh workflows before each turn (in case new ones were deployed)
            workflows = fetch_workflows_from_router(args.router_url)
            if workflows:
                client.set_available_workflows(workflows)
            
            response = client.chat(user_input)
            print(f"\nAssistant: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}\n")
            if args.verbose:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()

