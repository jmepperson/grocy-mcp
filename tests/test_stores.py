"""Tests for the stores core module."""

from unittest.mock import AsyncMock

from grocy_mcp.core.stores import stores_list


async def test_stores_list():
    client = AsyncMock()
    client.get_objects.return_value = [
        {"id": 1, "name": "Local Supermarket"},
        {"id": 2, "name": "Farmers Market"},
    ]
    result = await stores_list(client)
    client.get_objects.assert_called_once_with("shopping_locations")
    assert "Local Supermarket" in result
    assert "Farmers Market" in result
    assert "[1]" in result
    assert "[2]" in result


async def test_stores_list_empty():
    client = AsyncMock()
    client.get_objects.return_value = []
    result = await stores_list(client)
    assert result == "No stores found."
