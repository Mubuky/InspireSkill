"""Display-width aware table helpers for CLI human output."""

from __future__ import annotations

import unicodedata
from typing import Iterable, Literal, Sequence

from inspire.cli.utils.raw_ids import scrub_raw_ids

Align = Literal["left", "right"]


def _cell_text(value: object, *, scrub: bool = True) -> str:
    return scrub_raw_ids(value) if scrub else str(value)


def display_width(value: object) -> int:
    """Return terminal display width, counting CJK wide chars as two columns."""
    text = str(value)
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        if unicodedata.category(ch) in {"Cc", "Cf"}:
            continue
        width += 2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1
    return width


def clip_display(value: object, width: int) -> str:
    """Clip text to a display width without splitting wide characters."""
    text = str(value)
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text

    suffix = "..." if width >= 4 else "." * width
    suffix_width = display_width(suffix)
    limit = max(0, width - suffix_width)
    out: list[str] = []
    current = 0
    for ch in text:
        ch_width = display_width(ch)
        if current + ch_width > limit:
            break
        out.append(ch)
        current += ch_width
    return "".join(out) + suffix


def pad_cell(value: object, width: int, *, align: Align = "left") -> str:
    clipped = clip_display(value, width)
    padding = max(0, width - display_width(clipped))
    if align == "right":
        return (" " * padding) + clipped
    return clipped + (" " * padding)


def separator(widths: Sequence[int], *, char: str = "-") -> str:
    return char * (sum(widths) + max(0, len(widths) - 1))


def column_width(
    header: object,
    values: Iterable[object],
    *,
    max_width: int | None = None,
    scrub: bool = True,
) -> int:
    """Return a display-width aware column width for a header and values."""
    rendered = [_cell_text(value, scrub=scrub) for value in values]
    width = max(
        display_width(_cell_text(header, scrub=scrub)),
        *(display_width(v) for v in rendered),
        1,
    )
    if max_width is not None:
        return min(width, max_width)
    return width


def render_table(
    headers: Sequence[object],
    rows: Iterable[Sequence[object]],
    widths: Sequence[int],
    *,
    aligns: Sequence[str] | None = None,
    line_char: str = "-",
    scrub: bool = True,
) -> list[str]:
    """Render a fixed-width table using display widths."""
    if aligns is None:
        aligns = ["left"] * len(widths)
    header_cells = [_cell_text(header, scrub=scrub) for header in headers]
    row_cells = [[_cell_text(cell, scrub=scrub) for cell in row] for row in rows]
    sep = separator(widths, char=line_char)
    lines = [
        sep,
        " ".join(
            pad_cell(header, width, align="right" if align == "right" else "left")
            for header, width, align in zip(header_cells, widths, aligns)
        ),
        sep,
    ]
    for row in row_cells:
        lines.append(
            " ".join(
                pad_cell(cell, width, align="right" if align == "right" else "left")
                for cell, width, align in zip(row, widths, aligns)
            )
        )
    lines.append(sep)
    return lines


__all__ = [
    "clip_display",
    "column_width",
    "display_width",
    "pad_cell",
    "render_table",
    "separator",
]
