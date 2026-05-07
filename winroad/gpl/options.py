"""Placement options for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

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
        if self.initialPlaceMinDiffLength < 0:
            raise ValueError("initialPlaceMinDiffLength must be non-negative")
        if self.initialPlaceMaxSolverIter <= 0:
            raise ValueError("initialPlaceMaxSolverIter must be positive")
        if self.initialPlaceMaxFanout <= 0:
            raise ValueError("initialPlaceMaxFanout must be positive")
        if self.initialPlaceNetWeightScale <= 0:
            raise ValueError("initialPlaceNetWeightScale must be positive")
        if not 0.0 <= self.density <= 1.0:
            raise ValueError("Target density must be in [0.0, 1.0]")
        if not 0.0 <= self.overflow <= 1.0:
            raise ValueError("Target overflow must be in [0.0, 1.0]")
        if self.nesterovPlaceMaxIter < 0:
            raise ValueError("nesterovPlaceMaxIter must be non-negative")
        if self.keepResizeBelowOverflow < 0.0:
            raise ValueError("keepResizeBelowOverflow must be non-negative")
        if self.timingNetWeightMax < 1.0:
            raise ValueError("timingNetWeightMax must be at least 1.0")
        if any(item < 0 or item > 100 for item in self.timingNetWeightOverflows):
            raise ValueError("timingNetWeightOverflows entries must be percentages in [0, 100]")
        if self.minPhiCoef <= 0.0 or self.maxPhiCoef <= 0.0:
            raise ValueError("Phi coefficients must be positive")
        if self.minPhiCoef > self.maxPhiCoef:
            raise ValueError("minPhiCoef must be less than or equal to maxPhiCoef")
        if self.initDensityPenaltyFactor < 0.0:
            raise ValueError("initDensityPenaltyFactor must be non-negative")
        if self.initWireLengthCoef < 0.0:
            raise ValueError("initWireLengthCoef must be non-negative")
        if self.referenceHpwl < 0.0:
            raise ValueError("referenceHpwl must be non-negative")
        if (self.binGridCntX < 0) or (self.binGridCntY < 0):
            raise ValueError("binGridCntX/binGridCntY must be non-negative")
        if (self.binGridCntX == 0) ^ (self.binGridCntY == 0):
            raise ValueError("binGridCntX and binGridCntY must be set together")
        if not 0.0 <= self.routabilityCheckOverflow <= 1.0:
            raise ValueError("routabilityCheckOverflow must be in [0.0, 1.0]")
        if not 0.0 <= self.routabilitySnapshotOverflow <= 1.0:
            raise ValueError("routabilitySnapshotOverflow must be in [0.0, 1.0]")
        if not 0.0 <= self.routabilityMaxDensity <= 1.0:
            raise ValueError("routabilityMaxDensity must be in [0.0, 1.0]")
        if self.routabilityTargetRcMetric <= 0.0:
            raise ValueError("routabilityTargetRcMetric must be positive")
        if self.routabilityInflationRatioCoef < 0.0:
            raise ValueError("routabilityInflationRatioCoef must be non-negative")
        if self.routabilityMaxInflationRatio < 1.0:
            raise ValueError("routabilityMaxInflationRatio must be at least 1.0")
        if self.padLeft < 0 or self.padRight < 0:
            raise ValueError("padLeft/padRight must be non-negative")

    def report(self) -> Dict[str, Any]:
        """Return a stable dictionary for smoke tests and higher-level reports."""

        return {
            "initial_place_max_iter": self.initialPlaceMaxIter,
            "nesterov_place_max_iter": self.nesterovPlaceMaxIter,
            "density": self.density,
            "overflow": self.overflow,
            "timing_driven": self.timingDrivenMode,
            "routability_driven": self.routabilityDrivenMode,
            "uniform_target_density": self.uniformTargetDensityMode,
            "bin_grid": (self.binGridCntX, self.binGridCntY),
            "pad": (self.padLeft, self.padRight),
        }


