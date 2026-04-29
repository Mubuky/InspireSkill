"""Top-level orchestrator for layered config loading.

Layer order (later wins):

    defaults → account file → project file → project context → env → fallbacks

Identity (username / password / base_url / proxy) lives in the active
account's ``~/.inspire/accounts/<name>/config.toml``. Per-repo state
(``[context].project``, ``[paths].target_dir``, …) lives in
``./.inspire/config.toml``. Without an active account, identity fields
stay empty; callers that pass ``require_credentials=True`` will get a
``ConfigError`` pointing at ``inspire account add``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from inspire.config.models import Config
from inspire.config.toml import _find_project_config

from .load_account_layer import _apply_account_layer
from .load_accounts import _apply_project_context_and_defaults
from .load_common import _default_config_values, _initialize_sources
from .load_layers import _apply_project_layer
from .load_runtime import (
    _apply_env_layer,
    _apply_password_and_token_fallbacks,
    _validate_required_config,
)


_LEGACY_WORKSPACE_DEFAULT_WARNING_EMITTED = False


def _warn_legacy_workspace_default(account_path: Path | None, project_path: Path | None) -> None:
    """One-shot stderr warning if user still has the v3.0.x default-workspace fields.

    Removed in v3.1.0:
      - ``[job].workspace_id`` in either account or project ``config.toml``
      - ``[context].workspace`` in project ``config.toml``
      - ``INSPIRE_WORKSPACE_ID`` env var

    The legacy fields are silently ignored on load (they don't exist in
    the schema anymore), but emitting a one-time hint on first run helps
    users understand why their workflow stopped picking up the default.
    """
    global _LEGACY_WORKSPACE_DEFAULT_WARNING_EMITTED
    if _LEGACY_WORKSPACE_DEFAULT_WARNING_EMITTED:
        return

    hits: list[str] = []
    for path in (account_path, project_path):
        if not path or not path.exists():
            continue
        try:
            from inspire.config.toml import _load_toml

            data = _load_toml(path)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        job_section = data.get("job") if isinstance(data.get("job"), dict) else {}
        if isinstance(job_section, dict) and job_section.get("workspace_id"):
            hits.append(f"{path}: [job].workspace_id")
        ctx_section = data.get("context") if isinstance(data.get("context"), dict) else {}
        if isinstance(ctx_section, dict) and ctx_section.get("workspace"):
            hits.append(f"{path}: [context].workspace")

    if os.environ.get("INSPIRE_WORKSPACE_ID", "").strip():
        hits.append("env: INSPIRE_WORKSPACE_ID")

    if hits:
        _LEGACY_WORKSPACE_DEFAULT_WARNING_EMITTED = True
        try:
            sys.stderr.write(
                "\033[33m! v3.1.0 dropped the default-workspace concept. "
                "Found legacy field(s) (now ignored):\n"
            )
            for hit in hits:
                sys.stderr.write(f"    - {hit}\n")
            sys.stderr.write(
                "  Pass `--workspace <alias>` on each command instead "
                "(aliases live under [workspaces] in your account config).\033[0m\n"
            )
        except Exception:
            pass


def config_from_files_and_env(
    *,
    require_target_dir: bool = False,
    require_credentials: bool = True,
) -> tuple[Config, dict[str, str]]:
    """Load config from files + env vars with layered precedence."""
    config_dict = _default_config_values()
    sources = _initialize_sources(config_dict)

    account_config_path = _apply_account_layer(
        config_dict=config_dict,
        sources=sources,
    )
    project_layer_state = _apply_project_layer(config_dict=config_dict, sources=sources)

    _apply_project_context_and_defaults(
        config_dict=config_dict,
        sources=sources,
        project_context=project_layer_state.project_context,
        project_defaults=project_layer_state.project_defaults,
    )

    env_password = _apply_env_layer(
        config_dict=config_dict,
        sources=sources,
        prefer_source=project_layer_state.prefer_source,
    )
    _apply_password_and_token_fallbacks(
        config_dict=config_dict,
        sources=sources,
        env_password=env_password,
    )
    _validate_required_config(
        config_dict=config_dict,
        require_credentials=require_credentials,
        require_target_dir=require_target_dir,
    )

    config_dict["prefer_source"] = project_layer_state.prefer_source
    config = Config(**config_dict)
    config._global_config_path = account_config_path  # type: ignore[attr-defined]
    config._project_config_path = project_layer_state.project_config_path  # type: ignore[attr-defined]
    config._sources = sources  # type: ignore[attr-defined]

    _warn_legacy_workspace_default(
        account_config_path,
        project_layer_state.project_config_path,
    )

    return config, sources


def get_config_paths() -> tuple[Path | None, Path | None]:
    """Return (account_config_path_if_any, project_config_path_if_any).

    The first slot historically held the legacy global path; it now holds
    the active account's config path. Call sites that used to distinguish
    "global vs project" still work — the first slot is the writable,
    non-repo-specific config.
    """
    from .load_account_layer import _resolve_account_config_path

    account_path = _resolve_account_config_path()
    project_path = _find_project_config()
    return account_path, project_path


__all__ = ["config_from_files_and_env", "get_config_paths"]
