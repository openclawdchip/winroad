"""Compatibility forwarding module for the WinRoad gpl package.

The implementation has moved to :mod:`winroad.gpl`.  This file remains so
source-path users that load ``winroad/gpl.py`` directly still see the public API.
"""

from __future__ import annotations

from .gpl import *  # noqa: F401,F403
from .gpl import __all__  # noqa: F401
