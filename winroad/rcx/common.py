"""Shared helpers for the WinRoad rcx package."""

from __future__ import annotations

from typing import List, Optional


def _not_translated(name: str) -> NotImplementedError:
    """Return the standard boundary error for untranslated OpenROAD rcx code."""

    return NotImplementedError(f"OpenROAD rcx::{name} 尚未翻译为 Python 实现")


def _parse_number_list(text: Optional[str]) -> List[float]:
    """Parse the whitespace/comma separated numeric lists used by rcx Tcl options."""

    if not text:
        return []
    values: List[float] = []
    for word in text.replace(",", " ").split():
        values.append(float(word))
    return values
