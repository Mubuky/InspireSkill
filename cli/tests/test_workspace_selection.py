"""Tests for workspace selection.

v3.1.0 dropped the implicit "default workspace" concept entirely:
``select_workspace_id`` only resolves ``explicit_workspace_id`` /
``explicit_workspace_name``; if neither is provided it returns ``None``
and the caller is expected to surface a clear error pointing at
``--workspace``. The legacy ``gpu_type`` / ``cpu_only`` /
``prefer_internet`` kwargs are kept on the signature for backwards-
compat but silently ignored.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from inspire.config import Config, ConfigError
from inspire.config.workspaces import select_workspace_id, workspace_required_hint

WS_SPECIAL = "ws-22222222-2222-2222-2222-222222222222"


def _cfg(**kwargs) -> Config:
    return Config(username="", password="", **kwargs)


def test_no_arguments_returns_none() -> None:
    cfg = _cfg()
    assert select_workspace_id(cfg) is None


def test_no_default_workspace_field_in_config() -> None:
    """Sanity: the removed schema field is gone from Config."""
    assert not hasattr(Config(username="", password=""), "job_workspace_id")


def test_gpu_type_hint_is_silently_ignored() -> None:
    cfg = _cfg()
    assert select_workspace_id(cfg, gpu_type="H200") is None
    assert select_workspace_id(cfg, cpu_only=True) is None


def test_explicit_workspace_id_returns_directly() -> None:
    cfg = _cfg()
    explicit = "ws-11111111-1111-1111-1111-111111111111"
    assert select_workspace_id(cfg, explicit_workspace_id=explicit) == explicit


def test_explicit_workspace_name_uses_workspaces_map() -> None:
    cfg = _cfg(workspaces={"special": WS_SPECIAL})
    assert select_workspace_id(cfg, explicit_workspace_name="special") == WS_SPECIAL


def test_unknown_workspace_name_raises() -> None:
    cfg = _cfg(workspaces={"special": WS_SPECIAL})
    with pytest.raises(ConfigError, match="Unknown workspace name"):
        select_workspace_id(cfg, explicit_workspace_name="does-not-exist")


def test_placeholder_workspace_id_is_rejected_when_explicit() -> None:
    cfg = _cfg()
    with pytest.raises(ConfigError, match="placeholder"):
        select_workspace_id(
            cfg,
            explicit_workspace_id="ws-00000000-0000-0000-0000-000000000000",
        )


def test_workspace_required_hint_lists_aliases() -> None:
    cfg = _cfg(workspaces={"cpu": "ws-aaa", "gpu": "ws-bbb"})
    msg = workspace_required_hint(cfg)
    assert "--workspace <alias>" in msg
    assert "cpu" in msg and "gpu" in msg


def test_workspace_required_hint_when_no_aliases() -> None:
    cfg = _cfg()
    msg = workspace_required_hint(cfg)
    assert "No aliases configured" in msg
    assert "inspire init --discover" in msg


def test_config_loads_workspace_alias_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / ".inspire").mkdir()
    (project_root / ".inspire" / "config.toml").write_text(
        '[workspaces]\nspecial = "ws-22222222-2222-2222-2222-222222222222"\n',
        encoding="utf-8",
    )
    fake_home = tmp_path / "__home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.chdir(project_root)
    monkeypatch.delenv("INSPIRE_WORKSPACE_ID", raising=False)

    cfg, _ = Config.from_files_and_env(require_credentials=False)
    assert cfg.workspaces.get("special") == WS_SPECIAL


def test_legacy_job_workspace_id_in_toml_is_ignored_with_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Old configs with [job].workspace_id load cleanly + emit a one-line stderr warning."""
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / ".inspire").mkdir()
    (project_root / ".inspire" / "config.toml").write_text(
        '[job]\nworkspace_id = "ws-22222222-2222-2222-2222-222222222222"\n',
        encoding="utf-8",
    )
    fake_home = tmp_path / "__home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.chdir(project_root)
    monkeypatch.delenv("INSPIRE_WORKSPACE_ID", raising=False)

    # Reset the one-shot flag so this test always sees the warning fresh.
    from inspire.config import load as load_module

    monkeypatch.setattr(load_module, "_LEGACY_WORKSPACE_DEFAULT_WARNING_EMITTED", False)

    cfg, _ = Config.from_files_and_env(require_credentials=False)
    err = capsys.readouterr().err
    assert "v3.1.0 dropped the default-workspace concept" in err
    assert "[job].workspace_id" in err
    # Schema field should not exist on the loaded config.
    assert not hasattr(cfg, "job_workspace_id")
