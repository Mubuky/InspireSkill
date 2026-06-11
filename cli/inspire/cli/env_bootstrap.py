"""Early dotenv loading for the CLI entrypoint.

This is intentionally an entrypoint bootstrap, not part of the core config
loader: the goal is to make the whole process see project-declared variables,
including lower-level helpers that read ``os.environ`` directly.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Any

import click

from inspire.config.toml import (
    _find_project_configs,
    _load_toml,
    _project_config_write_path,
)

_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LOADED_ENV_FILE_KEYS: set[str] = set()
_LOADED_ENV_FILE_VALUES: dict[str, str] = {}
_LOADED_ENV_FILE_PATH: Path | None = None


def reset_loaded_env_file_state() -> None:
    for key, value in list(_LOADED_ENV_FILE_VALUES.items()):
        if os.environ.get(key) == value:
            os.environ.pop(key, None)
    _LOADED_ENV_FILE_KEYS.clear()
    _LOADED_ENV_FILE_VALUES.clear()
    global _LOADED_ENV_FILE_PATH
    _LOADED_ENV_FILE_PATH = None


def is_env_file_key(key: str) -> bool:
    return key in _LOADED_ENV_FILE_KEYS


def loaded_env_file_path() -> Path | None:
    return _LOADED_ENV_FILE_PATH


def _project_root_for_config_path(path: Path) -> Path:
    parts = path.parts
    if len(parts) >= 4 and parts[-4:-1] == (".inspire", "accounts", parts[-2]):
        return path.parents[3]
    return path.parent.parent


def _read_cli_env_file_value(config_path: Path) -> str | None:
    try:
        raw = _load_toml(config_path)
    except FileNotFoundError:
        return None
    cli_section = raw.get("cli")
    if not isinstance(cli_section, dict):
        return None
    value = str(cli_section.get("env_file") or "").strip()
    return value or None


def _configured_env_file() -> tuple[Path, Path] | None:
    shared_path, account_path = _find_project_configs()
    selected: tuple[Path, Path] | None = None
    for config_path in (shared_path, account_path):
        if config_path is None:
            continue
        value = _read_cli_env_file_value(config_path)
        if not value:
            continue
        env_path = Path(value).expanduser()
        if not env_path.is_absolute():
            env_path = _project_root_for_config_path(config_path) / env_path
        selected = (env_path, config_path)
    return selected


def _strip_inline_comment(text: str) -> str:
    for index, char in enumerate(text):
        if char == "#" and (index == 0 or text[index - 1].isspace()):
            return text[:index].rstrip()
    return text.rstrip()


def _find_quote_end(text: str, quote: str) -> int | None:
    escaped = False
    for index in range(1, len(text)):
        char = text[index]
        if quote == '"' and char == "\\" and not escaped:
            escaped = True
            continue
        if char == quote and not escaped:
            return index
        escaped = False
    return None


def _parse_env_value(raw_value: str, *, path: Path, line_no: int) -> str:
    value = raw_value.strip()
    if not value:
        return ""

    if value[0] in ("'", '"'):
        quote = value[0]
        end = _find_quote_end(value, quote)
        if end is None:
            raise click.ClickException(f"{path}:{line_no}: unterminated quoted value")
        literal = value[: end + 1]
        tail = value[end + 1 :].strip()
        if tail and not tail.startswith("#"):
            raise click.ClickException(f"{path}:{line_no}: unexpected text after quoted value")
        try:
            parsed = ast.literal_eval(literal)
        except (SyntaxError, ValueError) as exc:
            raise click.ClickException(f"{path}:{line_no}: invalid quoted value") from exc
        return str(parsed)

    return _strip_inline_comment(value)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise click.ClickException(f"Env file not found: {path}") from exc
    except OSError as exc:
        raise click.ClickException(f"Failed to read env file {path}: {exc}") from exc

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            raise click.ClickException(f"{path}:{line_no}: expected KEY=value")
        raw_key, raw_value = line.split("=", 1)
        key = raw_key.strip()
        if not _ENV_KEY_RE.match(key):
            raise click.ClickException(f"{path}:{line_no}: invalid environment variable name")
        values[key] = _parse_env_value(raw_value, path=path, line_no=line_no)
    return values


def _apply_env_values(path: Path, values: dict[str, str]) -> None:
    global _LOADED_ENV_FILE_PATH
    _LOADED_ENV_FILE_PATH = path
    for key, value in values.items():
        if key in os.environ:
            continue
        os.environ[key] = value
        _LOADED_ENV_FILE_KEYS.add(key)
        _LOADED_ENV_FILE_VALUES[key] = value


def bootstrap_env_file(
    *,
    env_file: Path | None,
    disabled: bool,
) -> Path | None:
    """Load an explicit or project-configured dotenv file into ``os.environ``."""
    reset_loaded_env_file_state()
    if disabled and env_file is not None:
        raise click.ClickException("--env-file cannot be combined with --no-env-file")
    if disabled:
        return None

    selected_path: Path | None = None
    source_config: Path | None = None
    if env_file is not None:
        selected_path = env_file.expanduser()
        if not selected_path.is_absolute():
            selected_path = Path.cwd() / selected_path
    else:
        configured = _configured_env_file()
        if configured is not None:
            selected_path, source_config = configured

    if selected_path is None:
        return None

    selected_path = selected_path.resolve()
    if not selected_path.exists():
        suffix = f" (declared in {source_config})" if source_config else ""
        raise click.ClickException(f"Env file not found: {selected_path}{suffix}")
    values = _parse_env_file(selected_path)
    _apply_env_values(selected_path, values)
    return selected_path


def write_shared_project_env_file(env_file: str) -> Path:
    """Persist ``[cli].env_file`` to the repo-wide project config."""
    value = str(env_file or "").strip()
    if not value:
        raise click.ClickException("env_file cannot be empty")
    if "\x00" in value:
        raise click.ClickException("env_file cannot contain NUL bytes")

    config_path = _project_config_write_path(shared=True)
    data: dict[str, Any] = _load_toml(config_path) if config_path.exists() else {}
    cli_section = data.get("cli")
    if not isinstance(cli_section, dict):
        cli_section = {}
        data["cli"] = cli_section
    cli_section["env_file"] = value

    from inspire.cli.commands.init.toml_helpers import _toml_dumps

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(_toml_dumps(data), encoding="utf-8")
    return config_path


__all__ = [
    "bootstrap_env_file",
    "is_env_file_key",
    "loaded_env_file_path",
    "reset_loaded_env_file_state",
    "write_shared_project_env_file",
]
