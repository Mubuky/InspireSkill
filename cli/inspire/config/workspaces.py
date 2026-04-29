"""Workspace selection utilities.

The CLI never guesses a workspace by GPU type or "CPU vs GPU" role. As of
v3.1.0 there is also **no implicit "default workspace"** — workspace must
come from one of:

1. ``--workspace <name-or-id>`` on the command itself → ``explicit_*``
2. The ``[workspaces]`` alias map (looked up by ``--workspace cpu`` etc.)

There is intentionally no config-level fallback. ``[job].workspace_id`` /
``INSPIRE_WORKSPACE_ID`` / ``[context].workspace`` were removed in v3.1.0
because "default workspace" was a redundant concept once ``[context].project``
exists, and made it easy for commands to silently target the wrong workspace.

If none of the explicit paths resolve, ``select_workspace_id`` returns
``None`` and the caller is expected to surface a clear error pointing at
``--workspace`` or the alias map.
"""

from __future__ import annotations

import re
from typing import Optional

from inspire.config import Config, ConfigError

_WORKSPACE_ID_RE = re.compile(
    r"^ws-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_PLACEHOLDER_WORKSPACE_ID = "ws-00000000-0000-0000-0000-000000000000"


def _validate_workspace_id(value: str) -> None:
    if value == _PLACEHOLDER_WORKSPACE_ID:
        raise ConfigError(
            "workspace_id is the placeholder. Pass a real workspace via "
            "--workspace <alias> (configure aliases under [workspaces])."
        )
    if not _WORKSPACE_ID_RE.match(value):
        raise ConfigError(f"Invalid workspace_id format: {value!r}")


def select_workspace_id(
    config: Config,
    *,
    gpu_type: Optional[str] = None,  # ignored — kept for backwards-compat signature
    cpu_only: Optional[bool] = None,  # ignored
    prefer_internet: bool = False,  # ignored
    explicit_workspace_id: Optional[str] = None,
    explicit_workspace_name: Optional[str] = None,
) -> Optional[str]:
    """Resolve a workspace id from explicit args only — no config default.

    Precedence:
      1. ``explicit_workspace_id``
      2. ``explicit_workspace_name`` — looked up against ``[workspaces]``
      3. ``None`` (no fallback) — caller MUST handle by erroring out.

    Removed in v3.1.0: ``config.job_workspace_id`` fallback (was sourced
    from ``[job].workspace_id`` / ``INSPIRE_WORKSPACE_ID`` /
    ``[context].workspace``). See module docstring.
    """
    del gpu_type, cpu_only, prefer_internet  # no longer consulted

    if explicit_workspace_id:
        _validate_workspace_id(explicit_workspace_id)
        return explicit_workspace_id

    if explicit_workspace_name:
        key = explicit_workspace_name.strip()
        if not key:
            raise ConfigError("Workspace name cannot be empty")

        candidate: Optional[str] = None
        normalized = key.lower()
        for name, workspace_id in (config.workspaces or {}).items():
            if name.lower() == normalized:
                candidate = workspace_id
                break

        if not candidate:
            available = sorted((config.workspaces or {}).keys())
            available_hint = ", ".join(available) if available else "(none configured)"
            raise ConfigError(
                f"Unknown workspace name: {explicit_workspace_name!r}. "
                f"Configure it under [workspaces] in config.toml. Available: {available_hint}"
            )

        _validate_workspace_id(candidate)
        return candidate

    return None


def workspace_required_hint(config: Config) -> str:
    """Build a one-line hint for the missing-workspace error path.

    Lists configured aliases so the user knows what `--workspace` will accept.
    """
    aliases = sorted((config.workspaces or {}).keys())
    if aliases:
        return (
            "pass --workspace <alias> "
            f"(configured aliases: {', '.join(aliases)})"
        )
    return (
        "pass --workspace <alias>. No aliases configured yet — "
        "run `inspire init --discover` to populate [workspaces]"
    )
