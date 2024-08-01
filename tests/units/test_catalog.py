# Copyright (c) 2023-2024 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""test anta.device.py."""

from __future__ import annotations

from json import load as json_load
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from yaml import safe_load

from anta.catalog import AntaCatalog, AntaCatalogFile, AntaTestDefinition
from anta.models import AntaTest
from anta.tests.interfaces import VerifyL3MTU
from anta.tests.mlag import VerifyMlagStatus
from anta.tests.software import VerifyEOSVersion
from anta.tests.system import (
    VerifyAgentLogs,
    VerifyCoredump,
    VerifyCPUUtilization,
    VerifyFileSystemUtilization,
    VerifyMemoryUtilization,
    VerifyNTP,
    VerifyReloadCause,
    VerifyUptime,
)
from tests.lib.utils import generate_test_ids_list
from tests.units.test_models import FakeTestWithInput

# Test classes used as expected values

DATA_DIR: Path = Path(__file__).parent.parent.resolve() / "data"

INIT_CATALOG_DATA: list[dict[str, Any]] = [
    {
        "name": "test_catalog",
        "filename": "test_catalog.yml",
        "tests": [
            (VerifyEOSVersion, VerifyEOSVersion.Input(versions=["4.31.1F"])),
        ],
    },
    {
        "name": "test_catalog",
        "filename": "test_catalog.json",
        "file_format": "json",
        "tests": [
            (VerifyEOSVersion, VerifyEOSVersion.Input(versions=["4.31.1F"])),
        ],
    },
    {
        "name": "test_catalog_with_tags",
        "filename": "test_catalog_with_tags.yml",
        "tests": [
            (
                VerifyUptime,
                VerifyUptime.Input(
                    minimum=10,
                    filters=VerifyUptime.Input.Filters(tags={"fabric"}),
                ),
            ),
            (
                VerifyUptime,
                VerifyUptime.Input(
                    minimum=9,
                    filters=VerifyUptime.Input.Filters(tags={"leaf"}),
                ),
            ),
            (VerifyReloadCause, {"filters": {"tags": ["leaf", "spine"]}}),
            (VerifyCoredump, VerifyCoredump.Input()),
            (VerifyAgentLogs, AntaTest.Input()),
            (VerifyCPUUtilization, VerifyCPUUtilization.Input(filters=VerifyCPUUtilization.Input.Filters(tags={"leaf"}))),
            (VerifyMemoryUtilization, VerifyMemoryUtilization.Input(filters=VerifyMemoryUtilization.Input.Filters(tags={"testdevice"}))),
            (VerifyFileSystemUtilization, None),
            (VerifyNTP, {}),
            (VerifyMlagStatus, None),
            (VerifyL3MTU, {"mtu": 1500, "filters": {"tags": ["demo"]}}),
        ],
    },
    {
        "name": "test_empty_catalog",
        "filename": "test_empty_catalog.yml",
        "tests": [],
    },
    {
        "name": "test_empty_dict_catalog",
        "filename": "test_empty_dict_catalog.yml",
        "tests": [],
    },
]
CATALOG_PARSE_FAIL_DATA: list[dict[str, Any]] = [
    {
        "name": "undefined_tests",
        "filename": "test_catalog_wrong_format.toto",
        "file_format": "toto",
        "error": "'toto' is not a valid format for an AntaCatalog file. Only 'yaml' and 'json' are supported.",
    },
    {
        "name": "invalid_json",
        "filename": "test_catalog_invalid_json.json",
        "file_format": "json",
        "error": "JSONDecodeError",
    },
    {
        "name": "undefined_tests",
        "filename": "test_catalog_with_undefined_tests.yml",
        "error": "FakeTest is not defined in Python module anta.tests.software",
    },
    {
        "name": "undefined_module",
        "filename": "test_catalog_with_undefined_module.yml",
        "error": "Module named anta.tests.undefined cannot be imported",
    },
    {
        "name": "undefined_module",
        "filename": "test_catalog_with_undefined_module.yml",
        "error": "Module named anta.tests.undefined cannot be imported",
    },
    {
        "name": "syntax_error",
        "filename": "test_catalog_with_syntax_error_module.yml",
        "error": "Value error, Module named tests.data.syntax_error cannot be imported. Verify that the module exists and there is no Python syntax issues.",
    },
    {
        "name": "undefined_module_nested",
        "filename": "test_catalog_with_undefined_module_nested.yml",
        "error": "Module named undefined from package anta.tests cannot be imported",
    },
    {
        "name": "not_a_list",
        "filename": "test_catalog_not_a_list.yml",
        "error": "Value error, Syntax error when parsing: True\nIt must be a list of ANTA tests. Check the test catalog.",
    },
    {
        "name": "test_definition_not_a_dict",
        "filename": "test_catalog_test_definition_not_a_dict.yml",
        "error": "Value error, Syntax error when parsing: VerifyEOSVersion\nIt must be a dictionary. Check the test catalog.",
    },
    {
        "name": "test_definition_multiple_dicts",
        "filename": "test_catalog_test_definition_multiple_dicts.yml",
        "error": "Value error, Syntax error when parsing: {'VerifyEOSVersion': {'versions': ['4.25.4M', '4.26.1F']}, "
        "'VerifyTerminAttrVersion': {'versions': ['4.25.4M']}}\nIt must be a dictionary with a single entry. Check the indentation in the test catalog.",
    },
    {"name": "wrong_type_after_parsing", "filename": "test_catalog_wrong_type.yml", "error": "must be a dict, got str"},
]
CATALOG_FROM_DICT_FAIL_DATA: list[dict[str, Any]] = [
    {
        "name": "undefined_tests",
        "filename": "test_catalog_with_undefined_tests.yml",
        "error": "FakeTest is not defined in Python module anta.tests.software",
    },
    {
        "name": "wrong_type",
        "filename": "test_catalog_wrong_type.yml",
        "error": "Wrong input type for catalog data, must be a dict, got str",
    },
]
CATALOG_FROM_LIST_FAIL_DATA: list[dict[str, Any]] = [
    {
        "name": "wrong_inputs",
        "tests": [
            (
                FakeTestWithInput,
                AntaTest.Input(),
            ),
        ],
        "error": "Test input has type AntaTest.Input but expected type FakeTestWithInput.Input",
    },
    {
        "name": "no_test",
        "tests": [(None, None)],
        "error": "Input should be a subclass of AntaTest",
    },
    {
        "name": "no_input_when_required",
        "tests": [(FakeTestWithInput, None)],
        "error": "FakeTestWithInput test inputs are not valid: 1 validation error for Input\n\tstring\n\t  Field required",
    },
    {
        "name": "wrong_input_type",
        "tests": [(FakeTestWithInput, {"string": True})],
        "error": "FakeTestWithInput test inputs are not valid: 1 validation error for Input\n\tstring\n\t  Input should be a valid string",
    },
]
TESTS_SETTER_FAIL_DATA: list[dict[str, Any]] = [
    {
        "name": "not_a_list",
        "tests": "not_a_list",
        "error": "The catalog must contain a list of tests",
    },
    {
        "name": "not_a_list_of_test_definitions",
        "tests": [42, 43],
        "error": "A test in the catalog must be an AntaTestDefinition instance",
    },
]


class TestAntaCatalog:
    """Test for anta.catalog.AntaCatalog."""

    @pytest.mark.parametrize("catalog_data", INIT_CATALOG_DATA, ids=generate_test_ids_list(INIT_CATALOG_DATA))
    def test_parse(self, catalog_data: dict[str, Any]) -> None:
        """Instantiate AntaCatalog from a file."""
        catalog: AntaCatalog = AntaCatalog.parse(DATA_DIR / catalog_data["filename"], file_format=catalog_data.get("file_format", "yaml"))

        assert len(catalog.tests) == len(catalog_data["tests"])
        for test_id, (test, inputs_data) in enumerate(catalog_data["tests"]):
            assert catalog.tests[test_id].test == test
            if inputs_data is not None:
                inputs = test.Input(**inputs_data) if isinstance(inputs_data, dict) else inputs_data
                assert inputs == catalog.tests[test_id].inputs

    @pytest.mark.parametrize("catalog_data", INIT_CATALOG_DATA, ids=generate_test_ids_list(INIT_CATALOG_DATA))
    def test_from_list(self, catalog_data: dict[str, Any]) -> None:
        """Instantiate AntaCatalog from a list."""
        catalog: AntaCatalog = AntaCatalog.from_list(catalog_data["tests"])

        assert len(catalog.tests) == len(catalog_data["tests"])
        for test_id, (test, inputs_data) in enumerate(catalog_data["tests"]):
            assert catalog.tests[test_id].test == test
            if inputs_data is not None:
                inputs = test.Input(**inputs_data) if isinstance(inputs_data, dict) else inputs_data
                assert inputs == catalog.tests[test_id].inputs

    @pytest.mark.parametrize("catalog_data", INIT_CATALOG_DATA, ids=generate_test_ids_list(INIT_CATALOG_DATA))
    def test_from_dict(self, catalog_data: dict[str, Any]) -> None:
        """Instantiate AntaCatalog from a dict."""
        file = DATA_DIR / catalog_data["filename"]
        with file.open(encoding="UTF-8") as file:
            file_format = catalog_data.get("file_format", "yaml")
            data = safe_load(file) if file_format == "yaml" else json_load(file)
            catalog: AntaCatalog = AntaCatalog.from_dict(data)

        assert len(catalog.tests) == len(catalog_data["tests"])
        for test_id, (test, inputs_data) in enumerate(catalog_data["tests"]):
            assert catalog.tests[test_id].test == test
            if inputs_data is not None:
                inputs = test.Input(**inputs_data) if isinstance(inputs_data, dict) else inputs_data
                assert inputs == catalog.tests[test_id].inputs

    @pytest.mark.parametrize("catalog_data", CATALOG_PARSE_FAIL_DATA, ids=generate_test_ids_list(CATALOG_PARSE_FAIL_DATA))
    def test_parse_fail(self, catalog_data: dict[str, Any]) -> None:
        """Errors when instantiating AntaCatalog from a file."""
        with pytest.raises((ValidationError, TypeError, ValueError, OSError)) as exec_info:
            AntaCatalog.parse(DATA_DIR / catalog_data["filename"], file_format=catalog_data.get("file_format", "yaml"))
        if isinstance(exec_info.value, ValidationError):
            assert catalog_data["error"] in exec_info.value.errors()[0]["msg"]
        else:
            assert catalog_data["error"] in str(exec_info)

    def test_parse_fail_parsing(self, caplog: pytest.LogCaptureFixture) -> None:
        """Errors when instantiating AntaCatalog from a file."""
        with pytest.raises(FileNotFoundError) as exec_info:
            AntaCatalog.parse(DATA_DIR / "catalog_does_not_exist.yml")
        assert "No such file or directory" in str(exec_info)
        assert len(caplog.record_tuples) >= 1
        _, _, message = caplog.record_tuples[0]
        assert "Unable to parse ANTA Test Catalog file" in message
        assert "FileNotFoundError: [Errno 2] No such file or directory" in message

    @pytest.mark.parametrize("catalog_data", CATALOG_FROM_LIST_FAIL_DATA, ids=generate_test_ids_list(CATALOG_FROM_LIST_FAIL_DATA))
    def test_from_list_fail(self, catalog_data: dict[str, Any]) -> None:
        """Errors when instantiating AntaCatalog from a list of tuples."""
        with pytest.raises(ValidationError) as exec_info:
            AntaCatalog.from_list(catalog_data["tests"])
        assert catalog_data["error"] in exec_info.value.errors()[0]["msg"]

    @pytest.mark.parametrize("catalog_data", CATALOG_FROM_DICT_FAIL_DATA, ids=generate_test_ids_list(CATALOG_FROM_DICT_FAIL_DATA))
    def test_from_dict_fail(self, catalog_data: dict[str, Any]) -> None:
        """Errors when instantiating AntaCatalog from a list of tuples."""
        file = DATA_DIR / catalog_data["filename"]
        with file.open(encoding="UTF-8") as file:
            data = safe_load(file)
        with pytest.raises((ValidationError, TypeError)) as exec_info:
            AntaCatalog.from_dict(data)
        if isinstance(exec_info.value, ValidationError):
            assert catalog_data["error"] in exec_info.value.errors()[0]["msg"]
        else:
            assert catalog_data["error"] in str(exec_info)

    def test_filename(self) -> None:
        """Test filename."""
        catalog = AntaCatalog(filename="test")
        assert catalog.filename == Path("test")
        catalog = AntaCatalog(filename=Path("test"))
        assert catalog.filename == Path("test")

    @pytest.mark.parametrize("catalog_data", INIT_CATALOG_DATA, ids=generate_test_ids_list(INIT_CATALOG_DATA))
    def test__tests_setter_success(self, catalog_data: dict[str, Any]) -> None:
        """Success when setting AntaCatalog.tests from a list of tuples."""
        catalog = AntaCatalog()
        catalog.tests = [AntaTestDefinition(test=test, inputs=inputs) for test, inputs in catalog_data["tests"]]
        assert len(catalog.tests) == len(catalog_data["tests"])
        for test_id, (test, inputs_data) in enumerate(catalog_data["tests"]):
            assert catalog.tests[test_id].test == test
            if inputs_data is not None:
                inputs = test.Input(**inputs_data) if isinstance(inputs_data, dict) else inputs_data
                assert inputs == catalog.tests[test_id].inputs

    @pytest.mark.parametrize("catalog_data", TESTS_SETTER_FAIL_DATA, ids=generate_test_ids_list(TESTS_SETTER_FAIL_DATA))
    def test__tests_setter_fail(self, catalog_data: dict[str, Any]) -> None:
        """Errors when setting AntaCatalog.tests from a list of tuples."""
        catalog = AntaCatalog()
        with pytest.raises(TypeError) as exec_info:
            catalog.tests = catalog_data["tests"]
        assert catalog_data["error"] in str(exec_info)

    def test_build_indexes_all(self) -> None:
        """Test AntaCatalog.build_indexes()."""
        catalog: AntaCatalog = AntaCatalog.parse(DATA_DIR / "test_catalog_with_tags.yml")
        catalog.build_indexes()
        assert len(catalog.tests_without_tags) == 5
        assert "leaf" in catalog.tag_to_tests
        assert len(catalog.tag_to_tests["leaf"]) == 3
        all_unique_tests = catalog.tests_without_tags
        for tests in catalog.tag_to_tests.values():
            all_unique_tests.update(tests)
        assert len(all_unique_tests) == 11
        assert catalog.indexes_built is True

    def test_build_indexes_filtered(self) -> None:
        """Test AntaCatalog.build_indexes()."""
        catalog: AntaCatalog = AntaCatalog.parse(DATA_DIR / "test_catalog_with_tags.yml")
        catalog.build_indexes({"VerifyUptime", "VerifyCoredump", "VerifyL3MTU"})
        assert "leaf" in catalog.tag_to_tests
        assert len(catalog.tag_to_tests["leaf"]) == 1
        assert len(catalog.tests_without_tags) == 1
        all_unique_tests = catalog.tests_without_tags
        for tests in catalog.tag_to_tests.values():
            all_unique_tests.update(tests)
        assert len(all_unique_tests) == 4
        assert catalog.indexes_built is True

    def test_get_tests_by_tags(self) -> None:
        """Test AntaCatalog.get_tests_by_tags()."""
        catalog: AntaCatalog = AntaCatalog.parse(DATA_DIR / "test_catalog_with_tags.yml")
        catalog.build_indexes()
        tests: set[AntaTestDefinition] = catalog.get_tests_by_tags(tags={"leaf"})
        assert len(tests) == 3
        tests = catalog.get_tests_by_tags(tags={"leaf", "spine"}, strict=True)
        assert len(tests) == 1

    def test_merge(self) -> None:
        """Test AntaCatalog.merge()."""
        catalog1: AntaCatalog = AntaCatalog.parse(DATA_DIR / "test_catalog.yml")
        assert len(catalog1.tests) == 1
        catalog2: AntaCatalog = AntaCatalog.parse(DATA_DIR / "test_catalog.yml")
        assert len(catalog2.tests) == 1
        catalog3: AntaCatalog = AntaCatalog.parse(DATA_DIR / "test_catalog_medium.yml")
        assert len(catalog3.tests) == 228

        assert len(catalog1.merge(catalog2).tests) == 2
        assert len(catalog1.tests) == 1
        assert len(catalog2.tests) == 1

        assert len(catalog2.merge(catalog3).tests) == 229
        assert len(catalog2.tests) == 1
        assert len(catalog3.tests) == 228

    def test_dump(self) -> None:
        """Test AntaCatalog.dump()."""
        catalog: AntaCatalog = AntaCatalog.parse(DATA_DIR / "test_catalog.yml")
        assert len(catalog.tests) == 1
        file: AntaCatalogFile = catalog.dump()
        assert sum(len(tests) for tests in file.root.values()) == 1

        catalog = AntaCatalog.parse(DATA_DIR / "test_catalog_medium.yml")
        assert len(catalog.tests) == 228
        file = catalog.dump()
        assert sum(len(tests) for tests in file.root.values()) == 228


class TestAntaCatalogFile:  # pylint: disable=too-few-public-methods
    """Test for anta.catalog.AntaCatalogFile."""

    def test_yaml(self) -> None:
        """Test AntaCatalogFile.yaml()."""
        file = DATA_DIR / "test_catalog_medium.yml"
        catalog = AntaCatalog.parse(file)
        assert len(catalog.tests) == 228
        catalog_yaml_str = catalog.dump().yaml()
        with file.open(encoding="UTF-8") as f:
            assert catalog_yaml_str == f.read()
