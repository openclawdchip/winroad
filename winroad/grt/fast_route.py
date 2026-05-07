"""WinRoad global routing package."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .congestion import CongestionInformation, RegionAdjustment, TileCongestion, TileInformation
from .guide import GSegment
from .types import CapacityReductionData, NetRouteMap, NetsPerCongestedArea, TileSet, _unsupported


@dataclass
class DebugSetting:
    """对应 FastRoute.h 的 DebugSetting。"""

    net: Any = None
    steinerTree: bool = False
    rectilinearSTree: bool = False
    tree2D: bool = False
    tree3D: bool = False
    edges3D: bool = False
    renderer: Any = None
    sttInputFileName: str = ""

    def isOn(self) -> bool:
        """C++ 中 renderer 非空表示 debug 打开。"""

        return self.renderer is not None


@dataclass
class CostParams:
    """对应 FastRoute.h 的 CostParams。"""

    logistic_coef: float
    cost_height: float
    slope: int


@dataclass
class Parent3D:
    """对应 FastRoute.h 的 parent3D。"""

    layer: int = 0
    x: int = 0
    y: int = 0


@dataclass
class FastRouteCore:
    """FastRouteCore 的 Python 边界。

    该类保存 FastRoute 公开配置、容量表、net 注册关系和资源更新入口。
    ``run()`` 及 maze/Steiner/层分配等重算法尚未移植，不返回假 route。
    """

    db: Any = None
    logger: Any = None
    service_registry: Any = None
    stt_builder: Any = None
    sta: Any = None
    x_grid: int = 0
    y_grid: int = 0
    num_layers: int = 0
    x_corner: int = 0
    y_corner: int = 0
    tile_size_value: int = 0
    x_grid_max: int = 0
    y_grid_max: int = 0
    resistance_aware: bool = False
    layer_directions: Dict[int, Any] = field(default_factory=dict)
    v_capacity_3D: List[int] = field(default_factory=list)
    h_capacity_3D: List[int] = field(default_factory=list)
    last_col_v_capacity_3D: List[int] = field(default_factory=list)
    last_row_h_capacity_3D: List[int] = field(default_factory=list)
    cap_per_layer: List[int] = field(default_factory=list)
    usage_per_layer: List[int] = field(default_factory=list)
    overflow_per_layer: List[int] = field(default_factory=list)
    max_h_overflow: List[int] = field(default_factory=list)
    max_v_overflow: List[int] = field(default_factory=list)
    original_resources: List[int] = field(default_factory=list)
    edge_capacities: Dict[Tuple[int, int, int, int, int], int] = field(default_factory=dict)
    edge_usage: Dict[Tuple[int, int, int, int, int], int] = field(default_factory=dict)
    resource_snapshot: Dict[str, Any] = field(default_factory=dict)
    tree_edges: Dict[Any, GRoute] = field(default_factory=dict)
    adjustments: List[Tuple[int, int, int, int, int, int, bool]] = field(default_factory=list)
    congestion_nets: Set[Any] = field(default_factory=set)
    congestion_grid_v: List[CongestionInformation] = field(default_factory=list)
    congestion_grid_h: List[CongestionInformation] = field(default_factory=list)
    ndr_nets: Set[Any] = field(default_factory=set)
    soft_ndr_nets: Set[Any] = field(default_factory=set)
    soft_ndr_usage: Dict[int, int] = field(default_factory=dict)
    nets: Dict[Any, Dict[str, Any]] = field(default_factory=dict)
    net_ids: List[Any] = field(default_factory=list)
    routes: NetRouteMap = field(default_factory=dict)
    planar_routes: NetRouteMap = field(default_factory=dict)
    total_overflow_value: int = 0
    has_2d_overflow: bool = False
    verbose: bool = False
    critical_nets_percentage: float = 0.0
    overflow_iterations: int = 50
    congestion_report_iter_step: int = 0
    congestion_file_name: Optional[str] = None
    num_threads: int = 1
    snapshot_batched_width: int = 0
    snapshot_batch_count: int = 0
    max_net_degree: int = 0
    detour_penalty: int = 0
    regular_x: bool = True
    regular_y: bool = True
    incremental_grt: bool = False
    debug: DebugSetting = field(default_factory=DebugSetting)

    @staticmethod
    def _edge_key(x1: int, y1: int, x2: int, y2: int, layer: int) -> Tuple[int, int, int, int, int]:
        """返回无向 grid edge 的稳定 key。"""

        p1 = (int(x1), int(y1))
        p2 = (int(x2), int(y2))
        if p2 < p1:
            p1, p2 = p2, p1
        return (p1[0], p1[1], p2[0], p2[1], int(layer))

    @staticmethod
    def _edge_to_dict(key: Tuple[int, int, int, int, int], value: int) -> Dict[str, int]:
        x1, y1, x2, y2, layer = key
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "layer": layer, "value": value}

    def clear(self) -> None:
        """对应 C++ ``clear()``，清理运行态数据。"""

        self.edge_capacities.clear()
        self.edge_usage.clear()
        self.resource_snapshot.clear()
        self.tree_edges.clear()
        self.adjustments.clear()
        self.congestion_nets.clear()
        self.congestion_grid_v.clear()
        self.congestion_grid_h.clear()
        self.ndr_nets.clear()
        self.soft_ndr_nets.clear()
        self.soft_ndr_usage.clear()
        self.nets.clear()
        self.net_ids.clear()
        self.routes.clear()
        self.planar_routes.clear()
        self.total_overflow_value = 0
        self.has_2d_overflow = False

    def saveCongestion(self, iter: int = -1) -> None:
        """保存当前拥塞摘要。

        真实 FastRoute 迭代文件格式尚未移植；这里写出 JSON 状态报告，供测试和
        上层工具落盘检查。
        """

        report = self.createCongestionReport()
        report["iteration"] = iter
        self._last_congestion_report = report
        if self.congestion_file_name:
            self.writeCongestionMap(self.congestion_file_name)

    def setGridsAndLayers(self, x: int, y: int, nLayers: int) -> None:
        """对应 C++ ``setGridsAndLayers()``。"""

        self.x_grid = x
        self.y_grid = y
        self.num_layers = nLayers
        self.v_capacity_3D = [0 for _ in range(nLayers + 1)]
        self.h_capacity_3D = [0 for _ in range(nLayers + 1)]
        self.last_col_v_capacity_3D = [0 for _ in range(nLayers + 1)]
        self.last_row_h_capacity_3D = [0 for _ in range(nLayers + 1)]
        self.cap_per_layer = [0 for _ in range(nLayers + 1)]
        self.usage_per_layer = [0 for _ in range(nLayers + 1)]
        self.overflow_per_layer = [0 for _ in range(nLayers + 1)]
        self.max_h_overflow = [0 for _ in range(nLayers + 1)]
        self.max_v_overflow = [0 for _ in range(nLayers + 1)]

    def addVCapacity(self, verticalCapacity: int, layer: int) -> None:
        while len(self.v_capacity_3D) <= layer:
            self.v_capacity_3D.append(0)
        self.v_capacity_3D[layer] = verticalCapacity

    def addHCapacity(self, horizontalCapacity: int, layer: int) -> None:
        while len(self.h_capacity_3D) <= layer:
            self.h_capacity_3D.append(0)
        self.h_capacity_3D[layer] = horizontalCapacity

    def setLowerLeft(self, x: int, y: int) -> None:
        self.x_corner = x
        self.y_corner = y

    def setTileSize(self, size: int) -> None:
        self.tile_size_value = size

    def setResistanceAware(self, resistance_aware: bool) -> None:
        self.resistance_aware = resistance_aware

    def addLayerDirection(self, layer_idx: int, direction: Any) -> None:
        self.layer_directions[layer_idx] = direction

    def addNet(
        self,
        db_net: Any,
        is_clock: bool,
        is_local: bool,
        driver_idx: int,
        cost: int,
        min_layer: int,
        max_layer: int,
        slack: float,
        edge_cost_per_layer: Optional[List[int]],
        routed: bool = False,
        alpha: float = 1.0,
        beta: float = 1.0,
        gamma: float = 1.0,
    ) -> Dict[str, Any]:
        """注册 FastRoute net，保留 C++ addNet 的参数边界。"""

        fr_net = {
            "db_net": db_net,
            "is_clock": is_clock,
            "is_local": is_local,
            "driver_idx": driver_idx,
            "cost": cost,
            "min_layer": min_layer,
            "max_layer": max_layer,
            "slack": slack,
            "edge_cost_per_layer": edge_cost_per_layer,
            "routed": routed,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
        }
        self.nets[db_net] = fr_net
        if db_net not in self.net_ids:
            self.net_ids.append(db_net)
        return fr_net

    def deleteNet(self, db_net: Any) -> None:
        self.removeNet(db_net)

    def removeNet(self, db_net: Any) -> None:
        self.nets.pop(db_net, None)
        self.routes.pop(db_net, None)
        self.planar_routes.pop(db_net, None)
        self.net_ids = [net for net in self.net_ids if net is not db_net and net != db_net]

    def mergeNet(self, removed_net: Any, preserved_net: Any) -> None:
        """合并 FastRoute net 的注册关系。"""

        if removed_net in self.routes:
            self.routes.setdefault(preserved_net, []).extend(self.routes.pop(removed_net))
        self.removeNet(removed_net)

    def clearNetRoute(self, db_net: Any) -> None:
        self.routes.pop(db_net, None)
        self.planar_routes.pop(db_net, None)

    def clearNetsToRoute(self) -> None:
        self.net_ids.clear()

    def initEdges(self) -> None:
        """2D edge 初始化入口；实际图构建待移植。"""

        self.edge_usage.clear()

    def init3DEdges(self) -> None:
        """3D edge 初始化入口；实际 multi_array 构建待移植。"""

        self.edge_usage.clear()

    def initLowerBoundCapacities(self) -> None:
        """容量下界初始化入口，待移植。"""

        _unsupported("FastRouteCore::initLowerBoundCapacities")

    def getDbNetLayerEdgeCost(self, db_net: Any, layer: int) -> int:
        """对应 C++ ``getDbNetLayerEdgeCost()``。

        edge cost 来自 FastRoute net 注册时保存的 NDR/track 消耗向量；缺失时
        维持 C++ 默认单位代价边界。
        """

        edge_costs = self.nets.get(db_net, {}).get("edge_cost_per_layer")
        if edge_costs is None or layer < 0 or layer >= len(edge_costs):
            return 1
        return int(edge_costs[layer])

    def initEdgesCapacityPerLayer(self) -> None:
        """按已保存 edge capacity 汇总每层容量。"""

        self.cap_per_layer = [0 for _ in range(self.num_layers + 1)]
        for (*_, layer), capacity in self.edge_capacities.items():
            while len(self.cap_per_layer) <= layer:
                self.cap_per_layer.append(0)
            self.cap_per_layer[layer] += capacity

    def setNumAdjustments(self, nAdjustments: int) -> None:
        """预留 C++ adjustment 容器大小；Python 只保留边界语义。"""

        if nAdjustments <= 0:
            self.adjustments.clear()

    def addAdjustment(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        layer: int,
        reducedCap: int,
        isReduce: bool,
    ) -> None:
        """记录 FastRoute edge capacity adjustment 边界。"""

        self.adjustments.append((x1, y1, x2, y2, layer, reducedCap, isReduce))

    def getAdjustments(self) -> List[Tuple[int, int, int, int, int, int, bool]]:
        """返回已登记的 capacity adjustments。"""

        return list(self.adjustments)

    def clearAdjustments(self) -> None:
        """清空 capacity adjustments。"""

        self.adjustments.clear()

    def releaseResourcesOnInterval(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FastRouteCore::releaseResourcesOnInterval")

    def addVerticalAdjustments(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FastRouteCore::addVerticalAdjustments")

    def addHorizontalAdjustments(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FastRouteCore::addHorizontalAdjustments")

    def saveResourcesBeforeAdjustments(self) -> None:
        """保存 adjustment 前资源快照，供建议 adjustment/report 复用。"""

        self.original_resources = list(self.cap_per_layer)
        self.resource_snapshot = self.createResourceSnapshot()

    def createResourceSnapshot(self) -> Dict[str, Any]:
        """返回当前 edge/layer resource 的可测试快照。"""

        return {
            "format": "winroad-grt-resource",
            "version": 1,
            "schema": self.getResourceSnapshotSchema(),
            "total_capacity_per_layer": list(self.cap_per_layer),
            "total_usage_per_layer": list(self.usage_per_layer),
            "total_overflow_per_layer": list(self.overflow_per_layer),
            "max_horizontal_overflows": list(self.max_h_overflow),
            "max_vertical_overflows": list(self.max_v_overflow),
            "edge_capacities": dict(self.edge_capacities),
            "edge_usage": dict(self.edge_usage),
            "edge_capacity_records": [
                self._edge_to_dict(key, value) for key, value in sorted(self.edge_capacities.items())
            ],
            "edge_usage_records": [
                self._edge_to_dict(key, value) for key, value in sorted(self.edge_usage.items())
            ],
        }

    def getResourceSnapshot(self) -> Dict[str, Any]:
        """返回最近一次保存的 resource snapshot。"""

        return dict(self.resource_snapshot)

    @staticmethod
    def getResourceSnapshotSchema() -> Dict[str, Any]:
        """返回 resource JSON 的轻量 schema 描述。"""

        return {
            "edge_record_fields": ["x1", "y1", "x2", "y2", "layer", "value"],
            "layer_arrays": [
                "total_capacity_per_layer",
                "total_usage_per_layer",
                "total_overflow_per_layer",
                "max_horizontal_overflows",
                "max_vertical_overflows",
            ],
            "notes": "edge records use normalized undirected grid edges; layer arrays are indexed by layer id.",
        }

    @staticmethod
    def _json_safe_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """移除 tuple-key dict，保留 records 形式，便于 json.dump。"""

        safe = dict(snapshot)
        safe.pop("edge_capacities", None)
        safe.pop("edge_usage", None)
        return safe

    def writeResourceReport(self, filename: str) -> None:
        """写出 JSON resource snapshot。"""

        with open(filename, "w", encoding="utf-8") as out:
            json.dump(self._json_safe_snapshot(self.createResourceSnapshot()), out, indent=2)
            out.write("\n")

    def computeSuggestedAdjustment(self) -> int:
        _unsupported("FastRouteCore::computeSuggestedAdjustment")

    def getPrecisionAdjustment(self, x: int, y: int, is_horizontal: bool) -> int:
        _unsupported("FastRouteCore::getPrecisionAdjustment")

    def initBlockedIntervals(self, track_space: List[int]) -> None:
        _unsupported("FastRouteCore::initBlockedIntervals")

    def initAuxVar(self) -> None:
        """初始化 FastRoute 辅助统计容器；真实 edge/tree 初始化仍由专门入口承担。"""

        self.initEdgesCapacityPerLayer()
        self.usage_per_layer = [0 for _ in range(max(self.num_layers + 1, len(self.cap_per_layer)))]
        self.overflow_per_layer = [0 for _ in range(len(self.usage_per_layer))]

    def setEdgeCapacity(self, x1: int, y1: int, x2: int, y2: int, layer: int, capacity: int) -> None:
        self.edge_capacities[self._edge_key(x1, y1, x2, y2, layer)] = capacity

    def getEdgeCapacity(self, x1: int, y1: int, x2: int, y2: int, layer: int) -> int:
        return self.edge_capacities.get(self._edge_key(x1, y1, x2, y2, layer), 0)

    def getAvailableResources(self, x1: int, y1: int, x2: int, y2: int, layer: int) -> int:
        key = self._edge_key(x1, y1, x2, y2, layer)
        return self.edge_capacities.get(key, 0) - self.edge_usage.get(key, 0)

    def incrementEdge3DUsage(self, x1: int, y1: int, x2: int, y2: int, layer: int) -> None:
        key = self._edge_key(x1, y1, x2, y2, layer)
        self.edge_usage[key] = self.edge_usage.get(key, 0) + 1

    def updateEdge2DAnd3DUsage(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        layer: int,
        used: int,
        db_net: Any,
    ) -> None:
        key = self._edge_key(x1, y1, x2, y2, layer)
        self.edge_usage[key] = self.edge_usage.get(key, 0) + used
        while len(self.usage_per_layer) <= layer:
            self.usage_per_layer.append(0)
        self.usage_per_layer[layer] += used
        capacity = self.edge_capacities.get(key, 0)
        overflow = max(0, self.edge_usage[key] - capacity)
        while len(self.overflow_per_layer) <= layer:
            self.overflow_per_layer.append(0)
        self.overflow_per_layer[layer] = max(self.overflow_per_layer[layer], overflow)
        self.total_overflow_value = sum(self.overflow_per_layer)
        if overflow > 0:
            self.congestion_nets.add(db_net)
            self.has_2d_overflow = True

    def hasAvailableResources(self, x1: int, y1: int, x2: int, y2: int, layer: int, db_net: Any) -> bool:
        return self.getAvailableResources(x1, y1, x2, y2, layer) > 0

    def updateRouteGridsLayer(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        layer: int,
        new_layer: int,
        db_net: Any,
    ) -> None:
        """更新已保存 route 中精确匹配 segment 的层号。

        这是状态同步辅助；涉及 rip-up/reroute 的真实层分配算法仍在 ``run``。
        """

        for route in (self.routes.get(db_net, []), self.planar_routes.get(db_net, [])):
            for segment in route:
                if (
                    segment.init_x,
                    segment.init_y,
                    segment.final_x,
                    segment.final_y,
                    segment.init_layer,
                    segment.final_layer,
                ) == (x1, y1, x2, y2, layer, layer):
                    segment.init_layer = new_layer
                    segment.final_layer = new_layer

    def addTreeEdge(self, x1: int, y1: int, x2: int, y2: int, layer: int, db_net: Any) -> None:
        """保存 FastRoute tree edge 的 GSegment 形式。"""

        self.tree_edges.setdefault(db_net, []).append(GSegment(x1, y1, layer, x2, y2, layer))

    def run(self) -> NetRouteMap:
        """执行 FastRoute 主算法。

        这里不能返回伪造 route；需后续按 FastRoute.cpp 继续移植。
        """

        _unsupported("FastRouteCore::run")

    def totalOverflow(self) -> int:
        return self.total_overflow_value

    def has2Doverflow(self) -> bool:
        return self.has_2d_overflow

    def getBlockage(self, layer: Any, x: int, y: int) -> Tuple[int, int]:
        _unsupported("FastRouteCore::getBlockage")

    def updateDbCongestion(self, min_routing_layer: int, max_routing_layer: int) -> None:
        _unsupported("FastRouteCore::updateDbCongestion")

    def getCapacityReductionData(self, cap_red_data: CapacityReductionData) -> None:
        _unsupported("FastRouteCore::getCapacityReductionData")

    def findCongestedEdgesNets(
        self,
        nets_in_congested_edges: NetsPerCongestedArea,
        vertical: bool,
    ) -> None:
        _unsupported("FastRouteCore::findCongestedEdgesNets")

    def getCongestionGrid(
        self,
        congestionGridV: List[CongestionInformation],
        congestionGridH: List[CongestionInformation],
    ) -> None:
        congestionGridV.extend(self.congestion_grid_v)
        congestionGridH.extend(self.congestion_grid_h)

    def buildTileCongestion(self) -> Dict[Tuple[int, int, int], TileInformation]:
        """按 edge usage/capacity 汇总 tile congestion 状态。"""

        tiles: Dict[Tuple[int, int, int], TileInformation] = {}
        for key, capacity in self.edge_capacities.items():
            x1, y1, x2, y2, layer = key
            usage = self.edge_usage.get(key, 0)
            tile_key = (min(x1, x2), min(y1, y2), layer)
            info = tiles.setdefault(tile_key, TileInformation())
            info.congestion.capacity += capacity
            info.congestion.usage += usage
        for db_net, route in self.routes.items():
            for segment in route:
                layer = segment.init_layer
                tile_key = (min(segment.init_x, segment.final_x), min(segment.init_y, segment.final_y), layer)
                info = tiles.setdefault(tile_key, TileInformation())
                info.nets.add(db_net)
        return tiles

    def getTileCongestion(self, x: int, y: int, layer: int) -> TileInformation:
        """返回单个 tile 的 congestion 摘要。"""

        return self.buildTileCongestion().get((x, y, layer), TileInformation())

    def reportCongestionSummary(self) -> Dict[str, Any]:
        """返回 report 边界使用的拥塞统计。"""

        tiles = self.buildTileCongestion()
        congested_tiles = {
            key: info
            for key, info in tiles.items()
            if info.congestion.capacity > 0 and info.congestion.usage > info.congestion.capacity
        }
        return {
            "total_overflow": self.totalOverflow(),
            "has_2d_overflow": self.has2Doverflow(),
            "congested_tile_count": len(congested_tiles),
            "total_tile_count": len(tiles),
            "congestion_nets": set(self.congestion_nets),
            "congestion_net_names": [str(net) for net in self.congestion_nets],
        }

    def createCongestionReport(self) -> Dict[str, Any]:
        """返回 JSON 安全的拥塞报告。"""

        summary = self.reportCongestionSummary()
        summary["format"] = "winroad-grt-congestion"
        summary["version"] = 1
        summary["schema"] = self.getCongestionReportSchema()
        summary["congestion_nets"] = [str(net) for net in self.congestion_nets]
        summary["tiles"] = [
            {
                "x": x,
                "y": y,
                "layer": layer,
                "capacity": info.congestion.capacity,
                "usage": info.congestion.usage,
                "overflow": max(0, info.congestion.usage - info.congestion.capacity),
                "nets": [str(net) for net in info.nets],
            }
            for (x, y, layer), info in sorted(self.buildTileCongestion().items())
        ]
        return summary

    @staticmethod
    def getCongestionReportSchema() -> Dict[str, Any]:
        """返回 congestion JSON 的轻量 schema 描述。"""

        return {
            "tile_fields": ["x", "y", "layer", "capacity", "usage", "overflow", "nets"],
            "summary_fields": [
                "total_overflow",
                "has_2d_overflow",
                "congested_tile_count",
                "total_tile_count",
                "congestion_nets",
            ],
            "notes": "tile overflow is max(usage - capacity, 0); nets are serialized with object names.",
        }

    def getSnapshotBatchCount(self) -> int:
        return self.snapshot_batch_count

    def getVerticalCapacities(self) -> List[int]:
        return self.v_capacity_3D

    def getHorizontalCapacities(self) -> List[int]:
        return self.h_capacity_3D

    def setLastColVCapacity(self, cap: int, layer: int) -> None:
        while len(self.last_col_v_capacity_3D) <= layer:
            self.last_col_v_capacity_3D.append(0)
        self.last_col_v_capacity_3D[layer] = cap

    def setLastRowHCapacity(self, cap: int, layer: int) -> None:
        while len(self.last_row_h_capacity_3D) <= layer:
            self.last_row_h_capacity_3D.append(0)
        self.last_row_h_capacity_3D[layer] = cap

    def getLastColumnVerticalCapacities(self) -> List[int]:
        return self.last_col_v_capacity_3D

    def getLastRowHorizontalCapacities(self) -> List[int]:
        return self.last_row_h_capacity_3D

    def setRegularX(self, regular_x: bool) -> None:
        self.regular_x = regular_x

    def setRegularY(self, regular_y: bool) -> None:
        self.regular_y = regular_y

    def setMaxNetDegree(self, max_degree: int) -> None:
        self.max_net_degree = max_degree

    def setDetourPenalty(self, penalty: int) -> None:
        self.detour_penalty = penalty

    def setVerbose(self, value: bool) -> None:
        self.verbose = value

    def setCriticalNetsPercentage(self, value: float) -> None:
        self.critical_nets_percentage = value

    def getCriticalNetsPercentage(self) -> float:
        return self.critical_nets_percentage

    def setOverflowIterations(self, iterations: int) -> None:
        self.overflow_iterations = iterations

    def setCongestionReportIterStep(self, congestion_report_iter_step: int) -> None:
        self.congestion_report_iter_step = congestion_report_iter_step

    def setCongestionReportFile(self, congestion_file_name: Optional[str]) -> None:
        self.congestion_file_name = congestion_file_name

    def setGridMax(self, x_max: int, y_max: int) -> None:
        self.x_grid_max = x_max
        self.y_grid_max = y_max

    def setNumThreads(self, num_threads: int) -> None:
        self.num_threads = num_threads

    def setSnapshotBatchedWidth(self, snapshot_batched_width: int) -> None:
        self.snapshot_batched_width = snapshot_batched_width

    def getSnapshotBatchedWidth(self) -> int:
        return self.snapshot_batched_width

    def setDebugOn(self, renderer: Any) -> None:
        self.debug.renderer = renderer

    def setDebugNet(self, net: Any) -> None:
        self.debug.net = net

    def setDebugSteinerTree(self, steinerTree: bool) -> None:
        self.debug.steinerTree = steinerTree

    def setDebugRectilinearSTree(self, rectilinearSTree: bool) -> None:
        self.debug.rectilinearSTree = rectilinearSTree

    def setDebugTree2D(self, tree2D: bool) -> None:
        self.debug.tree2D = tree2D

    def setDebugTree3D(self, tree3D: bool) -> None:
        self.debug.tree3D = tree3D

    def setDebugEdges3D(self, edges3D: bool) -> None:
        self.debug.edges3D = edges3D

    def setSttInputFilename(self, file_name: Optional[str]) -> None:
        self.debug.sttInputFileName = file_name or ""

    def getSttInputFileName(self) -> str:
        return self.debug.sttInputFileName

    def getDebugNet(self) -> Any:
        return self.debug.net

    def hasSaveSttInput(self) -> bool:
        return bool(self.debug.sttInputFileName)

    def x_corner_(self) -> int:
        return self.x_corner

    def y_corner_(self) -> int:
        return self.y_corner

    def tile_size(self) -> int:
        return self.tile_size_value

    def fastrouteRender(self) -> Any:
        return self.debug.renderer

    def getPlanarRoutes(self) -> NetRouteMap:
        return self.planar_routes

    def getPlanarRoute(self, db_net: Any, route: GRoute) -> None:
        route.extend(self.planar_routes.get(db_net, []))

    def get3DRoute(self, db_net: Any, route: GRoute) -> None:
        route.extend(self.routes.get(db_net, []))

    def getCongestionNets(self, congestion_nets: Set[Any]) -> None:
        congestion_nets.update(self.congestion_nets)

    def computeCongestionInformation(self) -> None:
        _unsupported("FastRouteCore::computeCongestionInformation")

    def getOriginalResources(self) -> List[int]:
        return self.original_resources

    def getTotalCapacityPerLayer(self) -> List[int]:
        return self.cap_per_layer

    def getTotalUsagePerLayer(self) -> List[int]:
        return self.usage_per_layer

    def getTotalOverflowPerLayer(self) -> List[int]:
        return self.overflow_per_layer

    def getMaxHorizontalOverflows(self) -> List[int]:
        return self.max_h_overflow

    def getMaxVerticalOverflows(self) -> List[int]:
        return self.max_v_overflow

    def clearNDRnets(self) -> None:
        self.ndr_nets.clear()
        self.soft_ndr_nets.clear()
        self.soft_ndr_usage.clear()

    def computeCongestedNDRnets(self) -> None:
        _unsupported("FastRouteCore::computeCongestedNDRnets")

    def updateSoftNDRNetUsage(self, net_id: int, edge_cost: int) -> None:
        self.soft_ndr_usage[net_id] = edge_cost

    def setSoftNDR(self, net_id: int) -> None:
        self.soft_ndr_nets.add(net_id)

    def applySoftNDR(self, net_ids: Sequence[int]) -> None:
        self.soft_ndr_nets.update(net_ids)

    def convertGridsToSegments(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FastRouteCore::convertGridsToSegments")

    def clearNetRouteById(self, netID: int) -> None:
        if 0 <= netID < len(self.net_ids):
            self.clearNetRoute(self.net_ids[netID])

    def clearNets(self) -> None:
        self.nets.clear()
        self.net_ids.clear()

    def setIncrementalGrt(self, is_incremental: bool) -> None:
        self.incremental_grt = is_incremental

    def writeCongestionMap(self, filename: str) -> None:
        """写出 JSON congestion map。"""

        with open(filename, "w", encoding="utf-8") as out:
            json.dump(self.createCongestionReport(), out, indent=2)
            out.write("\n")


