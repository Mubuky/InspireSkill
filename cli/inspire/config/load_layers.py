"""Project TOML layer.

The per-account TOML layer now covers what ``_apply_global_layer`` used to
handle — see ``load_account_layer.py``. This module only loads the
per-repo ``./.inspire/config.toml`` on top of the already-applied account
layer.
"""

from __future__ import annotations

from typing import Any

from inspire.config.models import SOURCE_PROJECT, ConfigError
from inspire.config.toml import (
    _find_project_config,
    _flatten_toml,
    _load_toml,
    _toml_key_to_field,
)

from .load_common import _ProjectLayerState, _parse_alias_map


def _apply_project_layer(
    *,
    config_dict: dict[str, Any],
    sources: dict[str, str],
) -> _ProjectLayerState:
    project_config_path = _find_project_config()
    layer_state = _ProjectLayerState(
        project_config_path=project_config_path,
        project_projects={},
        project_defaults={},
        project_context={},
    )
    if not project_config_path:
        return layer_state

    project_raw = _load_toml(project_config_path)

    # Legacy structural sections are silently ignored at project level too —
    # a project config should never carry an account catalog or [context].account.
    project_raw.pop("accounts", None)

    cli_section = project_raw.pop("cli", {})
    prefer_source = cli_section.get("prefer_source", "env")
    if prefer_source not in ("env", "toml"):
        raise ConfigError(
            f"Invalid prefer_source value: '{prefer_source}'\n"
            "Must be 'env' or 'toml' in [cli] section of project config."
        )
    layer_state.prefer_source = prefer_source

    project_compute_groups = project_raw.pop("compute_groups", [])
    project_remote_env = {str(k): str(v) for k, v in project_raw.pop("remote_env", {}).items()}
    project_projects = _parse_alias_map(project_raw.pop("projects", {}))
    layer_state.project_projects = project_projects

    raw_defaults = project_raw.pop("defaults", {})
    if isinstance(raw_defaults, dict):
        layer_state.project_defaults = raw_defaults
    raw_context = project_raw.pop("context", {})
    if isinstance(raw_context, dict):
        # [context].account has no meaning under the per-account layout.
        raw_context.pop("account", None)
        layer_state.project_context = raw_context

    project_workspaces: dict[str, str] = {}
    raw_workspaces = project_raw.get("workspaces") or {}
    if isinstance(raw_workspaces, dict):
        project_workspaces = {str(k): str(v) for k, v in raw_workspaces.items()}

    flat_project = _flatten_toml(project_raw)

    # Enforce ConfigOption.scope at the loader: a per-repo `./.inspire/config.toml`
    # may only carry project-scope keys. Account-scope identity / API / proxy
    # keys must live in the active account's `~/.inspire/accounts/<n>/config.toml`,
    # because one account is shared across many repos and silently overriding
    # auth from a repo file would let one repo poison another.
    from inspire.config.schema import get_option_by_toml

    misplaced: list[str] = []
    for toml_key in flat_project:
        opt = get_option_by_toml(toml_key)
        if opt is not None and opt.scope == "global":
            misplaced.append(toml_key)
    if misplaced:
        raise ConfigError(
            "Project config carries account-scope keys: "
            f"{', '.join(misplaced)}. Move them to the active account's "
            "config.toml (run `inspire init --discover` from inside the repo "
            "to refresh project state, or `inspire account add` to (re)set "
            "account-scope values). The project file should only contain "
            "[paths] / [context] / [defaults] / [workspaces] / [projects] / "
            "[compute_groups] / [remote_env] / [cli]."
        )

    for toml_key, value in flat_project.items():
        field_name = _toml_key_to_field(toml_key)
        if field_name and field_name in config_dict:
            config_dict[field_name] = value
            sources[field_name] = SOURCE_PROJECT

    if project_compute_groups:
        config_dict["compute_groups"] = project_compute_groups
        sources["compute_groups"] = SOURCE_PROJECT
    if project_remote_env:
        merged_remote_env = dict(config_dict.get("remote_env", {}))
        merged_remote_env.update(project_remote_env)
        config_dict["remote_env"] = merged_remote_env
        sources["remote_env"] = SOURCE_PROJECT

    # Merge project alias maps on top of account-level ones (project wins).
    if project_projects:
        merged_projects = dict(config_dict.get("projects", {}))
        merged_projects.update(project_projects)
        config_dict["projects"] = merged_projects
        sources["projects"] = SOURCE_PROJECT
    if project_workspaces:
        merged_workspaces = dict(config_dict.get("workspaces", {}))
        merged_workspaces.update(project_workspaces)
        config_dict["workspaces"] = merged_workspaces
        sources["workspaces"] = SOURCE_PROJECT

    return layer_state


__all__ = ["_apply_project_layer"]
