"""Compatibility forwarding module for the drt package.

The implementation lives in :mod:`winroad.drt`. This file is kept so tools that
look for the historical ``winroad/drt.py`` path still find a forwarding shim.
"""

from __future__ import annotations

from .drt import *  # noqa: F401,F403
