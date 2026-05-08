"""Timing-driven placement boundary for WinRoad gpl."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from .nesterov import GNet, NesterovBaseCommon


def _logger_call(log: Any, level: str, *args: Any) -> None:
    method = getattr(log, level, None)
    if callable(method):
        try:
            method(*args)
        except Exception:
            pass


def _call_optional(obj: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    method = getattr(obj, name, None)
    if callable(method):
        return method(*args, **kwargs)
    return None


def _fuzzy_inf(value: float) -> bool:
    return value == float("inf") or value == float("-inf")


class TimingBase:
    def __init__(
        self,
        nbc: Optional[NesterovBaseCommon] = None,
        grt: Any = None,
        rs: Any = None,
        log: Any = None,
    ):
        self.grt_ = grt
        self.rs_ = rs
        self.log_ = log
        self.nbc_ = nbc
        self.timingNetWeightOverflow_: List[int] = []
        self.timingOverflowChk_: List[bool] = []
        self.net_weight_max_ = 5.0

    def initTimingOverflowChk(self) -> None:
        self.timingOverflowChk_ = [False] * len(self.timingNetWeightOverflow_)

    def isTimingNetWeightOverflow(self, overflow: float) -> bool:
        intOverflow = round(overflow * 100)
        if not self.timingNetWeightOverflow_ or intOverflow > self.timingNetWeightOverflow_[0]:
            return False
        needTdRun = False
        for i in range(len(self.timingNetWeightOverflow_)):
            if self.timingNetWeightOverflow_[i] > intOverflow:
                if not self.timingOverflowChk_[i]:
                    self.timingOverflowChk_[i] = True
                    needTdRun = True
                continue
            return needTdRun
        return needTdRun

    def addTimingNetWeightOverflow(self, overflow: int) -> None:
        if overflow not in self.timingNetWeightOverflow_:
            self.timingNetWeightOverflow_.append(int(overflow))
        self.timingNetWeightOverflow_.sort(reverse=True)
        self.initTimingOverflowChk()

    def setTimingNetWeightOverflows(self, overflows: Sequence[int]) -> None:
        self.timingNetWeightOverflow_.clear()
        for overflow in sorted((int(item) for item in overflows), reverse=True):
            self.addTimingNetWeightOverflow(overflow)
        self.initTimingOverflowChk()

    def deleteTimingNetWeightOverflow(self, overflow: int) -> None:
        try:
            self.timingNetWeightOverflow_.remove(int(overflow))
        except ValueError:
            pass

    def clearTimingNetWeightOverflow(self) -> None:
        self.timingNetWeightOverflow_.clear()
        self.timingOverflowChk_.clear()

    def getTimingNetWeightOverflowSize(self) -> int:
        return len(self.timingNetWeightOverflow_)

    def setTimingNetWeightMax(self, max: float) -> None:
        self.net_weight_max_ = float(max)

    def executeTimingDriven(self, run_journal_restore: bool) -> bool:
        if self.rs_ is None:
            return False
        _call_optional(self.rs_, "findResizeSlacks", run_journal_restore)
        if not run_journal_restore:
            _call_optional(self.nbc_, "fixPointers")
        worst_slack_nets = _call_optional(self.rs_, "resizeWorstSlackNets") or []
        if not worst_slack_nets:
            _logger_call(self.log_, "warn", "GPL", 105, "Timing-driven: no net slacks found. Timing-driven mode disabled.")
            return False
        slack_min = _call_optional(self.rs_, "resizeNetSlack", worst_slack_nets[0])
        slack_max = _call_optional(self.rs_, "resizeNetSlack", worst_slack_nets[-1])
        if slack_min is None or slack_max is None:
            _logger_call(self.log_, "warn", "GPL", 102, "Timing-driven: no slacks found. Timing-driven mode disabled.")
            return False
        slack_min = float(slack_min)
        slack_max = float(slack_max)
        _logger_call(self.log_, "info", "GPL", 106, "Timing-driven: worst slack {:.3g}", slack_min)
        if _fuzzy_inf(slack_min):
            _logger_call(self.log_, "warn", "GPL", 102, "Timing-driven: no slacks found. Timing-driven mode disabled.")
            return False
        weighted_net_count = 0
        if self.nbc_ is None:
            return False
        for gNet in self.nbc_.getGNets():
            gNet.setTimingWeight(1.0)
            if len(gNet.gPins()) <= 1:
                continue
            db_net = gNet.getPbNet().getDbNet() if gNet.getPbNet() is not None else None
            if db_net is None:
                continue
            net_slack = _call_optional(self.rs_, "resizeNetSlack", db_net)
            if net_slack is None:
                continue
            net_slack = float(net_slack)
            if net_slack < slack_max:
                if slack_max == slack_min:
                    gNet.setTimingWeight(1.0)
                else:
                    weight = 1 + (self.net_weight_max_ - 1) * (slack_max - net_slack) / (slack_max - slack_min)
                    gNet.setTimingWeight(weight)
                weighted_net_count += 1
            _logger_call(
                self.log_,
                "debugPrint",
                "GPL",
                "timing",
                1,
                "net:{} slack:{} weight:{}",
                gNet.getName(),
                net_slack,
                gNet.getTotalWeight(),
            )
        _logger_call(self.log_, "debugPrint", "GPL", "timing", 1, "Timing-driven: weighted {} nets.", weighted_net_count)
        return True
