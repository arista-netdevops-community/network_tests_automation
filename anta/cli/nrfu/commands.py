# Copyright (c) 2023-2025 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
"""Click commands that render ANTA tests results."""

from __future__ import annotations

import logging
import pathlib
from typing import Literal

import click

from anta.cli.utils import exit_with_code

from .utils import print_jinja, print_json, print_table, print_text, run_tests, save_markdown_report, save_to_csv

logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.option(
    "--group-by",
    default=None,
    type=click.Choice(["device", "test"], case_sensitive=False),
    help="Group result by test or device.",
    required=False,
)
@click.option(
    "--expand",
    "-x",
    default=False,
    show_envvar=True,
    is_flag=True,
    show_default=True,
    help="Flag to indicate if test descriptions and atomic results should be shown.",
)
@click.option(
    "--inputs",
    default=None,
    show_envvar=True,
    type=click.Choice(["all", "parent", "atomic"], case_sensitive=False),
    show_default=True,
    help="Option to indicate if inputs related to each tests or their atomic results should be shown. All show inputs from parent and atomic results.",
)
def table(ctx: click.Context, *, group_by: Literal["device", "test"] | None, expand: bool, inputs: Literal["all", "parent", "atomic"] | None) -> None:
    """ANTA command to check network state with table results."""
    run_tests(ctx)
    print_table(ctx, expand=expand, group_by=group_by, inputs=inputs)
    exit_with_code(ctx)


@click.command()
@click.pass_context
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False, exists=False, writable=True, path_type=pathlib.Path),
    show_envvar=True,
    required=False,
    help="Path to save report as a JSON file",
)
def json(ctx: click.Context, output: pathlib.Path | None) -> None:
    """ANTA command to check network state with JSON results."""
    run_tests(ctx)
    print_json(ctx, output=output)
    exit_with_code(ctx)


@click.command()
@click.pass_context
@click.option(
    "--expand-atomic",
    "-x",
    default=False,
    show_envvar=True,
    is_flag=True,
    show_default=True,
    help="Flag to indicate if atomic results should be rendered",
)
def text(ctx: click.Context, *, expand_atomic: bool) -> None:
    """ANTA command to check network state with text results."""
    run_tests(ctx)
    print_text(ctx, expand_atomic=expand_atomic)
    exit_with_code(ctx)


@click.command()
@click.pass_context
@click.option(
    "--csv-output",
    type=click.Path(
        file_okay=True,
        dir_okay=False,
        exists=False,
        writable=True,
        path_type=pathlib.Path,
    ),
    show_envvar=True,
    required=False,
    help="Path to save report as a CSV file",
)
def csv(ctx: click.Context, csv_output: pathlib.Path) -> None:
    """ANTA command to check network states with CSV result."""
    run_tests(ctx)
    save_to_csv(ctx, csv_file=csv_output)
    exit_with_code(ctx)


@click.command()
@click.pass_context
@click.option(
    "--template",
    "-tpl",
    type=click.Path(file_okay=True, dir_okay=False, exists=True, readable=True, path_type=pathlib.Path),
    show_envvar=True,
    required=True,
    help="Path to the template to use for the report",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False, exists=False, writable=True, path_type=pathlib.Path),
    show_envvar=True,
    required=False,
    help="Path to save report as a file",
)
def tpl_report(ctx: click.Context, template: pathlib.Path, output: pathlib.Path | None) -> None:
    """ANTA command to check network state with templated report."""
    run_tests(ctx)
    print_jinja(results=ctx.obj["result_manager"], template=template, output=output)
    exit_with_code(ctx)


@click.command()
@click.pass_context
@click.option(
    "--md-output",
    type=click.Path(file_okay=True, dir_okay=False, exists=False, writable=True, path_type=pathlib.Path),
    show_envvar=True,
    required=True,
    help="Path to save the report as a Markdown file",
)
def md_report(ctx: click.Context, md_output: pathlib.Path) -> None:
    """ANTA command to check network state with Markdown report."""
    run_tests(ctx)
    save_markdown_report(ctx, md_output=md_output)
    exit_with_code(ctx)
