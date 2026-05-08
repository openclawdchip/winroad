"""Graphics debug interface for WinRoad gpl."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

class AbstractGraphics:
    """对应 `gpl::AbstractGraphics` 的 Python 可覆盖接口。

    OpenROAD 的 GUI 后端会覆盖这些方法进行绘图；Python 版本默认只记录
    事件，保证 GPL 调试入口在无 GUI 环境下也可验证、可报告。
    """

    def __init__(self, logger: Any = None):
        self.logger = logger
        self.debug_on = False
        self.events_: List[Tuple[str, Any]] = []

    def _record(self, kind: str, payload: Any = None) -> None:
        self.events_.append((kind, payload))

    def MakeNew(self, logger: Any) -> "AbstractGraphics":
        return self.__class__(logger)

    def debugForMbff(self) -> None:
        self.debug_on = True
        self._record("debug_mbff", None)

    def debugForInitialPlace(self, pbc: PlacerBaseCommon, pbVec: List[PlacerBase]) -> None:
        self.debug_on = True
        self._record(
            "debug_initial",
            {
                "placer_bases": len(pbVec),
                "insts": len(pbc.getInsts()) if pbc is not None else 0,
                "place_insts": len(pbc.placeInsts()) if pbc is not None else 0,
            },
        )

    def debugForNesterovPlace(
        self,
        np: NesterovPlace,
        pbc: PlacerBaseCommon,
        nbc: NesterovBaseCommon,
        rb: RouteBase,
        pbVec: List[PlacerBase],
        nbVec: List[NesterovBase],
        draw_bins: bool,
        inst: Optional[DbInst],
    ) -> None:
        self.debug_on = True
        self._record(
            "debug_nesterov",
            {
                "placer_bases": len(pbVec),
                "nesterov_bases": len(nbVec),
                "draw_bins": draw_bins,
                "inst": getattr(inst, "name", None),
                "gcells": len(nbc.getGCells()) if nbc is not None else 0,
                "gnets": len(nbc.getGNets()) if nbc is not None else 0,
                "has_route_base": rb is not None,
                "has_nesterov_place": np is not None,
            },
        )

    def cellPlot(self, pause: bool = False) -> None:
        self.cellPlotImpl(pause)

    def addIter(self, iter: int, overflow: float) -> None:
        self._record("iter", {"iter": iter, "overflow": overflow})

    def addTimingDrivenIter(self, iter: int) -> None:
        self._record("timing_iter", {"iter": iter})

    def addRoutabilitySnapshot(self, iter: int) -> None:
        self._record("routability_snapshot", {"iter": iter})

    def addRoutabilityIter(self, iter: int, revert: bool) -> None:
        self._record("routability_iter", {"iter": iter, "revert": revert})

    def mbffMapping(self, segs: Sequence[Any]) -> None:
        self._record("mbff_mapping", {"segments": len(segs)})

    def mbffFlopClusters(self, ffs: Sequence[DbInst]) -> None:
        self._record("mbff_flop_clusters", {"flops": len(ffs)})

    def status(self, message: str) -> None:
        self._record("status", message)

    def drawObjects(self, painter: Any = None) -> None:
        self._record("draw_objects", {"painter": painter is not None})

    def select(self, layer: Any = None, x: int = 0, y: int = 0) -> List[Any]:
        self._record("select", {"layer": getattr(layer, "name", None), "x": x, "y": y})
        return []

    def canAdjustGrid(self) -> bool:
        return False

    def getGridXSize(self) -> float:
        return 0.0

    def getGridYSize(self) -> float:
        return 0.0

    def getBounds(self) -> Tuple[int, int, int, int]:
        return (0, 0, 0, 0)

    def populateMap(self) -> bool:
        self._record("populate_map", None)
        return False

    def combineMapData(self, base_has_value: bool, base: float, new_data: float) -> Tuple[bool, float]:
        return bool(base_has_value), base if base_has_value else new_data

    def populateXYGrid(self) -> None:
        self._record("populate_xy_grid", None)

    @staticmethod
    def guiActive() -> bool:
        return False

    def addFrameLabel(self, gui: Any, bbox: Any, label: str, label_name: str, image_width_px: int) -> None:
        self._record(
            "frame_label",
            {"label": label, "label_name": label_name, "image_width_px": image_width_px},
        )

    def saveLabeledImage(self, path: str, label: str, label_name: str = "", image_width_px: int = 0) -> None:
        self._record(
            "save_labeled_image",
            {"path": path, "label": label, "label_name": label_name, "image_width_px": image_width_px},
        )

    def getGuiObjectFromGraphics(self) -> None:
        return None

    def drawForce(self, painter: Any = None) -> None:
        self._record("draw_force", {"painter": painter is not None})

    def drawCells(self, cells: Sequence[Any], painter: Any = None) -> None:
        self._record("draw_cells", {"cells": len(cells), "painter": painter is not None})

    def drawSingleGCell(self, gCell: Any, painter: Any = None) -> None:
        self._record("draw_single_gcell", {"gcell": getattr(gCell, "name", None), "painter": painter is not None})

    def initHeatmap(self) -> None:
        self._record("init_heatmap", None)

    def drawNesterov(self, painter: Any = None) -> None:
        self._record("draw_nesterov", {"painter": painter is not None})

    def drawInitial(self, painter: Any = None) -> None:
        self._record("draw_initial", {"painter": painter is not None})

    def drawMBFF(self, painter: Any = None) -> None:
        self._record("draw_mbff", {"painter": painter is not None})

    def drawBounds(self, painter: Any = None) -> None:
        self._record("draw_bounds", {"painter": painter is not None})

    def reportSelected(self) -> Dict[str, Any]:
        report = {"selected": 0}
        self._record("report_selected", report)
        return report

    def enabled(self) -> bool:
        return self.debug_on

    def setDebugOn(self, set_on: bool) -> None:
        self.debug_on = bool(set_on)
        self._record("debug_on", self.debug_on)

    def cellPlotImpl(self, pause: bool) -> None:
        self._record("cell_plot", {"pause": pause})

    def events(self) -> List[Tuple[str, Any]]:
        return list(self.events_)

    def clearEvents(self) -> None:
        self.events_.clear()

    def report(self, sample_limit: int = 0) -> Dict[str, Any]:
        """导出图形调试事件摘要；不包含任何布局算法结果。"""

        counts = Counter(kind for kind, _ in self.events_)
        report: Dict[str, Any] = {
            "enabled": self.enabled(),
            "event_count": len(self.events_),
            "event_counts": dict(counts),
            "last_event": self.events_[-1] if self.events_ else None,
        }
        if sample_limit > 0:
            report["sample_events"] = self.events_[:sample_limit]
        return report


class GraphicsNone(AbstractGraphics):
    """对应 OpenROAD `GraphicsNone`，默认无图形后端。"""

    def __init__(self, logger: Any = None):
        super().__init__(logger)

    def MakeNew(self, logger: Any) -> "GraphicsNone":
        return GraphicsNone(logger)

    def enabled(self) -> bool:
        """无 GUI 后端不打开绘图窗口，但仍保留 debug_on 状态供报告使用。"""

        return self.debug_on


