from __future__ import annotations

from click.testing import CliRunner

from inspire.cli.commands.notebook import transport as transport_module
from inspire.cli.main import main as cli_main


def test_policy_blocks_ssh_when_public_internet_false() -> None:
    policy = transport_module.NotebookTransportPolicy(
        notebook="gpu-box",
        notebook_id="nb-123",
        public_internet=False,
        reason="live_probe",
    )

    assert policy.allow_ssh is False
    assert policy.exec_transport == "jupyter"
    assert "JupyterTerminal" in policy.block_hint


def test_policy_allows_ssh_when_public_internet_true() -> None:
    policy = transport_module.NotebookTransportPolicy(
        notebook="cpu-box",
        notebook_id="nb-456",
        public_internet=True,
        reason="live_probe",
    )

    assert policy.allow_ssh is True
    assert policy.exec_transport == "ssh"


def test_ssh_command_blocks_restricted_notebook_before_bootstrap(monkeypatch) -> None:  # noqa: ANN001
    from inspire.cli.commands.notebook import ssh as ssh_module

    monkeypatch.setattr(
        ssh_module,
        "preflight_notebook_transport_policy",
        lambda *_a, **_k: transport_module.NotebookTransportPolicy(
            notebook="gpu-box",
            notebook_id="nb-123",
            public_internet=False,
            reason="live_probe",
        ),
    )
    called = {"run": False}
    monkeypatch.setattr(
        ssh_module,
        "run_notebook_ssh",
        lambda **_k: called.__setitem__("run", True),
    )

    result = CliRunner().invoke(
        cli_main,
        ["notebook", "ssh", "gpu-box", "--workspace", "分布式训练空间"],
    )

    assert result.exit_code != 0
    assert called["run"] is False
    assert "blocked on notebooks without public internet" in result.output


def test_notebook_scp_rejects_restricted_notebook_with_cp_hint(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    from inspire.cli.commands.notebook import remote_scp as scp_module

    local_file = tmp_path / "config.yaml"
    local_file.write_text("x")
    monkeypatch.setattr(
        scp_module,
        "preflight_notebook_transport_policy",
        lambda *_a, **_k: transport_module.NotebookTransportPolicy(
            notebook="gpu-box",
            notebook_id="nb-123",
            public_internet=False,
            reason="live_probe",
        ),
    )

    result = CliRunner().invoke(
        cli_main,
        [
            "notebook",
            "scp",
            "gpu-box",
            str(local_file),
            "/inspire/hdd/project/topic/user/config.yaml",
        ],
    )

    assert result.exit_code != 0
    assert "SSH-based" in result.output
    assert "public-internet notebook" in result.output
    assert "/inspire/" in result.output
