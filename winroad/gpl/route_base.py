"""Routability boundary for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..odb import DbDatabase
from .common import _area
from .nesterov import GCell, GCellChange, NesterovBase, NesterovBaseCommon
from .options import PlaceOptions

@dataclass
class RouteBaseVars:
    """对应 `gpl::RouteBaseVars`。"""

    useRudy: bool
    targetRC: float
    inflationRatioCoef: float
    maxInflationRatio: float
    maxDensity: float
    ignoreEdgeRatio: float = 0.0
    minInflationRatio: float = 1.0
    rcK1: float = 1.0
    rcK2: float = 1.0
    rcK3: float = 0.0
    rcK4: float = 0.0

    @classmethod
    def from_options(cls, options: PlaceOptions) -> "RouteBaseVars":
        return cls(
            useRudy=options.routabilityUseRudy,
            targetRC=options.routabilityTargetRcMetric,
            inflationRatioCoef=options.routabilityInflationRatioCoef,
            maxInflationRatio=options.routabilityMaxInflationRatio,
            maxDensity=options.routabilityMaxDensity,
            rcK1=options.routabilityRcK1,
            rcK2=options.routabilityRcK2,
            rcK3=options.routabilityRcK3,
            rcK4=options.routabilityRcK4,
        )


@dataclass
class Tile:
    """对应 `gpl::Tile`。"""

    x_: int = 0
    y_: int = 0
    lx_: int = 0
    ly_: int = 0
    ux_: int = 0
    uy_: int = 0
    layers_: int = 0
    inflationRatio_: float = 1.0
    inflatedRatio_: float = 0.0

    def area(self) -> int:
        return _area((self.lx_, self.ly_, self.ux_, self.uy_))

    def inflationRatio(self) -> float:
        return self.inflationRatio_

    def inflatedRatio(self) -> float:
        return self.inflatedRatio_

    def setInflationRatio(self, ratio: float) -> None:
        self.inflationRatio_ = ratio

    def setInflatedRatio(self, ratio: float) -> None:
        self.inflatedRatio_ = ratio


@dataclass
class TileGrid:
    """对应 `gpl::TileGrid`。"""

    log_: Any = None
    tileStor_: List[Tile] = field(default_factory=list)
    tiles_: List[Tile] = field(default_factory=list)
    lx_: int = 0
    ly_: int = 0
    tileCntX_: int = 0
    tileCntY_: int = 0
    tileSizeX_: int = 0
    tileSizeY_: int = 0
    numRoutingLayers_: int = 0

    def setLogger(self, log: Any) -> None:
        self.log_ = log

    def setTileCnt(self, tileCntX: int, tileCntY: int) -> None:
        self.tileCntX_, self.tileCntY_ = tileCntX, tileCntY

    def setTileCntX(self, tileCntX: int) -> None:
        self.tileCntX_ = tileCntX

    def setTileCntY(self, tileCntY: int) -> None:
        self.tileCntY_ = tileCntY

    def setTileSize(self, tileSizeX: int, tileSizeY: int) -> None:
        self.tileSizeX_, self.tileSizeY_ = tileSizeX, tileSizeY

    def setTileSizeX(self, tileSizeX: int) -> None:
        self.tileSizeX_ = tileSizeX

    def setTileSizeY(self, tileSizeY: int) -> None:
        self.tileSizeY_ = tileSizeY

    def setNumRoutingLayers(self, num: int) -> None:
        self.numRoutingLayers_ = num

    def setLx(self, lx: int) -> None:
        self.lx_ = lx

    def setLy(self, ly: int) -> None:
        self.ly_ = ly

    def lx(self) -> int:
        return self.lx_

    def ly(self) -> int:
        return self.ly_

    def ux(self) -> int:
        return self.lx_ + self.tileCntX_ * self.tileSizeX_

    def uy(self) -> int:
        return self.ly_ + self.tileCntY_ * self.tileSizeY_

    def tileCntX(self) -> int:
        return self.tileCntX_

    def tileCntY(self) -> int:
        return self.tileCntY_

    def tileSizeX(self) -> int:
        return self.tileSizeX_

    def tileSizeY(self) -> int:
        return self.tileSizeY_

    def numRoutingLayers(self) -> int:
        return self.numRoutingLayers_

    def tiles(self) -> List[Tile]:
        return self.tiles_

    def initTiles(self, use_rudy: bool) -> None:
        self.tileStor_.clear()
        for y in range(max(0, self.tileCntY_)):
            for x in range(max(0, self.tileCntX_)):
                lx = self.lx_ + x * self.tileSizeX_
                ly = self.ly_ + y * self.tileSizeY_
                self.tileStor_.append(Tile(x, y, lx, ly, lx + self.tileSizeX_, ly + self.tileSizeY_, self.numRoutingLayers_))
        self.tiles_ = list(self.tileStor_)


class RouteBase:
    """对应 `gpl::RouteBase`，保留 RUDY/GR routability 边界。"""

    def __init__(
        self,
        rbVars: RouteBaseVars,
        db: Optional[DbDatabase],
        grouter: Any,
        nbc: Optional[NesterovBaseCommon],
        nbVec: List[NesterovBase],
        log: Any,
    ):
        self.rbVars_ = rbVars
        self.db_ = db
        self.grouter_ = grouter
        self.nbc_ = nbc
        self.nbVec_ = nbVec
        self.log_ = log
        self.tg_ = TileGrid()
        self.inflatedAreaDelta_: List[int] = []
        self.minRcInflatedAreaDelta_: List[int] = []
        self.accumulatedInflatedAreaDelta_: List[int] = []
        self.revert_count_ = 0
        self.final_average_rc_ = 0.0
        self.overflowed_tiles_count_ = 0
        self.total_route_overflow_ = 0.0
        self.is_min_rc_ = False
        self.minRc_ = 1e30
        self.minRcTargetDensity_: List[float] = []
        self.min_RC_violated_cnt_ = 0
        self.max_routability_no_improvement_ = 3
        self.max_routability_revert_ = 50
        self.rc_metric_: List[float] = []
        self.route_overflow_: List[float] = []
        self.route_utilization_: List[float] = []
        self.tile_inflation_ratios_: Dict[int, float] = {}
        self.minRcCellSizes_: Dict[int, Tuple[int, int]] = {}
        self.tg_.setLogger(log)

    def setNesterovBaseCommon(self, nbc: NesterovBaseCommon) -> None:
        self.nbc_ = nbc

    def setNesterovBases(self, nbVec: Sequence[NesterovBase]) -> None:
        self.nbVec_ = list(nbVec)

    def initRouteBase(self) -> None:
        self.tg_.tileStor_.clear()
        self.tg_.tiles_.clear()
        if not self.nbVec_:
            return
        nb = self.nbVec_[0]
        bg = nb.getBinGrid()
        self.tg_.setLx(bg.lx())
        self.tg_.setLy(bg.ly())
        self.tg_.setTileCnt(max(1, bg.getBinCntX()), max(1, bg.getBinCntY()))
        self.tg_.setTileSize(max(1, int(round(bg.getBinSizeX()))), max(1, int(round(bg.getBinSizeY()))))
        self.tg_.initTiles(self.rbVars_.useRudy)
        self.inflatedAreaDelta_ = [0 for _ in self.nbVec_]
        self.accumulatedInflatedAreaDelta_ = [0 for _ in self.nbVec_]

    def updateGrtRoute(self) -> None:
        raise NotImplementedError("OpenROAD GR route update has not been translated yet")

    def getGrtResult(self) -> None:
        raise NotImplementedError("OpenROAD GR result extraction has not been translated yet")

    def loadGrt(self) -> None:
        raise NotImplementedError("OpenROAD GR heatmap loading has not been translated yet")

    def getGrtRC(self) -> float:
        raise NotImplementedError("OpenROAD GR RC metric has not been translated yet")

    def calculateRudyTiles(self) -> None:
        raise NotImplementedError("OpenROAD RUDY tile calculation has not been translated yet")

    def updateRudyRoute(self) -> None:
        self.calculateRudyTiles()
        self.updateRudyAverage(False)

    def updateRudyAverage(self, verbose: bool = True) -> None:
        raise NotImplementedError("OpenROAD RUDY average update has not been translated yet")

    def updateRoute(self) -> None:
        if self.rbVars_.useRudy:
            self.updateRudyRoute()
        else:
            self.updateGrtRoute()
            self.getGrtResult()

    def getRudyAverage(self) -> float:
        return self.final_average_rc_

    def getRC(self) -> float:
        return self.getRudyAverage() if self.rbVars_.useRudy else self.getGrtRC()

    def getOverflowedTilesCount(self) -> int:
        return self.overflowed_tiles_count_

    def getTotalTilesCount(self) -> int:
        return len(self.tg_.tiles())

    def getTotalRudyOverflow(self) -> float:
        return self.total_route_overflow_

    def isMinRc(self) -> bool:
        return self.is_min_rc_

    def routability(self, routability_driven_revert_count: int) -> Tuple[bool, bool]:
        raise NotImplementedError("OpenROAD routability-driven inflation loop has not been translated yet")

    def updateInflationRatio(self) -> None:
        raise NotImplementedError("OpenROAD routability inflation-ratio update has not been translated yet")

    def updateGCellSize(self) -> None:
        raise NotImplementedError("OpenROAD routability gcell size update has not been translated yet")

    def revertGCellSizeToMinRc(self) -> None:
        if not self.minRcCellSizes_:
            return
        for nb in self.nbVec_:
            for gcell in nb.getGCells():
                saved = self.minRcCellSizes_.get(id(gcell))
                if saved is None:
                    continue
                dx, dy = saved
                gcell.setSize(dx, dy, GCellChange.kRoutability)
            nb.updateAreas()
        if self.minRcTargetDensity_:
            for nb, target_density in zip(self.nbVec_, self.minRcTargetDensity_):
                nb.setTargetDensity(target_density)
        self.revert_count_ += 1

    def saveMinRc(self) -> None:
        self.minRcTargetDensity_ = [nb.getTargetDensity() for nb in self.nbVec_]
        self.minRcInflatedAreaDelta_ = list(self.inflatedAreaDelta_)
        self.minRcCellSizes_ = {
            id(gcell): (gcell.dx(), gcell.dy())
            for nb in self.nbVec_
            for gcell in nb.getGCells()
        }

    def resetMinRc(self) -> None:
        self.minRc_ = 1e30
        self.is_min_rc_ = False
        self.minRcTargetDensity_.clear()
        self.minRcInflatedAreaDelta_.clear()
        self.minRcCellSizes_.clear()

    def inflatedAreaDelta(self) -> List[int]:
        return self.inflatedAreaDelta_

    def getTotalInflation(self) -> int:
        return sum(self.inflatedAreaDelta_)

    def getRevertCount(self) -> int:
        return self.revert_count_

    def saveRcMetric(self, rc: Optional[float] = None) -> None:
        value = self.getRC() if rc is None else rc
        self.rc_metric_.append(value)
        if value < self.minRc_:
            self.minRc_ = value
            self.is_min_rc_ = True
            self.saveMinRc()
        else:
            self.is_min_rc_ = False

    def saveRouteOverflow(self, overflow: Optional[float] = None) -> None:
        value = self.total_route_overflow_ if overflow is None else overflow
        self.route_overflow_.append(value)

    def saveRouteUtilization(self, utilization: float) -> None:
        self.route_utilization_.append(utilization)

    def getRcMetricHistory(self) -> List[float]:
        return self.rc_metric_

    def getRouteOverflowHistory(self) -> List[float]:
        return self.route_overflow_

    def getRouteUtilizationHistory(self) -> List[float]:
        return self.route_utilization_

    def reportCongestion(self) -> Dict[str, Any]:
        return {
            "use_rudy": self.rbVars_.useRudy,
            "rc": self.final_average_rc_,
            "min_rc": self.minRc_,
            "target_rc": self.rbVars_.targetRC,
            "overflowed_tiles": self.overflowed_tiles_count_,
            "total_tiles": self.getTotalTilesCount(),
            "total_route_overflow": self.total_route_overflow_,
            "total_inflation": self.getTotalInflation(),
            "revert_count": self.revert_count_,
            "is_min_rc": self.is_min_rc_,
            "rc_history": list(self.rc_metric_),
            "overflow_history": list(self.route_overflow_),
            "utilization_history": list(self.route_utilization_),
        }


