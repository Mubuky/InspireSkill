"""`inspire model` subcommands — registry browsing."""

from __future__ import annotations

from typing import Any, Optional

import click

from inspire.cli.context import (
    Context,
    EXIT_API_ERROR,
    EXIT_AUTH_ERROR,
    EXIT_CONFIG_ERROR,
    pass_context,
)
from inspire.cli.formatters import json_formatter
from inspire.cli.formatters.human_formatter import format_epoch
from inspire.cli.utils.auth import AuthenticationError
from inspire.cli.utils.errors import exit_with_error as _handle_error
from inspire.cli.utils.id_resolver import resolve_by_name
from inspire.cli.utils.raw_ids import scrub_raw_ids
from inspire.config import Config, ConfigError
from inspire.config.workspaces import select_workspace_id
from inspire.platform.web import browser_api as browser_api_module
from inspire.platform.web.session import get_web_session


def _resolve_workspace_id(config: Config, workspace: Optional[str]) -> Optional[str]:
    if workspace is None:
        return None
    return select_workspace_id(config, explicit_workspace_name=workspace)


def _format_model_rows(rows: list[dict[str, str]], total: int) -> str:
    """Render a model-registry list.

    ``total`` is the server-reported total across pages; the footer prints
    ``Showing X of Y`` when ``len(rows) < total`` so paginating users don't
    confuse the visible page with the full registry.
    """
    if not rows:
        return "No models found."
    widths = {
        col: max(len(col.title().replace("_", " ")), *(len(r[col]) for r in rows))
        for col in ("name", "latest", "vllm", "created_at")
    }
    header = (
        f"{'Name':<{widths['name']}} {'Latest':<{widths['latest']}} {'vLLM':<{widths['vllm']}} "
        f"{'Created':<{widths['created_at']}}"
    )
    sep = "-" * len(header)
    lines = ["Model Registry", header, sep]
    for r in rows:
        lines.append(
            f"{r['name']:<{widths['name']}} "
            f"{r['latest']:<{widths['latest']}} "
            f"{r['vllm']:<{widths['vllm']}} "
            f"{r['created_at']:<{widths['created_at']}}"
        )
    lines.append(sep)
    if total > len(rows):
        lines.append(f"Showing {len(rows)} of {total}")
    else:
        lines.append(f"Total: {len(rows)}")
    return "\n".join(lines)


def _resolve_model_name(ctx: Context, name: str) -> str:
    def _lister():
        session = get_web_session()
        items, _ = browser_api_module.list_models(page=1, page_size=-1, session=session)
        return [
            {
                "name": m.name,
                "id": m.model_id,
                "status": "vLLM" if m.is_vllm_compatible else "",
                "created_at": format_epoch(m.created_at) if m.created_at else "",
            }
            for m in items
        ]

    return resolve_by_name(
        ctx,
        name=name,
        resource_type="model",
        list_candidates=_lister,
        json_output=ctx.json_output,
    )


@click.command("list")
@click.option("--workspace", default=None, help="Workspace name (from [workspaces])")
@click.option("--page", type=int, default=1, show_default=True)
@click.option("--page-size", type=int, default=-1, show_default=True, help="-1 = fetch all")
@pass_context
def list_model(
    ctx: Context,
    workspace: Optional[str],
    page: int,
    page_size: int,
) -> None:
    """List models in the current (or given) workspace."""
    try:
        config, _ = Config.from_files_and_env(require_credentials=False)
        resolved_workspace = _resolve_workspace_id(config, workspace)
        session = get_web_session()
        items, total = browser_api_module.list_models(
            workspace_id=resolved_workspace,
            page=page,
            page_size=page_size,
            session=session,
        )

        if ctx.json_output:
            click.echo(
                json_formatter.format_json(
                    {"total": total, "items": [m.raw if m.raw else m.__dict__ for m in items]}
                )
            )
            return

        rows = [
            {
                "name": scrub_raw_ids(m.name or "-"),
                "latest": scrub_raw_ids(m.latest_version or "-"),
                "vllm": "yes" if m.is_vllm_compatible else "no",
                "created_at": scrub_raw_ids(format_epoch(m.created_at) if m.created_at else "-"),
            }
            for m in items
        ]
        click.echo(_format_model_rows(rows, total=int(total) if total is not None else len(rows)))

    except ConfigError as e:
        _handle_error(ctx, "ConfigError", str(e), EXIT_CONFIG_ERROR)
    except AuthenticationError as e:
        _handle_error(ctx, "AuthenticationError", str(e), EXIT_AUTH_ERROR)
    except Exception as e:
        _handle_error(ctx, "APIError", str(e), EXIT_API_ERROR)


@click.command("status")
@click.argument("name")
@pass_context
def status_model(ctx: Context, name: str) -> None:
    """Show detail of a specific model by name."""
    try:
        session = get_web_session()
        model_id = _resolve_model_name(ctx, name)
        data = browser_api_module.get_model_detail(model_id=model_id, session=session)

        if ctx.json_output:
            click.echo(json_formatter.format_json(data))
            return

        model_payload = data.get("model")
        inner: dict[str, Any] = model_payload if isinstance(model_payload, dict) else data
        click.echo("Model")
        click.echo(f"Name:        {scrub_raw_ids(inner.get('name', 'N/A'))}")
        click.echo(f"Description: {scrub_raw_ids(inner.get('description', '') or '(none)')}")
        click.echo(f"vLLM-ready:  {'yes' if inner.get('is_vllm_compatible') else 'no'}")
        click.echo(f"Published:   {'yes' if inner.get('has_published') else 'no'}")
        if data.get("project_name"):
            click.echo(f"Project:     {scrub_raw_ids(data.get('project_name'))}")
        if data.get("user_name"):
            click.echo(f"Owner:       {scrub_raw_ids(data.get('user_name'))}")
        if inner.get("created_at"):
            click.echo(f"Created:     {format_epoch(inner.get('created_at'))}")

    except AuthenticationError as e:
        _handle_error(ctx, "AuthenticationError", str(e), EXIT_AUTH_ERROR)
    except Exception as e:
        _handle_error(ctx, "APIError", str(e), EXIT_API_ERROR)


@click.command("versions")
@click.argument("name")
@pass_context
def versions_model(ctx: Context, name: str) -> None:
    """List all versions of a model by name."""
    try:
        session = get_web_session()
        model_id = _resolve_model_name(ctx, name)
        data = browser_api_module.list_model_versions(model_id=model_id, session=session)

        if ctx.json_output:
            click.echo(json_formatter.format_json(data))
            return

        items = data.get("list") if isinstance(data, dict) else None
        if not items:
            click.echo(f"No versions for model {scrub_raw_ids(name)}.")
            return

        click.echo(
            f"Versions for {scrub_raw_ids(name)}  (total={data.get('total', len(items))}, "
            f"next={scrub_raw_ids(data.get('next_version', '?'))})"
        )
        for i, item in enumerate(items, 1):
            model_payload = item.get("model") if isinstance(item, dict) else None
            inner = model_payload if isinstance(model_payload, dict) else item
            version = inner.get("version") or inner.get("model_version") or "?"
            size = inner.get("model_size_gb") or inner.get("size") or ""
            path = inner.get("model_path") or ""
            vllm = "vLLM" if inner.get("is_vllm_compatible") else ""
            bits = [f"v{version}"]
            if size:
                bits.append(f"{size} GB")
            if vllm:
                bits.append(vllm)
            if path:
                bits.append(f"path={scrub_raw_ids(path)}")
            click.echo(f"  [{i}] " + "  ".join(scrub_raw_ids(b) for b in bits))

    except AuthenticationError as e:
        _handle_error(ctx, "AuthenticationError", str(e), EXIT_AUTH_ERROR)
    except Exception as e:
        _handle_error(ctx, "APIError", str(e), EXIT_API_ERROR)


__all__ = ["list_model", "status_model", "versions_model"]
