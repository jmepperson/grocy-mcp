"""Core store (Grocy shopping location) listing functions."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient


async def stores_list(client: GrocyClient) -> str:
    """Return a formatted list of all stores (Grocy calls this 'shopping locations')."""
    stores = await client.get_objects("shopping_locations")
    if not stores:
        return "No stores found."

    lines = ["Stores:"]
    for store in stores:
        lines.append(f"  [{store['id']}] {store.get('name', '?')}")

    return "\n".join(lines)
