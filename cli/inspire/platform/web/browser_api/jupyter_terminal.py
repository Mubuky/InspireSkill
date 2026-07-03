from __future__ import annotations

import base64
import re
import shlex
import uuid
from dataclasses import dataclass
from typing import Optional

from inspire.platform.web.browser_api import rtunnel as rtunnel_module
from inspire.platform.web.browser_api.core import (
    _in_asyncio_loop,
    _launch_browser,
    _new_context,
    _run_in_thread,
)
from inspire.platform.web.browser_api.playwright_notebooks import open_notebook_lab
from inspire.platform.web.session import WebSession
from inspire.platform.web.session import get_web_session

JUPYTER_DONE_PREFIX = "__INSPIRE_JUPYTER_DONE_"
MISSING_MARKER_RETURN_CODE = 124


@dataclass(frozen=True)
class JupyterCommandResult:
    returncode: int
    output: str
    completed: bool
    marker: str


@dataclass(frozen=True)
class NetworkEndpointResult:
    group: str
    host: str
    port: int
    ok: bool


@dataclass(frozen=True)
class NotebookNetworkProbe:
    public_internet: bool | None
    endpoints: tuple[NetworkEndpointResult, ...]

    @property
    def public_successes(self) -> list[str]:
        return [
            f"{item.host}:{item.port}"
            for item in self.endpoints
            if item.group == "PUBLIC" and item.ok
        ]

    @property
    def public_failures(self) -> list[str]:
        return [
            f"{item.host}:{item.port}"
            for item in self.endpoints
            if item.group == "PUBLIC" and not item.ok
        ]


PUBLIC_PROBE_ENDPOINTS: tuple[tuple[str, int], ...] = (
    ("www.baidu.com", 443),
    ("www.qq.com", 443),
    ("www.163.com", 443),
    ("mirrors.tuna.tsinghua.edu.cn", 443),
)


def new_completion_marker() -> str:
    return f"{JUPYTER_DONE_PREFIX}{uuid.uuid4().hex}"


def build_jupyter_exec_command(command: str, *, marker: str) -> str:
    script = "\n".join(
        [
            "set +e",
            command,
            "__inspire_status=$?",
            f"printf '\\n%s:exit:%s\\n' {shlex.quote(marker)} \"$__inspire_status\"",
            "exit \"$__inspire_status\"",
            "",
        ]
    )
    encoded = base64.b64encode(script.encode()).decode("ascii")
    return f"echo '{encoded}' | base64 -d | bash\r"


def parse_jupyter_exec_output(raw_output: str, *, marker: str) -> JupyterCommandResult:
    pattern = re.compile(rf"{re.escape(marker)}:exit:(\d+)\s*")
    match = pattern.search(raw_output)
    if not match:
        return JupyterCommandResult(
            returncode=MISSING_MARKER_RETURN_CODE,
            output=raw_output,
            completed=False,
            marker=marker,
        )
    output = raw_output[: match.start()]
    return JupyterCommandResult(
        returncode=int(match.group(1)),
        output=output,
        completed=True,
        marker=marker,
    )


def build_network_probe_command(
    *,
    public_endpoints: tuple[tuple[str, int], ...] = PUBLIC_PROBE_ENDPOINTS,
) -> str:
    lines = [
        "probe_one() {",
        '  group="$1"; host="$2"; port="$3"',
        '  if timeout 3 bash -c "</dev/tcp/${host}/${port}" >/dev/null 2>&1; then',
        '    echo "$group $host $port ok"',
        "  else",
        '    echo "$group $host $port fail"',
        "  fi",
        "}",
    ]
    for host, port in public_endpoints:
        lines.append(f"probe_one PUBLIC {shlex.quote(host)} {int(port)}")
    return "\n".join(lines)


def parse_network_probe_output(output: str) -> NotebookNetworkProbe:
    endpoints: list[NetworkEndpointResult] = []
    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        group, host, port_raw, status = parts
        if group != "PUBLIC":
            continue
        if not port_raw.isdigit():
            continue
        endpoints.append(
            NetworkEndpointResult(
                group=group,
                host=host,
                port=int(port_raw),
                ok=status == "ok",
            )
        )
    public_items = [item for item in endpoints if item.group == "PUBLIC"]
    public = any(item.ok for item in public_items) if public_items else None
    return NotebookNetworkProbe(
        public_internet=public,
        endpoints=tuple(endpoints),
    )


def _send_terminal_command_capture_via_websocket(
    page_or_frame: object,
    *,
    ws_url: str,
    stdin_data: str,
    timeout_ms: int,
    marker: str,
) -> Optional[JupyterCommandResult]:
    prompt_timeout_ms = max(0, min(timeout_ms - 500, 3000))
    try:
        raw_output = page_or_frame.evaluate(
            """
            async ({ wsUrl, stdinData, timeoutMs, promptTimeoutMs, marker }) => {
              return await new Promise((resolve, reject) => {
                let settled = false;
                let sent = false;
                let socket = null;
                let output = "";
                const finish = (value) => {
                  if (settled) return;
                  settled = true;
                  clearTimeout(timer);
                  try {
                    if (socket) socket.close();
                  } catch (_) {}
                  resolve(value);
                };
                const fail = (err) => {
                  if (settled) return;
                  settled = true;
                  clearTimeout(timer);
                  try {
                    if (socket) socket.close();
                  } catch (_) {}
                  reject(err);
                };
                const timer = setTimeout(() => finish(output), timeoutMs);
                const doSend = () => {
                  if (sent || settled) return;
                  sent = true;
                  const CHUNK = 2048;
                  const DELAY = 50;
                  const chunks = [];
                  for (let i = 0; i < stdinData.length; i += CHUNK) {
                    chunks.push(stdinData.slice(i, i + CHUNK));
                  }
                  let idx = 0;
                  const next = () => {
                    if (settled) return;
                    try {
                      socket.send(JSON.stringify(["stdin", chunks[idx]]));
                    } catch (err) {
                      fail(err);
                      return;
                    }
                    idx++;
                    if (idx < chunks.length) {
                      setTimeout(next, DELAY);
                    }
                  };
                  next();
                };
                socket = new WebSocket(wsUrl);
                socket.onopen = () => {
                  setTimeout(doSend, promptTimeoutMs);
                };
                socket.onerror = () => fail(new Error("terminal websocket error"));
                socket.onmessage = (event) => {
                  let msg = null;
                  try {
                    msg = JSON.parse(event.data);
                  } catch (_) {
                    return;
                  }
                  if (!Array.isArray(msg) || msg.length < 2) return;
                  if (msg[0] !== "stdout") return;
                  const text = String(msg[1] || "");
                  output += text;
                  if (!sent && /[$#]\\s*$/.test(text)) {
                    doSend();
                  }
                  if (sent && output.includes(marker)) {
                    finish(output);
                  }
                };
              });
            }
            """,
            {
                "wsUrl": ws_url,
                "stdinData": stdin_data,
                "timeoutMs": max(int(timeout_ms), 1000),
                "promptTimeoutMs": prompt_timeout_ms,
                "marker": marker,
            },
        )
    except Exception:
        return None
    return parse_jupyter_exec_output(str(raw_output or ""), marker=marker)


def run_command_capture_in_existing_lab(
    *,
    context: object,
    lab_frame: object,
    command: str,
    timeout_ms: int,
    marker: str | None = None,
) -> JupyterCommandResult:
    effective_marker = marker or new_completion_marker()
    term_name = rtunnel_module._create_terminal_via_api(context, lab_frame.url)
    if not term_name:
        return JupyterCommandResult(
            returncode=MISSING_MARKER_RETURN_CODE,
            output="",
            completed=False,
            marker=effective_marker,
        )
    try:
        ws_url = rtunnel_module._build_terminal_websocket_url(lab_frame.url, term_name)
        result = _send_terminal_command_capture_via_websocket(
            lab_frame,
            ws_url=ws_url,
            stdin_data=build_jupyter_exec_command(command, marker=effective_marker),
            timeout_ms=timeout_ms,
            marker=effective_marker,
        )
        if result is None:
            return JupyterCommandResult(
                returncode=MISSING_MARKER_RETURN_CODE,
                output="",
                completed=False,
                marker=effective_marker,
            )
        return result
    finally:
        rtunnel_module._delete_terminal_via_api(
            context,
            lab_url=lab_frame.url,
            term_name=term_name,
        )


def run_command_capture_in_notebook(
    *,
    notebook_id: str,
    command: str,
    session: Optional[WebSession] = None,
    headless: bool = True,
    timeout: int = 60,
    marker: str | None = None,
) -> JupyterCommandResult:
    if _in_asyncio_loop():
        return _run_in_thread(
            _run_command_capture_in_notebook_sync,
            notebook_id=notebook_id,
            command=command,
            session=session,
            headless=headless,
            timeout=timeout,
            marker=marker,
        )
    return _run_command_capture_in_notebook_sync(
        notebook_id=notebook_id,
        command=command,
        session=session,
        headless=headless,
        timeout=timeout,
        marker=marker,
    )


def probe_notebook_network(
    *,
    notebook_id: str,
    session: Optional[WebSession] = None,
    timeout: int = 30,
) -> NotebookNetworkProbe:
    result = run_command_capture_in_notebook(
        notebook_id=notebook_id,
        command=build_network_probe_command(),
        session=session,
        timeout=timeout,
    )
    if not result.completed:
        return NotebookNetworkProbe(
            public_internet=None,
            endpoints=(),
        )
    return parse_network_probe_output(result.output)


def _run_command_capture_in_notebook_sync(
    *,
    notebook_id: str,
    command: str,
    session: Optional[WebSession],
    headless: bool,
    timeout: int,
    marker: str | None,
) -> JupyterCommandResult:
    from playwright.sync_api import sync_playwright

    if session is None:
        session = get_web_session()

    effective_marker = marker or new_completion_marker()
    timeout_ms = max(int(timeout * 1000), 1000)
    with sync_playwright() as p:
        browser = _launch_browser(p, headless=headless)
        context = _new_context(browser, storage_state=session.storage_state)
        page = context.new_page()

        try:
            lab_frame = open_notebook_lab(page, notebook_id=notebook_id, session=session)
            try:
                lab_frame.locator("text=加载中").first.wait_for(state="hidden", timeout=30000)
            except Exception:
                pass
            return run_command_capture_in_existing_lab(
                context=context,
                lab_frame=lab_frame,
                command=command,
                timeout_ms=timeout_ms,
                marker=effective_marker,
            )
        finally:
            try:
                context.close()
            finally:
                browser.close()
