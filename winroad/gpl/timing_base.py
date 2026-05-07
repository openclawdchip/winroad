"""Timing-driven placement boundary for WinRoad gpl."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from .nesterov import GNet, NesterovBaseCommon

class TimingBase:
    """对应 `gpl::TimingBase`，保留 timing-driven net reweight 边界。"""

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
        self.timingOverflowChk_: List[int] = []
        self.net_weight_max_ = 5.0
        self.timing_driven_nets_: List[GNet] = []
        self.prev_timing_weights_: Dict[int, float] = {}
        self.run_journal_restore_ = False
        self.timing_driven_iter_ = 0
        self.last_overflow_ = 0.0
        self.last_resizer_result_ = False

    def isTimingNetWeightOverflow(self, overflow: float) -> bool:
        checkpoint = int(round(overflow * 100))
        self.last_overflow_ = overflow
        if checkpoint not in self.timingOverflowChk_:
            return False
        self.timingOverflowChk_.remove(checkpoint)
        return True

    def addTimingNetWeightOverflow(self, overflow: int) -> None:
        self.timingNetWeightOverflow_.append(overflow)
        self.initTimingOverflowChk()

    def setTimingNetWeightOverflows(self, overflows: Sequence[int]) -> None:
        self.timingNetWeightOverflow_ = list(overflows)
        self.initTimingOverflowChk()

    def deleteTimingNetWeightOverflow(self, overflow: int) -> None:
        self.timingNetWeightOverflow_ = [item for item in self.timingNetWeightOverflow_ if item != overflow]
        self.initTimingOverflowChk()

    def clearTimingNetWeightOverflow(self) -> None:
        self.timingNetWeightOverflow_.clear()
        self.timingOverflowChk_.clear()

    def getTimingNetWeightOverflowSize(self) -> int:
        return len(self.timingNetWeightOverflow_)

    def setTimingNetWeightMax(self, max: float) -> None:
        self.net_weight_max_ = max

    def executeTimingDriven(self, run_journal_restore: bool) -> bool:
        self.run_journal_restore_ = run_journal_restore
        self.timing_driven_iter_ += 1
        self.prev_timing_weights_ = {}
        if self.nbc_ is not None:
            for index, gnet in enumerate(self.nbc_.getGNets()):
                self.prev_timing_weights_[index] = gnet.getTimingWeight()
        raise NotImplementedError("OpenROAD timing-driven net reweight has not been translated yet")

    def resetTimingDrivenNets(self) -> None:
        self.timing_driven_nets_.clear()
        if self.nbc_ is not None:
            self.nbc_.resetTimingNetWeights()

    def updateGNetWeights(self) -> None:
        raise NotImplementedError("OpenROAD timing-driven gnet weight update has not been translated yet")

    def runResizerForTiming(self, run_journal_restore: bool) -> bool:
        raise NotImplementedError("OpenROAD resizer timing repair hook has not been translated yet")

    def resetFillerCells(self) -> None:
        raise NotImplementedError("OpenROAD timing-driven filler reset has not been translated yet")

    def initTimingOverflowChk(self) -> None:
        self.timingOverflowChk_ = sorted(set(self.timingNetWeightOverflow_), reverse=True)

    def timingOverflowChk(self) -> List[int]:
        return self.timingOverflowChk_

    def timingDrivenNets(self) -> List[GNet]:
        return self.timing_driven_nets_

    def restorePrevTimingWeights(self) -> None:
        if self.nbc_ is None:
            return
        for index, gnet in enumerate(self.nbc_.getGNets()):
            if index in self.prev_timing_weights_:
                gnet.setTimingWeight(self.prev_timing_weights_[index])

    def reportTimingDriven(self) -> Dict[str, Any]:
        return {
            "checkpoints": list(self.timingNetWeightOverflow_),
            "remaining_checkpoints": list(self.timingOverflowChk_),
            "max_weight": self.net_weight_max_,
            "timing_driven_iter": self.timing_driven_iter_,
            "timing_driven_nets": len(self.timing_driven_nets_),
            "last_overflow": self.last_overflow_,
            "run_journal_restore": self.run_journal_restore_,
        }


