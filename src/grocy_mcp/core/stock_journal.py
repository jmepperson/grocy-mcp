"""Core stock journal/history functions for Grocy."""

from __future__ import annotations

from grocy_mcp.client import GrocyClient
from grocy_mcp.core.resolve import resolve_product


async def stock_journal(client: GrocyClient, product: str | None = None) -> str:
    """Return recent stock journal entries, optionally filtered by product."""
    entries = await client.get_objects("stock_log")
    if not entries:
        return "No stock journal entries found."

    # Build product/location name maps
    products = await client.get_objects("products")
    product_map = {p["id"]: p.get("name", f"Product {p['id']}") for p in products}
    locations = await client.get_objects("locations")
    location_map = {loc["id"]: loc.get("name", f"Location {loc['id']}") for loc in locations}
    stores = await client.get_objects("shopping_locations")
    store_map = {store["id"]: store.get("name", f"Store {store['id']}") for store in stores}

    # Filter by product if specified
    if product is not None:
        product_id = await resolve_product(client, product)
        entries = [e for e in entries if e.get("product_id") == product_id]
        if not entries:
            return f"No stock journal entries found for '{product}'."

    # Sort by row_created_timestamp descending, take last 50
    entries.sort(key=lambda e: e.get("row_created_timestamp", ""), reverse=True)
    entries = entries[:50]

    lines = ["Stock journal (most recent first):"]
    for entry in entries:
        prod_name = product_map.get(entry.get("product_id"), f"Product {entry.get('product_id')}")
        amount = entry.get("amount", "?")
        txn_type = entry.get("transaction_type", "?")
        timestamp = entry.get("row_created_timestamp", "?")
        line = f"  [{entry.get('id', '?')}] {prod_name} — {txn_type} {amount} — {timestamp}"

        price = entry.get("price")
        if price is not None:
            line += f" — {price:g}"

        location_id = entry.get("location_id")
        if location_id in location_map:
            line += f" @ {location_map[location_id]}"

        shopping_location_id = entry.get("shopping_location_id")
        if shopping_location_id in store_map:
            line += f" from {store_map[shopping_location_id]}"

        lines.append(line)

    return "\n".join(lines)
