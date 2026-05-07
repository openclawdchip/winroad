"""WinRoad global routing package."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .congestion import RegionAdjustment
from .fast_route import FastRouteCore
from .grid import Grid, Net, Pin, PinGridLocation
from .guide import GSegment
from .types import CapacityReductionData, GRoute, NetRouteMap, Point, Rect, RoutePt, _object_name, _unsupported


@dataclass
class GlobalRouter:
    """OpenROAD grt 顶层入口类。

    该类对应 ``GlobalRouter.h``，负责保存 OpenDB/block、FastRouteCore、
    routes、grid/routing layer、用户 adjustment、增量 dirty nets 等状态。
    """

    logger: Any = None
    service_registry: Any = None
    stt_builder: Any = None
    db: Any = None
    sta: Any = None
    antenna_checker: Any = None
    opendp: Any = None
    fastroute_core: FastRouteCore = field(init=False)
    grid_origin: Point = (0, 0)
    routes: NetRouteMap = field(default_factory=dict)
    partial_routes: NetRouteMap = field(default_factory=dict)
    db_net_map: Dict[Any, Net] = field(default_factory=dict)
    grid: Grid = field(default_factory=Grid)
    routing_layers: Dict[int, Any] = field(default_factory=dict)
    routing_tracks: List[RoutingTracks] = field(default_factory=list)
    infinite_capacity: bool = False
    adjustment: float = 0.0
    congestion_iterations: int = 50
    congestion_report_iter_step: int = 0
    congestion_file_name: Optional[str] = None
    allow_congestion: bool = False
    resistance_aware: bool = False
    snapshot_batched_width: int = 0
    num_threads: int = 1
    macro_extension: int = 0
    initialized: bool = False
    total_diodes_count: int = 0
    is_congested: bool = False
    use_cugr: bool = False
    skip_large_fanout: int = 2**31 - 1
    has_macros_or_pads: bool = False
    check_pin_placement: bool = True
    region_adjustments: List[RegionAdjustment] = field(default_factory=list)
    verbose: bool = False
    seed: int = 0
    caps_perturbation_percentage: float = 0.0
    perturbation_amount: int = 0
    block: Any = None
    dirty_nets: Set[Any] = field(default_factory=set)
    nets_to_route: List[Any] = field(default_factory=list)
    is_incremental: bool = False
    renderer: Any = None
    heatmap: Any = None
    heatmap_rudy: Any = None
    rudy: Any = None
    grouter_cbk: Optional["GRouteDbCbk"] = None

    def __post_init__(self) -> None:
        self.fastroute_core = FastRouteCore(
            db=self.db,
            logger=self.logger,
            service_registry=self.service_registry,
            stt_builder=self.stt_builder,
            sta=self.sta,
        )

    def _net_key_from_name(self, net_name: str) -> Any:
        """按名称寻找已知 db net；找不到时保留字符串 key。"""

        for db_net in list(self.db_net_map) + list(self.routes) + list(self.partial_routes):
            if _object_name(db_net) == net_name:
                return db_net
        block_nets = getattr(self.block, "nets", None)
        if isinstance(block_nets, dict):
            if net_name in block_nets:
                return block_nets[net_name]
            for db_net in block_nets.values():
                if _object_name(db_net) == net_name:
                    return db_net
        return net_name

    def _route_payload(self, nets: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
        """构造 guide/segment JSON 载荷。"""

        route_map = self.routes
        selected_nets = list(nets) if nets is not None else list(route_map)
        return {
            "format": "winroad-grt-routes",
            "version": 1,
            "routes": [
                {
                    "net": _object_name(db_net),
                    "segments": [segment.toDict() for segment in route_map.get(db_net, [])],
                }
                for db_net in selected_nets
                if db_net in route_map
            ],
        }

    def _load_route_payload(self, payload: Dict[str, Any]) -> None:
        """从 ``_route_payload`` 的 JSON 载荷恢复 routes。"""

        loaded: NetRouteMap = {}
        for net_payload in payload.get("routes", []):
            db_net = self._net_key_from_name(str(net_payload.get("net", "")))
            loaded[db_net] = [GSegment.fromDict(segment) for segment in net_payload.get("segments", [])]
        self.routes.update(loaded)
        self.fastroute_core.routes.update(loaded)

    def _write_route_text(self, file_name: str, nets: Optional[Sequence[Any]] = None) -> None:
        """写出轻量 guide/segment 文本，不触碰 OpenDB。"""

        with open(file_name, "w", encoding="utf-8") as out:
            json.dump(self._route_payload(nets), out, indent=2)
            out.write("\n")

    def _read_route_text(self, file_name: str) -> None:
        """读取轻量 JSON 或逐行 guide/segment 文本。"""

        with open(file_name, "r", encoding="utf-8") as src:
            text = src.read()
        stripped = text.strip()
        if not stripped:
            return
        if stripped[0] == "{":
            self._load_route_payload(json.loads(stripped))
            return
        loaded: NetRouteMap = {}
        current_net: Any = None
        for line_no, line in enumerate(stripped.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(":"):
                current_net = self._net_key_from_name(line[:-1].strip())
                loaded.setdefault(current_net, [])
                continue
            net_name, segment = GSegment.fromGuideTokens(line.split())
            db_net = self._net_key_from_name(net_name) if net_name is not None else current_net
            if db_net is None:
                raise ValueError(f"{file_name}:{line_no}: guide 行缺少 net 名")
            loaded.setdefault(db_net, []).append(segment)
        self.routes.update(loaded)
        self.fastroute_core.routes.update(loaded)

    def getRegionAdjustments(self) -> List[RegionAdjustment]:
        """返回用户配置的 region/layer adjustments。"""

        return list(self.region_adjustments)

    def getLayerAdjustments(self) -> Dict[int, float]:
        """返回 layer-only adjustment 映射。"""

        return {
            adjustment.layer: adjustment.adjustment
            for adjustment in self.region_adjustments
            if adjustment.region == (0, 0, 0, 0)
        }

    def initGui(self, routing_congestion_data_source: Any, routing_congestion_data_source_rudy: Any) -> None:
        self.heatmap = routing_congestion_data_source
        self.heatmap_rudy = routing_congestion_data_source_rudy

    def clear(self) -> None:
        """清空 grt 运行态。"""

        self.fastroute_core.clear()
        self.routes.clear()
        self.partial_routes.clear()
        self.db_net_map.clear()
        self.grid.clear()
        self.routing_layers.clear()
        self.routing_tracks.clear()
        self.dirty_nets.clear()
        self.nets_to_route.clear()
        self.initialized = False
        self.is_congested = False

    def setAdjustment(self, adjustment: float) -> None:
        self.adjustment = adjustment

    def setMinRoutingLayer(self, min_layer: int) -> None:
        if self.block is not None:
            setattr(self.block, "min_routing_layer", min_layer)
        self.routing_layers.setdefault("min", min_layer)

    def setMaxRoutingLayer(self, max_layer: int) -> None:
        if self.block is not None:
            setattr(self.block, "max_routing_layer", max_layer)
        self.routing_layers.setdefault("max", max_layer)

    def getMinRoutingLayer(self) -> int:
        return int(getattr(self.block, "min_routing_layer", self.routing_layers.get("min", 0)))

    def getMaxRoutingLayer(self) -> int:
        return int(getattr(self.block, "max_routing_layer", self.routing_layers.get("max", 0)))

    def setMinLayerForClock(self, min_layer: int) -> None:
        if self.block is not None:
            setattr(self.block, "min_layer_for_clock", min_layer)
        self.routing_layers["clock_min"] = min_layer

    def setMaxLayerForClock(self, max_layer: int) -> None:
        if self.block is not None:
            setattr(self.block, "max_layer_for_clock", max_layer)
        self.routing_layers["clock_max"] = max_layer

    def getMinLayerForClock(self) -> int:
        return int(getattr(self.block, "min_layer_for_clock", self.routing_layers.get("clock_min", 0)))

    def getMaxLayerForClock(self) -> int:
        return int(getattr(self.block, "max_layer_for_clock", self.routing_layers.get("clock_max", 0)))

    def setCriticalNetsPercentage(self, critical_nets_percentage: float) -> None:
        self.fastroute_core.setCriticalNetsPercentage(critical_nets_percentage)

    def addLayerAdjustment(self, layer: int, reduction_percentage: float) -> None:
        self.region_adjustments.append(RegionAdjustment(0, 0, 0, 0, layer, reduction_percentage))
        self.fastroute_core.addAdjustment(0, 0, 0, 0, layer, int(reduction_percentage), True)

    def addRegionAdjustment(
        self,
        min_x: int,
        min_y: int,
        max_x: int,
        max_y: int,
        layer: int,
        reduction_percentage: float,
    ) -> None:
        self.region_adjustments.append(
            RegionAdjustment(min_x, min_y, max_x, max_y, layer, reduction_percentage)
        )
        self.fastroute_core.addAdjustment(
            min_x,
            min_y,
            max_x,
            max_y,
            layer,
            int(reduction_percentage),
            True,
        )

    def setVerbose(self, value: bool) -> None:
        self.verbose = value
        self.fastroute_core.setVerbose(value)

    def setCongestionIterations(self, iterations: int) -> None:
        self.congestion_iterations = iterations
        self.fastroute_core.setOverflowIterations(iterations)

    def setCongestionReportIterStep(self, congestion_report_iter_step: int) -> None:
        self.congestion_report_iter_step = congestion_report_iter_step
        self.fastroute_core.setCongestionReportIterStep(congestion_report_iter_step)

    def setCongestionReportFile(self, file_name: Optional[str]) -> None:
        self.congestion_file_name = file_name
        self.fastroute_core.setCongestionReportFile(file_name)

    def setGridOrigin(self, x: int, y: int) -> None:
        self.grid_origin = (x, y)

    def setAllowCongestion(self, allow_congestion: bool) -> None:
        self.allow_congestion = allow_congestion

    def setResistanceAware(self, resistance_aware: bool) -> None:
        self.resistance_aware = resistance_aware
        self.fastroute_core.setResistanceAware(resistance_aware)

    def setSnapshotBatchedWidth(self, snapshot_batched_width: int) -> None:
        self.snapshot_batched_width = snapshot_batched_width
        self.fastroute_core.setSnapshotBatchedWidth(snapshot_batched_width)

    def getSnapshotBatchedWidth(self) -> int:
        return self.snapshot_batched_width

    def getSnapshotBatchCount(self) -> int:
        return self.fastroute_core.getSnapshotBatchCount()

    def setMacroExtension(self, macro_extension: int) -> None:
        self.macro_extension = macro_extension

    def setUseCUGR(self, use_cugr: bool) -> None:
        self.use_cugr = use_cugr

    def setSkipLargeFanoutNets(self, skip_large_fanout: int) -> None:
        self.skip_large_fanout = skip_large_fanout

    def setNumThreads(self, num_threads: int) -> None:
        self.num_threads = num_threads
        self.fastroute_core.setNumThreads(num_threads)

    def setInfiniteCapacity(self, infinite_capacity: bool) -> None:
        self.infinite_capacity = infinite_capacity

    def readGuides(self, file_name: str) -> None:
        """读取 WinRoad 轻量 guide 文件到当前 routes。"""

        self._read_route_text(file_name)

    def loadGuidesFromDB(self) -> None:
        """从 block.guides 恢复 guide，不直接访问 OpenDB。"""

        block_guides = getattr(self.block, "guides", None)
        if block_guides is None:
            return
        loaded: NetRouteMap = {}
        items = block_guides.items() if isinstance(block_guides, dict) else block_guides
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                db_net, segments = item
            else:
                db_net = getattr(item, "net", None)
                segments = getattr(item, "segments", [])
            loaded[db_net] = [
                segment if isinstance(segment, GSegment) else GSegment.fromDict(segment)
                for segment in segments
            ]
        self.routes.update(loaded)
        self.fastroute_core.routes.update(loaded)

    def updateNetResources(self, net: Net, release_resources: bool) -> None:
        _unsupported("GlobalRouter::updateNetResources")

    def ensurePinsPositions(self, db_net: Any) -> None:
        _unsupported("GlobalRouter::ensurePinsPositions")

    def findCoveredAccessPoint(self, net: Net, pin: Pin) -> bool:
        _unsupported("GlobalRouter::findCoveredAccessPoint")

    def updateUncoveredPinsPositions(self, db_net: Any, pins_not_covered: str = "") -> bool:
        _unsupported("GlobalRouter::updateUncoveredPinsPositions")

    def saveGuidesFromDB(self, guides: Dict[Any, Any]) -> None:
        """把外部 guide 映射保存进当前 routes。"""

        loaded: NetRouteMap = {}
        for db_net, segments in guides.items():
            loaded[db_net] = [
                segment if isinstance(segment, GSegment) else GSegment.fromDict(segment)
                for segment in segments
            ]
        self.routes.update(loaded)
        self.fastroute_core.routes.update(loaded)

    def saveGuides(self, nets: Sequence[Any]) -> None:
        """把当前 routes 写回 block.guides，不写 OpenDB wire。"""

        guides = {
            db_net: [segment.toDict() for segment in self.routes.get(db_net, [])]
            for db_net in nets
            if db_net in self.routes
        }
        if self.block is not None:
            setattr(self.block, "guides", guides)

    def writeSegments(self, file_name: str) -> None:
        """写出当前 routes 的轻量 segment 文件。"""

        self._write_route_text(file_name)

    def readSegments(self, file_name: str) -> None:
        """读取 ``writeSegments`` 生成的轻量 segment 文件。"""

        self._read_route_text(file_name)

    def netIsCovered(self, db_net: Any, pins_not_covered: str = "") -> bool:
        _unsupported("GlobalRouter::netIsCovered")

    def segmentIsLine(self, segment: GSegment) -> bool:
        """判断 segment 是否为同层水平/垂直线段。"""

        same_layer = segment.init_layer == segment.final_layer
        horizontal = segment.init_y == segment.final_y and segment.init_x != segment.final_x
        vertical = segment.init_x == segment.final_x and segment.init_y != segment.final_y
        return same_layer and (horizontal or vertical)

    def segmentCoversPin(self, segment: GSegment, pin: Pin) -> bool:
        """判断同层线段/via 是否覆盖 pin 的 on-grid 坐标。"""

        x, y = pin.getOnGridPosition()
        layer = pin.getConnectionLayer()
        if segment.isVia():
            low = min(segment.init_layer, segment.final_layer)
            high = max(segment.init_layer, segment.final_layer)
            return (x, y) == (segment.init_x, segment.init_y) and low <= layer <= high
        if layer != segment.init_layer or layer != segment.final_layer:
            return False
        if segment.init_x == segment.final_x == x:
            return min(segment.init_y, segment.final_y) <= y <= max(segment.init_y, segment.final_y)
        if segment.init_y == segment.final_y == y:
            return min(segment.init_x, segment.final_x) <= x <= max(segment.init_x, segment.final_x)
        return False

    def buildNetGraph(self, net: Any) -> List[List[int]]:
        """用当前 route segments 建立 segment 邻接图。"""

        route = self.routes.get(net, [])
        graph = [[] for _ in route]
        for i, seg_i in enumerate(route):
            for j in range(i + 1, len(route)):
                if self.segmentsConnect(seg_i, route[j]):
                    graph[i].append(j)
                    graph[j].append(i)
        return graph

    def isConnected(self, net: Any) -> bool:
        """检查当前保存的 route segment 是否连通。"""

        route = self.routes.get(net, [])
        if not route:
            return False
        graph = self.buildNetGraph(net)
        seen = {0}
        stack = [0]
        while stack:
            node = stack.pop()
            for nxt in graph[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return len(seen) == len(route)

    def segmentsConnect(self, segment1: GSegment, segment2: GSegment) -> bool:
        """判断两个 GSegment 是否在任一 RoutePt 端点相接。"""

        return bool(set(segment1.endpoints()) & set(segment2.endpoints()))

    def isCoveringPin(self, net: Net, segment: GSegment) -> bool:
        return any(self.segmentCoversPin(segment, pin) for pin in net.getPins())

    def initFastRoute(
        self,
        min_routing_layer: int,
        max_routing_layer: int,
        check_pin_placement: bool = True,
    ) -> List[Any]:
        """初始化 FastRoute 边界状态。

        C++ 版本会初始化 grid、routing layer、netlist、capacity 与 obstruction。
        这里仅记录配置并返回待路由 net 列表；真实初始化流程后续逐函数移植。
        """

        self.setMinRoutingLayer(min_routing_layer)
        self.setMaxRoutingLayer(max_routing_layer)
        self.check_pin_placement = check_pin_placement
        self.fastroute_core.setIncrementalGrt(self.is_incremental)
        self.initialized = True
        return list(self.nets_to_route)

    def initFastRouteIncr(self, nets: List[Any]) -> None:
        self.is_incremental = True
        self.nets_to_route = list(nets)
        self.fastroute_core.setIncrementalGrt(True)

    def routeLayerLengths(self, db_net: Any) -> List[int]:
        """统计当前 route 在各层的曼哈顿长度。"""

        lengths: Dict[int, int] = {}
        for segment in self.routes.get(db_net, []):
            if segment.init_layer == segment.final_layer:
                lengths[segment.init_layer] = lengths.get(segment.init_layer, 0) + segment.length()
        if not lengths:
            return []
        return [lengths.get(layer, 0) for layer in range(max(lengths) + 1)]

    def startIncremental(self) -> None:
        self.is_incremental = True
        self.grouter_cbk = GRouteDbCbk(self)
        self.fastroute_core.setIncrementalGrt(True)

    def endIncremental(self, save_guides: bool = False) -> None:
        if save_guides:
            self.saveGuides(self.nets_to_route)
        self.is_incremental = False
        self.grouter_cbk = None
        self.fastroute_core.setIncrementalGrt(False)

    def globalRoute(self, save_guides: bool = False) -> None:
        """执行全局布线主流程，待移植。"""

        _unsupported("GlobalRouter::globalRoute")

    def saveCongestion(self) -> None:
        self.fastroute_core.saveCongestion()

    def getRoutes(self) -> NetRouteMap:
        return self.routes

    def getPartialRoutes(self) -> NetRouteMap:
        return self.partial_routes

    def getNet(self, db_net: Any) -> Optional[Net]:
        return self.db_net_map.get(db_net)

    def getTileSize(self) -> int:
        return self.grid.getTileSize()

    def isNonLeafClock(self, db_net: Any) -> bool:
        signal_type = str(getattr(db_net, "sig_type", getattr(db_net, "signal_type", ""))).lower()
        return "clock" in signal_type

    def hasAvailableResources(
        self,
        is_horizontal: bool,
        pos_x: int,
        pos_y: int,
        layer_level: int,
        db_net: Any,
    ) -> bool:
        x2 = pos_x + (1 if is_horizontal else 0)
        y2 = pos_y + (0 if is_horizontal else 1)
        return self.fastroute_core.hasAvailableResources(pos_x, pos_y, x2, y2, layer_level, db_net)

    def getPositionOnGrid(self, real_position: Point) -> Point:
        return self.grid.getPositionOnGrid(real_position)

    def repairAntennas(
        self,
        diode_mterm: Any,
        iterations: int,
        ratio_margin: float,
        jumper_only: bool,
        diode_only: bool,
        num_threads: int = 1,
    ) -> int:
        _unsupported("GlobalRouter::repairAntennas")

    def updateResources(
        self,
        init_x: int,
        init_y: int,
        final_x: int,
        final_y: int,
        layer_level: int,
        used: int,
        db_net: Any,
    ) -> None:
        self.fastroute_core.updateEdge2DAnd3DUsage(
            init_x, init_y, final_x, final_y, layer_level, used, db_net
        )

    def updateFastRouteGridsLayer(
        self,
        init_x: int,
        init_y: int,
        final_x: int,
        final_y: int,
        layer_level: int,
        new_layer_level: int,
        db_net: Any,
    ) -> None:
        _unsupported("GlobalRouter::updateFastRouteGridsLayer")

    def addDirtyNet(self, net: Any) -> None:
        self.dirty_nets.add(net)

    def updateCUGRNet(self, net: Any) -> None:
        _unsupported("GlobalRouter::updateCUGRNet")

    def getDirtyNets(self) -> Set[Any]:
        return self.dirty_nets

    def haveRoutes(self) -> bool:
        return bool(self.routes)

    def haveDbGuides(self) -> bool:
        block_guides = getattr(self.block, "guides", None)
        return bool(block_guides)

    def designIsPlaced(self) -> bool:
        insts = getattr(self.block, "insts", {})
        return all(str(getattr(inst, "status", "")).lower().endswith("placed") for inst in insts.values())

    def haveDetailedRoutes(self, db_nets: Optional[Sequence[Any]] = None) -> bool:
        nets = db_nets if db_nets is not None else getattr(self.block, "nets", {}).values()
        return all(bool(getattr(net, "wire", None) or getattr(net, "wires", None)) for net in nets)

    def addNetToRoute(self, db_net: Any) -> None:
        if db_net not in self.nets_to_route:
            self.nets_to_route.append(db_net)

    def getNetsToRoute(self) -> List[Any]:
        return self.nets_to_route

    def mergeNetsRouting(self, db_net1: Any, db_net2: Any) -> None:
        self.routes.setdefault(db_net1, []).extend(self.routes.pop(db_net2, []))

    def connectRouting(self, db_net1: Any, db_net2: Any) -> bool:
        _unsupported("GlobalRouter::connectRouting")

    def findBufferPinPostions(self, net1: Net, net2: Net) -> Tuple[Point, Point]:
        _unsupported("GlobalRouter::findBufferPinPostions")

    def findTopLayerOverPosition(self, pin_pos: Point, route: GRoute) -> int:
        top = 0
        for segment in route:
            if (segment.init_x, segment.init_y) == pin_pos or (segment.final_x, segment.final_y) == pin_pos:
                top = max(top, segment.init_layer, segment.final_layer)
        return top

    def createConnectionForPositions(
        self,
        pin_pos1: Point,
        pin_pos2: Point,
        layer1: int,
        layer2: int,
    ) -> GRoute:
        """创建两个 grid 位置之间的直连边界。

        仅在同 x 或同 y 时生成真实 segment；需要绕线时交给 FastRoute 主算法。
        """

        if pin_pos1[0] != pin_pos2[0] and pin_pos1[1] != pin_pos2[1]:
            _unsupported("GlobalRouter::createConnectionForPositions(non_manhattan)")
        route: GRoute = []
        if layer1 != layer2:
            route.append(GSegment(pin_pos1[0], pin_pos1[1], layer1, pin_pos1[0], pin_pos1[1], layer2))
        route.append(GSegment(pin_pos1[0], pin_pos1[1], layer2, pin_pos2[0], pin_pos2[1], layer2))
        return route

    def insertViasForConnection(self, connection: GRoute, via_pos: Point, layer: int, conn_layer: int) -> None:
        if layer != conn_layer:
            connection.append(GSegment(via_pos[0], via_pos[1], layer, via_pos[0], via_pos[1], conn_layer))

    def getBlockage(self, layer: Any, x: int, y: int) -> Tuple[int, int]:
        _unsupported("GlobalRouter::getBlockage")

    def setSeed(self, seed: int) -> None:
        self.seed = seed

    def setCapacitiesPerturbationPercentage(self, percentage: float) -> None:
        self.caps_perturbation_percentage = percentage

    def setPerturbationAmount(self, perturbation: int) -> None:
        self.perturbation_amount = perturbation

    def perturbCapacities(self) -> None:
        _unsupported("GlobalRouter::perturbCapacities")

    def initDebugFastRoute(self, renderer: Any) -> None:
        self.fastroute_core.setDebugOn(renderer)

    def getDebugFastRoute(self) -> Any:
        return self.fastroute_core.fastrouteRender()

    def setDebugNet(self, net: Any) -> None:
        self.fastroute_core.setDebugNet(net)

    def setDebugSteinerTree(self, steinerTree: bool) -> None:
        self.fastroute_core.setDebugSteinerTree(steinerTree)

    def setDebugRectilinearSTree(self, rectilinearSTree: bool) -> None:
        self.fastroute_core.setDebugRectilinearSTree(rectilinearSTree)

    def setDebugTree2D(self, tree2D: bool) -> None:
        self.fastroute_core.setDebugTree2D(tree2D)

    def setDebugTree3D(self, tree3D: bool) -> None:
        self.fastroute_core.setDebugTree3D(tree3D)

    def setDebugEdges3D(self, edges3D: bool) -> None:
        self.fastroute_core.setDebugEdges3D(edges3D)

    def setSttInputFilename(self, file_name: Optional[str]) -> None:
        self.fastroute_core.setSttInputFilename(file_name)

    def saveSttInputFile(self, net: Net) -> None:
        _unsupported("GlobalRouter::saveSttInputFile")

    def reportNetLayerWirelengths(self, db_net: Any, out: Any) -> None:
        """写出单 net 的 global-route 分层线长报告。"""

        lengths = self.routeLayerLengths(db_net)
        writer = getattr(out, "write", None)
        lines = [f"net {_object_name(db_net)}"]
        for layer, length in enumerate(lengths):
            if length:
                lines.append(f"  layer {layer}: {length}")
        text = "\n".join(lines) + "\n"
        if callable(writer):
            writer(text)
        else:
            raise TypeError("out 需要提供 write(str) 方法")

    def reportLayerWireLengths(self, global_route: bool, detailed_route: bool) -> None:
        """计算并缓存分层线长报告边界。"""

        if detailed_route:
            _unsupported("GlobalRouter::reportLayerWireLengths(detailed_route)")
        if not global_route:
            self._last_layer_wirelength_report = []
            return
        totals: Dict[int, int] = {}
        for route in self.routes.values():
            for segment in route:
                if segment.init_layer == segment.final_layer:
                    totals[segment.init_layer] = totals.get(segment.init_layer, 0) + segment.length()
        self._last_layer_wirelength_report = [
            (layer, totals.get(layer, 0)) for layer in range(max(totals) + 1)
        ] if totals else []

    def getLastLayerWirelengthReport(self) -> List[Tuple[int, int]]:
        """返回最近一次 ``reportLayerWireLengths`` 的结果。"""

        return list(getattr(self, "_last_layer_wirelength_report", []))

    def globalRoutingToBox(self, route: GSegment) -> Rect:
        """把 grid segment 转成 box 边界的占位几何。"""

        return (
            min(route.init_x, route.final_x),
            min(route.init_y, route.final_y),
            max(route.init_x, route.final_x),
            max(route.init_y, route.final_y),
        )

    def boxToGlobalRouting(self, route_bds: Rect, layer: int, via_layer: int, route: GRoute) -> None:
        x_min, y_min, x_max, y_max = route_bds
        final_layer = via_layer if via_layer >= 0 else layer
        route.append(GSegment(x_min, y_min, layer, x_max, y_max, final_layer))

    def updateVias(self) -> None:
        _unsupported("GlobalRouter::updateVias")

    def reportNetWireLength(
        self,
        net: Any,
        global_route: bool,
        detailed_route: bool,
        verbose: bool,
        file_name: Optional[str],
    ) -> None:
        """报告单 net global-route 线长；detailed route 继续保持未移植。"""

        if detailed_route:
            _unsupported("GlobalRouter::reportNetWireLength(detailed_route)")
        if not global_route:
            return
        total = sum(segment.length() for segment in self.routes.get(net, []))
        lines = [f"net {_object_name(net)} wirelength {total}"]
        if verbose:
            lengths = self.routeLayerLengths(net)
            lines.extend(f"layer {layer} {length}" for layer, length in enumerate(lengths) if length)
        text = "\n".join(lines) + "\n"
        if file_name:
            with open(file_name, "w", encoding="utf-8") as out:
                out.write(text)
        else:
            self._last_net_wirelength_report = text

    def reportNetDetailedRouteWL(self, wire: Any, out: Any) -> None:
        _unsupported("GlobalRouter::reportNetDetailedRouteWL")

    def createWLReportFile(self, file_name: str, verbose: bool) -> None:
        """写出当前 global-route 线长报告文件。"""

        with open(file_name, "w", encoding="utf-8") as out:
            for db_net in self.routes:
                total = sum(segment.length() for segment in self.routes.get(db_net, []))
                out.write(f"net {_object_name(db_net)} wirelength {total}\n")
                if verbose:
                    for layer, length in enumerate(self.routeLayerLengths(db_net)):
                        if length:
                            out.write(f"  layer {layer}: {length}\n")

    def getCongestionReport(self) -> Dict[str, Any]:
        """返回 FastRouteCore 当前拥塞报告摘要。"""

        return self.fastroute_core.reportCongestionSummary()

    def getResourceSnapshot(self) -> Dict[str, Any]:
        """返回 FastRouteCore 最近一次 resource snapshot。"""

        return self.fastroute_core.getResourceSnapshot()

    def getPinGridPositions(self, db_net: Any) -> List[PinGridLocation]:
        net = self.db_net_map.get(db_net)
        if net is None:
            return []
        return [
            PinGridLocation(
                iterm=pin.getITerm(),
                bterm=pin.getBTerm(),
                pt=pin.getPosition(),
                grid_pt=pin.getOnGridPosition(),
                conn_layer=pin.getConnectionLayer(),
            )
            for pin in net.getPins()
        ]

    def getLayerResistance(self, layer: int, length: int, net: Any) -> float:
        _unsupported("GlobalRouter::getLayerResistance")

    def getViaResistance(self, from_layer: int, to_layer: int) -> float:
        _unsupported("GlobalRouter::getViaResistance")

    def dbuToMicrons(self, dbu: int) -> float:
        units = getattr(self.block, "dbu_per_micron", 1000) or 1000
        return dbu / units

    def estimatePathResistance(self, pin1: Any, pin2: Any, *args: Any, **kwargs: Any) -> float:
        _unsupported("GlobalRouter::estimatePathResistance")

    def findPinAccessPointPositions(
        self,
        pin: Pin,
        ap_positions: Dict[Any, List[Point]],
        all_access_points: bool = False,
    ) -> bool:
        _unsupported("GlobalRouter::findPinAccessPointPositions")

    def getNetLayerRange(self, db_net: Any) -> Tuple[int, int]:
        net = self.db_net_map.get(db_net)
        if net is None or not net.pins:
            return self.getMinRoutingLayer(), self.getMaxRoutingLayer()
        layers = [layer for pin in net.pins for layer in pin.layers]
        if not layers:
            return self.getMinRoutingLayer(), self.getMaxRoutingLayer()
        return min(layers), max(layers)

    def setNetAlphaBetaGamma(self, db_net: Any, alpha: float, beta: float, gamma: float) -> None:
        """记录单 net 的 alpha/beta/gamma 参数。"""

        net = self.db_net_map.get(db_net)
        if net is not None:
            net.setCostParameters(alpha, beta, gamma)
        self.fastroute_core.nets.setdefault(db_net, {})["alpha"] = alpha
        self.fastroute_core.nets.setdefault(db_net, {})["beta"] = beta
        self.fastroute_core.nets.setdefault(db_net, {})["gamma"] = gamma

    def getNetAlphaBetaGamma(self, db_net: Any) -> Tuple[float, float, float]:
        """返回单 net 的 alpha/beta/gamma 参数。"""

        net = self.db_net_map.get(db_net)
        if net is not None:
            return net.getCostParameters()
        fr_net = self.fastroute_core.nets.get(db_net, {})
        return (
            float(fr_net.get("alpha", 1.0)),
            float(fr_net.get("beta", 1.0)),
            float(fr_net.get("gamma", 1.0)),
        )

    def getGridSize(self) -> Tuple[int, int]:
        return self.grid.getXGrids(), self.grid.getYGrids()

    def getGridTileSize(self) -> int:
        return self.grid.getTileSize()

    def getMinMaxLayer(self) -> Tuple[int, int]:
        return self.getMinRoutingLayer(), self.getMaxRoutingLayer()

    def getCapacityReductionData(self, cap_red_data: CapacityReductionData) -> None:
        _unsupported("GlobalRouter::getCapacityReductionData")

    def isInitialized(self) -> bool:
        return self.initialized

    def isCongested(self) -> bool:
        return self.is_congested

    def setDbBlock(self, block: Any) -> None:
        self.block = block

    def setRenderer(self, groute_renderer: Any) -> None:
        self.renderer = groute_renderer

    def getRenderer(self) -> Any:
        return self.renderer

    def fastroute(self) -> FastRouteCore:
        return self.fastroute_core

    def getRudy(self) -> Any:
        return self.rudy

    def writePinLocations(self, file_name: str) -> None:
        _unsupported("GlobalRouter::writePinLocations")


@dataclass
class GRouteDbCbk:
    """对应 ``GlobalRouter.h`` 的 GRouteDbCbk。

    OpenDB 回调在实例移动、net 创建/删除/合并、term 连接变化时标记 dirty net。
    """

    grouter: GlobalRouter

    def instItermsDirty(self, inst: Any) -> None:
        for iterm in getattr(inst, "iterms", []):
            net = getattr(iterm, "net", None)
            if net is not None:
                self.grouter.addDirtyNet(net)

    def inDbPostMoveInst(self, inst: Any) -> None:
        self.instItermsDirty(inst)

    def inDbInstSwapMasterAfter(self, inst: Any) -> None:
        self.instItermsDirty(inst)

    def inDbNetDestroy(self, net: Any) -> None:
        self.grouter.addDirtyNet(net)

    def inDbNetCreate(self, net: Any) -> None:
        self.grouter.addDirtyNet(net)

    def inDbNetPostMerge(self, preserved_net: Any, removed_net: Any) -> None:
        self.grouter.addDirtyNet(preserved_net)
        self.grouter.addDirtyNet(removed_net)

    def inDbNetPostGuideRestore(self, net: Any) -> None:
        self.grouter.addDirtyNet(net)

    def inDbITermPreDisconnect(self, iterm: Any) -> None:
        net = getattr(iterm, "net", None)
        if net is not None:
            self.grouter.addDirtyNet(net)

    def inDbITermPostConnect(self, iterm: Any) -> None:
        net = getattr(iterm, "net", None)
        if net is not None:
            self.grouter.addDirtyNet(net)

    def inDbITermPostSetAccessPoints(self, iterm: Any) -> None:
        net = getattr(iterm, "net", None)
        if net is not None:
            self.grouter.addDirtyNet(net)

    def inDbBTermPostConnect(self, bterm: Any) -> None:
        net = getattr(bterm, "net", None)
        if net is not None:
            self.grouter.addDirtyNet(net)

    def inDbBTermPreDisconnect(self, bterm: Any) -> None:
        net = getattr(bterm, "net", None)
        if net is not None:
            self.grouter.addDirtyNet(net)


@dataclass
class IncrementalGRoute:
    """保存 GlobalRouter 状态并启用增量 dirty-net 回调。"""

    groute: GlobalRouter
    block: Any
    db_cbk: GRouteDbCbk = field(init=False)

    def __post_init__(self) -> None:
        self.db_cbk = GRouteDbCbk(self.groute)
        self.groute.setDbBlock(self.block)
        self.groute.startIncremental()

    def updateRoutes(self, save_guides: bool = True) -> List[Any]:
        """更新 dirty nets 的 route，主算法待移植。"""

        _unsupported("IncrementalGRoute::updateRoutes")

    def close(self) -> None:
        """显式结束增量模式。"""

        self.groute.endIncremental()

    def __enter__(self) -> "IncrementalGRoute":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()



def getITermName(iterm: Any) -> str:
    """对应 grt::getITermName。"""

    if iterm is None:
        return ""
    get_name = getattr(iterm, "getName", None)
    if callable(get_name):
        return str(get_name())
    name = getattr(iterm, "name", None)
    return str(name if name is not None else iterm)


def getLayerName(layer_idx: int, db: Any) -> str:
    """对应 grt::getLayerName。"""

    layers = getattr(db, "tech_layers", None)
    if isinstance(layers, dict):
        for name, layer in layers.items():
            number = getattr(layer, "number", None)
            if number == layer_idx:
                return str(name)
    return str(layer_idx)


def create_global_router(
    logger: Any = None,
    service_registry: Any = None,
    stt_builder: Any = None,
    db: Any = None,
    sta: Any = None,
    antenna_checker: Any = None,
    opendp: Any = None,
) -> GlobalRouter:
    """创建 GlobalRouter，作为模块级便利入口。"""

    return GlobalRouter(
        logger=logger,
        service_registry=service_registry,
        stt_builder=stt_builder,
        db=db,
        sta=sta,
        antenna_checker=antenna_checker,
        opendp=opendp,
    )
