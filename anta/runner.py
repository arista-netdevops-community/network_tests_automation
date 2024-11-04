# Copyright (c) 2023-2024 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""ANTA runner function."""

from __future__ import annotations

import asyncio
import logging
import os
import resource
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from anta import GITHUB_SUGGESTION
from anta.cli.console import console
from anta.logger import anta_log_exception, exc_to_str
from anta.models import AntaTest
from anta.tools import Catchtime, cprofile

if TYPE_CHECKING:
    from asyncio import Task
    from collections.abc import AsyncGenerator, Coroutine

    from anta.catalog import AntaCatalog, AntaTestDefinition
    from anta.device import AntaDevice
    from anta.inventory import AntaInventory
    from anta.result_manager import ResultManager
    from anta.result_manager.models import TestResult

logger = logging.getLogger(__name__)

DEFAULT_NOFILE = 16384
"""Default number of open file descriptors for the ANTA process."""
DEFAULT_MAX_CONCURRENCY = 10000
"""Default maximum number of tests to run concurrently."""
DEFAULT_MAX_CONNECTIONS = 100
"""Default underlying HTTPX client maximum number of connections per device."""


def adjust_max_concurrency() -> int:
    """Adjust the maximum number of tests (coroutines) to run concurrently.

    The limit is set to the value of the ANTA_MAX_CONCURRENCY environment variable.

    If the `ANTA_MAX_CONCURRENCY` environment variable is not set or is invalid, `DEFAULT_MAX_CONCURRENCY` is used.

    Returns
    -------
    int
        The maximum number of tests to run concurrently.
    """
    try:
        max_concurrency = int(os.environ.get("ANTA_MAX_CONCURRENCY", DEFAULT_MAX_CONCURRENCY))
    except ValueError as exception:
        logger.warning("The ANTA_MAX_CONCURRENCY environment variable value is invalid: %s\nDefault to %s.", exc_to_str(exception), DEFAULT_MAX_CONCURRENCY)
        max_concurrency = DEFAULT_MAX_CONCURRENCY
    return max_concurrency


def adjust_rlimit_nofile() -> tuple[int, int]:
    """Adjust the maximum number of open file descriptors for the ANTA process.

    The limit is set to the lower of the current hard limit and the value of the ANTA_NOFILE environment variable.

    If the `ANTA_NOFILE` environment variable is not set or is invalid, `DEFAULT_NOFILE` is used.

    Returns
    -------
    tuple[int, int]
        The new soft and hard limits for open file descriptors.
    """
    try:
        nofile = int(os.environ.get("ANTA_NOFILE", DEFAULT_NOFILE))
    except ValueError as exception:
        logger.warning("The ANTA_NOFILE environment variable value is invalid: %s\nDefault to %s.", exc_to_str(exception), DEFAULT_NOFILE)
        nofile = DEFAULT_NOFILE

    limits = resource.getrlimit(resource.RLIMIT_NOFILE)
    logger.debug("Initial limit numbers for open file descriptors for the current ANTA process: Soft Limit: %s | Hard Limit: %s", limits[0], limits[1])
    nofile = min(limits[1], nofile)
    logger.debug("Setting soft limit for open file descriptors for the current ANTA process to %s", nofile)
    resource.setrlimit(resource.RLIMIT_NOFILE, (nofile, limits[1]))
    return resource.getrlimit(resource.RLIMIT_NOFILE)


def log_cache_statistics(devices: list[AntaDevice]) -> None:
    """Log cache statistics for each device in the inventory.

    Parameters
    ----------
    devices
        List of devices in the inventory.
    """
    for device in devices:
        if device.cache_statistics is not None:
            msg = (
                f"Cache statistics for '{device.name}': "
                f"{device.cache_statistics['cache_hits']} hits / {device.cache_statistics['total_commands_sent']} "
                f"command(s) ({device.cache_statistics['cache_hit_ratio']})"
            )
            logger.info(msg)
        else:
            logger.info("Caching is not enabled on %s", device.name)


async def run(tests_generator: AsyncGenerator[Coroutine[Any, Any, TestResult], None], limit: int) -> AsyncGenerator[TestResult, None]:
    """Run tests with a concurrency limit.

    This function takes an asynchronous generator of test coroutines and runs them
    with a limit on the number of concurrent tests. It yields test results as each
    test completes.

    Inspired by: https://death.andgravity.com/limit-concurrency

    Parameters
    ----------
    tests_generator
        An asynchronous generator that yields test coroutines.
    limit
        The maximum number of concurrent tests to run.

    Yields
    ------
        The result of each completed test.
    """
    # NOTE: The `aiter` built-in function is not available in Python 3.9
    aws = tests_generator.__aiter__()  # pylint: disable=unnecessary-dunder-call
    aws_ended = False
    pending: set[Task[TestResult]] = set()

    while pending or not aws_ended:
        # Add tests to the pending set until the limit is reached or no more tests are available
        while len(pending) < limit and not aws_ended:
            try:
                # NOTE: The `anext` built-in function is not available in Python 3.9
                aw = await aws.__anext__()  # pylint: disable=unnecessary-dunder-call
            except StopAsyncIteration:  # noqa: PERF203
                aws_ended = True
                logger.debug("All tests have been added to the pending set.")
            else:
                # Ensure the coroutine is scheduled to run and add it to the pending set
                pending.add(asyncio.create_task(aw))
                logger.debug("Added a test to the pending set: %s", aw)

        if len(pending) >= limit:
            logger.debug("Concurrency limit reached: %s tests running. Waiting for tests to complete.", limit)

        if not pending:
            logger.debug("No pending tests and all tests have been processed. Exiting.")
            return

        # Wait for at least one of the pending tests to complete
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        logger.debug("Completed %s test(s). Pending count: %s", len(done), len(pending))

        # Yield results of completed tests
        while done:
            yield await done.pop()


async def setup_inventory(inventory: AntaInventory, tags: set[str] | None, devices: set[str] | None, *, established_only: bool) -> AntaInventory | None:
    """Set up the inventory for the ANTA run.

    Parameters
    ----------
    inventory
        AntaInventory object that includes the device(s).
    tags
        Tags to filter devices from the inventory.
    devices
        Devices on which to run tests. None means all devices.
    established_only
        If True use return only devices where a connection is established.

    Returns
    -------
    AntaInventory | None
        The filtered AntaInventory or None if there are no devices to run tests on.
    """
    if len(inventory) == 0:
        logger.info("The inventory is empty, exiting")
        return None

    # Filter the inventory based on the CLI provided tags and devices if any
    selected_inventory = inventory.get_inventory(tags=tags, devices=devices) if tags or devices else inventory

    with Catchtime(logger=logger, message="Connecting to devices"):
        # Connect to the devices
        await selected_inventory.connect_inventory()

    # Remove devices that are unreachable
    selected_inventory = selected_inventory.get_inventory(established_only=established_only)

    # If there are no devices in the inventory after filtering, exit
    if not selected_inventory.devices:
        msg = f'No reachable device {f"matching the tags {tags} " if tags else ""}was found.{f" Selected devices: {devices} " if devices is not None else ""}'
        logger.warning(msg)
        return None

    return selected_inventory


def setup_tests(
    inventory: AntaInventory, catalog: AntaCatalog, tests: set[str] | None, tags: set[str] | None
) -> tuple[int, defaultdict[AntaDevice, set[AntaTestDefinition]] | None]:
    """Set up the tests for the ANTA run.

    Parameters
    ----------
    inventory
        AntaInventory object that includes the device(s).
    catalog
        AntaCatalog object that includes the list of tests.
    tests
        Tests to run against devices. None means all tests.
    tags
        Tags to filter devices from the inventory.

    Returns
    -------
    tuple[int, defaultdict[AntaDevice, set[AntaTestDefinition]] | None]
        The total number of tests and a mapping of devices to the tests to run or None if there are no tests to run.
    """
    # Build indexes for the catalog. If `tests` is set, filter the indexes based on these tests
    catalog.build_indexes(filtered_tests=tests)

    # Using a set to avoid inserting duplicate tests
    device_to_tests: defaultdict[AntaDevice, set[AntaTestDefinition]] = defaultdict(set)

    total_test_count = 0

    # Create the device to tests mapping from the tags
    for device in inventory.devices:
        if tags:
            # If there are CLI tags, execute tests with matching tags for this device
            if not (matching_tags := tags.intersection(device.tags)):
                # The device does not have any selected tag, skipping
                continue
            device_to_tests[device].update(catalog.get_tests_by_tags(matching_tags))
        else:
            # If there is no CLI tags, execute all tests that do not have any tags
            device_to_tests[device].update(catalog.tag_to_tests[None])

            # Then add the tests with matching tags from device tags
            device_to_tests[device].update(catalog.get_tests_by_tags(device.tags))

        total_test_count += len(device_to_tests[device])

    if total_test_count == 0:
        msg = (
            f"There are no tests{f' matching the tags {tags} ' if tags else ' '}to run in the current test catalog and device inventory, please verify your inputs."
        )
        logger.warning(msg)
        return total_test_count, None

    return total_test_count, device_to_tests


async def test_generator(
    selected_tests: defaultdict[AntaDevice, set[AntaTestDefinition]], manager: ResultManager
) -> AsyncGenerator[Coroutine[Any, Any, TestResult], None]:
    """Get the coroutines for the ANTA run.

        It creates an async generator of coroutines which are created by the `test` method of the AntaTest instances. Each coroutine is a test to run.

    Parameters
    ----------
    selected_tests
        A mapping of devices to the tests to run. The selected tests are created by the `setup_tests` function.
    manager
        A ResultManager

    Yields
    ------
        The coroutine (test) to run.
    """
    for device, test_definitions in selected_tests.items():
        for test in test_definitions:
            try:
                test_instance = test.test(device=device, inputs=test.inputs)
                manager.add(test_instance.result)
                coroutine = test_instance.test()
            except Exception as e:  # noqa: PERF203, BLE001
                # An AntaTest instance is potentially user-defined code.
                # We need to catch everything and exit gracefully with an error message.
                message = "\n".join(
                    [
                        f"There is an error when creating test {test.test.__module__}.{test.test.__name__}.",
                        f"If this is not a custom test implementation: {GITHUB_SUGGESTION}",
                    ],
                )
                anta_log_exception(e, message, logger)
            else:
                yield coroutine


@cprofile()
async def main(  # noqa: PLR0913
    manager: ResultManager,
    inventory: AntaInventory,
    catalog: AntaCatalog,
    devices: set[str] | None = None,
    tests: set[str] | None = None,
    tags: set[str] | None = None,
    *,
    established_only: bool = True,
    dry_run: bool = False,
) -> None:
    """Run ANTA.

    Use this as an entrypoint to the test framework in your script.
    ResultManager object gets updated with the test results.

    Parameters
    ----------
    manager
        ResultManager object to populate with the test results.
    inventory
        AntaInventory object that includes the device(s).
    catalog
        AntaCatalog object that includes the list of tests.
    devices
        Devices on which to run tests. None means all devices. These may come from the `--device / -d` CLI option in NRFU.
    tests
        Tests to run against devices. None means all tests. These may come from the `--test / -t` CLI option in NRFU.
    tags
        Tags to filter devices from the inventory. These may come from the `--tags` CLI option in NRFU.
    established_only
        Include only established device(s).
    dry_run
        Build the list of coroutine to run and stop before test execution.
    """
    # Adjust the maximum number of open file descriptors for the ANTA process
    limits = adjust_rlimit_nofile()

    # Adjust the maximum number of tests to run concurrently
    max_concurrency = adjust_max_concurrency()

    if not catalog.tests:
        logger.info("The list of tests is empty, exiting")
        return

    with Catchtime(logger=logger, message="Preparing ANTA NRFU Run"):
        # Setup the inventory
        selected_inventory = inventory if dry_run else await setup_inventory(inventory, tags, devices, established_only=established_only)
        if selected_inventory is None:
            return

        with Catchtime(logger=logger, message="Preparing the tests"):
            total_tests, selected_tests = setup_tests(selected_inventory, catalog, tests, tags)
            if total_tests == 0 or selected_tests is None:
                return
            final_tests_count = sum(len(tests) for tests in selected_tests.values())

        generator = test_generator(selected_tests, manager)

        # TODO: 34 is a magic numbers from RichHandler formatting catering for date, level and path
        width = min(int(console.width) - 34, len("Maximum number of open file descriptors for the current ANTA process: 0000000000\n"))

        run_info = (
            f"{' ANTA NRFU Run Information ':-^{width}}\n"
            f"Number of devices: {len(inventory)} ({len(selected_inventory)} established)\n"
            f"Total number of selected tests: {total_tests}\n"
            f"Maximum number of tests to run concurrently: {max_concurrency}\n"
            f"Maximum number of connections per device: {DEFAULT_MAX_CONNECTIONS}\n"
            f"Maximum number of open file descriptors for the current ANTA process: {limits[0]}\n"
            f"{'':-^{width}}"
        )

        logger.info(run_info)

        total_potential_connections = len(selected_inventory) * DEFAULT_MAX_CONNECTIONS

        if total_tests > max_concurrency:
            logger.warning(
                "The total number of tests is higher than the maximum number of tests to run concurrently.\n"
                "ANTA will be throttled to run at the maximum number of tests to run concurrently to ensure system stability.\n"
                "Please consult the ANTA FAQ."
            )
        if total_potential_connections > limits[0]:
            logger.warning(
                "The total potential connections to devices is higher than the open file descriptors limit for this ANTA process.\n"
                "Errors may occur while running the tests.\n"
                "Please consult the ANTA FAQ."
            )

        # Cleanup no longer needed objects before running the tests
        del selected_tests

    if dry_run:
        logger.info("Dry-run mode, exiting before running the tests.")
        async for test in generator:
            test.close()
        return

    if AntaTest.progress is not None:
        AntaTest.nrfu_task = AntaTest.progress.add_task("Running NRFU Tests...", total=final_tests_count)

    with Catchtime(logger=logger, message="Running ANTA tests"):
        async for result in run(generator, limit=max_concurrency):
            logger.debug(result)

    log_cache_statistics(selected_inventory.devices)
