"""Hold timing repair flow boundary for :mod:`winroad.rsz`."""

from __future__ import annotations

from typing import Any, Dict

from .common import _not_translated


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

    def init(self) -> None:
        self.db_network_ = self.resizer_.db_network_

    def repairHold(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RepairHold::repairHold")

    def setHoldBuffer(self, buffer_cell: Any) -> None:
        self.buffer_cell_ = buffer_cell

    def holdBuffer(self) -> Any:
        return self.buffer_cell_

    def recordInsertedBuffer(self, count: int = 1, buffer_cell: Any = None) -> None:
        if buffer_cell is not None:
            self.buffer_cell_ = buffer_cell
        self.inserted_buffer_count_ += count

    def recordResize(self, count: int = 1) -> None:
        self.resize_count_ += count

    def recordClonedGate(self, count: int = 1) -> None:
        self.cloned_gate_count_ += count

    def holdBufferCount(self) -> int:
        return self.inserted_buffer_count_

    def reportHoldBuffer(self) -> Any:
        return self.buffer_cell_

    def reportCounters(self) -> Dict[str, int]:
        return {
            "inserted_buffers": self.inserted_buffer_count_,
            "resized_drivers": self.resize_count_,
            "cloned_gates": self.cloned_gate_count_,
        }

    def resizeCount(self) -> int:
        return self.resize_count_

    def clonedGateCount(self) -> int:
        return self.cloned_gate_count_
