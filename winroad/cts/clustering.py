"""Sink clustering boundaries for CTS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .options import CtsOptions
from .tech_char import TechChar
from .types import Point, _not_translated


@dataclass
class Matching:
    """对应 `SinkClustering` 中的 matching 结果。"""

    left: Point
    right: Point
    cost: float = 0.0
    p0: int = 0
    p1: int = 0

    def getP0(self) -> int:
        return self.p0

    def getP1(self) -> int:
        return self.p1


@dataclass
class SinkClustering:
    """对应 `SinkClustering`。"""

    options: Optional[CtsOptions] = None
    tech_char: Optional[TechChar] = None
    points: List[Point] = field(default_factory=list)
    caps: List[float] = field(default_factory=list)
    theta_index_vector: List[Tuple[float, int]] = field(default_factory=list)
    matchings: List[Matching] = field(default_factory=list)
    sink_clusters: Dict[int, List[Point]] = field(default_factory=dict)
    best_solution: List[List[int]] = field(default_factory=list)
    solution: List[Point] = field(default_factory=list)
    max_internal_diameter: float = 0.0
    cap_per_unit: float = 0.0
    use_max_diameter: bool = False
    use_max_size: bool = False
    use_max_cap_limit: bool = False
    scale_factor: int = 1
    first_run: bool = True
    x_span: float = 0.0
    y_span: float = 0.0
    max_diameter: float = 0.0
    max_size: int = 0
    best_solution_cost: float = float("inf")
    scale: float = 1.0

    def addPoint(self, point: Point, cap: float = 0.0) -> None:
        self.points.append(point)
        self.caps.append(cap)

    def addCap(self, cap: float) -> None:
        self.caps.append(cap)

    def run(
        self,
        group_size: Optional[int] = None,
        max_diameter: Optional[float] = None,
        scale_factor: Optional[int] = None,
    ) -> None:
        _not_translated("SinkClustering::run")

    def getNumPoints(self) -> int:
        return len(self.points)

    def allMatchings(self) -> List[Matching]:
        return list(self.matchings)

    def sinkClusteringSolution(self) -> List[List[int]]:
        return [list(cluster) for cluster in self.best_solution]

    def getSolution(self) -> List[Point]:
        return list(self.solution)

    def getWireLength(self, points: Optional[List[Point]] = None) -> float:
        if points is None:
            return sum(match.cost for match in self.matchings)
        return sum(points[i - 1].computeDist(points[i]) for i in range(1, len(points)))

    def getScaleFactor(self) -> int:
        return self.scale_factor

    def getMaxDiameter(self) -> float:
        return self.max_diameter

    def getMaxSize(self) -> int:
        return self.max_size

    def normalizePoints(self, max_diameter: float = 10) -> None:
        _not_translated("SinkClustering::normalizePoints")

    def computeAllThetas(self) -> None:
        _not_translated("SinkClustering::computeAllThetas")

    def sortPoints(self) -> None:
        self.theta_index_vector.sort()

    def writePlotFile(self, group_size: Optional[int] = None) -> None:
        _not_translated("SinkClustering::writePlotFile")

    def findBestMatching(self, group_size: int) -> bool:
        _not_translated("SinkClustering::findBestMatching")

    def computeTheta(self, x: float, y: float) -> float:
        _not_translated("SinkClustering::computeTheta")

    def numVertex(self, x: int, y: int) -> int:
        _not_translated("SinkClustering::numVertex")

    def isLimitExceeded(
        self, size: int, cost: float, cap_cost: float, size_limit: int
    ) -> bool:
        if self.use_max_size and size > size_limit:
            return True
        if self.use_max_diameter and cost > self.max_diameter:
            return True
        if self.use_max_cap_limit and cap_cost > self.max_internal_diameter:
            return True
        return False
