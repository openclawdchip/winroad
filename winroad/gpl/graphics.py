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


