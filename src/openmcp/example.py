"""
"""

from mcp.server.fastmcp import FastMCP
from concierge.openmcp import OpenMCP, Config

server = OpenMCP(FastMCP(name="demo-server"))


@server.tool()
def search_users(query: str, limit: int = 10):
    return {"users": [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]}


@server.tool()
def get_user(user_id: int):
    """Get detailed user information by ID."""
    return {"id": user_id, "name": "John", "email": "john@example.com"}


@server.tool()
def update_user(user_id: int, name: str):
    """Update a user's profile information."""
    return {"success": True}


@server.tool()
def get_payment_errors(service: str, date: str):
    return {"errors": [{"code": "E001", "message": "Card declined"}]}


@server.tool()
def list_orders(customer_id: int, status: str = "all"):
    return {"orders": [{"id": 100, "status": "shipped"}]}


if __name__ == "__main__":
    server.run()
