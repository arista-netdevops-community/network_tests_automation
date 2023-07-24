"""
Tests for anta.tools.pydantic
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import pytest

from anta.tools.pydantic import pydantic_to_dict

if TYPE_CHECKING:
    from anta.result_manager.models import ListResult

EXPECTED_ONE_ENTRY = [
    {"name": "testdevice", "test": "VerifyTest0", "test_category": ["test"], "test_description": "Verifies Test 0", "result": "unset", "messages": []}
]
EXPECTED_THREE_ENTRIES = [
    {"name": "testdevice", "test": "VerifyTest0", "test_category": ["test"], "test_description": "Verifies Test 0", "result": "unset", "messages": []},
    {"name": "testdevice", "test": "VerifyTest1", "test_category": ["test"], "test_description": "Verifies Test 1", "result": "unset", "messages": []},
    {"name": "testdevice", "test": "VerifyTest2", "test_category": ["test"], "test_description": "Verifies Test 2", "result": "unset", "messages": []},
]


@pytest.mark.parametrize(
    "number_of_entries, expected",
    [
        pytest.param(0, [], id="empty"),
        pytest.param(1, EXPECTED_ONE_ENTRY, id="one"),
        pytest.param(3, EXPECTED_THREE_ENTRIES, id="three"),
    ],
)
def test_pydantic_to_dict(
    list_result_factory: Callable[[int], ListResult],
    number_of_entries: int,
    expected: dict[str, Any],
) -> None:
    """
    Test pydantic_to_dict
    """
    list_result = list_result_factory(number_of_entries)
    assert pydantic_to_dict(list_result) == expected
