"""Geometry checker worker boundary."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

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
        self.target_objs_: List[Any] = []
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
        if obj not in self.target_objs_:
            self.target_objs_.append(obj)

    def setTargetObjs(self, objs: Iterable[Any]) -> None:
        self.target_objs_ = []
        for obj in objs:
            self.addTargetObj(obj)

    def setIgnoreDB(self) -> None:
        self.ignore_db_ = True

    def setIgnoreMinArea(self) -> None:
        self.ignore_min_area_ = True

    def getExtBox(self) -> Rect:
        return self.ext_box_

    def getDrcBox(self) -> Rect:
        return self.drc_box_

    def getTargetObjs(self) -> List[Any]:
        return self.target_objs_

    def addMarker(self, marker: frMarker) -> None:
        """记录外部已创建 marker；不执行 DRC 检查。"""

        self.markers_.append(marker)

    def clearMarkers(self) -> None:
        self.markers_.clear()

    def getMarkers(self) -> List[frMarker]:
        return self.markers_

    def getMarkerSummary(self) -> Dict[str, Any]:
        by_layer: Dict[int, int] = {}
        for marker in self.markers_:
            by_layer[marker.getLayerNum()] = by_layer.get(marker.getLayerNum(), 0) + 1
        return {"count": len(self.markers_), "by_layer": by_layer}

    def getPWires(self) -> List[Any]:
        return self.pwires_

    def snapshot(self) -> Dict[str, Any]:
        """返回 GC worker 状态；不跑规则检查，也不更新 DR net。"""

        return {
            "ext_box": self.ext_box_,
            "drc_box": self.drc_box_,
            "target_net": getattr(self.target_net_, "getName", lambda: str(self.target_net_))() if self.target_net_ is not None else "",
            "target_objs": len(self.target_objs_),
            "marker_summary": self.getMarkerSummary(),
            "markers": [marker.to_dict() if hasattr(marker, "to_dict") else str(marker) for marker in self.markers_],
            "pwires": len(self.pwires_),
            "ignore_db": self.ignore_db_,
            "ignore_min_area": self.ignore_min_area_,
        }

    def init(self, design: frDesign) -> None:
        _unsupported("FlexGCWorker::init")

    def main(self) -> int:
        _unsupported("FlexGCWorker::main")

    def updateDRNet(self, net: Any) -> None:
        _unsupported("FlexGCWorker::updateDRNet")

__all__ = ["FlexGCWorker"]
