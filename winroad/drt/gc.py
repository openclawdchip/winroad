"""Geometry checker worker boundary."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Set

from .fr import frDesign, frMarker, frTechObject
from .types import Rect, RouterConfiguration, _unsupported

class FlexGCWorker:
    """对应 ``gc/FlexGC.h`` 的 geometry checker worker。"""

    def __init__(
        self,
        tech: Optional[frTechObject] = None,
        logger: Any = None,
        router_cfg: Optional[RouterConfiguration] = None,
        dr_worker: Any = None,
    ):
        self.tech_ = tech or frTechObject()
        self.logger_ = logger
        self.router_cfg_ = router_cfg or RouterConfiguration()
        self.dr_worker_ = dr_worker
        self.ext_box_: Rect = (0, 0, 0, 0)
        self.drc_box_: Rect = (0, 0, 0, 0)
        self.target_net_: Optional[Any] = None
        self.target_objs_: Set[Any] = set()
        self.markers_: List[frMarker] = []
        self.pwires_: List[Any] = []
        self.ignore_db_: bool = False
        self.ignore_min_area_: bool = False

    def setExtBox(self, box: Rect) -> None:
        self.ext_box_ = box

    def setDrcBox(self, box: Rect) -> None:
        self.drc_box_ = box

    def setTargetNet(self, net: Any) -> bool:
        self.target_net_ = net
        return True

    def getTargetNet(self) -> Any:
        return self.target_net_

    def resetTargetNet(self) -> None:
        self.target_net_ = None

    def addTargetObj(self, obj: Any) -> None:
        self.target_objs_.add(obj)

    def setTargetObjs(self, objs: Iterable[Any]) -> None:
        self.target_objs_ = set(objs)

    def setIgnoreDB(self) -> None:
        self.ignore_db_ = True

    def setIgnoreMinArea(self) -> None:
        self.ignore_min_area_ = True

    def getMarkers(self) -> List[frMarker]:
        return self.markers_

    def getPWires(self) -> List[Any]:
        return self.pwires_

    def init(self, design: frDesign) -> None:
        _unsupported("FlexGCWorker::init")

    def main(self) -> int:
        _unsupported("FlexGCWorker::main")

    def updateDRNet(self, net: Any) -> None:
        _unsupported("FlexGCWorker::updateDRNet")

__all__ = ["FlexGCWorker"]
