from __future__ import annotations

from click.testing import CliRunner

from inspire.cli.commands.notebook import remote_shell as shell_module
from inspire.cli.commands.notebook.transport import NotebookTransportPolicy
from inspire.cli.main import main as cli_main
from inspire.config import Config


def test_shell_uses_jupyter_when_policy_blocks_ssh(monkeypatch) -> None:  # noqa: ANN001
    config = Config(username="", password="")

    monkeypatch.setattr(
        Config,
        "from_files_and_env",
        classmethod(lambda cls, require_credentials=True: (config, {})),
    )
    monkeypatch.setattr(
        shell_module,
        "preflight_notebook_transport_policy",
        lambda *_a, **_k: NotebookTransportPolicy(
            notebook="gpu-box",
            notebook_id="nb-123",
            public_internet=False,
            reason="live_probe",
        ),
        raising=False,
    )
    called = {"jupyter": False}
    monkeypatch.setattr(
        shell_module.browser_api_module,
        "open_jupyter_terminal_shell",
        lambda **_k: called.__setitem__("jupyter", True) or 0,
        raising=False,
    )

    result = CliRunner().invoke(cli_main, ["notebook", "shell", "gpu-box"])

    assert result.exit_code == 0
    assert called["jupyter"] is True
