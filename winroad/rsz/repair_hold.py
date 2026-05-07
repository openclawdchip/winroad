"""Hold timing repair flow boundary for :mod:`winroad.rsz`."""

from __future__ import annotations

import json
from typing import Any, Dict

from .common import RepairHoldConfig, _json_value, _not_translated


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
        return self.config_

    def resetConfig(self) -> None:
        self.buffer_cell_ = None
        self.max_passes_ = 0
        self.max_repairs_per_pass_ = 0
        self.allow_setup_violations_ = False
        self.setup_slack_margin_ = 0.0
        self.config_ = RepairHoldConfig()

    def config(self) -> RepairHoldConfig:
        return self.config_

    def reportConfig(self) -> Dict[str, Any]:
        return self.config_.as_dict()

    def recordInsertedBuffer(self, count: int = 1, buffer_cell: Any = None) -> None:
        if count < 0:
            raise ValueError("inserted buffer count must be non-negative")
        if buffer_cell is not None:
            self.buffer_cell_ = buffer_cell
            self.config_.buffer_cell = buffer_cell
        self.inserted_buffer_count_ += count

    def recordResize(self, count: int = 1) -> None:
        if count < 0:
            raise ValueError("resize count must be non-negative")
        self.resize_count_ += count

    def recordClonedGate(self, count: int = 1) -> None:
        if count < 0:
            raise ValueError("cloned gate count must be non-negative")
        self.cloned_gate_count_ += count

    def resetCounters(self) -> None:
        self.resize_count_ = 0
        self.inserted_buffer_count_ = 0
        self.cloned_gate_count_ = 0

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
        data = self.reportCounters()
        data["config"] = self.reportConfig()
        return data

    def to_json(self, **json_kwargs: Any) -> str:
        kwargs = {"sort_keys": True}
        kwargs.update(json_kwargs)
        return json.dumps(self.statistics(), **kwargs)

    def resizeCount(self) -> int:
        return self.resize_count_

    def clonedGateCount(self) -> int:
        return self.cloned_gate_count_
