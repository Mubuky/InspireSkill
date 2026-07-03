from __future__ import annotations

import click

from inspire.cli.context import EXIT_API_ERROR, Context, pass_context
from inspire.cli.formatters import json_formatter
from inspire.cli.utils.errors import exit_with_error
from inspire.cli.utils.notebook_cli import (
    WEB_AUTH_HINT,
    get_base_url,
    load_config,
    require_web_session,
)
from inspire.platform.web import browser_api as browser_api_module

from .notebook_lookup import _resolve_notebook_id


def _resolve_notebook_for_net_test(
    ctx: Context,
    *,
    notebook: str,
    workspace: str,
):
    from inspire.config.workspaces import resolve_workspace_query_scope

    session = require_web_session(ctx, hint=WEB_AUTH_HINT)
    config = load_config(ctx)
    workspace_ids, _ = resolve_workspace_query_scope(
        config,
        workspace=workspace,
        session=session,
    )
    notebook_id, _workspace_id = _resolve_notebook_id(
        ctx,
        session=session,
        config=config,
        base_url=get_base_url(),
        identifier=notebook,
        json_output=ctx.json_output,
        workspace_ids=workspace_ids,
    )
    return session, notebook_id, notebook


def _yes_no_unknown(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


@click.command("net-test")
@click.argument("notebook")
@click.option("--workspace", required=True, help="Workspace name or 'all'.")
@click.option("--timeout", type=click.IntRange(5), default=30, show_default=True)
@pass_context
def notebook_net_test(ctx: Context, notebook: str, workspace: str, timeout: int) -> None:
    """Probe notebook egress through JupyterTerminal, without SSH or rtunnel."""
    try:
        session, notebook_id, notebook_name = _resolve_notebook_for_net_test(
            ctx,
            notebook=notebook,
            workspace=workspace,
        )
        result = browser_api_module.probe_notebook_network(
            notebook_id=notebook_id,
            session=session,
            timeout=timeout,
        )
    except Exception as exc:
        exit_with_error(ctx, "APIError", str(exc), EXIT_API_ERROR)
        return

    payload = {
        "notebook": notebook_name,
        "public_internet": result.public_internet,
        "public_successes": result.public_successes,
        "public_failures": result.public_failures,
    }
    if ctx.json_output:
        click.echo(json_formatter.format_json(payload))
        return

    click.echo(f"Notebook: {notebook_name}")
    click.echo(f"Public internet: {_yes_no_unknown(result.public_internet)}")
    if result.public_successes:
        click.echo("Public successes: " + ", ".join(result.public_successes))
    if result.public_failures:
        click.echo("Public failures: " + ", ".join(result.public_failures))
