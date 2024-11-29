# Copyright (c) 2023-2024 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Test functions related to various STUN settings."""

# Mypy does not understand AntaTest.Input typing
# mypy: disable-error-code=attr-defined
from __future__ import annotations

from typing import ClassVar

from anta.input_models.stun import ClientAddress
from anta.models import AntaCommand, AntaTemplate, AntaTest
from anta.tools import get_value


class VerifyStunClient(AntaTest):
    """Verifies the translation for a source address on a STUN client.

    This test performs the following checks for each specified address family:

      1. Validates that there is a translation for the source address on the STUN client.
      2. If public IP and port details are provided, validates their correctness against the configuration.

    Expected Results
    ----------------
    * Success: If all of the following conditions are met:
        - The test will pass if the source address translation is present.
        - If public IP and port details are provided, they must also match the translation information.
    * Failure: If any of the following occur:
        - There is no translation for the source address on the STUN client.
        - The public IP or port details, if specified, are incorrect.

    Examples
    --------
    ```yaml
    anta.tests.stun:
      - VerifyStunClient:
          stun_clients:
            - source_address: 172.18.3.2
              public_address: 172.18.3.21
              source_port: 4500
              public_port: 6006
            - source_address: 100.64.3.2
              public_address: 100.64.3.21
              source_port: 4500
              public_port: 6006
    ```
    """

    categories: ClassVar[list[str]] = ["stun"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaTemplate(template="show stun client translations {source_address} {source_port}", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifyStunClient test."""

        stun_clients: list[ClientAddress]
        """List of STUN clients."""
        ClientAddress: ClassVar[type[ClientAddress]] = ClientAddress

    def render(self, template: AntaTemplate) -> list[AntaCommand]:
        """Render the template for each STUN translation."""
        return [template.render(source_address=client.source_address, source_port=client.source_port) for client in self.inputs.stun_clients]

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifyStunClient."""
        self.result.is_success()

        # Iterate over each command output and corresponding client input
        for command, client_input in zip(self.instance_commands, self.inputs.stun_clients):
            bindings = command.json_output["bindings"]
            input_public_address = client_input.public_address
            input_public_port = client_input.public_port

            # If no bindings are found for the STUN client, mark the test as a failure and continue with the next client
            if not bindings:
                self.result.is_failure(f"{client_input} - STUN client translation not found.")
                continue

            # Extract the transaction ID from the bindings
            transaction_id = next(iter(bindings.keys()))

            # Verifying the public address if provided
            if input_public_address and str(input_public_address) != (actual_public_address := get_value(bindings, f"{transaction_id}.publicAddress.ip")):
                self.result.is_failure(f"{client_input} - Incorrect public-facing address - Expected: {input_public_address} Actual: {actual_public_address}")

            # Verifying the public port if provided
            if input_public_port and input_public_port != (actual_public_port := get_value(bindings, f"{transaction_id}.publicAddress.port")):
                self.result.is_failure(f"{client_input} - Incorrect public-facing port - Expected: {input_public_port} Actual: {actual_public_port}")


class VerifyStunServer(AntaTest):
    """Verifies the STUN server status is enabled and running.

    Expected Results
    ----------------
    * Success: The test will pass if the STUN server status is enabled and running.
    * Failure: The test will fail if the STUN server is disabled or not running.

    Examples
    --------
    ```yaml
    anta.tests.stun:
      - VerifyStunServer:
    ```
    """

    categories: ClassVar[list[str]] = ["stun"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show stun server status", revision=1)]

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifyStunServer."""
        command_output = self.instance_commands[0].json_output
        status_disabled = not command_output.get("enabled")
        not_running = command_output.get("pid") == 0

        if status_disabled and not_running:
            self.result.is_failure("STUN server status is disabled and not running.")
        elif status_disabled:
            self.result.is_failure("STUN server status is disabled.")
        elif not_running:
            self.result.is_failure("STUN server is not running.")
        else:
            self.result.is_success()
