"""Hold timing repair flow boundary for :mod:`winroad.rsz`."""

from __future__ import annotations

import json
from typing import Any, Dict

from .common import RepairFlowPhase, RepairFlowState, RepairHoldConfig, RepairPhaseEvent, _json_value, _not_translated


class RepairHold:
    """hold timing repair 主流程边界。"""

    hold_slack_limit_ratio_max_ = 0.2
    print_interval_ = 10

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.logger_ = resizer.logger_
        self.db_network_ = resizer.db_network_
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.resize_count_ = 0
        self.inserted_buffer_count_ = 0
        self.cloned_gate_count_ = 0
        self.buffer_cell_ = None
        self.max_passes_ = 0
        self.max_repairs_per_pass_ = 0
        self.allow_setup_violations_ = False
        self.setup_slack_margin_ = 0.0
        self.initial_design_area_ = 0.0
        self.config_ = RepairHoldConfig()
        self.phase_ = RepairFlowPhase.IDLE
        self.phase_history_ = []

    def init(self) -> None:
        self.db_network_ = self.resizer_.db_network_

    def repairHold(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RepairHold::repairHold")

    def setHoldBuffer(self, buffer_cell: Any) -> None:
        self.buffer_cell_ = buffer_cell
        self.config_.buffer_cell = buffer_cell

    def holdBuffer(self) -> Any:
        return self.buffer_cell_

    def configure(
        self,
        buffer_cell: Any = None,
        max_passes: Any = None,
        max_repairs_per_pass: Any = None,
        allow_setup_violations: Any = None,
        setup_slack_margin: Any = None,
    ) -> RepairHoldConfig:
        prev = self.config_
        if buffer_cell is not None:
            self.buffer_cell_ = buffer_cell
        self.max_passes_ = int(prev.max_passes if max_passes is None else max_passes)
        self.max_repairs_per_pass_ = int(
            prev.max_repairs_per_pass if max_repairs_per_pass is None else max_repairs_per_pass
        )
        self.allow_setup_violations_ = (
            prev.allow_setup_violations if allow_setup_violations is None else bool(allow_setup_violations)
        )
        self.setup_slack_margin_ = prev.setup_slack_margin if setup_slack_margin is None else setup_slack_margin
        self.config_ = RepairHoldConfig(
            buffer_cell=self.buffer_cell_,
            max_passes=self.max_passes_,
            max_repairs_per_pass=self.max_repairs_per_pass_,
            allow_setup_violations=self.allow_setup_violations_,
            setup_slack_margin=self.setup_slack_margin_,
        )
        self.setPhase(RepairFlowPhase.CONFIGURED, "configure")
        return self.config_

    def resetConfig(self) -> None:
        self.buffer_cell_ = None
        self.max_passes_ = 0
        self.max_repairs_per_pass_ = 0
        self.allow_setup_violations_ = False
        self.setup_slack_margin_ = 0.0
        self.config_ = RepairHoldConfig()
        self.setPhase(RepairFlowPhase.IDLE, "reset_config")

    def config(self) -> RepairHoldConfig:
        return self.config_

    def importConfig(self, data: Dict[str, Any]) -> RepairHoldConfig:
        """导入 hold 配置；不插 buffer、不查询 STA。"""

        config = RepairHoldConfig.from_dict(data)
        return self.configure(
            buffer_cell=config.buffer_cell,
            max_passes=config.max_passes,
            max_repairs_per_pass=config.max_repairs_per_pass,
            allow_setup_violations=config.allow_setup_violations,
            setup_slack_margin=config.setup_slack_margin,
        )

    def exportConfig(self) -> Dict[str, Any]:
        return self.reportConfig()

    def reportConfig(self) -> Dict[str, Any]:
        return self.config_.as_dict()

    def recordInsertedBuffer(self, count: int = 1, buffer_cell: Any = None) -> None:
        if count < 0:
            raise ValueError("inserted buffer count must be non-negative")
        if buffer_cell is not None:
            self.buffer_cell_ = buffer_cell
            self.config_.buffer_cell = buffer_cell
        self.inserted_buffer_count_ += count
        if count:
            self.setPhase(RepairFlowPhase.REPAIRING, "record_inserted_buffer")

    def recordResize(self, count: int = 1) -> None:
        if count < 0:
            raise ValueError("resize count must be non-negative")
        self.resize_count_ += count
        if count:
            self.setPhase(RepairFlowPhase.REPAIRING, "record_resize")

    def recordClonedGate(self, count: int = 1) -> None:
        if count < 0:
            raise ValueError("cloned gate count must be non-negative")
        self.cloned_gate_count_ += count
        if count:
            self.setPhase(RepairFlowPhase.REPAIRING, "record_cloned_gate")

    def resetCounters(self) -> None:
        self.resize_count_ = 0
        self.inserted_buffer_count_ = 0
        self.cloned_gate_count_ = 0
        self.setPhase(RepairFlowPhase.IDLE, "reset_counters")

    def holdBufferCount(self) -> int:
        return self.inserted_buffer_count_

    def reportHoldBuffer(self) -> Any:
        return self.buffer_cell_

    def reportCounters(self) -> Dict[str, Any]:
        return {
            "inserted_buffers": self.inserted_buffer_count_,
            "resized_drivers": self.resize_count_,
            "cloned_gates": self.cloned_gate_count_,
            "buffer_cell": _json_value(self.buffer_cell_),
        }

    def statistics(self) -> Dict[str, Any]:
        return self.reportState()

    def reportState(self) -> Dict[str, Any]:
        return RepairFlowState(
            name="RepairHold",
            config=self.reportConfig(),
            counters=self.reportCounters(),
            details={"hold_buffer": _json_value(self.buffer_cell_)},
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
        """校验 hold 批处理配置列表。"""

        errors = []
        normalized = []
        for index, item in enumerate(batch):
            try:
                config = RepairHoldConfig.from_dict(item)
                if config.max_passes < 0:
                    raise ValueError("max_passes must be non-negative")
                if config.max_repairs_per_pass < 0:
                    raise ValueError("max_repairs_per_pass must be non-negative")
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

    def resizeCount(self) -> int:
        return self.resize_count_

    def clonedGateCount(self) -> int:
        return self.cloned_gate_count_
