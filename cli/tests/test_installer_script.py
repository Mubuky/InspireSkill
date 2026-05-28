from __future__ import annotations

from pathlib import Path


def test_installer_uses_installed_inspire_for_browser_runtime_setup() -> None:
    installer = Path(__file__).resolve().parents[1].parent / "scripts" / "install.sh"
    text = installer.read_text(encoding="utf-8")

    assert '"$INSPIRE_BIN" _ensure-playwright-runtime' in text
    assert 'uvx --from "$SPEC" playwright' not in text
    assert "Manual repair command" not in text
