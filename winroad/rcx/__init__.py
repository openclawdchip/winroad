"""WinRoad OpenRCX package.

The package is split along rcx responsibility boundaries while preserving the
historical ``winroad.rcx`` public API.
"""

from __future__ import annotations

from .measure import CoupleAndCompute, CoupleOptions, CouplingDimensionParams, CouplingState, SegmentTables, extMeasure, extMeasureRC
from .options import BenchWiresOptions, DiffOptions, ExtractOptions, PatternOptions, ReadSpefOpts, SpefOptions, extMainOptions
from .corner import extCorner
from .rc_model import extDistRC, extDistRCTable, extDistWidthRCTable, extMetRCTable, extRCTable, extRCModel, extViaModel
from .spef import extSpef
from .ext import Ext, OpenRCX, extMain

__all__ = [
    "BenchWiresOptions",
    "ExtractOptions",
    "SpefOptions",
    "ReadSpefOpts",
    "DiffOptions",
    "PatternOptions",
    "CoupleOptions",
    "CoupleAndCompute",
    "extDistRC",
    "extDistRCTable",
    "extDistWidthRCTable",
    "extMetRCTable",
    "extViaModel",
    "extRCTable",
    "extCorner",
    "extMainOptions",
    "extRCModel",
    "CouplingState",
    "CouplingDimensionParams",
    "SegmentTables",
    "extMeasure",
    "extMeasureRC",
    "extSpef",
    "extMain",
    "Ext",
    "OpenRCX",
]
