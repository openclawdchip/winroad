"""Compatibility forwarding module for the CTS package.

The implementation has moved to :mod:`winroad.cts`.  This file remains only for
legacy source layouts that reference ``winroad/cts.py`` directly.
"""

from __future__ import annotations

from .cts import *  # noqa: F401,F403
