"""Design-rule repair flow boundary for :mod:`winroad.rsz`."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .buffered_net import BufferedNet
from .common import RepairDesignLimits, RepairDesignViolationCounters, RepairFlowState, _not_translated


class ResizerObserver:
    """图形/调试观察者接口，对应 ``ResizerObserver.hh``。"""

    def setNet(self, net: Any) -> None:
        pass

    def stopOnSubdivideStep(self, stop: bool) -> None:
        pass

    def subdivideStart(self, net: Any) -> None:
        pass

    def subdivide(self, line: Any) -> None:
        pass

    def subdivideDone(self) -> None:
        pass

    def repairNetStart(self, bnet: BufferedNet, net: Any) -> None:
        pass

    def makeBuffer(self, inst: Any) -> None:
        pass

    def repairNetDone(self) -> None:
        pass

class PreChecks:
    """修复前的 slew/cap 合理性检查边界。"""

    default_min_cap_load = 1e-18

    def __init__(self, resizer: "Resizer") -> None:
        self.logger_ = resizer.logger_
        self.sta_ = resizer.sta_
        self.resizer_ = resizer
        self.best_case_slew_ = -1.0
        self.best_case_slew_load_ = -1.0
        self.best_case_slew_computed_ = False
        self.min_cap_load_ = self.default_min_cap_load
        self.min_cap_load_computed_ = False

    def checkSlewLimit(self, ref_cap: float, max_load_slew: float) -> None:
        _not_translated("PreChecks::checkSlewLimit")

    def checkCapLimit(self, drvr_pin: Any) -> None:
        _not_translated("PreChecks::checkCapLimit")

class RepairDesign:
    """修复 max slew/cap/fanout/long wire 的流程边界。"""

    min_print_interval_ = 10
    max_print_interval_ = 1000

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.logger_ = resizer.logger_
        self.db_network_ = resizer.db_network_
        self.pre_checks_ = PreChecks(resizer)
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.dbu_ = resizer.dbu_
        self.initial_design_area_ = 0.0
        self.parasitics_src_ = None
        self.buffer_sizes_: List[Any] = []
        self.drvr_pin_ = None
        self.max_cap_ = 0.0
        self.max_length_ = 0
        self.max_wire_length_ = 0.0
        self.max_slew_ = 0.0
        self.max_cap_margin_ = 0.0
        self.max_fanout_ = 0
        self.slew_margin_ = 0.0
        self.cap_margin_ = 0.0
        self.corner_ = None
        self.resize_count_ = 0
        self.inserted_buffer_count_ = 0
        self.repaired_net_count_ = 0
        self.long_wire_count_ = 0
        self.max_slew_count_ = 0
        self.max_cap_count_ = 0
        self.max_fanout_count_ = 0
        self.print_interval_ = 0
        self.graphics_: Optional[ResizerObserver] = None
        self.r_strongest_buffer_ = 0.0
        self.slew_rc_factor_: Optional[float] = None
        self.limits_ = RepairDesignLimits()

    def init(self) -> None:
        self.db_network_ = self.resizer_.db_network_
        self.dbu_ = self.resizer_.dbu_

    def repairDesign(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("RepairDesign::repairDesign")

    def insertedBufferCount(self) -> int:
        return self.inserted_buffer_count_

    def configureLimits(
        self,
        max_wire_length: Optional[float] = None,
        max_slew: Optional[float] = None,
        max_cap: Optional[float] = None,
        max_fanout: Optional[int] = None,
        slew_margin: Optional[float] = None,
        cap_margin: Optional[float] = None,
        corner: Any = None,
        buffer_cells: Optional[Sequence[Any]] = None,
    ) -> RepairDesignLimits:
        """合并 repair_design violation 参数，不触发真实 STA/DB 修复。"""

        prev = self.limits_
        self.limits_ = RepairDesignLimits(
            max_wire_length=prev.max_wire_length if max_wire_length is None else max_wire_length,
            max_slew=prev.max_slew if max_slew is None else max_slew,
            max_cap=prev.max_cap if max_cap is None else max_cap,
            max_fanout=prev.max_fanout if max_fanout is None else max_fanout,
            slew_margin=prev.slew_margin if slew_margin is None else slew_margin,
            cap_margin=prev.cap_margin if cap_margin is None else cap_margin,
            corner=prev.corner if corner is None else corner,
            buffer_cells=list(prev.buffer_cells if buffer_cells is None else buffer_cells),
        )
        self._applyLimits()
        return self.limits_

    def _applyLimits(self) -> None:
        self.max_wire_length_ = float(self.limits_.max_wire_length or 0.0)
        self.max_length_ = int(self.limits_.max_wire_length or 0)
        self.max_slew_ = float(self.limits_.max_slew or 0.0)
        self.max_cap_ = float(self.limits_.max_cap or 0.0)
        self.max_fanout_ = int(self.limits_.max_fanout or 0)
        self.slew_margin_ = self.limits_.slew_margin
        self.cap_margin_ = self.limits_.cap_margin
        self.corner_ = self.limits_.corner
        self.buffer_sizes_ = list(self.limits_.buffer_cells)

    def resetLimits(self) -> None:
        self.limits_ = RepairDesignLimits()
        self._applyLimits()

    def limits(self) -> RepairDesignLimits:
        return self.limits_

    def importConfig(self, data: Dict[str, Any]) -> RepairDesignLimits:
        """导入 repair_design violation 配置，不启动真实 net 修复。"""

        return self.configureLimits(
            max_wire_length=data.get("max_wire_length"),
            max_slew=data.get("max_slew"),
            max_cap=data.get("max_cap"),
            max_fanout=data.get("max_fanout"),
            slew_margin=data.get("slew_margin"),
            cap_margin=data.get("cap_margin"),
            corner=data.get("corner"),
            buffer_cells=data.get("buffer_cells"),
        )

    def exportConfig(self) -> Dict[str, Any]:
        return self.reportLimits()

    def reportLimits(self) -> Dict[str, Any]:
        return self.limits_.as_dict()

    def resetViolationCounters(self) -> None:
        self.resize_count_ = 0
        self.inserted_buffer_count_ = 0
        self.repaired_net_count_ = 0
        self.long_wire_count_ = 0
        self.max_slew_count_ = 0
        self.max_cap_count_ = 0
        self.max_fanout_count_ = 0

    def recordRepair(
        self,
        long_wire: int = 0,
        max_slew: int = 0,
        max_cap: int = 0,
        max_fanout: int = 0,
        inserted_buffers: int = 0,
        resized_drivers: int = 0,
        repaired_nets: int = 0,
    ) -> None:
        """累加 C++ repair pass 会维护的 counters。"""

        values = (
            long_wire,
            max_slew,
            max_cap,
            max_fanout,
            inserted_buffers,
            resized_drivers,
            repaired_nets,
        )
        if any(value < 0 for value in values):
            raise ValueError("repair counters must be non-negative")
        self.long_wire_count_ += long_wire
        self.max_slew_count_ += max_slew
        self.max_cap_count_ += max_cap
        self.max_fanout_count_ += max_fanout
        self.inserted_buffer_count_ += inserted_buffers
        self.resize_count_ += resized_drivers
        self.repaired_net_count_ += repaired_nets

    def violationCounters(self) -> RepairDesignViolationCounters:
        return RepairDesignViolationCounters(
            repaired_nets=self.repaired_net_count_,
            inserted_buffers=self.inserted_buffer_count_,
            resized_drivers=self.resize_count_,
            long_wire=self.long_wire_count_,
            max_slew=self.max_slew_count_,
            max_cap=self.max_cap_count_,
            max_fanout=self.max_fanout_count_,
        )

    def resizedDriverCount(self) -> int:
        return self.resize_count_

    def repairedNetCount(self) -> int:
        return self.repaired_net_count_

    def repairNet(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("RepairDesign::repairNet")

    def repairClkNets(self, max_wire_length: float) -> None:
        _not_translated("RepairDesign::repairClkNets")

    def repairClkInverters(self) -> None:
        _not_translated("RepairDesign::repairClkInverters")

    def reportViolationCounters(self, *_args: Any, **_kwargs: Any) -> Dict[str, int]:
        return self.violationCounters().as_dict()

    def reportState(self) -> Dict[str, Any]:
        return RepairFlowState(
            name="RepairDesign",
            config=self.reportLimits(),
            counters=self.reportViolationCounters(),
            details={
                "initial_design_area": self.initial_design_area_,
                "slew_rc_factor": self.slew_rc_factor_,
                "buffer_sizes": list(self.buffer_sizes_),
            },
        ).as_dict()

    def statistics(self) -> Dict[str, Any]:
        return self.reportState()

    def validateBatch(self, batch: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """校验 repair_design 批处理限制参数。"""

        errors: List[str] = []
        normalized: List[Dict[str, Any]] = []
        numeric_fields = ("max_wire_length", "max_slew", "max_cap", "slew_margin", "cap_margin")
        for index, item in enumerate(batch):
            try:
                config = dict(item)
                for field in numeric_fields:
                    if config.get(field) is not None and float(config[field]) < 0.0:
                        raise ValueError(f"{field} must be non-negative")
                if config.get("max_fanout") is not None and int(config["max_fanout"]) < 0:
                    raise ValueError("max_fanout must be non-negative")
                normalized.append(
                    RepairDesignLimits(
                        max_wire_length=config.get("max_wire_length"),
                        max_slew=config.get("max_slew"),
                        max_cap=config.get("max_cap"),
                        max_fanout=config.get("max_fanout"),
                        slew_margin=float(config.get("slew_margin", 0.0) or 0.0),
                        cap_margin=float(config.get("cap_margin", 0.0) or 0.0),
                        corner=config.get("corner"),
                        buffer_cells=list(config.get("buffer_cells", []) or []),
                    ).as_dict()
                )
            except Exception as exc:  # noqa: BLE001 - 批处理报告所有错误。
                errors.append(f"batch[{index}]: {exc}")
        return {"valid": not errors, "errors": errors, "items": normalized}

    def setDebugGraphics(self, graphics: ResizerObserver) -> None:
        self.graphics_ = graphics

    def getSlewRCFactor(self) -> float:
        if self.slew_rc_factor_ is None:
            self.computeSlewRCFactor()
        return self.slew_rc_factor_ if self.slew_rc_factor_ is not None else 0.0

    def computeSlewRCFactor(self) -> None:
        _not_translated("RepairDesign::computeSlewRCFactor")
