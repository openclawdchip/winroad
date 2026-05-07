"""Compatibility forwarding module for the :mod:`winroad.rsz` package."""

from __future__ import annotations

try:
    from .rsz import *  # type: ignore[F403]
    from .rsz import __all__  # type: ignore[F401]
except ImportError:  # pragma: no cover - supports direct file loading by path.
    from winroad.rsz import *  # type: ignore[F403]
    from winroad.rsz import __all__  # type: ignore[F401]
