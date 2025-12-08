"""Concierge CLI"""

import sys
from pathlib import Path

import click
import yaml

from concierge.server import start_server_from_config
from concierge_clients.client_tool_calling import ToolCallingClient


@click.group()
def cli():
    """Concierge - Agentic Web Interfaces"""
    pass


@cli.command()
@click.option("--config", default="concierge.yaml", help="Config file path")
def serve(config):
    """Start Concierge server from config file"""
    config_path = Path(config).resolve()
    if not config_path.exists():
        click.echo(f"Error: Config file not found: {config}", err=True)
        sys.exit(1)

    start_server_from_config(str(config_path))


@cli.command()
@click.option("--config", default="concierge.yaml", help="Config file path")
@click.option("--api-base", required=True, help="OpenAI API base URL")
@click.option("--api-key", required=True, help="OpenAI API key")
@click.option("--verbose", is_flag=True, help="Show detailed logs")
def chat(config, api_base, api_key, verbose):
    """Start interactive chat with Concierge server"""
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"Error: Config file not found: {config}")
        return

    config_data = yaml.safe_load(config_path.read_text())
    host = config_data.get("server", {}).get("host", "0.0.0.0")
    port = config_data.get("server", {}).get("port", 8082)

    click.echo(f"Connecting to: http://{host}:{port}")
    click.echo(f"Model: gpt-5 via {api_base}")
    click.echo("Type 'exit' to quit\n")

    client = ToolCallingClient(api_base, api_key, verbose=verbose)
    client.concierge_url = f"http://{host}:{port}"
    client.run()


if __name__ == "__main__":
    cli()
