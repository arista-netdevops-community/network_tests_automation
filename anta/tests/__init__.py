#!/usr/bin/python
# coding: utf-8 -*-
"""
Test decorator from which tests can derive
"""

import logging
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, List
import traceback

from anta.inventory.models import InventoryDevice
from anta.result_manager.models import TestResult

logger = logging.getLogger(__name__)


def anta_test(function: Callable[..., Coroutine[Any, Any, TestResult]]) -> Callable[..., Coroutine[Any, Any, Coroutine[Any, Any, TestResult]]]:
    """
    Decorator to generate the structure for a test
    * func (Callable): the test to be decorated
    """

    @wraps(function)
    async def wrapper(
        device: InventoryDevice, *args: List[Any], **kwargs: Dict[str, Any]
    ) -> TestResult:
        """
        wrapper for func
        Args:
            TODO

        Returns:
            TestResult instance with
            * result = "unset" if the test has not been executed
            * result = "success" if the MLAG status is OK
            * result = "failure" otherwise.
            * result = "error" if any exception is caught
        """
        result = TestResult(name=str(device.host), test=function.__name__)
        logger.debug(f"Start {function.__name__} check for host {device.host}")

        try:
            return await function(device, result, *args, **kwargs)

        # In this case we want to catch all exceptions
        except Exception as e:  # pylint: disable=broad-except
            logger.error(
                f"Exception raised for test {function.__name__} (on device {device.host}) - {type(e).__name__}: {str(e)}"
            )
            logger.debug(traceback.format_exc())
            result.is_error(f'{type(e).__name__}: {str(e)}')
            return result

    return wrapper
