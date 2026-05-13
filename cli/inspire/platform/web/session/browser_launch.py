"""Shared Playwright Chromium launch options."""

from __future__ import annotations

from typing import Any


CHROMIUM_CONTAINER_ARGS = (
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
)


def chromium_launch_kwargs(*, headless: bool = True, proxy: Any = None) -> dict[str, Any]:
    """Return Chromium launch kwargs that also work in Inspire containers.

    Inspire notebooks commonly run as root inside containers with a small
    ``/dev/shm``. Chromium can start successfully and then close the page
    process on first navigation unless these compatibility flags are present.
    """
    kwargs: dict[str, Any] = {
        "headless": headless,
        "args": list(CHROMIUM_CONTAINER_ARGS),
    }
    if proxy is not None:
        kwargs["proxy"] = proxy
    return kwargs


__all__ = ["CHROMIUM_CONTAINER_ARGS", "chromium_launch_kwargs"]
