"""Graphics debug interface for WinRoad gpl."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

class AbstractGraphics:
    """对应 `gpl::AbstractGraphics` 的 Python 抽象接口。"""

    def MakeNew(self, logger: Any) -> "AbstractGraphics":
        raise NotImplementedError

    def debugForMbff(self) -> None:
        raise NotImplementedError

    def debugForInitialPlace(self, pbc: PlacerBaseCommon, pbVec: List[PlacerBase]) -> None:
        raise NotImplementedError

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
        raise NotImplementedError

    def cellPlot(self, pause: bool = False) -> None:
        self.cellPlotImpl(pause)

    def addIter(self, iter: int, overflow: float) -> None:
        raise NotImplementedError

    def addTimingDrivenIter(self, iter: int) -> None:
        raise NotImplementedError

    def addRoutabilitySnapshot(self, iter: int) -> None:
        raise NotImplementedError

    def addRoutabilityIter(self, iter: int, revert: bool) -> None:
        raise NotImplementedError

    def mbffMapping(self, segs: Sequence[Any]) -> None:
        raise NotImplementedError

    def mbffFlopClusters(self, ffs: Sequence[DbInst]) -> None:
        raise NotImplementedError

    def status(self, message: str) -> None:
        raise NotImplementedError

    def enabled(self) -> bool:
        raise NotImplementedError

    def setDebugOn(self, set_on: bool) -> None:
        raise NotImplementedError

    def cellPlotImpl(self, pause: bool) -> None:
        raise NotImplementedError


class GraphicsNone(AbstractGraphics):
    """对应 OpenROAD `GraphicsNone`，默认无图形后端。"""

    def __init__(self, logger: Any = None):
        self.logger = logger
        self.debug_on = False
        self.events_: List[Tuple[str, Any]] = []

    def MakeNew(self, logger: Any) -> "GraphicsNone":
        return GraphicsNone(logger)

    def debugForMbff(self) -> None:
        self.debug_on = True
        self.events_.append(("debug_mbff", None))

    def debugForInitialPlace(self, pbc: PlacerBaseCommon, pbVec: List[PlacerBase]) -> None:
        self.debug_on = True
        self.events_.append(("debug_initial", len(pbVec)))

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
        self.events_.append(("debug_nesterov", len(nbVec)))

    def addIter(self, iter: int, overflow: float) -> None:
        self.events_.append(("iter", (iter, overflow)))

    def addTimingDrivenIter(self, iter: int) -> None:
        self.events_.append(("timing_iter", iter))

    def addRoutabilitySnapshot(self, iter: int) -> None:
        self.events_.append(("routability_snapshot", iter))

    def addRoutabilityIter(self, iter: int, revert: bool) -> None:
        self.events_.append(("routability_iter", (iter, revert)))

    def mbffMapping(self, segs: Sequence[Any]) -> None:
        return None

    def mbffFlopClusters(self, ffs: Sequence[DbInst]) -> None:
        return None

    def status(self, message: str) -> None:
        self.events_.append(("status", message))

    def enabled(self) -> bool:
        return False

    def setDebugOn(self, set_on: bool) -> None:
        self.debug_on = set_on

    def cellPlotImpl(self, pause: bool) -> None:
        self.events_.append(("cell_plot", pause))

    def events(self) -> List[Tuple[str, Any]]:
        return self.events_


