"""Tests for workflow-oriented preview/apply helpers."""

from unittest.mock import AsyncMock, patch

import pytest

from grocy_mcp.core.workflows import (
    workflow_match_products_preview_data,
    workflow_shopping_reconcile_apply_data,
    workflow_shopping_reconcile_preview_data,
    workflow_stock_intake_apply_data,
)
from grocy_mcp.exceptions import GrocyValidationError


async def test_workflow_match_products_preview_exact_barcode():
    client = AsyncMock()
    client.get_objects.side_effect = [
        [{"id": 1, "name": "Whole Milk"}],
        [{"id": 10, "product_id": 1, "barcode": "5000112637922"}],
    ]

    result = await workflow_match_products_preview_data(
        client,
        [{"label": "milk", "quantity": 2, "barcode": "5000112637922", "unit_text": "cartons"}],
    )

    assert result[0]["status"] == "matched"
    assert result[0]["matched_product_id"] == 1
    assert result[0]["matched_product_name"] == "Whole Milk"
    assert result[0]["suggested_amount"] == 2


async def test_workflow_match_products_preview_exact_name():
    client = AsyncMock()
    client.get_objects.side_effect = [
        [{"id": 1, "name": "Whole Milk"}],
        [],
    ]

    result = await workflow_match_products_preview_data(
        client,
        [{"label": "whole milk", "quantity": 1}],
    )

    assert result[0]["status"] == "matched"
    assert result[0]["matched_product_id"] == 1


async def test_workflow_match_products_preview_ambiguous_substring():
    client = AsyncMock()
    client.get_objects.side_effect = [
        [{"id": 1, "name": "Whole Milk"}, {"id": 2, "name": "Oat Milk"}],
        [],
    ]

    result = await workflow_match_products_preview_data(
        client,
        [{"label": "milk", "quantity": 1}],
    )

    assert result[0]["status"] == "ambiguous"
    assert len(result[0]["candidates"]) == 2


async def test_workflow_match_products_preview_unmatched():
    client = AsyncMock()
    client.get_objects.side_effect = [
        [{"id": 1, "name": "Whole Milk"}],
        [],
    ]

    result = await workflow_match_products_preview_data(
        client,
        [{"label": "bananas", "quantity": 1}],
    )

    assert result[0]["status"] == "unmatched"
    assert result[0]["candidates"] == []


async def test_workflow_match_products_preview_rejects_invalid_payload():
    client = AsyncMock()

    with pytest.raises(GrocyValidationError, match="Invalid items\\[0\\]"):
        await workflow_match_products_preview_data(client, [{"label": "", "quantity": 0}])


async def test_workflow_stock_intake_apply_data():
    client = AsyncMock()

    result = await workflow_stock_intake_apply_data(
        client,
        [{"product_id": 12, "amount": 2, "note": "organic"}],
    )

    client.add_stock.assert_awaited_once_with(12, 2, note="organic")
    assert result["applied_count"] == 1
    assert result["applied_items"][0]["note"] == "organic"


async def test_workflow_stock_intake_apply_data_with_price_and_location():
    client = AsyncMock()

    with (
        patch("grocy_mcp.core.workflows.resolve_location", return_value=5) as mock_loc,
        patch("grocy_mcp.core.workflows.resolve_store", return_value=9) as mock_store,
    ):
        result = await workflow_stock_intake_apply_data(
            client,
            [
                {
                    "product_id": 12,
                    "amount": 2,
                    "price": 3.49,
                    "location": "Fridge",
                    "store": "Farmers Market",
                    "best_before_date": "2026-12-31",
                }
            ],
        )

    mock_loc.assert_awaited_once_with(client, "Fridge")
    mock_store.assert_awaited_once_with(client, "Farmers Market")
    client.add_stock.assert_awaited_once_with(
        12,
        2,
        price=3.49,
        location_id=5,
        shopping_location_id=9,
        best_before_date="2026-12-31",
    )
    assert result["applied_items"][0]["price"] == 3.49


async def test_workflow_match_products_preview_carries_price_and_store():
    client = AsyncMock()
    client.get_objects.side_effect = [
        [{"id": 1, "name": "Whole Milk"}],
        [],
    ]

    result = await workflow_match_products_preview_data(
        client,
        [
            {
                "label": "whole milk",
                "quantity": 1,
                "price": 3.49,
                "store": "Farmers Market",
            }
        ],
    )

    assert result[0]["price"] == 3.49
    assert result[0]["store"] == "Farmers Market"


async def test_workflow_shopping_reconcile_preview_data():
    client = AsyncMock()
    client.get_shopping_list.return_value = [
        {"id": 3, "product_id": 12, "amount": 1},
        {"id": 4, "product_id": 12, "amount": 3},
    ]

    result = await workflow_shopping_reconcile_preview_data(
        client,
        [{"product_id": 12, "amount": 2}],
        list_id=1,
    )

    assert result[0]["status"] == "matched"
    assert result[0]["actions"] == [
        {"shopping_item_id": 3, "action": "remove", "previous_amount": 1.0},
        {
            "shopping_item_id": 4,
            "action": "set_amount",
            "previous_amount": 3.0,
            "new_amount": 2.0,
        },
    ]


async def test_workflow_shopping_reconcile_preview_data_partial():
    client = AsyncMock()
    client.get_shopping_list.return_value = [{"id": 5, "product_id": 12, "amount": 1}]

    result = await workflow_shopping_reconcile_preview_data(
        client,
        [{"product_id": 12, "amount": 2}],
        list_id=1,
    )

    assert result[0]["status"] == "partial"
    assert result[0]["unapplied_amount"] == 1


async def test_workflow_shopping_reconcile_apply_data():
    client = AsyncMock()

    result = await workflow_shopping_reconcile_apply_data(
        client,
        [
            {"shopping_item_id": 3, "action": "remove"},
            {"shopping_item_id": 4, "action": "set_amount", "new_amount": 2},
        ],
    )

    client.remove_shopping_list_item.assert_awaited_once_with(3)
    client.update_shopping_list_item.assert_awaited_once_with(4, {"amount": 2.0})
    assert result["applied_count"] == 2
