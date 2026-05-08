"""Placement options for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
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

        float_fields = {
            "initialPlaceNetWeightScale": self.initialPlaceNetWeightScale,
            "density": self.density,
            "overflow": self.overflow,
            "keepResizeBelowOverflow": self.keepResizeBelowOverflow,
            "timingNetWeightMax": self.timingNetWeightMax,
            "minPhiCoef": self.minPhiCoef,
            "maxPhiCoef": self.maxPhiCoef,
            "initDensityPenaltyFactor": self.initDensityPenaltyFactor,
            "initWireLengthCoef": self.initWireLengthCoef,
            "referenceHpwl": self.referenceHpwl,
            "routabilityCheckOverflow": self.routabilityCheckOverflow,
            "routabilitySnapshotOverflow": self.routabilitySnapshotOverflow,
            "routabilityMaxDensity": self.routabilityMaxDensity,
            "routabilityTargetRcMetric": self.routabilityTargetRcMetric,
            "routabilityInflationRatioCoef": self.routabilityInflationRatioCoef,
            "routabilityMaxInflationRatio": self.routabilityMaxInflationRatio,
            "routabilityRcK1": self.routabilityRcK1,
            "routabilityRcK2": self.routabilityRcK2,
            "routabilityRcK3": self.routabilityRcK3,
            "routabilityRcK4": self.routabilityRcK4,
        }
        for name, value in float_fields.items():
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
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
        if self.timingDrivenMode and not self.timingNetWeightOverflows:
            raise ValueError("timingNetWeightOverflows must not be empty when timing-driven mode is enabled")

    def report(self) -> Dict[str, Any]:
        """Return a stable dictionary for smoke tests and higher-level reports."""

        return {
            "initial_place_max_iter": self.initialPlaceMaxIter,
            "initial_place_min_diff_length": self.initialPlaceMinDiffLength,
            "initial_place_max_solver_iter": self.initialPlaceMaxSolverIter,
            "initial_place_max_fanout": self.initialPlaceMaxFanout,
            "initial_place_net_weight_scale": self.initialPlaceNetWeightScale,
            "force_center_initial_place": self.forceCenterInitialPlace,
            "skip_io": self.skipIoMode,
            "nesterov_place_max_iter": self.nesterovPlaceMaxIter,
            "density": self.density,
            "overflow": self.overflow,
            "timing_driven": self.timingDrivenMode,
            "routability_driven": self.routabilityDrivenMode,
            "uniform_target_density": self.uniformTargetDensityMode,
            "bin_grid": (self.binGridCntX, self.binGridCntY),
            "pad": (self.padLeft, self.padRight),
            "timing_net_weight_overflows": list(self.timingNetWeightOverflows),
            "timing_net_weight_max": self.timingNetWeightMax,
            "keep_resize_below_overflow": self.keepResizeBelowOverflow,
            "routability_use_rudy": self.routabilityUseRudy,
            "disable_revert_if_diverge": self.disableRevertIfDiverge,
            "disable_pin_density_adjust": self.disablePinDensityAdjust,
            "enable_routing_congestion": self.enable_routing_congestion,
            "phi_coef": (self.minPhiCoef, self.maxPhiCoef),
            "init_density_penalty_factor": self.initDensityPenaltyFactor,
            "init_wire_length_coef": self.initWireLengthCoef,
            "reference_hpwl": self.referenceHpwl,
            "routability_check_overflow": self.routabilityCheckOverflow,
            "routability_snapshot_overflow": self.routabilitySnapshotOverflow,
            "routability_max_density": self.routabilityMaxDensity,
            "routability_target_rc_metric": self.routabilityTargetRcMetric,
            "routability_inflation_ratio_coef": self.routabilityInflationRatioCoef,
            "routability_max_inflation_ratio": self.routabilityMaxInflationRatio,
            "routability_rc_coefficients": (
                self.routabilityRcK1,
                self.routabilityRcK2,
                self.routabilityRcK3,
                self.routabilityRcK4,
            ),
        }


