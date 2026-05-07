"""Compatibility forwarding module for the WinRoad rcx package."""

from __future__ import annotations

try:
    from .rcx import *  # noqa: F401,F403
except ImportError:  # pragma: no cover - supports direct legacy loading.
    from winroad.rcx import *  # type: ignore # noqa: F401,F403
