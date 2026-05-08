"""Routability boundary for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, floor, pow, sqrt
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..odb import DbDatabase
from .common import _area
from .nesterov import GCell, GCellChange, NesterovBase, NesterovBaseCommon
from .options import PlaceOptions


def _logger_call(log: Any, level: str, *args: Any, **kwargs: Any) -> None:
    method = getattr(log, level, None)
    if callable(method):
        try:
            method(*args, **kwargs)
        except Exception:
            pass


def _debug_print(log: Any, *args: Any, **kwargs: Any) -> None:
    method = getattr(log, "debugPrint", None)
    if callable(method):
        try:
            method(*args, **kwargs)
        except Exception:
            pass


def _is_horizontal_layer(layer: Any) -> bool:
    direction = getattr(layer, "getDirection", None)
    value = direction() if callable(direction) else direction
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name.upper() == "HORIZONTAL"
    text = str(value).upper()
    return "HORIZONTAL" in text


def _call_optional(obj: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    method = getattr(obj, name, None)
    if callable(method):
        return method(*args, **kwargs)
    return None


def _db_chip(db: Optional[DbDatabase]) -> Any:
    if db is None:
        return None
    getter = getattr(db, "getChip", None)
    return getter() if callable(getter) else getattr(db, "chip", None)


def _db_block(db: Optional[DbDatabase]) -> Any:
    chip = _db_chip(db)
    if chip is None:
        return None
    getter = getattr(chip, "getBlock", None)
    if callable(getter):
        return getter()
    getter = getattr(chip, "get_top_block", None)
    if callable(getter):
        return getter()
    return getattr(chip, "block", None)


def _db_tech(db: Optional[DbDatabase]) -> Any:
    if db is None:
        return None
    getter = getattr(db, "getTech", None)
    return getter() if callable(getter) else getattr(db, "tech", None)


def _dbu_area_to_microns(block: Any, area: int) -> float:
    if block is None:
        return float(area)
    method = getattr(block, "dbuAreaToMicrons", None)
    if callable(method):
        try:
            return float(method(area))
        except Exception:
            pass
    return float(area)


@dataclass
class RouteBaseVars:
    useRudy: bool = True
    targetRC: float = 1.01
    inflationRatioCoef: float = 3.0
    maxInflationRatio: float = 6.0
    maxDensity: float = 0.90
    ignoreEdgeRatio: float = 0.8
    minInflationRatio: float = 1.01
    rcK1: float = 1.0
    rcK2: float = 1.0
    rcK3: float = 0.0
    rcK4: float = 0.0
    maxInflationIter: int = 4

    @classmethod
    def from_options(cls, options: PlaceOptions) -> "RouteBaseVars":
        return cls(
            useRudy=options.routabilityUseRudy,
            targetRC=options.routabilityTargetRcMetric,
            inflationRatioCoef=options.routabilityInflationRatioCoef,
            maxInflationRatio=options.routabilityMaxInflationRatio,
            maxDensity=options.routabilityMaxDensity,
            ignoreEdgeRatio=getattr(options, "routabilityIgnoreEdgeRatio", 0.8),
            minInflationRatio=getattr(options, "routabilityMinInflationRatio", 1.01),
            rcK1=options.routabilityRcK1,
            rcK2=options.routabilityRcK2,
            rcK3=options.routabilityRcK3,
            rcK4=options.routabilityRcK4,
            maxInflationIter=getattr(options, "routabilityMaxInflationIter", 4),
        )

    def reset(self) -> None:
        self.useRudy = True
        self.targetRC = 1.01
        self.inflationRatioCoef = 3.0
        self.maxInflationRatio = 6.0
        self.maxDensity = 0.90
        self.ignoreEdgeRatio = 0.8
        self.minInflationRatio = 1.01
        self.rcK1 = 1.0
        self.rcK2 = 1.0
        self.rcK3 = 0.0
        self.rcK4 = 0.0
        self.maxInflationIter = 4


@dataclass
class Tile:
    x_: int = 0
    y_: int = 0
    lx_: int = 0
    ly_: int = 0
    ux_: int = 0
    uy_: int = 0
    layers_: int = 0
    inflationRatio_: float = 1.0
    inflatedRatio_: float = 0.0

    def x(self) -> int:
        return self.x_

    def y(self) -> int:
        return self.y_

    def lx(self) -> int:
        return self.lx_

    def ly(self) -> int:
        return self.ly_

    def ux(self) -> int:
        return self.ux_

    def uy(self) -> int:
        return self.uy_

    def area(self) -> int:
        return _area((self.lx_, self.ly_, self.ux_, self.uy_))

    def inflationRatio(self) -> float:
        return self.inflationRatio_

    def inflatedRatio(self) -> float:
        return self.inflatedRatio_

    def setInflationRatio(self, ratio: float) -> None:
        self.inflationRatio_ = float(ratio)

    def setInflatedRatio(self, ratio: float) -> None:
        self.inflatedRatio_ = float(ratio)


@dataclass
class TileGrid:
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
        self.tileCntX_ = tileCntX
        self.tileCntY_ = tileCntY

    def setTileCntX(self, tileCntX: int) -> None:
        self.tileCntX_ = tileCntX

    def setTileCntY(self, tileCntY: int) -> None:
        self.tileCntY_ = tileCntY

    def setTileSize(self, tileSizeX: int, tileSizeY: int) -> None:
        self.tileSizeX_ = tileSizeX
        self.tileSizeY_ = tileSizeY

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

    def getTile(self, x: int, y: int) -> Optional[Tile]:
        if x < 0 or y < 0 or x >= self.tileCntX_ or y >= self.tileCntY_:
            return None
        index = y * self.tileCntX_ + x
        if index >= len(self.tiles_):
            return None
        return self.tiles_[index]

    def initTiles(self, use_rudy: bool) -> None:
        del use_rudy
        self.tileStor_.clear()
        self.tiles_.clear()
        for y in range(max(0, self.tileCntY_)):
            for x in range(max(0, self.tileCntX_)):
                lx = self.lx_ + x * self.tileSizeX_
                ly = self.ly_ + y * self.tileSizeY_
                tile = Tile(x, y, lx, ly, lx + self.tileSizeX_, ly + self.tileSizeY_, self.numRoutingLayers_)
                self.tileStor_.append(tile)
                self.tiles_.append(tile)

    def reportStatus(self) -> Dict[str, Any]:
        return {
            "tile_count": len(self.tiles_),
            "tile_count_x": self.tileCntX_,
            "tile_count_y": self.tileCntY_,
            "tile_size_x": self.tileSizeX_,
            "tile_size_y": self.tileSizeY_,
            "origin": (self.lx_, self.ly_),
            "box": (self.lx(), self.ly(), self.ux(), self.uy()),
            "routing_layers": self.numRoutingLayers_,
            "average_congestion": self.averageCongestion(),
            "overflowed_tiles": sum(1 for tile in self.tiles_ if tile.inflationRatio() > 1.0),
        }

    def averageCongestion(self) -> float:
        if not self.tiles_:
            return 0.0
        total = 0.0
        count = 0
        for tile in self.tiles_:
            total += tile.inflationRatio()
            count += 1
        return total / count if count else 0.0

    def heatmap(self) -> List[List[float]]:
        return [
            [self.getTile(x, y).inflationRatio() if self.getTile(x, y) is not None else 0.0 for x in range(self.tileCntX_)]
            for y in range(self.tileCntY_)
        ]


class RouteBase:
    def __init__(
        self,
        rbVars: Optional[RouteBaseVars] = None,
        db: Optional[DbDatabase] = None,
        grouter: Any = None,
        nbc: Optional[NesterovBaseCommon] = None,
        nbVec: Optional[Sequence[NesterovBase]] = None,
        log: Any = None,
    ):
        self.rbVars_ = rbVars or RouteBaseVars()
        self.db_ = db
        self.grouter_ = grouter
        self.nbc_ = nbc
        self.nbVec_ = list(nbVec or [])
        self.log_ = log
        self.tg_: Optional[TileGrid] = None
        self.inflatedAreaDelta_ = 0
        self.numCall_ = 0
        self.minRc_ = 1e30
        self.minRcTargetDensity_ = 0.0
        self.minRcViolatedCnt_ = 0
        self._min_rc_cell_sizes: Dict[int, Tuple[int, int]] = {}
        self._saved_fillers: List[Any] = []
        self._saved_tile_inflation: Dict[Tuple[int, int], float] = {}
        self.finalRC_ = 0.0
        self.init()

    def init(self) -> None:
        self.tg_ = TileGrid()
        self.tg_.setLogger(self.log_)
        _call_optional(self.nbc_, "resizeMinRcCellSize")

    def initRouteBase(self) -> None:
        self.init()

    def updateGrtRoute(self) -> None:
        if self.grouter_ is None:
            return
        _call_optional(self.grouter_, "globalRoute")

    def getGrtResult(self) -> None:
        _call_optional(self.nbc_, "updateDbGCells")
        if self.grouter_ is None:
            return
        _call_optional(self.grouter_, "setAllowCongestion", True)
        _call_optional(self.grouter_, "setCongestionIterations", 0)
        _call_optional(self.grouter_, "setCriticalNetsPercentage", 0)
        _call_optional(self.grouter_, "globalRoute")
        self.updateGrtRoute()

    def loadGrt(self) -> None:
        if self.grouter_ is None:
            return
        _call_optional(self.grouter_, "setAllowCongestion", True)
        _call_optional(self.grouter_, "setCongestionIterations", 0)
        _call_optional(self.grouter_, "setCriticalNetsPercentage", 0)
        _call_optional(self.grouter_, "globalRoute")

    def getGrtRC(self) -> float:
        if self.db_ is None or self.grouter_ is None or self.tg_ is None:
            return 0.0
        block = _db_block(self.db_)
        tech = _db_tech(self.db_)
        gGrid = getattr(block, "getGCellGrid", lambda: None)() if block is not None else None
        if gGrid is None or tech is None:
            return 0.0
        numLayers = getattr(tech, "getRoutingLayerCount", lambda: 0)()
        self.tg_.setNumRoutingLayers(numLayers)
        gridX: List[int] = []
        gridY: List[int] = []
        getattr(gGrid, "getGridX", lambda out: None)(gridX)
        getattr(gGrid, "getGridY", lambda out: None)(gridY)
        if len(gridX) < 2 or len(gridY) < 2:
            return 0.0
        self.tg_.setLx(gridX[0])
        self.tg_.setLy(gridY[0])
        self.tg_.setTileSize(gridX[1] - gridX[0], gridY[1] - gridY[0])
        self.tg_.setTileCnt(len(gridX), len(gridY))
        self.tg_.initTiles(self.rbVars_.useRudy)

        min_routing_layer, max_routing_layer = _call_optional(self.grouter_, "getMinMaxLayer") or (1, numLayers)
        hor_edge: List[float] = []
        ver_edge: List[float] = []
        total_h = 0.0
        total_v = 0.0
        overflow_cnt = 0
        for tile in self.tg_.tiles():
            for i in range(1, self.tg_.numRoutingLayers() + 1):
                layer = _call_optional(tech, "findRoutingLayer", i)
                if layer is None:
                    continue
                ratio = self._getUsageCapacityRatio(tile, layer, gGrid, self.grouter_, self.rbVars_.ignoreEdgeRatio)
                if i < min_routing_layer or i > max_routing_layer:
                    ratio = 0.0
                if ratio >= 0.0:
                    if _is_horizontal_layer(layer):
                        total_h += max(0.0, -1.0 + ratio)
                        hor_edge.append(ratio)
                    else:
                        total_v += max(0.0, -1.0 + ratio)
                        ver_edge.append(ratio)
                    if ratio > 1.0:
                        overflow_cnt += 1
        self._log_grt_rc(total_h, total_v, overflow_cnt, hor_edge, ver_edge)
        self.finalRC_ = self._weighted_grt_rc(hor_edge, ver_edge)
        return self.finalRC_

    def updateRudyRoute(self) -> None:
        if self.grouter_ is None or self.tg_ is None:
            return
        rudy = _call_optional(self.grouter_, "getRudy")
        if rudy is None:
            return
        _call_optional(rudy, "calculateRudy")
        self.tg_.setNumRoutingLayers(0)
        self.tg_.setLx(0)
        self.tg_.setLy(0)
        tile_size = _call_optional(rudy, "getTileSize") or 0
        self.tg_.setTileSize(tile_size, tile_size)
        x_grids, y_grids = _call_optional(self.grouter_, "getGridSize") or (0, 0)
        self.tg_.setTileCnt(x_grids, y_grids)
        self.tg_.initTiles(self.rbVars_.useRudy)
        for tile in self.tg_.tiles():
            tile_obj = _call_optional(rudy, "getTile", tile.x(), tile.y())
            if tile_obj is None:
                continue
            ratio = float(_call_optional(tile_obj, "getRudy") or 0.0) / 100.0
            if ratio >= self.rbVars_.minInflationRatio:
                inflationRatio = pow(ratio, self.rbVars_.inflationRatioCoef)
                inflationRatio = min(inflationRatio, self.rbVars_.maxInflationRatio)
                tile.setInflationRatio(inflationRatio)

    def getRudyResult(self) -> None:
        _call_optional(self.nbc_, "updateDbGCells")
        self.updateRudyRoute()

    def getRudyRC(self) -> float:
        if self.grouter_ is None or self.tg_ is None:
            return 0.0
        rudy = _call_optional(self.grouter_, "getRudy")
        if rudy is None:
            return 0.0
        totalRouteOverflow = 0.0
        overflowTileCnt = 0
        edgeCongArray: List[float] = []
        for tile in self.tg_.tiles():
            tile_obj = _call_optional(rudy, "getTile", tile.x(), tile.y())
            if tile_obj is None:
                continue
            ratio = float(_call_optional(tile_obj, "getRudy") or 0.0) / 100.0
            if ratio >= 0.0:
                totalRouteOverflow += max(0.0, -1.0 + ratio)
                edgeCongArray.append(ratio)
                if ratio > 1.0:
                    overflowTileCnt += 1
        _logger_call(self.log_, "info", "GPL", 41, "Total routing overflow: {:.4f}", totalRouteOverflow)
        _logger_call(
            self.log_,
            "info",
            "GPL",
            42,
            "Number of overflowed tiles: {} ({:.2f}%)",
            overflowTileCnt,
            (float(overflowTileCnt) / len(self.tg_.tiles())) * 100 if self.tg_.tiles() else 0.0,
        )
        avg005RC, avg010RC, avg020RC, avg050RC = self._top_rc_averages(edgeCongArray)
        _logger_call(self.log_, "info", "GPL", 43, "Average top 0.5% routing congestion: {:.4f}", avg005RC)
        _logger_call(self.log_, "info", "GPL", 44, "Average top 1.0% routing congestion: {:.4f}", avg010RC)
        _logger_call(self.log_, "info", "GPL", 45, "Average top 2.0% routing congestion: {:.4f}", avg020RC)
        _logger_call(self.log_, "info", "GPL", 46, "Average top 5.0% routing congestion: {:.4f}", avg050RC)
        finalRC = self._weighted_rudy_rc(avg005RC, avg010RC, avg020RC, avg050RC)
        _logger_call(self.log_, "info", "GPL", 47, "Routability iteration weighted routing congestion: {:.4f}", finalRC)
        self.finalRC_ = finalRC
        return finalRC

    def routability(self, routability_driven_revert_count: int = 0) -> Tuple[bool, bool]:
        self.increaseCounter()
        self.init()
        if self.tg_ is None:
            self.init()
        curRc = 0.0
        if self.rbVars_.useRudy:
            self.getRudyResult()
            curRc = self.getRudyRC()
        else:
            self.getGrtResult()
            curRc = self.getGrtRC()
        if curRc < self.rbVars_.targetRC:
            _logger_call(
                self.log_,
                "info",
                "GPL",
                50,
                "Weighted routing congestion is lower than target routing congestion({:.4f}), end routability optimization.",
                self.rbVars_.targetRC,
            )
            self.resetRoutabilityResources()
            return False, False
        if (self.minRc_ - curRc) > 0.001:
            _logger_call(
                self.log_,
                "info",
                "GPL",
                48,
                "Routing congestion ({:.4f}) lower than previous minimum ({:.4g}). Updating minimum.",
                curRc,
                self.minRc_,
            )
            self.minRc_ = curRc
            if self.nbVec_:
                self.minRcTargetDensity_ = self.nbVec_[0].getTargetDensity()
            self.minRcViolatedCnt_ = 0
            _call_optional(self.nbVec_[0] if self.nbVec_ else None, "clearRemovedFillers")
            self._save_min_rc_cell_sizes()
        else:
            self.minRcViolatedCnt_ += 1
            _logger_call(
                self.log_,
                "info",
                "GPL",
                49,
                "Routing congestion ({:.4f}) higher than minimum ({:.4f}). Consecutive non-improvement count: {}.",
                curRc,
                self.minRc_,
                self.minRcViolatedCnt_,
            )
        for tile in self.tg_.tiles():
            tile.setInflatedRatio(tile.inflationRatio() if tile.inflationRatio() > 1.0 else 1.0)
        self.inflatedAreaDelta_ = 0
        if self.nbc_ is not None:
            for gCell in self.nbc_.getGCells():
                if not gCell.isStdInstance():
                    continue
                idxX = min((gCell.dCx() - self.tg_.lx()) // max(1, self.tg_.tileSizeX()), self.tg_.tileCntX() - 1)
                idxY = min((gCell.dCy() - self.tg_.ly()) // max(1, self.tg_.tileSizeY()), self.tg_.tileCntY() - 1)
                index = idxY * self.tg_.tileCntX() + idxX
                if index >= len(self.tg_.tiles()):
                    continue
                tile = self.tg_.tiles()[index]
                if tile.inflatedRatio() <= 1.0:
                    continue
                prevCellArea = int(gCell.dx()) * int(gCell.dy())
                gCell.setSize(
                    int(round(gCell.dx() * sqrt(tile.inflatedRatio()))),
                    int(round(gCell.dy() * sqrt(tile.inflatedRatio()))),
                    GCellChange.kRoutability,
                )
                newCellArea = int(gCell.dx()) * int(gCell.dy())
                self.inflatedAreaDelta_ += newCellArea - prevCellArea
        block = _db_block(self.db_)
        inflated_area_delta_microns = _dbu_area_to_microns(block, self.inflatedAreaDelta_)
        nbc = self.nbVec_[0] if self.nbVec_ else None
        inst_area = max(1, nbc.nesterovInstsArea() if nbc is not None else 1)
        inflated_area_delta_percentage = (float(self.inflatedAreaDelta_) / inst_area) * 100.0
        _logger_call(self.log_, "info", "GPL", 51, "Inflated area: {}", inflated_area_delta_microns)
        _logger_call(self.log_, "info", "GPL", 52, "Placement target density: {:.4f}", nbc.getTargetDensity() if nbc else 0.0)
        prev_white_space_area = nbc.whiteSpaceArea() if nbc else 0.0
        prev_movable_area = nbc.movableArea() if nbc else 0.0
        prev_total_filler_area = nbc.getTotalFillerArea() if nbc else 0.0
        prev_total_gcells_area = (nbc.nesterovInstsArea() + nbc.getTotalFillerArea()) if nbc else 0.0
        prev_expected_gcells_area = self.inflatedAreaDelta_ + prev_total_gcells_area
        if nbc is not None:
            nbc.cutFillerCells(self.inflatedAreaDelta_)
        if nbc is not None and (
            nbc.getTargetDensity() > self.rbVars_.maxDensity or self.minRcViolatedCnt_ >= 3
        ):
            if nbc.getTargetDensity() > self.rbVars_.maxDensity:
                _logger_call(
                    self.log_,
                    "info",
                    "GPL",
                    53,
                    "Target density {:.4f} exceeds the maximum allowed {:.4f}.",
                    nbc.getTargetDensity(),
                    self.rbVars_.maxDensity,
                )
            if self.minRcViolatedCnt_ >= 3:
                _logger_call(
                    self.log_,
                    "info",
                    "GPL",
                    54,
                    "No improvement in routing congestion for {} consecutive iterations (limit is 3).",
                    self.minRcViolatedCnt_,
                )
            _logger_call(
                self.log_,
                "info",
                "GPL",
                55,
                "Reverting inflation values and target density from the iteration with minimum observed routing congestion.",
            )
            _logger_call(self.log_, "info", "GPL", 56, "Minimum observed routing congestion: {:.4f}", self.minRc_)
            _logger_call(
                self.log_,
                "info",
                "GPL",
                57,
                "Target density at minimum routing congestion: {:.4f}",
                self.minRcTargetDensity_,
            )
            nbc.setTargetDensity(self.minRcTargetDensity_)
            self.revertGCellSizeToMinRc()
            _call_optional(nbc, "restoreRemovedFillers")
            nbc.updateDensitySize()
            self.resetRoutabilityResources()
            return False, True
        if nbc is not None:
            nbc.updateAreas()
        new_total_gcells_area = (nbc.nesterovInstsArea() + nbc.getTotalFillerArea()) if nbc else 0.0
        new_expected_gcells_area = self.inflatedAreaDelta_ + new_total_gcells_area
        _logger_call(
            self.log_,
            "info",
            "GPL",
            58,
            "White space area: {}",
            _dbu_area_to_microns(block, int(nbc.whiteSpaceArea()) if nbc else 0),
        )
        _logger_call(
            self.log_,
            "info",
            "GPL",
            59,
            "Movable instances area: {}",
            _dbu_area_to_microns(block, int(nbc.movableArea()) if nbc else 0),
        )
        _logger_call(
            self.log_,
            "info",
            "GPL",
            60,
            "Total filler area: {}",
            _dbu_area_to_microns(block, int(nbc.getTotalFillerArea()) if nbc else 0),
        )
        _logger_call(
            self.log_,
            "info",
            "GPL",
            61,
            "Total non-inflated area: {}",
            _dbu_area_to_microns(block, int(new_total_gcells_area)),
        )
        _logger_call(
            self.log_,
            "info",
            "GPL",
            62,
            "Total inflated area: {}",
            _dbu_area_to_microns(block, int(new_expected_gcells_area)),
        )
        _logger_call(self.log_, "info", "GPL", 63, "New Target Density: {:.4f}", nbc.getTargetDensity() if nbc else 0.0)
        if nbc is not None:
            nbc.updateDensitySize()
        self.resetRoutabilityResources()
        return True, True

    def resetRoutabilityResources(self) -> None:
        self.inflatedAreaDelta_ = 0
        if not self.rbVars_.useRudy and self.grouter_ is not None:
            _call_optional(self.grouter_, "clear")
        if self.tg_ is not None:
            self.tg_.tileStor_.clear()
            self.tg_.tiles_.clear()

    def increaseCounter(self) -> None:
        self.numCall_ += 1
        _logger_call(self.log_, "info", "GPL", 40, "Routability iteration: {}", self.numCall_)

    def inflatedAreaDelta(self) -> int:
        return self.inflatedAreaDelta_

    def numCall(self) -> int:
        return self.numCall_

    def getRudyAverage(self) -> float:
        return self.finalRC_

    def getRC(self) -> float:
        return self.getRudyAverage() if self.rbVars_.useRudy else self.getGrtRC()

    def getTotalRudyOverflow(self) -> float:
        return self._total_route_overflow()

    def getOverflowedTilesCount(self) -> int:
        if self.tg_ is None:
            return 0
        return sum(1 for tile in self.tg_.tiles() if tile.inflationRatio() > 1.0)

    def getTotalTilesCount(self) -> int:
        return len(self.tg_.tiles()) if self.tg_ is not None else 0

    def reportCongestion(self) -> Dict[str, Any]:
        return {
            "use_rudy": self.rbVars_.useRudy,
            "rc": self.finalRC_,
            "min_rc": self.minRc_,
            "target_rc": self.rbVars_.targetRC,
            "inflated_area_delta": self.inflatedAreaDelta_,
            "num_call": self.numCall_,
            "min_rc_target_density": self.minRcTargetDensity_,
            "min_rc_violated_cnt": self.minRcViolatedCnt_,
            "tile_grid": self.tg_.reportStatus() if self.tg_ is not None else {},
        }

    def reportRoutability(self) -> Dict[str, Any]:
        return self.reportCongestion()

    def _save_min_rc_cell_sizes(self) -> None:
        self._min_rc_cell_sizes = {}
        if self.nbc_ is None:
            return
        for gcell in self.nbc_.getGCells():
            self._min_rc_cell_sizes[id(gcell)] = (gcell.dx(), gcell.dy())

    def revertGCellSizeToMinRc(self) -> None:
        if self.nbc_ is None or not self._min_rc_cell_sizes:
            return
        for gcell in self.nbc_.getGCells():
            saved = self._min_rc_cell_sizes.get(id(gcell))
            if saved is None:
                continue
            gcell.setSize(saved[0], saved[1], GCellChange.kRoutability)

    def _getUsageCapacityRatio(
        self,
        tile: Tile,
        layer: Any,
        gGrid: Any,
        grouter: Any,
        ignoreEdgeRatio: float,
    ) -> float:
        blockH = 0
        blockV = 0
        blockage = _call_optional(grouter, "getBlockage", layer, tile.x(), tile.y())
        if isinstance(blockage, tuple) and len(blockage) == 2:
            blockH, blockV = blockage
        isHorizontal = _is_horizontal_layer(layer)
        curCap = _call_optional(gGrid, "getCapacity", layer, tile.x(), tile.y()) or 0
        curUse = _call_optional(gGrid, "getUsage", layer, tile.x(), tile.y()) or 0
        blockage_val = blockH if isHorizontal else blockV
        if curCap == 0:
            return float("-inf")
        blockageRatio = float(blockage_val) / float(curCap)
        if blockageRatio >= ignoreEdgeRatio:
            return float("-inf")
        return float(curUse) / float(curCap)

    def _top_rc_averages(self, edgeCongArray: List[float]) -> Tuple[float, float, float, float]:
        if not edgeCongArray:
            return 0.0, 0.0, 0.0, 0.0
        sorted_edges = sorted(edgeCongArray, reverse=True)
        return (
            self._avg_top(sorted_edges, 0.005),
            self._avg_top(sorted_edges, 0.01),
            self._avg_top(sorted_edges, 0.02),
            self._avg_top(sorted_edges, 0.05),
        )

    def _avg_top(self, values: List[float], fraction: float) -> float:
        count = len(values)
        limit = int(floor(fraction * count))
        total = 0.0
        for i, value in enumerate(values):
            if i < fraction * count:
                total += value
        denom = int(ceil(fraction * count))
        return total / denom if denom > 0 else 0.0

    def _weighted_rudy_rc(self, avg005RC: float, avg010RC: float, avg020RC: float, avg050RC: float) -> float:
        denom = self.rbVars_.rcK1 + self.rbVars_.rcK2 + self.rbVars_.rcK3 + self.rbVars_.rcK4
        if denom == 0:
            return 0.0
        return (
            self.rbVars_.rcK1 * avg005RC
            + self.rbVars_.rcK2 * avg010RC
            + self.rbVars_.rcK3 * avg020RC
            + self.rbVars_.rcK4 * avg050RC
        ) / denom

    def _weighted_grt_rc(self, horEdgeCongArray: List[float], verEdgeCongArray: List[float]) -> float:
        hor005, hor010, hor020, hor050 = self._top_rc_averages(horEdgeCongArray)
        ver005, ver010, ver020, ver050 = self._top_rc_averages(verEdgeCongArray)
        _logger_call(self.log_, "info", "GPL", 67, "0.5%RC: {:.4f}", max(hor005, ver005))
        _logger_call(self.log_, "info", "GPL", 68, "1.0%RC: {:.4f}", max(hor010, ver010))
        _logger_call(self.log_, "info", "GPL", 69, "2.0%RC: {:.4f}", max(hor020, ver020))
        _logger_call(self.log_, "info", "GPL", 70, "5.0%RC: {:.4f}", max(hor050, ver050))
        _logger_call(self.log_, "info", "GPL", 71, "0.5rcK: {:.2f}", self.rbVars_.rcK1)
        _logger_call(self.log_, "info", "GPL", 72, "1.0rcK: {:.2f}", self.rbVars_.rcK2)
        _logger_call(self.log_, "info", "GPL", 73, "2.0rcK: {:.2f}", self.rbVars_.rcK3)
        _logger_call(self.log_, "info", "GPL", 74, "5.0rcK: {:.2f}", self.rbVars_.rcK4)
        denom = self.rbVars_.rcK1 + self.rbVars_.rcK2 + self.rbVars_.rcK3 + self.rbVars_.rcK4
        if denom == 0:
            return 0.0
        finalRC = (
            self.rbVars_.rcK1 * max(hor005, ver005)
            + self.rbVars_.rcK2 * max(hor010, ver010)
            + self.rbVars_.rcK3 * max(hor020, ver020)
            + self.rbVars_.rcK4 * max(hor050, ver050)
        ) / denom
        _logger_call(self.log_, "info", "GPL", 75, "Final routing congestion: {}", finalRC)
        return finalRC

    def _log_grt_rc(self, total_h: float, total_v: float, overflow_cnt: int, hor_edge: List[float], ver_edge: List[float]) -> None:
        _logger_call(self.log_, "info", "GPL", 64, "TotalRouteOverflowH2: {:.4f}", total_h)
        _logger_call(self.log_, "info", "GPL", 65, "TotalRouteOverflowV2: {:.4f}", total_v)
        _logger_call(self.log_, "info", "GPL", 66, "OverflowTileCnt2: {}", overflow_cnt)

    def _total_route_overflow(self) -> float:
        if self.tg_ is None:
            return 0.0
        return sum(max(0.0, tile.inflationRatio() - 1.0) for tile in self.tg_.tiles())
