"""Compatibility wrapper for the :mod:`winroad.grt` package.

The implementation now lives under ``winroad/grt/``. This file is kept so
path-based users of the old single-file module still see the public API.
"""

from __future__ import annotations

from .grt import *  # noqa: F401,F403
