"""Placement options for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

@dataclass
class PlaceOptions:
    """对应 `gpl::PlaceOptions`，保留 C++ 默认值和字段名。"""

    initialPlaceMaxIter: int = 20
    initialPlaceMinDiffLength: int = 1500
    initialPlaceMaxSolverIter: int = 100
    initialPlaceMaxFanout: int = 200
    initialPlaceNetWeightScale: float = 800.0
    skipIoMode: bool = False
    forceCenterInitialPlace: bool = False
    timingDrivenMode: bool = False
    routabilityDrivenMode: bool = False
    uniformTargetDensityMode: bool = False
    timingNetWeightOverflows: List[int] = field(default_factory=lambda: [64, 20])
    timingNetWeightMax: float = 5.0
    overflow: float = 0.1
    nesterovPlaceMaxIter: int = 5000
    keepResizeBelowOverflow: float = 1.0
    routabilityUseRudy: bool = True
    disableRevertIfDiverge: bool = False
    disablePinDensityAdjust: bool = False
    enable_routing_congestion: bool = False
    minPhiCoef: float = 0.95
    maxPhiCoef: float = 1.05
    initDensityPenaltyFactor: float = 0.00008
    initWireLengthCoef: float = 0.25
    referenceHpwl: float = 446000000.0
    binGridCntX: int = 0
    binGridCntY: int = 0
    density: float = 0.7
    routabilityCheckOverflow: float = 0.3
    routabilitySnapshotOverflow: float = 0.6
    routabilityMaxDensity: float = 0.99
    routabilityTargetRcMetric: float = 1.01
    routabilityInflationRatioCoef: float = 2.0
    routabilityMaxInflationRatio: float = 3.0
    routabilityRcK1: float = 1.0
    routabilityRcK2: float = 1.0
    routabilityRcK3: float = 0.0
    routabilityRcK4: float = 0.0
    padLeft: int = 0
    padRight: int = 0

    def skipIo(self) -> None:
        """对应 `PlaceOptions::skipIo()`。"""

        self.skipIoMode = True
        self.initialPlaceMaxIter = 0
        self.timingDrivenMode = False
        self.routabilityDrivenMode = False

    def validate(self, logger: Any = None) -> None:
        """对应 `PlaceOptions::validate()` 的 Python 检查。"""

        if self.initialPlaceMaxIter < 0:
            raise ValueError("initialPlaceMaxIter must be non-negative")
        if self.initialPlaceMaxFanout <= 0:
            raise ValueError("initialPlaceMaxFanout must be positive")
        if not 0.0 <= self.density <= 1.0:
            raise ValueError("Target density must be in [0.0, 1.0]")


