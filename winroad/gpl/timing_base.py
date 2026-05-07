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
        self.prev_timing_weights_by_id_: Dict[int, float] = {}
        self.restore_count_ = 0
        self.last_restored_weights_ = 0
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
        self.snapshotTimingWeights()
        raise NotImplementedError("OpenROAD timing-driven net reweight has not been translated yet")

    def resetTimingDrivenNets(self) -> None:
        self.timing_driven_nets_.clear()
        if self.nbc_ is not None:
            self.nbc_.resetTimingNetWeights()

    def addTimingDrivenNet(self, gnet: GNet) -> None:
        """记录 timing-driven net，真实 STA slack 筛选仍在未翻译入口中。"""

        if gnet not in self.timing_driven_nets_:
            self.timing_driven_nets_.append(gnet)

    def clearTimingDrivenNets(self) -> None:
        self.timing_driven_nets_.clear()

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
        restored = 0
        for index, gnet in enumerate(self.nbc_.getGNets()):
            weight = self.prev_timing_weights_by_id_.get(id(gnet), self.prev_timing_weights_.get(index))
            if weight is not None:
                gnet.setTimingWeight(weight)
                restored += 1
        self.restore_count_ += 1
        self.last_restored_weights_ = restored

    def snapshotTimingWeights(self) -> None:
        self.prev_timing_weights_ = {}
        self.prev_timing_weights_by_id_ = {}
        if self.nbc_ is None:
            return
        for index, gnet in enumerate(self.nbc_.getGNets()):
            weight = gnet.getTimingWeight()
            self.prev_timing_weights_[index] = weight
            self.prev_timing_weights_by_id_[id(gnet)] = weight

    def clearTimingWeightSnapshot(self) -> None:
        self.prev_timing_weights_.clear()
        self.prev_timing_weights_by_id_.clear()

    def reportTimingDriven(self) -> Dict[str, Any]:
        return {
            "checkpoints": list(self.timingNetWeightOverflow_),
            "remaining_checkpoints": list(self.timingOverflowChk_),
            "max_weight": self.net_weight_max_,
            "timing_driven_iter": self.timing_driven_iter_,
            "timing_driven_nets": len(self.timing_driven_nets_),
            "last_overflow": self.last_overflow_,
            "run_journal_restore": self.run_journal_restore_,
            "snapshot_weights": len(self.prev_timing_weights_),
            "restore_count": self.restore_count_,
            "last_restored_weights": self.last_restored_weights_,
        }

    def reportTimingNets(self, sample_limit: int = 0) -> Dict[str, Any]:
        """导出 timing-driven net 样本和权重快照状态。"""

        report: Dict[str, Any] = {
            "timing_driven_nets": len(self.timing_driven_nets_),
            "snapshot_weights": len(self.prev_timing_weights_),
            "snapshot_weights_by_id": len(self.prev_timing_weights_by_id_),
        }
        if sample_limit > 0:
            report["sample_nets"] = [gnet.report() for gnet in self.timing_driven_nets_[:sample_limit]]
        return report


