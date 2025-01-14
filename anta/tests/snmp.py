# Copyright (c) 2023-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Module related to the EOS various SNMP tests."""

# Mypy does not understand AntaTest.Input typing
# mypy: disable-error-code=attr-defined
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, get_args

from pydantic import field_validator

from anta.custom_types import PositiveInteger, SnmpErrorCounter, SnmpPdu
from anta.input_models.snmp import SnmpHost
from anta.models import AntaCommand, AntaTest
from anta.tools import get_value

if TYPE_CHECKING:
    from anta.models import AntaTemplate


class VerifySnmpStatus(AntaTest):
    """Verifies whether the SNMP agent is enabled in a specified VRF.

    Expected Results
    ----------------
    * Success: The test will pass if the SNMP agent is enabled in the specified VRF.
    * Failure: The test will fail if the SNMP agent is disabled in the specified VRF.

    Examples
    --------
    ```yaml
    anta.tests.snmp:
      - VerifySnmpStatus:
          vrf: default
    ```
    """

    description = "Verifies if the SNMP agent is enabled."
    categories: ClassVar[list[str]] = ["snmp"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show snmp", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifySnmpStatus test."""

        vrf: str = "default"
        """The name of the VRF in which to check for the SNMP agent. Defaults to `default` VRF."""

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifySnmpStatus."""
        command_output = self.instance_commands[0].json_output
        if command_output["enabled"] and self.inputs.vrf in command_output["vrfs"]["snmpVrfs"]:
            self.result.is_success()
        else:
            self.result.is_failure(f"SNMP agent disabled in vrf {self.inputs.vrf}")


class VerifySnmpIPv4Acl(AntaTest):
    """Verifies if the SNMP agent has the right number IPv4 ACL(s) configured for a specified VRF.

    Expected Results
    ----------------
    * Success: The test will pass if the SNMP agent has the provided number of IPv4 ACL(s) in the specified VRF.
    * Failure: The test will fail if the SNMP agent has not the right number of IPv4 ACL(s) in the specified VRF.

    Examples
    --------
    ```yaml
    anta.tests.snmp:
      - VerifySnmpIPv4Acl:
          number: 3
          vrf: default
    ```
    """

    description = "Verifies if the SNMP agent has IPv4 ACL(s) configured."
    categories: ClassVar[list[str]] = ["snmp"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show snmp ipv4 access-list summary", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifySnmpIPv4Acl test."""

        number: PositiveInteger
        """The number of expected IPv4 ACL(s)."""
        vrf: str = "default"
        """The name of the VRF in which to check for the SNMP agent. Defaults to `default` VRF."""

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifySnmpIPv4Acl."""
        command_output = self.instance_commands[0].json_output
        ipv4_acl_list = command_output["ipAclList"]["aclList"]
        ipv4_acl_number = len(ipv4_acl_list)
        if ipv4_acl_number != self.inputs.number:
            self.result.is_failure(f"Expected {self.inputs.number} SNMP IPv4 ACL(s) in vrf {self.inputs.vrf} but got {ipv4_acl_number}")
            return

        not_configured_acl = [acl["name"] for acl in ipv4_acl_list if self.inputs.vrf not in acl["configuredVrfs"] or self.inputs.vrf not in acl["activeVrfs"]]

        if not_configured_acl:
            self.result.is_failure(f"SNMP IPv4 ACL(s) not configured or active in vrf {self.inputs.vrf}: {not_configured_acl}")
        else:
            self.result.is_success()


class VerifySnmpIPv6Acl(AntaTest):
    """Verifies if the SNMP agent has the right number IPv6 ACL(s) configured for a specified VRF.

    Expected Results
    ----------------
    * Success: The test will pass if the SNMP agent has the provided number of IPv6 ACL(s) in the specified VRF.
    * Failure: The test will fail if the SNMP agent has not the right number of IPv6 ACL(s) in the specified VRF.

    Examples
    --------
    ```yaml
    anta.tests.snmp:
      - VerifySnmpIPv6Acl:
          number: 3
          vrf: default
    ```
    """

    description = "Verifies if the SNMP agent has IPv6 ACL(s) configured."
    categories: ClassVar[list[str]] = ["snmp"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show snmp ipv6 access-list summary", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifySnmpIPv6Acl test."""

        number: PositiveInteger
        """The number of expected IPv6 ACL(s)."""
        vrf: str = "default"
        """The name of the VRF in which to check for the SNMP agent. Defaults to `default` VRF."""

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifySnmpIPv6Acl."""
        command_output = self.instance_commands[0].json_output
        ipv6_acl_list = command_output["ipv6AclList"]["aclList"]
        ipv6_acl_number = len(ipv6_acl_list)
        if ipv6_acl_number != self.inputs.number:
            self.result.is_failure(f"Expected {self.inputs.number} SNMP IPv6 ACL(s) in vrf {self.inputs.vrf} but got {ipv6_acl_number}")
            return

        acl_not_configured = [acl["name"] for acl in ipv6_acl_list if self.inputs.vrf not in acl["configuredVrfs"] or self.inputs.vrf not in acl["activeVrfs"]]

        if acl_not_configured:
            self.result.is_failure(f"SNMP IPv6 ACL(s) not configured or active in vrf {self.inputs.vrf}: {acl_not_configured}")
        else:
            self.result.is_success()


class VerifySnmpLocation(AntaTest):
    """Verifies the SNMP location of a device.

    Expected Results
    ----------------
    * Success: The test will pass if the SNMP location matches the provided input.
    * Failure: The test will fail if the SNMP location does not match the provided input.

    Examples
    --------
    ```yaml
    anta.tests.snmp:
      - VerifySnmpLocation:
          location: New York
    ```
    """

    categories: ClassVar[list[str]] = ["snmp"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show snmp", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifySnmpLocation test."""

        location: str
        """Expected SNMP location of the device."""

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifySnmpLocation."""
        # Verifies the SNMP location is configured.
        if not (location := get_value(self.instance_commands[0].json_output, "location.location")):
            self.result.is_failure("SNMP location is not configured.")
            return

        # Verifies the expected SNMP location.
        if location != self.inputs.location:
            self.result.is_failure(f"Expected `{self.inputs.location}` as the location, but found `{location}` instead.")
        else:
            self.result.is_success()


class VerifySnmpContact(AntaTest):
    """Verifies the SNMP contact of a device.

    Expected Results
    ----------------
    * Success: The test will pass if the SNMP contact matches the provided input.
    * Failure: The test will fail if the SNMP contact does not match the provided input.

    Examples
    --------
    ```yaml
    anta.tests.snmp:
      - VerifySnmpContact:
          contact: Jon@example.com
    ```
    """

    categories: ClassVar[list[str]] = ["snmp"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show snmp", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifySnmpContact test."""

        contact: str
        """Expected SNMP contact details of the device."""

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifySnmpContact."""
        # Verifies the SNMP contact is configured.
        if not (contact := get_value(self.instance_commands[0].json_output, "contact.contact")):
            self.result.is_failure("SNMP contact is not configured.")
            return

        # Verifies the expected SNMP contact.
        if contact != self.inputs.contact:
            self.result.is_failure(f"Expected `{self.inputs.contact}` as the contact, but found `{contact}` instead.")
        else:
            self.result.is_success()


class VerifySnmpPDUCounters(AntaTest):
    """Verifies the SNMP PDU counters.

    By default, all SNMP PDU counters will be checked for any non-zero values.
    An optional list of specific SNMP PDU(s) can be provided for granular testing.

    Expected Results
    ----------------
    * Success: The test will pass if the SNMP PDU counter(s) are non-zero/greater than zero.
    * Failure: The test will fail if the SNMP PDU counter(s) are zero/None/Not Found.

    Examples
    --------
    ```yaml
    anta.tests.snmp:
      - VerifySnmpPDUCounters:
          pdus:
            - outTrapPdus
            - inGetNextPdus
    ```
    """

    categories: ClassVar[list[str]] = ["snmp"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show snmp", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifySnmpPDUCounters test."""

        pdus: list[SnmpPdu] | None = None
        """Optional list of SNMP PDU counters to be verified. If not provided, test will verifies all PDU counters."""

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifySnmpPDUCounters."""
        snmp_pdus = self.inputs.pdus
        command_output = self.instance_commands[0].json_output

        # Verify SNMP PDU counters.
        if not (pdu_counters := get_value(command_output, "counters")):
            self.result.is_failure("SNMP counters not found.")
            return

        # In case SNMP PDUs not provided, It will check all the update error counters.
        if not snmp_pdus:
            snmp_pdus = list(get_args(SnmpPdu))

        failures = {pdu: value for pdu in snmp_pdus if (value := pdu_counters.get(pdu, "Not Found")) == "Not Found" or value == 0}

        # Check if any failures
        if not failures:
            self.result.is_success()
        else:
            self.result.is_failure(f"The following SNMP PDU counters are not found or have zero PDU counters:\n{failures}")


class VerifySnmpErrorCounters(AntaTest):
    """Verifies the SNMP error counters.

    By default, all  error counters will be checked for any non-zero values.
    An optional list of specific error counters can be provided for granular testing.

    Expected Results
    ----------------
    * Success: The test will pass if the SNMP error counter(s) are zero/None.
    * Failure: The test will fail if the SNMP error counter(s) are non-zero/not None/Not Found or is not configured.

    Examples
    --------
    ```yaml
    anta.tests.snmp:
      - VerifySnmpErrorCounters:
          error_counters:
            - inVersionErrs
            - inBadCommunityNames
    """

    categories: ClassVar[list[str]] = ["snmp"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show snmp", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifySnmpErrorCounters test."""

        error_counters: list[SnmpErrorCounter] | None = None
        """Optional list of SNMP error counters to be verified. If not provided, test will verifies all error counters."""

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifySnmpErrorCounters."""
        error_counters = self.inputs.error_counters
        command_output = self.instance_commands[0].json_output

        # Verify SNMP PDU counters.
        if not (snmp_counters := get_value(command_output, "counters")):
            self.result.is_failure("SNMP counters not found.")
            return

        # In case SNMP error counters not provided, It will check all the error counters.
        if not error_counters:
            error_counters = list(get_args(SnmpErrorCounter))

        error_counters_not_ok = {counter: value for counter in error_counters if (value := snmp_counters.get(counter))}

        # Check if any failures
        if not error_counters_not_ok:
            self.result.is_success()
        else:
            self.result.is_failure(f"The following SNMP error counters are not found or have non-zero error counters:\n{error_counters_not_ok}")


class VerifySnmpNotificationHost(AntaTest):
    """Verifies the SNMP notification host(s) (SNMP manager) configurations.

    This test performs the following checks for each specified host:

     1. Verifies that the SNMP host(s) is configured on the device.
     2. Verifies that the notification type ("trap" or "inform") matches the expected value.
     3. Ensures that UDP port provided matches the expected value.
     4. Ensures the following depending on SNMP version:
        - For SNMP version v1/v2c, a valid community string is set and matches the expected value.
        - For SNMP version v3, a valid user field is set and matches the expected value.

    Expected Results
    ----------------
    * Success: The test will pass if all of the following conditions are met:
        - The SNMP host(s) is configured on the device.
        - The notification type ("trap" or "inform") and UDP port match the expected value.
        - Ensures the following depending on SNMP version:
            - For SNMP version v1/v2c, a community string is set and it matches the expected value.
            - For SNMP version v3, a valid user field is set and matches the expected value.
    * Failure: The test will fail if any of the following conditions is met:
        - The SNMP host(s) is not configured on the device.
        - The notification type ("trap" or "inform") or UDP port do not matches the expected value.
        - Ensures the following depending on SNMP version:
            - For SNMP version v1/v2c, a community string is not matches the expected value.
            - For SNMP version v3, an user field is not matches the expected value.

    Examples
    --------
    ```yaml
    anta.tests.snmp:
      - VerifySnmpNotificationHost:
          notification_hosts:
            - hostname: 192.168.1.100
              vrf: default
              notification_type: trap
              version: v1
              udp_port: 162
              community_string: public
              user: public
    ```
    """

    categories: ClassVar[list[str]] = ["snmp"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show snmp notification host", revision=1)]

    class Input(AntaTest.Input):
        """Input model for the VerifySnmpNotificationHost test."""

        notification_hosts: list[SnmpHost]
        """List of SNMP host(s)."""

        @field_validator("notification_hosts")
        @classmethod
        def validate_notification_hosts(cls, notification_hosts: list[SnmpHost]) -> list[SnmpHost]:
            """Validate that all required fields are provided in each SNMP Notification Host."""
            for host in notification_hosts:
                if host.version is None:
                    msg = f"{host}; 'version' field missing in the input"
                    raise ValueError(msg)
                if host.version in ["v1", "v2c"] and host.community_string is None:
                    msg = f"{host} Version: {host.version}; 'community_string' field missing in the input"
                    raise ValueError(msg)
                if host.version == "v3" and host.user is None:
                    msg = f"{host} Version: {host.version}; 'user' field missing in the input"
                    raise ValueError(msg)
            return notification_hosts

    @AntaTest.anta_test
    def test(self) -> None:
        """Main test function for VerifySnmpNotificationHost."""
        self.result.is_success()

        # If SNMP is not configured, test fails.
        if not (snmp_hosts := get_value(self.instance_commands[0].json_output, "hosts")):
            self.result.is_failure("No SNMP host is configured.")
            return

        for host in self.inputs.notification_hosts:
            vrf = "" if host.vrf == "default" else host.vrf
            hostname = str(host.hostname)
            notification_type = host.notification_type
            version = host.version
            udp_port = host.udp_port
            community_string = host.community_string
            user = host.user
            default_value = "Not Found"

            host_details = next(
                (host for host in snmp_hosts if (host.get("hostname") == hostname and host.get("protocolVersion") == version and host.get("vrf") == vrf)), None
            )
            # If expected SNMP host is not configured with the specified protocol version, test fails.
            if not host_details:
                self.result.is_failure(f"{host} Version: {version} - Not configured")
                continue

            # If actual notification type do not matches the expected value, test fails.
            if notification_type != (actual_notification_type := get_value(host_details, "notificationType", default_value)):
                self.result.is_failure(f"{host} - Incorrect notification type - Expected: {notification_type} Actual: {actual_notification_type}")

            # If actual udp port do not matches the expected value, test fails.
            if udp_port != (actual_udp_port := get_value(host_details, "port", default_value)):
                self.result.is_failure(f"{host} - Incorrect UDP port - Expected: {udp_port} Actual: {actual_udp_port}")

            user_found = user != (actual_user := get_value(host_details, "v3Params.user", default_value))
            version_user_check = (version == "v3", user_found)

            # If SNMP protocol version is v1 or v2c and actual community string do not matches the expected value, test fails.
            if version in ["v1", "v2c"] and community_string != (actual_community_string := get_value(host_details, "v1v2cParams.communityString", default_value)):
                self.result.is_failure(f"{host} Version: {version} - Incorrect community string - Expected: {community_string} Actual: {actual_community_string}")

            # If SNMP protocol version is v3 and actual user do not matches the expected value, test fails.
            elif all(version_user_check):
                self.result.is_failure(f"{host} Version: {version} - Incorrect user - Expected: {user} Actual: {actual_user}")
