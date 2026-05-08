"""Power recovery flow boundary for :mod:`winroad.rsz`."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Set

from .common import (
    RecoverPowerConfig,
    RepairFlowPhase,
    RepairFlowState,
    RepairPhaseEvent,
    _json_value,
    _not_translated,
    _obj_key,
)


class RecoverPower:
    """setup slack 充足路径上的 power recovery 流程边界。"""

    setup_slack_margin_ = 1e-11
    setup_slack_max_margin_ = 1e-4
    failed_move_threshold_limit_ = 500
    decreasing_slack_max_passes_ = 50
    rebuffer_max_fanout_ = 20
    split_load_min_fanout_ = 8
    rebuffer_buffer_penalty_ = 0.01
    min_print_interval_ = 10
    max_print_interval_ = 100

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.logger_ = resizer.logger_
        self.db_network_ = resizer.db_network_
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.scene_ = None
        self.resize_count_ = 0
        self.swapped_cell_count_ = 0
        self.sizedown_cell_count_ = 0
        self.recovered_power_ = 0.0
        self.match_cell_footprint_ = False
        self.verbose_ = False
        self.bad_vertices_: Set[Any] = set()
        self.initial_design_area_ = 0.0
        self.print_interval_ = 0
        self.config_ = RecoverPowerConfig(setup_slack_margin=self.setup_slack_margin_)
        self.phase_ = RepairFlowPhase.IDLE
        self.phase_history_ = []

    def init(self) -> None:
        self.db_network_ = self.resizer_.db_network_

    def recoverPower(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RecoverPower::recoverPower")

    def configure(
        self,
        recover_power_percent: Optional[float] = None,
        match_cell_footprint: Optional[bool] = None,
        verbose: Optional[bool] = None,
        scene: Any = None,
        setup_slack_margin: Optional[float] = None,
    ) -> RecoverPowerConfig:
        prev = self.config_
        recover_power_percent = (
            prev.recover_power_percent if recover_power_percent is None else recover_power_percent
        )
        match_cell_footprint = (
            prev.match_cell_footprint if match_cell_footprint is None else match_cell_footprint
        )
        verbose = prev.verbose if verbose is None else verbose
        scene = prev.scene if scene is None else scene
        setup_slack_margin = prev.setup_slack_margin if setup_slack_margin is None else setup_slack_margin
        self.match_cell_footprint_ = match_cell_footprint
        self.verbose_ = verbose
        self.scene_ = scene
        self.setup_slack_margin_ = setup_slack_margin
        self.config_ = RecoverPowerConfig(
            recover_power_percent=recover_power_percent,
            match_cell_footprint=match_cell_footprint,
            verbose=verbose,
            scene=scene,
            setup_slack_margin=setup_slack_margin,
        )
        self.setPhase(RepairFlowPhase.CONFIGURED, "configure")
        return self.config_

    def resetConfig(self) -> None:
        self.scene_ = None
        self.match_cell_footprint_ = False
        self.verbose_ = False
        self.setup_slack_margin_ = type(self).setup_slack_margin_
        self.config_ = RecoverPowerConfig(setup_slack_margin=self.setup_slack_margin_)
        self.setPhase(RepairFlowPhase.IDLE, "reset_config")

    def config(self) -> RecoverPowerConfig:
        return self.config_

    def importConfig(self, data: Dict[str, Any]) -> RecoverPowerConfig:
        """导入 power recovery 配置，不执行 cell swap 或 size down。"""

        config = RecoverPowerConfig.from_dict(data)
        return self.configure(
            recover_power_percent=config.recover_power_percent,
            match_cell_footprint=config.match_cell_footprint,
            verbose=config.verbose,
            scene=config.scene,
            setup_slack_margin=config.setup_slack_margin,
        )

    def exportConfig(self) -> Dict[str, Any]:
        return self.reportConfig()

    def reportConfig(self) -> Dict[str, Any]:
        return self.config_.as_dict()

    def recordSwap(self, count: int = 1, recovered_power: float = 0.0) -> None:
        if count < 0:
            raise ValueError("swap count must be non-negative")
        self.swapped_cell_count_ += count
        self.recovered_power_ += recovered_power
        if count:
            self.setPhase(RepairFlowPhase.REPAIRING, "record_swap")

    def recordSizeDown(self, count: int = 1, recovered_power: float = 0.0) -> None:
        if count < 0:
            raise ValueError("size-down count must be non-negative")
        self.sizedown_cell_count_ += count
        self.resize_count_ += count
        self.recovered_power_ += recovered_power
        if count:
            self.setPhase(RepairFlowPhase.REPAIRING, "record_size_down")

    def recordResize(self, count: int = 1) -> None:
        if count < 0:
            raise ValueError("resize count must be non-negative")
        self.resize_count_ += count
        if count:
            self.setPhase(RepairFlowPhase.REPAIRING, "record_resize")

    def resetCounters(self) -> None:
        self.resize_count_ = 0
        self.swapped_cell_count_ = 0
        self.sizedown_cell_count_ = 0
        self.recovered_power_ = 0.0
        self.bad_vertices_.clear()
        self.setPhase(RepairFlowPhase.IDLE, "reset_counters")

    def markBadVertex(self, vertex: Any) -> None:
        self.bad_vertices_.add(_obj_key(vertex))

    def isBadVertex(self, vertex: Any) -> bool:
        return _obj_key(vertex) in self.bad_vertices_

    def recoveredPower(self) -> float:
        return self.recovered_power_

    def resizeCount(self) -> int:
        return self.resize_count_

    def swappedCellCount(self) -> int:
        return self.swapped_cell_count_

    def sizeDownCount(self) -> int:
        return self.sizedown_cell_count_

    def reportCounters(self) -> Dict[str, Any]:
        return {
            "swapped_cells": self.swapped_cell_count_,
            "sizedown_cells": self.sizedown_cell_count_,
            "resized_cells": self.resize_count_,
            "recovered_power": self.recovered_power_,
            "bad_vertices": len(self.bad_vertices_),
            "match_cell_footprint": self.match_cell_footprint_,
            "verbose": self.verbose_,
        }

    def statistics(self) -> Dict[str, Any]:
        return self.reportState()

    def reportState(self) -> Dict[str, Any]:
        return RepairFlowState(
            name="RecoverPower",
            config=self.reportConfig(),
            counters=self.reportCounters(),
            details={"bad_vertices_detail": _json_value(self.bad_vertices_)},
            phase=self.phase_,
            history=self.phase_history_,
        ).as_dict()

    def setPhase(self, phase: RepairFlowPhase, reason: str = "") -> None:
        self.phase_ = phase
        self.phase_history_.append(RepairPhaseEvent(phase=phase, reason=reason, order=len(self.phase_history_)))

    def finishPass(self, committed: bool, reason: str = "") -> None:
        phase = RepairFlowPhase.COMMITTED if committed else RepairFlowPhase.ROLLED_BACK
        self.setPhase(phase, reason)

    def validateBatch(self, batch: Any) -> Dict[str, Any]:
        """校验 recover_power 批处理配置列表。"""

        errors = []
        normalized = []
        for index, item in enumerate(batch):
            try:
                config = RecoverPowerConfig.from_dict(item)
                if config.recover_power_percent < 0.0:
                    raise ValueError("recover_power_percent must be non-negative")
                if config.setup_slack_margin < 0.0:
                    raise ValueError("setup_slack_margin must be non-negative")
                normalized.append(config.as_dict())
            except Exception as exc:  # noqa: BLE001 - 批处理报告所有错误。
                errors.append(f"batch[{index}]: {exc}")
        return {"valid": not errors, "errors": errors, "items": normalized}

    def to_json(self, **json_kwargs: Any) -> str:
        kwargs = {"sort_keys": True}
        kwargs.update(json_kwargs)
        return json.dumps(self.statistics(), **kwargs)
