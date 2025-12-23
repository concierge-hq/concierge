# Concierge V0.2
"""Concierge CLI"""
import click
import sys
import yaml
from pathlib import Path
# from concierge_clients.client_tool_calling import ToolCallingClient 
# (ToolCallingClient is for the client CLI, which we might not need in the worker image, but let's leave it for now)
# Assuming concierge_clients is available.
from .main import start_server_from_config, start_server
@click.group()
def cli():
    """Concierge - Agentic Web Interfaces"""
    pass

@cli.command()
@click.option('--config', default='concierge.yaml', help='Config file path')
def serve(config):
    """Start Concierge server from config file"""
    config_path = Path(config).resolve()
    if not config_path.exists():
        click.echo(f"Error: Config file not found: {config}", err=True)
        sys.exit(1)
    
    start_server_from_config(str(config_path))

@cli.command()
@click.option('--router-url', default='http://localhost:8090', help='Router URL (default: http://localhost:8090)')
@click.option('--api-base', required=True, help='OpenAI API base URL')
@click.option('--api-key', required=True, help='OpenAI API key')
@click.option('--model', default='gpt-4-turbo', help='Model name')
@click.option('--verbose', is_flag=True, help='Show detailed logs')
def chat(router_url, api_base, api_key, model, verbose):
    """Start interactive chat with Concierge workflows via router"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "router"))
    from debug_session import ConciergeSession
    import requests
    
    click.echo(f"Connecting to router: {router_url}")
    click.echo(f"Model: {model} via {api_base}")
    
    # Create ConciergeSession
    client = ConciergeSession(
        api_base=api_base,
        api_key=api_key,
        model=model,
        verbose=verbose,
    )
    
    # Fetch workflows from router
    try:
        response = requests.get(f"{router_url}/api/workflows", timeout=10)
        response.raise_for_status()
        data = response.json()
        workflows = []
        for wf in data.get("workflows", []):
            # Router returns worker_url, convert to execute endpoint
            worker_url = wf.get("worker_url", "")
            execute_url = f"{worker_url}/execute" if worker_url else ""
            workflows.append({
                "name": wf.get("name", ""),
                "description": wf.get("description", ""),
                "url": execute_url,
            })
        client.set_available_workflows(workflows)
        click.echo(f"Found {len(workflows)} workflow(s)")
    except Exception as e:
        click.echo(f"Warning: Failed to fetch workflows: {e}", err=True)
        click.echo("You can still search manually\n")
    
    click.echo("Type 'exit' to quit\n")
    
    # Interactive chat loop
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                break
            
            # Refresh workflows before each turn
            try:
                response = requests.get(f"{router_url}/api/workflows", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    workflows = []
                    for wf in data.get("workflows", []):
                        worker_url = wf.get("worker_url", "")
                        execute_url = f"{worker_url}/execute" if worker_url else ""
                        workflows.append({
                            "name": wf.get("name", ""),
                            "description": wf.get("description", ""),
                            "url": execute_url,
                        })
                    client.set_available_workflows(workflows)
            except:
                pass  # Continue with existing workflows
            
            response = client.chat(user_input)
            click.echo(f"\nAssistant: {response}\n")
            
        except KeyboardInterrupt:
            click.echo("\n\nExiting...")
            break
        except Exception as e:
            click.echo(f"\nError: {e}\n", err=True)
            if verbose:
                import traceback
                traceback.print_exc()

if __name__ == '__main__':
    cli()

