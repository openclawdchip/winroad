"""Routability boundary for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, floor, sqrt
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..odb import DbDatabase
from .common import _area
from .nesterov import GCell, GCellChange, NesterovBase, NesterovBaseCommon
from .options import PlaceOptions


class GrtAdapterError(RuntimeError):
    """Structured failure for injected global-router boundaries."""

    def __init__(self, stage: str, message: str, *, method: Optional[str] = None, cause: Optional[BaseException] = None):
        self.stage = stage
        self.method = method
        self.cause = cause
        detail = {"stage": stage, "message": message}
        if method is not None:
            detail["method"] = method
        if cause is not None:
            detail["cause"] = f"{type(cause).__name__}: {cause}"
        self.detail = detail
        super().__init__(str(detail))


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
    routeDemand_: float = 0.0
    routeCapacity_: float = 0.0
    routeOverflow_: float = 0.0
    horizontalDemand_: float = 0.0
    verticalDemand_: float = 0.0

    def area(self) -> int:
        return _area((self.lx_, self.ly_, self.ux_, self.uy_))

    def dx(self) -> int:
        return max(0, self.ux_ - self.lx_)

    def dy(self) -> int:
        return max(0, self.uy_ - self.ly_)

    def inflationRatio(self) -> float:
        return self.inflationRatio_

    def inflatedRatio(self) -> float:
        return self.inflatedRatio_

    def setInflationRatio(self, ratio: float) -> None:
        self.inflationRatio_ = ratio

    def setInflatedRatio(self, ratio: float) -> None:
        self.inflatedRatio_ = ratio

    def resetRouteDemand(self) -> None:
        self.routeDemand_ = 0.0
        self.routeOverflow_ = 0.0
        self.horizontalDemand_ = 0.0
        self.verticalDemand_ = 0.0

    def addRouteDemand(self, demand: float, horizontal: float = 0.0, vertical: float = 0.0) -> None:
        self.routeDemand_ += max(0.0, demand)
        self.horizontalDemand_ += max(0.0, horizontal)
        self.verticalDemand_ += max(0.0, vertical)

    def setRouteCapacity(self, capacity: float) -> None:
        self.routeCapacity_ = max(0.0, capacity)

    def updateOverflow(self) -> float:
        self.routeOverflow_ = max(0.0, self.routeDemand_ - self.routeCapacity_)
        return self.routeOverflow_

    def congestion(self) -> float:
        return self.routeDemand_ / self.routeCapacity_ if self.routeCapacity_ > 0.0 else 0.0

    def report(self) -> Dict[str, Any]:
        """导出 tile 状态，真实 RUDY/GR 计算仍由未翻译入口负责。"""

        return {
            "index": (self.x_, self.y_),
            "box": (self.lx_, self.ly_, self.ux_, self.uy_),
            "layers": self.layers_,
            "area": self.area(),
            "inflation_ratio": self.inflationRatio_,
            "inflated_ratio": self.inflatedRatio_,
            "route_demand": self.routeDemand_,
            "route_capacity": self.routeCapacity_,
            "route_overflow": self.routeOverflow_,
            "horizontal_demand": self.horizontalDemand_,
            "vertical_demand": self.verticalDemand_,
            "congestion": self.congestion(),
        }


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

    def getTile(self, x: int, y: int) -> Optional[Tile]:
        if x < 0 or y < 0 or x >= self.tileCntX_ or y >= self.tileCntY_:
            return None
        index = y * self.tileCntX_ + x
        if index >= len(self.tiles_):
            return None
        return self.tiles_[index]

    def initTiles(self, use_rudy: bool) -> None:
        self.tileStor_.clear()
        for y in range(max(0, self.tileCntY_)):
            for x in range(max(0, self.tileCntX_)):
                lx = self.lx_ + x * self.tileSizeX_
                ly = self.ly_ + y * self.tileSizeY_
                self.tileStor_.append(Tile(x, y, lx, ly, lx + self.tileSizeX_, ly + self.tileSizeY_, self.numRoutingLayers_))
        self.tiles_ = list(self.tileStor_)

    def resetRouteDemand(self) -> None:
        for tile in self.tiles_:
            tile.resetRouteDemand()

    def setDefaultCapacity(self) -> None:
        for tile in self.tiles_:
            # Python 层没有 routing-track 数据时，用 tile 面积乘 routing layer 数作为
            # 归一化容量；RUDY demand 使用同一面积单位，报告值可稳定比较。
            tile.setRouteCapacity(float(tile.area() * max(1, tile.layers_ or self.numRoutingLayers_ or 1)))
            tile.updateOverflow()

    def iterOverlappingTiles(self, lx: int, ly: int, ux: int, uy: int) -> List[Tile]:
        if not self.tiles_ or self.tileSizeX_ <= 0 or self.tileSizeY_ <= 0:
            return []
        gx0 = max(0, min(self.tileCntX_ - 1, floor((lx - self.lx_) / self.tileSizeX_)))
        gy0 = max(0, min(self.tileCntY_ - 1, floor((ly - self.ly_) / self.tileSizeY_)))
        gx1 = max(0, min(self.tileCntX_ - 1, floor((max(lx, ux - 1) - self.lx_) / self.tileSizeX_)))
        gy1 = max(0, min(self.tileCntY_ - 1, floor((max(ly, uy - 1) - self.ly_) / self.tileSizeY_)))
        result: List[Tile] = []
        for y in range(gy0, gy1 + 1):
            for x in range(gx0, gx1 + 1):
                tile = self.getTile(x, y)
                if tile is not None:
                    result.append(tile)
        return result

    def reportStatus(self, sample_limit: int = 0) -> Dict[str, Any]:
        """导出 tile grid 几何配置，供 RouteBase 报告和 smoke 使用。"""

        report: Dict[str, Any] = {
            "tile_count": len(self.tiles_),
            "tile_count_x": self.tileCntX_,
            "tile_count_y": self.tileCntY_,
            "tile_size_x": self.tileSizeX_,
            "tile_size_y": self.tileSizeY_,
            "origin": (self.lx_, self.ly_),
            "box": (self.lx(), self.ly(), self.ux(), self.uy()),
            "routing_layers": self.numRoutingLayers_,
            "average_congestion": self.averageCongestion(),
            "overflowed_tiles": sum(1 for tile in self.tiles_ if tile.routeOverflow_ > 0.0),
        }
        if sample_limit > 0:
            report["sample_tiles"] = [tile.report() for tile in self.tiles_[:sample_limit]]
        return report

    def heatmap(self) -> List[List[float]]:
        return [
            [self.getTile(x, y).congestion() if self.getTile(x, y) is not None else 0.0 for x in range(self.tileCntX_)]
            for y in range(self.tileCntY_)
        ]

    def averageCongestion(self) -> float:
        if not self.tiles_:
            return 0.0
        return sum(tile.congestion() for tile in self.tiles_) / len(self.tiles_)


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
        self.congestion_history_: List[Dict[str, float]] = []
        self.tile_inflation_ratios_: Dict[int, float] = {}
        self.minRcCellSizes_: Dict[int, Tuple[int, int]] = {}
        self.gcell_base_sizes_: Dict[int, Tuple[int, int]] = {}
        self.rudy_net_count_ = 0
        self.rudy_pin_count_ = 0
        self.grt_congestion_report_: Dict[str, Any] = {}
        self.grt_resource_snapshot_: Dict[str, Any] = {}
        self.grt_guide_report_: Dict[str, Any] = {}
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
        router = self._requireGrtAdapter("update_route")
        last_error: Optional[BaseException] = None
        for name in ("updateRoutes", "globalRoute", "route", "run"):
            method = getattr(router, name, None)
            if not callable(method):
                continue
            try:
                if name == "updateRoutes":
                    method(save_guides=True)
                elif name == "globalRoute":
                    method(save_guides=True)
                else:
                    method()
                return
            except NotImplementedError as exc:
                last_error = exc
                continue
            except Exception as exc:
                raise GrtAdapterError("update_route", "global-router adapter route call failed", method=name, cause=exc) from exc

        core = self._grtCore(router)
        if core is not None and core is not router:
            run = getattr(core, "run", None)
            if callable(run):
                try:
                    run()
                    return
                except NotImplementedError as exc:
                    last_error = exc
                except Exception as exc:
                    raise GrtAdapterError("update_route", "global-router core route call failed", method="fastroute.run", cause=exc) from exc

        raise GrtAdapterError(
            "update_route",
            "global-router adapter has no translated route/update entry",
            cause=last_error,
        )

    def getGrtResult(self) -> None:
        router = self._requireGrtAdapter("result")
        self.grt_congestion_report_ = self._callGrtReport(
            router,
            "result",
            ("createCongestionReport", "getCongestionReport"),
            "congestion report",
        )
        self.grt_resource_snapshot_ = self._callGrtReport(
            router,
            "result",
            ("createResourceSnapshot", "getResourceSnapshot"),
            "resource snapshot",
        )
        try:
            self.grt_guide_report_ = self._callGrtReport(
                router,
                "result",
                ("createGuideReport",),
                "guide report",
            )
        except GrtAdapterError:
            self.grt_guide_report_ = self._routesGuideSummary(router)
        self.loadGrt()

    def loadGrt(self) -> None:
        router = self._requireGrtAdapter("load")
        if not self.grt_congestion_report_:
            self.grt_congestion_report_ = self._callGrtReport(
                router,
                "load",
                ("createCongestionReport", "getCongestionReport"),
                "congestion report",
            )
        if not self.grt_resource_snapshot_:
            self.grt_resource_snapshot_ = self._callGrtReport(
                router,
                "load",
                ("createResourceSnapshot", "getResourceSnapshot"),
                "resource snapshot",
            )
        records = self._grtTileRecords(self.grt_congestion_report_)
        if not records:
            records = self._grtTileRecordsFromResource(self.grt_resource_snapshot_)
        if not records:
            raise GrtAdapterError("load", "global-router adapter returned no tile/resource congestion records")
        self.importTileCongestion(records)

    def getGrtRC(self) -> float:
        if not self.tg_.tiles_ or (not self.grt_congestion_report_ and not self.grt_resource_snapshot_):
            self.loadGrt()
        return self.final_average_rc_

    def calculateRudyTiles(self) -> None:
        """用现有 GNet/GPin bbox 计算轻量 RUDY tile demand。

        这里不调用 FastRoute/ODB。RUDY demand 只来自 Python Nesterov 对象中的
        net pin 坐标，按 net bbox 与 tile 的重叠面积分摊到 tile。
        """

        self.tg_.resetRouteDemand()
        self.tg_.setDefaultCapacity()
        self.rudy_net_count_ = 0
        self.rudy_pin_count_ = 0
        if not self.tg_.tiles_:
            self.final_average_rc_ = 0.0
            self.overflowed_tiles_count_ = 0
            self.total_route_overflow_ = 0.0
            return

        for net in self._iterGNets():
            pins = self._netPins(net)
            if len(pins) < 2:
                continue
            bbox = self._pinBBox(pins)
            if bbox is None:
                continue
            lx, ly, ux, uy = bbox
            width = max(1, ux - lx)
            height = max(1, uy - ly)
            bbox_area = float(max(1, width * height))
            wire_area = float((width + height) * max(1, min(self.tg_.tileSizeX_, self.tg_.tileSizeY_)))
            weight = float(getattr(net, "getTotalWeight", lambda: 1.0)())
            self.rudy_net_count_ += 1
            self.rudy_pin_count_ += len(pins)

            for tile in self.tg_.iterOverlappingTiles(lx, ly, ux + 1, uy + 1):
                overlap = self._overlapArea((lx, ly, ux + 1, uy + 1), (tile.lx_, tile.ly_, tile.ux_, tile.uy_))
                if overlap <= 0:
                    continue
                share = overlap / bbox_area
                horizontal = width * max(1, tile.dy()) * share * weight
                vertical = height * max(1, tile.dx()) * share * weight
                tile.addRouteDemand(wire_area * share * weight, horizontal, vertical)

        for tile in self.tg_.tiles_:
            tile.updateOverflow()

    def updateRudyRoute(self) -> None:
        self.calculateRudyTiles()
        self.updateRudyAverage(False)

    def updateRudyAverage(self, verbose: bool = True) -> None:
        tiles = self.tg_.tiles()
        if not tiles:
            self.final_average_rc_ = 0.0
            self.overflowed_tiles_count_ = 0
            self.total_route_overflow_ = 0.0
            return
        self.final_average_rc_ = sum(tile.congestion() for tile in tiles) / len(tiles)
        self.overflowed_tiles_count_ = sum(1 for tile in tiles if tile.routeOverflow_ > 0.0)
        self.total_route_overflow_ = sum(tile.routeOverflow_ for tile in tiles)
        if verbose:
            self.saveCongestionSnapshot(rc=self.final_average_rc_, overflow=self.total_route_overflow_)

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
        self.updateRoute()
        rc = self.getRC()
        self.saveCongestionSnapshot(rc=rc, overflow=self.total_route_overflow_)
        if rc <= self.rbVars_.targetRC:
            return False, False
        if routability_driven_revert_count >= self.max_routability_revert_:
            return False, True
        self.updateInflationRatio()
        self.updateGCellSize()
        return True, False

    def updateInflationRatio(self) -> None:
        target = max(1.0e-12, self.rbVars_.targetRC)
        coef = max(0.0, self.rbVars_.inflationRatioCoef)
        min_ratio = max(1.0, self.rbVars_.minInflationRatio)
        max_ratio = max(min_ratio, self.rbVars_.maxInflationRatio)
        self.tile_inflation_ratios_.clear()
        for tile in self.tg_.tiles():
            congestion = tile.congestion()
            excess = max(0.0, congestion - target)
            ratio = min(max_ratio, max(min_ratio, 1.0 + coef * excess / target))
            tile.setInflationRatio(ratio)
            tile.setInflatedRatio(congestion / target if target > 0.0 else 0.0)
            self.tile_inflation_ratios_[id(tile)] = ratio

    def updateGCellSize(self) -> None:
        if not self.nbVec_:
            return
        if not self.tile_inflation_ratios_:
            self.updateInflationRatio()
        self.inflatedAreaDelta_ = [0 for _ in self.nbVec_]
        if len(self.accumulatedInflatedAreaDelta_) != len(self.nbVec_):
            self.accumulatedInflatedAreaDelta_ = [0 for _ in self.nbVec_]

        for nb_index, nb in enumerate(self.nbVec_):
            area_delta = 0
            for gcell in nb.getGCells():
                if getattr(gcell, "isLocked", lambda: False)():
                    continue
                tile = self._tileForPoint(gcell.cx(), gcell.cy())
                if tile is None:
                    continue
                ratio = max(1.0, tile.inflationRatio())
                key = id(gcell)
                base_dx, base_dy = self.gcell_base_sizes_.setdefault(key, (max(1, gcell.dx()), max(1, gcell.dy())))
                scale = sqrt(ratio)
                new_dx = max(1, int(round(base_dx * scale)))
                new_dy = max(1, int(round(base_dy * scale)))
                old_area = max(0, gcell.dx() * gcell.dy())
                new_area = max(0, new_dx * new_dy)
                if new_area == old_area:
                    continue
                gcell.setSize(new_dx, new_dy, GCellChange.kRoutability)
                area_delta += new_area - old_area
            self.inflatedAreaDelta_[nb_index] = area_delta
            self.accumulatedInflatedAreaDelta_[nb_index] += area_delta
            nb.updateAreas()
            self._updateTargetDensity(nb)

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

    def saveCongestionSnapshot(
        self,
        rc: Optional[float] = None,
        overflow: Optional[float] = None,
        utilization: Optional[float] = None,
    ) -> Dict[str, float]:
        snapshot = {
            "rc": self.final_average_rc_ if rc is None else rc,
            "overflow": self.total_route_overflow_ if overflow is None else overflow,
            "utilization": 0.0 if utilization is None else utilization,
            "overflowed_tiles": float(self.overflowed_tiles_count_),
            "total_tiles": float(self.getTotalTilesCount()),
            "total_inflation": float(self.getTotalInflation()),
        }
        self.congestion_history_.append(snapshot)
        self.rc_metric_.append(snapshot["rc"])
        self.route_overflow_.append(snapshot["overflow"])
        self.route_utilization_.append(snapshot["utilization"])
        if snapshot["rc"] < self.minRc_:
            self.minRc_ = snapshot["rc"]
            self.is_min_rc_ = True
            self.saveMinRc()
        else:
            self.is_min_rc_ = False
        return snapshot

    def getRcMetricHistory(self) -> List[float]:
        return self.rc_metric_

    def getRouteOverflowHistory(self) -> List[float]:
        return self.route_overflow_

    def getRouteUtilizationHistory(self) -> List[float]:
        return self.route_utilization_

    def getCongestionHistory(self) -> List[Dict[str, float]]:
        return self.congestion_history_

    def clearCongestionHistory(self) -> None:
        self.rc_metric_.clear()
        self.route_overflow_.clear()
        self.route_utilization_.clear()
        self.congestion_history_.clear()

    def importRudyHeatmap(self, heatmap: Sequence[Sequence[float]], capacity: Optional[float] = None) -> None:
        """导入外部 heatmap 到 tile demand。

        heatmap 值按 congestion ratio 解释；若未指定容量，使用 tile 当前容量或默认
        容量。该接口只更新 tile 数据，不触发 FastRoute。
        """

        self.tg_.setDefaultCapacity()
        for y, row in enumerate(heatmap):
            for x, value in enumerate(row):
                tile = self.tg_.getTile(x, y)
                if tile is None:
                    continue
                tile.resetRouteDemand()
                tile_capacity = float(capacity) if capacity is not None else tile.routeCapacity_
                tile.setRouteCapacity(tile_capacity)
                tile.addRouteDemand(max(0.0, float(value)) * tile.routeCapacity_)
                tile.updateOverflow()
        self.updateRudyAverage(False)

    def importTileCongestion(self, items: Sequence[Dict[str, Any]]) -> None:
        """按 tile 字典导入 congestion/demand/capacity。"""

        self.tg_.setDefaultCapacity()
        for item in items:
            index = item.get("index", (item.get("x", 0), item.get("y", 0)))
            x, y = int(index[0]), int(index[1])
            tile = self.tg_.getTile(x, y)
            if tile is None:
                continue
            tile.resetRouteDemand()
            if "route_capacity" in item:
                tile.setRouteCapacity(float(item["route_capacity"]))
            elif "capacity" in item:
                tile.setRouteCapacity(float(item["capacity"]))
            if "route_demand" in item:
                tile.addRouteDemand(float(item["route_demand"]))
            elif "demand" in item:
                tile.addRouteDemand(float(item["demand"]))
            elif "congestion" in item:
                tile.addRouteDemand(float(item["congestion"]) * tile.routeCapacity_)
            tile.updateOverflow()
        self.updateRudyAverage(False)

    def exportRudyHeatmap(self) -> List[List[float]]:
        return self.tg_.heatmap()

    def reportTileCongestion(self, sample_limit: int = 0) -> Dict[str, Any]:
        tiles = self.tg_.tiles()
        worst = max((tile.congestion() for tile in tiles), default=0.0)
        report: Dict[str, Any] = {
            "average_congestion": self.final_average_rc_,
            "worst_congestion": worst,
            "overflowed_tiles": self.overflowed_tiles_count_,
            "total_overflow": self.total_route_overflow_,
            "rudy_nets": self.rudy_net_count_,
            "rudy_pins": self.rudy_pin_count_,
            "heatmap": self.exportRudyHeatmap(),
        }
        if sample_limit > 0:
            report["sample_tiles"] = [tile.report() for tile in tiles[:sample_limit]]
        return report

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
            "congestion_history": [dict(item) for item in self.congestion_history_],
            "tile_grid": self.tg_.reportStatus(),
            "tile_congestion": self.reportTileCongestion(),
            "grt_congestion_report": dict(self.grt_congestion_report_),
            "grt_resource_snapshot": dict(self.grt_resource_snapshot_),
            "grt_guide_report": dict(self.grt_guide_report_),
            "min_rc_saved_cells": len(self.minRcCellSizes_),
            "min_rc_saved_regions": len(self.minRcTargetDensity_),
        }

    def _iterGNets(self) -> List[Any]:
        nets: List[Any] = []
        seen = set()
        for nb in self.nbVec_:
            getter = getattr(nb, "getGNets", None)
            if not callable(getter):
                continue
            for net in getter():
                key = id(net)
                if key not in seen:
                    seen.add(key)
                    nets.append(net)
        if self.nbc_ is not None:
            getter = getattr(self.nbc_, "getGNets", None)
            if callable(getter):
                for net in getter():
                    key = id(net)
                    if key not in seen:
                        seen.add(key)
                        nets.append(net)
        return nets

    def _netPins(self, net: Any) -> List[Any]:
        getter = getattr(net, "getGPins", None)
        return list(getter()) if callable(getter) else list(getattr(net, "gPins_", []))

    def _pinBBox(self, pins: Sequence[Any]) -> Optional[Tuple[int, int, int, int]]:
        coords: List[Tuple[int, int]] = []
        for pin in pins:
            cx = getattr(pin, "cx", None)
            cy = getattr(pin, "cy", None)
            x = cx() if callable(cx) else getattr(pin, "cx_", None)
            y = cy() if callable(cy) else getattr(pin, "cy_", None)
            if x is not None and y is not None:
                coords.append((int(x), int(y)))
        if len(coords) < 2:
            return None
        xs = [coord[0] for coord in coords]
        ys = [coord[1] for coord in coords]
        return min(xs), min(ys), max(xs), max(ys)

    def _overlapArea(self, a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> int:
        lx = max(a[0], b[0])
        ly = max(a[1], b[1])
        ux = min(a[2], b[2])
        uy = min(a[3], b[3])
        return _area((lx, ly, ux, uy))

    def _requireGrtAdapter(self, stage: str) -> Any:
        if self.grouter_ is None:
            raise GrtAdapterError(stage, "global-router adapter is not injected")
        return self.grouter_

    def _grtCore(self, router: Any) -> Optional[Any]:
        getter = getattr(router, "fastroute", None)
        if callable(getter):
            core = getter()
            if core is not None:
                return core
        return getattr(router, "fastroute_core", None)

    def _callGrtReport(
        self,
        router: Any,
        stage: str,
        names: Sequence[str],
        label: str,
    ) -> Dict[str, Any]:
        targets = [router]
        core = self._grtCore(router)
        if core is not None and core is not router:
            targets.append(core)
        for target in targets:
            for name in names:
                method = getattr(target, name, None)
                if not callable(method):
                    continue
                try:
                    result = method()
                except NotImplementedError as exc:
                    raise GrtAdapterError(stage, f"global-router adapter {label} entry is not translated", method=name, cause=exc) from exc
                except Exception as exc:
                    raise GrtAdapterError(stage, f"global-router adapter {label} call failed", method=name, cause=exc) from exc
                if isinstance(result, dict) and result:
                    return result
                raise GrtAdapterError(stage, f"global-router adapter returned empty {label}", method=name)
        raise GrtAdapterError(stage, f"global-router adapter has no {label} entry", method="|".join(names))

    def _grtTileRecords(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        records = report.get("tiles") or report.get("tile_records") or report.get("congestion_tiles") or []
        result: List[Dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            mapped = self._mapGrtTileRecord(record)
            if mapped is not None:
                result.append(mapped)
        return result

    def _grtTileRecordsFromResource(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        buckets: Dict[Tuple[int, int], Dict[str, float]] = {}
        for record in snapshot.get("edge_capacity_records", []):
            if not isinstance(record, dict):
                continue
            try:
                x = min(int(record.get("x1", 0)), int(record.get("x2", 0)))
                y = min(int(record.get("y1", 0)), int(record.get("y2", 0)))
                value = float(record.get("value", 0.0))
            except (TypeError, ValueError):
                continue
            bucket = buckets.setdefault((x, y), {"index": (x, y), "route_capacity": 0.0, "route_demand": 0.0})
            bucket["route_capacity"] += value
        for record in snapshot.get("edge_usage_records", []):
            if not isinstance(record, dict):
                continue
            try:
                x = min(int(record.get("x1", 0)), int(record.get("x2", 0)))
                y = min(int(record.get("y1", 0)), int(record.get("y2", 0)))
                value = float(record.get("value", 0.0))
            except (TypeError, ValueError):
                continue
            bucket = buckets.setdefault((x, y), {"index": (x, y), "route_capacity": 0.0, "route_demand": 0.0})
            bucket["route_demand"] += value
        return [item for item in buckets.values() if item["route_capacity"] > 0.0 or item["route_demand"] > 0.0]

    def _mapGrtTileRecord(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if "index" in record:
                index = record["index"]
                x, y = int(index[0]), int(index[1])
            else:
                x, y = int(record.get("x", 0)), int(record.get("y", 0))
            capacity = float(record.get("capacity", record.get("route_capacity", 0.0)))
            demand = float(record.get("usage", record.get("route_demand", record.get("demand", 0.0))))
        except (TypeError, ValueError, IndexError):
            return None
        if capacity <= 0.0 and "congestion" not in record:
            return None
        mapped = {"index": (x, y), "route_capacity": capacity}
        if demand > 0.0:
            mapped["route_demand"] = demand
        elif "congestion" in record:
            mapped["congestion"] = float(record["congestion"])
        else:
            mapped["route_demand"] = 0.0
        return mapped

    def _routesGuideSummary(self, router: Any) -> Dict[str, Any]:
        getter = getattr(router, "getRoutes", None)
        routes = getter() if callable(getter) else getattr(router, "routes", None)
        if not isinstance(routes, dict):
            raise GrtAdapterError("result", "global-router adapter has no guide report or route map")
        return {
            "format": "winroad-gpl-grt-guide-summary",
            "net_count": len(routes),
            "segment_count": sum(len(route) for route in routes.values()),
        }

    def _tileForPoint(self, x: int, y: int) -> Optional[Tile]:
        if self.tg_.tileSizeX_ <= 0 or self.tg_.tileSizeY_ <= 0:
            return None
        tx = int((x - self.tg_.lx_) // self.tg_.tileSizeX_)
        ty = int((y - self.tg_.ly_) // self.tg_.tileSizeY_)
        return self.tg_.getTile(tx, ty)

    def _updateTargetDensity(self, nb: NesterovBase) -> None:
        max_density = min(1.0, max(0.0, self.rbVars_.maxDensity))
        if max_density <= 0.0:
            return
        region_area = max(1, getattr(nb.pb_, "getRegionArea", lambda: 1)())
        movable_area = max(0, nb.getMovableArea())
        target_density = min(max_density, max(0.01, movable_area / region_area))
        nb.setTargetDensity(target_density)


