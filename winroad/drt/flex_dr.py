"""Detailed routing stage boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .fr import frDesign, frRegionQuery, frTechObject
from .types import RipUpMode, RouterConfiguration, frCoord, frUInt4, _unsupported

@dataclass
class FlexDRViaData:
    """对应 ``FlexDR.h`` 的 FlexDRViaData。"""

    halfViaEncArea: List[Tuple[frCoord, frCoord]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """返回 via 搜索辅助数据快照；不生成新 via，也不评估 enclosure。"""

        return {"halfViaEncArea": list(self.halfViaEncArea)}


@dataclass
class FlexDRSearchRepairArgs:
    """对应 ``FlexDR::SearchRepairArgs``。"""

    size: int
    offset: int
    mazeEndIter: int
    workerDRCCost: frUInt4
    workerMarkerCost: frUInt4
    workerFixedShapeCost: frUInt4
    workerMarkerDecay: float
    ripupMode: RipUpMode = RipUpMode.INCR
    followGuide: bool = True

    def isEqualIgnoringSizeAndOffset(self, other: "FlexDRSearchRepairArgs") -> bool:
        return (
            self.mazeEndIter == other.mazeEndIter
            and self.workerDRCCost == other.workerDRCCost
            and self.workerMarkerCost == other.workerMarkerCost
            and self.workerFixedShapeCost == other.workerFixedShapeCost
            and self.workerMarkerDecay == other.workerMarkerDecay
            and self.ripupMode == other.ripupMode
            and self.followGuide == other.followGuide
        )

    def to_dict(self) -> Dict[str, Any]:
        """返回 searchRepair 参数状态；算法入口本身仍保持未实现。"""

        return {
            "size": self.size,
            "offset": self.offset,
            "mazeEndIter": self.mazeEndIter,
            "workerDRCCost": self.workerDRCCost,
            "workerMarkerCost": self.workerMarkerCost,
            "workerFixedShapeCost": self.workerFixedShapeCost,
            "workerMarkerDecay": self.workerMarkerDecay,
            "ripupMode": self.ripupMode.value,
            "followGuide": self.followGuide,
        }


class FlexDR:
    """对应 ``dr/FlexDR.h`` 的 detailed routing 顶层编排类。"""

    def __init__(
        self,
        router: Optional["TritonRoute"],
        design: frDesign,
        logger: Any = None,
        db: Any = None,
        router_cfg: Optional[RouterConfiguration] = None,
    ):
        self.router_ = router
        self.design_ = design
        self.logger_ = logger
        self.db_ = db
        self.router_cfg_ = router_cfg or RouterConfiguration()
        self.via_data_ = FlexDRViaData()
        self.graphics_: Optional[Any] = None
        self.iter_: int = 0
        self.numViols_: List[int] = []
        self.distributed_: Dict[str, Any] = {}

    def getTech(self) -> frTechObject:
        return self.design_.getTech()

    def getDesign(self) -> frDesign:
        return self.design_

    def getRegionQuery(self) -> frRegionQuery:
        return self.design_.getRegionQuery()

    def getViaData(self) -> FlexDRViaData:
        return self.via_data_

    def setDebug(self, dr_graphics: Any) -> None:
        self.graphics_ = dr_graphics

    def getGraphics(self) -> Any:
        return self.graphics_

    def setDistributed(self, dist: Any, remote_ip: str, remote_port: int, directory: str) -> None:
        self.distributed_ = {"dist": dist, "remote_ip": remote_ip, "remote_port": remote_port, "dir": directory}

    def getDistributedState(self) -> Dict[str, Any]:
        """返回 distributed worker 连接状态，不启动远端 worker。"""

        return dict(self.distributed_)

    def getIter(self) -> int:
        return self.iter_

    def incIter(self) -> None:
        self.iter_ += 1

    def setNumViols(self, viols: List[int]) -> None:
        self.numViols_ = list(viols)

    def getNumViols(self) -> List[int]:
        return self.numViols_

    def init(self) -> None:
        _unsupported("FlexDR::init")

    def main(self) -> int:
        _unsupported("FlexDR::main")

    def searchRepair(self, args: FlexDRSearchRepairArgs) -> None:
        _unsupported("FlexDR::searchRepair")

    def end(self, done: bool = False) -> None:
        _unsupported("FlexDR::end")

    def reportGuideCoverage(self) -> None:
        block = self.design_.getTopBlock()
        rows: List[str] = ["net,guides,orig_guides,route_objs,has_guides"]
        if block is not None:
            for net in block.getNets():
                rows.append(
                    f"{net.getName()},{len(net.getGuides())},{len(net.getOrigGuides())},"
                    f"{net.getRouteObjCount()},{int(net.hasGuides())}"
                )
        report = "\n".join(rows) + "\n"
        if self.router_cfg_.GUIDE_REPORT_FILE:
            Path(self.router_cfg_.GUIDE_REPORT_FILE).write_text(report, encoding="utf-8")
        elif self.logger_ is not None and hasattr(self.logger_, "info"):
            self.logger_.info(report.rstrip())

    def getGuideCoverageRows(self) -> List[Dict[str, Any]]:
        """返回当前 guide 覆盖报告行；只统计已有 guide，不做覆盖率估算。"""

        block = self.design_.getTopBlock()
        rows: List[Dict[str, Any]] = []
        if block is None:
            return rows
        for net in block.getNets():
            row = net.getGuideSummary()
            row["has_guides"] = net.hasGuides()
            rows.append(row)
        return rows

    def validateGuides(self) -> List[str]:
        """检查已有 guide 的基础状态；不计算真实覆盖率。"""

        block = self.design_.getTopBlock()
        if block is None:
            return []
        errors: List[str] = []
        for net in block.getNets():
            errors.extend(net.validateGuides())
        return errors

    def snapshot(self) -> Dict[str, Any]:
        """返回 DR 阶段状态快照；不运行 detailed routing 或 DRC 修复。"""

        return {
            "iter": self.iter_,
            "num_viols": list(self.numViols_),
            "via_data": self.via_data_.to_dict(),
            "distributed": self.getDistributedState(),
            "guide_coverage": self.getGuideCoverageRows(),
            "guide_validation_errors": self.validateGuides(),
        }

    def fixMaxSpacing(self) -> None:
        _unsupported("FlexDR::fixMaxSpacing")

__all__ = ["FlexDR", "FlexDRSearchRepairArgs", "FlexDRViaData"]
