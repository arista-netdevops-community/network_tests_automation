# Copyright (c) 2023-2024 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""See https://docs.pytest.org/en/stable/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files."""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import respx

from anta.device import AsyncEOSDevice
from anta.inventory import AntaInventory

DATA_DIR: Path = Path(__file__).parent.resolve() / "data"


@pytest.fixture(params=[{"count": 1}], ids=["1-reachable-device-without-cache"])
def inventory(request: pytest.FixtureRequest) -> Iterator[AntaInventory]:
    """Generate an ANTA inventory."""
    user = "admin"
    password = "password"  # noqa: S105
    disable_cache = request.param.get("disable_cache", True)
    reachable = request.param.get("reachable", True)
    if "filename" in request.param:
        inv = AntaInventory.parse(DATA_DIR / request.param["filename"], username=user, password=password, disable_cache=disable_cache)
    else:
        inv = AntaInventory()
        for i in range(request.param["count"]):
            inv.add_device(
                AsyncEOSDevice(
                    host=f"device-{i}.anta.arista.com",
                    username=user,
                    password=password,
                    name=f"device-{i}",
                    disable_cache=disable_cache,
                )
            )
    if reachable:
        # This context manager makes all devices reachable
        with patch("asyncio.open_connection", AsyncMock(spec=asyncio.open_connection, return_value=(Mock(), Mock()))), respx.mock:
            respx.post(path="/command-api", headers={"Content-Type": "application/json-rpc"}, json__params__cmds__0__cmd="show version").respond(
                json={
                    "result": [
                        {
                            "modelName": "pytest",
                        }
                    ],
                }
            )
            yield inv
    else:
        with patch("asyncio.open_connection", AsyncMock(spec=asyncio.open_connection, side_effect=TimeoutError)):
            yield inv
