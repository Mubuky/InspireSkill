from __future__ import annotations

import base64

from inspire.platform.web.browser_api import jupyter_terminal as jt


def test_build_exec_command_hides_done_marker_from_terminal_echo() -> None:
    command = jt.build_jupyter_exec_command("echo hi", marker="__INSPIRE_DONE_abc__")

    assert command.startswith("echo '")
    assert command.endswith("' | base64 -d | bash\r")
    encoded = command[len("echo '") : -len("' | base64 -d | bash\r")]
    decoded = base64.b64decode(encoded).decode()
    assert "echo hi" in decoded
    assert "__INSPIRE_DONE_abc__" in decoded
    assert "__INSPIRE_DONE_abc__" not in encoded


def test_parse_command_output_extracts_returncode_and_removes_marker() -> None:
    raw = "hello\n__INSPIRE_DONE_abc__:exit:7\n"
    result = jt.parse_jupyter_exec_output(raw, marker="__INSPIRE_DONE_abc__")

    assert result.returncode == 7
    assert result.output == "hello\n"
    assert result.completed is True


def test_parse_command_output_marks_missing_marker_unknown() -> None:
    result = jt.parse_jupyter_exec_output("partial output", marker="__INSPIRE_DONE_abc__")

    assert result.returncode == 124
    assert result.output == "partial output"
    assert result.completed is False


def test_send_terminal_command_capture_collects_stdout_until_marker() -> None:
    captured: dict[str, object] = {}

    class _Frame:
        def evaluate(self, script: str, payload: dict):  # noqa: ANN201
            captured["script"] = script
            captured["payload"] = payload
            return "hello\n__INSPIRE_DONE_abc__:exit:0\n"

    result = jt._send_terminal_command_capture_via_websocket(
        _Frame(),
        ws_url="wss://nb.example.com/terminals/websocket/1",
        stdin_data="echo hi\r",
        timeout_ms=5000,
        marker="__INSPIRE_DONE_abc__",
    )

    assert result is not None
    assert result.returncode == 0
    assert result.output == "hello\n"
    assert captured["payload"] == {
        "wsUrl": "wss://nb.example.com/terminals/websocket/1",
        "stdinData": "echo hi\r",
        "timeoutMs": 5000,
        "promptTimeoutMs": 3000,
        "marker": "__INSPIRE_DONE_abc__",
    }
    assert "new WebSocket" in captured["script"]


def test_send_terminal_command_capture_returns_none_on_evaluate_failure() -> None:
    class _Frame:
        def evaluate(self, script: str, payload: dict):  # noqa: ANN201
            raise RuntimeError("browser closed")

    assert (
        jt._send_terminal_command_capture_via_websocket(
            _Frame(),
            ws_url="wss://nb.example.com/terminals/websocket/1",
            stdin_data="echo hi\r",
            timeout_ms=5000,
            marker="__INSPIRE_DONE_abc__",
        )
        is None
    )


def test_run_command_capture_in_existing_lab_cleans_up_terminal(monkeypatch) -> None:  # noqa: ANN001
    events: list[tuple[str, object]] = []

    class _Frame:
        url = "https://nb.example.com/lab"

    monkeypatch.setattr(jt.rtunnel_module, "_create_terminal_via_api", lambda *_a, **_k: "term-1")
    monkeypatch.setattr(
        jt.rtunnel_module,
        "_build_terminal_websocket_url",
        lambda _url, _term: "wss://nb.example.com/terminals/websocket/term-1",
    )
    monkeypatch.setattr(
        jt,
        "_send_terminal_command_capture_via_websocket",
        lambda *_a, **_k: jt.JupyterCommandResult(
            returncode=0,
            output="ok\n",
            completed=True,
            marker=_k["marker"],
        ),
    )
    monkeypatch.setattr(
        jt.rtunnel_module,
        "_delete_terminal_via_api",
        lambda _ctx, *, lab_url, term_name: events.append(("delete", f"{lab_url}|{term_name}"))
        or True,
    )

    result = jt.run_command_capture_in_existing_lab(
        context=object(),
        lab_frame=_Frame(),
        command="echo ok",
        timeout_ms=5000,
    )

    assert result.returncode == 0
    assert result.output == "ok\n"
    assert events == [("delete", "https://nb.example.com/lab|term-1")]


def test_parse_network_probe_output() -> None:
    output = "\n".join(
        [
            "PUBLIC www.baidu.com 443 ok",
            "PUBLIC www.qq.com 443 fail",
            "",
        ]
    )

    result = jt.parse_network_probe_output(output)

    assert result.public_internet is True
    assert result.public_successes == ["www.baidu.com:443"]
    assert result.public_failures == ["www.qq.com:443"]


def test_parse_network_probe_output_all_public_failures() -> None:
    output = "PUBLIC www.baidu.com 443 fail\nPUBLIC www.qq.com 443 fail\n"

    result = jt.parse_network_probe_output(output)

    assert result.public_internet is False
