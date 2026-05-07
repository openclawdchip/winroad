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

    def incIter(self) -> None:
        self.iter_ += 1

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
        rows: List[str] = ["net,guides,orig_guides,has_guides"]
        if block is not None:
            for net in block.getNets():
                rows.append(f"{net.getName()},{len(net.getGuides())},{len(net.getOrigGuides())},{int(net.hasGuides())}")
        report = "\n".join(rows) + "\n"
        if self.router_cfg_.GUIDE_REPORT_FILE:
            Path(self.router_cfg_.GUIDE_REPORT_FILE).write_text(report, encoding="utf-8")
        elif self.logger_ is not None and hasattr(self.logger_, "info"):
            self.logger_.info(report.rstrip())

    def fixMaxSpacing(self) -> None:
        _unsupported("FlexDR::fixMaxSpacing")

__all__ = ["FlexDR", "FlexDRSearchRepairArgs", "FlexDRViaData"]
