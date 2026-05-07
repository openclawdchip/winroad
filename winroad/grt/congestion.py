"""WinRoad global routing package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Set

from .guide import GSegment
from .types import Rect


@dataclass
class TileCongestion:
    """对应 grt::TileCongestion。"""

    capacity: int = 0
    usage: int = 0


@dataclass
class TileInformation:
    """对应 grt::TileInformation。"""

    nets: Set[Any] = field(default_factory=set)
    congestion: TileCongestion = field(default_factory=TileCongestion)


@dataclass
class CongestionInformation:
    """对应 grt::CongestionInformation。"""

    segment: GSegment = field(default_factory=GSegment)
    congestion: TileCongestion = field(default_factory=TileCongestion)
    sources: Set[Any] = field(default_factory=set)


@dataclass
class CapacityReduction:
    """对应 grt::CapacityReduction。"""

    capacity: int = 0
    reduction: int = 0


@dataclass
class RegionAdjustment:
    """对应 GlobalRouter.h 的 RegionAdjustment。"""

    min_x: int
    min_y: int
    max_x: int
    max_y: int
    layer: int
    adjustment: float

    @property
    def region(self) -> Rect:
        """返回 OpenDB Rect 等价 tuple。"""

        return (self.min_x, self.min_y, self.max_x, self.max_y)

    def getRegion(self) -> Rect:
        """对应 C++ ``getRegion()``。"""

        return self.region

    def getLayer(self) -> int:
        """对应 C++ ``getLayer()``。"""

        return self.layer

    def getAdjustment(self) -> float:
        """对应 C++ ``getAdjustment()``。"""

        return self.adjustment



