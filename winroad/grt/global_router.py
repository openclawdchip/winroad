"""WinRoad global routing package."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .congestion import RegionAdjustment
from .fast_route import FastRouteCore
from .grid import Grid, Net, Pin, PinGridLocation, RoutingTracks
from .guide import GSegment, GuideFile, routes_to_guide_file
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
        selected_routes = {db_net: route_map[db_net] for db_net in selected_nets if db_net in route_map}
        return routes_to_guide_file(selected_routes, _object_name).toDict()

    def _load_route_payload(self, payload: Dict[str, Any]) -> None:
        """从 ``_route_payload`` 的 JSON 载荷恢复 routes。"""

        loaded: NetRouteMap = {}
        for guide in GuideFile.fromDict(payload).guides:
            db_net = self._net_key_from_name(guide.net)
            loaded[db_net] = list(guide.segments)
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
        loaded: NetRouteMap = {}
        for guide in GuideFile.fromText(text).guides:
            db_net = self._net_key_from_name(guide.net)
            loaded[db_net] = list(guide.segments)
        self.routes.update(loaded)
        self.fastroute_core.routes.update(loaded)

    def _write_route_guide_text(self, file_name: str, nets: Optional[Sequence[Any]] = None) -> None:
        """写出 OpenROAD guide 风格的轻量文本。"""

        route_map = self.routes
        selected_nets = list(nets) if nets is not None else list(route_map)
        selected_routes = {db_net: route_map[db_net] for db_net in selected_nets if db_net in route_map}
        with open(file_name, "w", encoding="utf-8") as out:
            out.write(routes_to_guide_file(selected_routes, _object_name).toGuideText())

    @staticmethod
    def _adjustment_to_dict(adjustment: RegionAdjustment) -> Dict[str, Any]:
        return {
            "min_x": adjustment.min_x,
            "min_y": adjustment.min_y,
            "max_x": adjustment.max_x,
            "max_y": adjustment.max_y,
            "layer": adjustment.layer,
            "adjustment": adjustment.adjustment,
        }

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

    def findRegionAdjustments(
        self,
        *,
        layer: Optional[int] = None,
        region: Optional[Rect] = None,
        include_layer_only: bool = True,
    ) -> List[RegionAdjustment]:
        """按 layer/region 查询 adjustment。"""

        matches: List[RegionAdjustment] = []
        for adjustment in self.region_adjustments:
            if layer is not None and adjustment.layer != layer:
                continue
            if region is not None and adjustment.region != region:
                continue
            if not include_layer_only and adjustment.region == (0, 0, 0, 0):
                continue
            matches.append(adjustment)
        return matches

    def getRegionAdjustment(
        self,
        min_x: int,
        min_y: int,
        max_x: int,
        max_y: int,
        layer: int,
        default: Optional[float] = None,
    ) -> Optional[float]:
        """返回指定 region/layer 的 adjustment 值。"""

        region = (min_x, min_y, max_x, max_y)
        for adjustment in self.region_adjustments:
            if adjustment.region == region and adjustment.layer == layer:
                return adjustment.adjustment
        return default

    def clearAdjustments(self) -> None:
        """清空 GlobalRouter/FastRouteCore 中的 capacity adjustments。"""

        self.region_adjustments.clear()
        self.fastroute_core.clearAdjustments()

    def removeLayerAdjustment(self, layer: int) -> None:
        """删除指定 layer-only adjustment。"""

        self.region_adjustments = [
            adjustment
            for adjustment in self.region_adjustments
            if not (adjustment.region == (0, 0, 0, 0) and adjustment.layer == layer)
        ]
        self._syncFastRouteAdjustments()

    def removeRegionAdjustment(self, min_x: int, min_y: int, max_x: int, max_y: int, layer: int) -> None:
        """删除指定 region/layer adjustment。"""

        target = (min_x, min_y, max_x, max_y)
        self.region_adjustments = [
            adjustment
            for adjustment in self.region_adjustments
            if not (adjustment.region == target and adjustment.layer == layer)
        ]
        self._syncFastRouteAdjustments()

    def removeAdjustments(
        self,
        *,
        layer: Optional[int] = None,
        region: Optional[Rect] = None,
        layer_only: Optional[bool] = None,
    ) -> int:
        """按条件删除 adjustments，返回删除数量。"""

        before = len(self.region_adjustments)

        def should_remove(adjustment: RegionAdjustment) -> bool:
            if layer is not None and adjustment.layer != layer:
                return False
            if region is not None and adjustment.region != region:
                return False
            if layer_only is True and adjustment.region != (0, 0, 0, 0):
                return False
            if layer_only is False and adjustment.region == (0, 0, 0, 0):
                return False
            return layer is not None or region is not None or layer_only is not None

        self.region_adjustments = [
            adjustment for adjustment in self.region_adjustments if not should_remove(adjustment)
        ]
        removed = before - len(self.region_adjustments)
        if removed:
            self._syncFastRouteAdjustments()
        return removed

    def _syncFastRouteAdjustments(self) -> None:
        """把 GlobalRouter adjustment 列表同步到 FastRouteCore。"""

        self.fastroute_core.clearAdjustments()
        for adjustment in self.region_adjustments:
            self.fastroute_core.addAdjustment(
                adjustment.min_x,
                adjustment.min_y,
                adjustment.max_x,
                adjustment.max_y,
                adjustment.layer,
                int(adjustment.adjustment),
                True,
            )

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

    def writeGuides(
        self,
        file_name: str,
        nets: Optional[Sequence[Any]] = None,
        *,
        format: str = "json",
    ) -> None:
        """写出当前 routes。

        ``format="json"`` 保留完整 segment flags；``format="guide"`` 写出
        OpenROAD guide 风格文本，便于人工查看。
        """

        if format == "json":
            self._write_route_text(file_name, nets)
        elif format in {"guide", "text"}:
            self._write_route_guide_text(file_name, nets)
        else:
            raise ValueError("format 必须是 'json'、'guide' 或 'text'")

    def readGuideFiles(self, file_names: Sequence[str], *, clear: bool = False) -> List[str]:
        """批量读取 guide/segment 文件，返回已读取文件列表。"""

        if clear:
            self.clearRoutes()
        loaded: List[str] = []
        for file_name in file_names:
            self.readGuides(file_name)
            loaded.append(file_name)
        return loaded

    def writeGuideFiles(
        self,
        outputs: Dict[str, Optional[Sequence[Any]]],
        *,
        format: str = "json",
    ) -> List[str]:
        """批量写 guide 文件。

        ``outputs`` 的 key 是文件名，value 是该文件要写出的 nets；value 为
        ``None`` 时写出所有 routes。
        """

        written: List[str] = []
        for file_name, nets in outputs.items():
            self.writeGuides(file_name, nets, format=format)
            written.append(file_name)
        return written

    def splitGuidesByNet(
        self,
        directory: str,
        *,
        suffix: str = ".guide.json",
        format: str = "json",
    ) -> Dict[str, str]:
        """按 net 拆分写出 guide 文件，返回 net 名到文件名的映射。"""

        import os

        os.makedirs(directory, exist_ok=True)
        result: Dict[str, str] = {}
        for db_net in self.routes:
            net_name = _object_name(db_net)
            safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in net_name)
            file_name = os.path.join(directory, safe_name + suffix)
            self.writeGuides(file_name, [db_net], format=format)
            result[net_name] = file_name
        return result

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

    def getNetRouteMetrics(self, db_net: Any) -> Dict[str, Any]:
        """返回单 net 当前 route 的可落地指标。"""

        route = self.routes.get(db_net, [])
        layer_lengths = self.routeLayerLengths(db_net)
        bbox: Optional[Rect] = None
        points: List[Tuple[int, int]] = []
        via_count = 0
        jumper_count = 0
        three_d_count = 0
        for segment in route:
            points.extend([(segment.init_x, segment.init_y), (segment.final_x, segment.final_y)])
            if segment.isVia():
                via_count += abs(segment.final_layer - segment.init_layer) or 1
            if segment.isJumper():
                jumper_count += 1
            if segment.is3DRoute():
                three_d_count += 1
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            bbox = (min(xs), min(ys), max(xs), max(ys))
        total_wirelength = sum(layer_lengths)
        return {
            "net": _object_name(db_net),
            "segment_count": len(route),
            "wirelength": total_wirelength,
            "layer_wirelengths": layer_lengths,
            "via_count": via_count,
            "jumper_count": jumper_count,
            "three_d_segment_count": three_d_count,
            "bbox": list(bbox) if bbox is not None else None,
            "connected": self.isConnected(db_net) if route else False,
            "pin_count": self.db_net_map.get(db_net).getNumPins() if db_net in self.db_net_map else 0,
        }

    def getRouteMetrics(self) -> Dict[str, Any]:
        """返回所有 nets 的 route metrics 摘要。"""

        nets = [self.getNetRouteMetrics(db_net) for db_net in self.routes]
        return {
            "format": "winroad-grt-route-metrics",
            "version": 1,
            "net_count": len(nets),
            "total_wirelength": sum(item["wirelength"] for item in nets),
            "total_segments": sum(item["segment_count"] for item in nets),
            "total_vias": sum(item["via_count"] for item in nets),
            "nets": nets,
        }

    @staticmethod
    def _segment_orientation(segment: GSegment) -> str:
        """返回 segment 的方向标签，保持 report 字段稳定。"""

        if segment.isVia():
            return "via"
        if segment.init_layer != segment.final_layer:
            return "layer_change"
        if segment.init_y == segment.final_y:
            return "horizontal"
        if segment.init_x == segment.final_x:
            return "vertical"
        return "non_manhattan"

    @staticmethod
    def _segment_unit_edges(segment: GSegment) -> List[Tuple[int, int, int, int, int]]:
        """把同层曼哈顿 segment 展开为 unit grid edges。

        FastRoute 的资源表按相邻 grid edge 保存；guide segment 可以跨多个
        tile，因此 report 查询资源时需要做这个轻量展开。via 不消耗二维
        edge，真实 via cost/resistance 仍由未移植入口负责。
        """

        if segment.isVia() or segment.init_layer != segment.final_layer:
            return []
        if segment.init_x != segment.final_x and segment.init_y != segment.final_y:
            return []
        edges: List[Tuple[int, int, int, int, int]] = []
        if segment.init_x == segment.final_x:
            step = 1 if segment.final_y >= segment.init_y else -1
            for y in range(segment.init_y, segment.final_y, step):
                edges.append((segment.init_x, y, segment.final_x, y + step, segment.init_layer))
        else:
            step = 1 if segment.final_x >= segment.init_x else -1
            for x in range(segment.init_x, segment.final_x, step):
                edges.append((x, segment.init_y, x + step, segment.final_y, segment.init_layer))
        return edges

    def getSegmentStatus(
        self,
        segment: GSegment,
        *,
        net: Any = None,
        index: Optional[int] = None,
        include_resources: bool = True,
    ) -> Dict[str, Any]:
        """返回单个 GSegment 的状态查询结果。

        该接口只解释已有 segment，不尝试修正、拆线或估算绕线；这让它能安全
        用在 guide/segment 序列化后的 round-trip 校验中。
        """

        low_layer = min(segment.init_layer, segment.final_layer)
        high_layer = max(segment.init_layer, segment.final_layer)
        status: Dict[str, Any] = {
            "net": _object_name(net) if net is not None else "",
            "index": index,
            "segment": segment.toDict(),
            "orientation": self._segment_orientation(segment),
            "is_line": self.segmentIsLine(segment),
            "is_via": segment.isVia(),
            "is_jumper": segment.isJumper(),
            "is_3d_route": segment.is3DRoute(),
            "length": segment.length(),
            "layer_span": [low_layer, high_layer],
            "bbox": list(self.globalRoutingToBox(segment)),
            "endpoints": [
                {"x": segment.init_x, "y": segment.init_y, "layer": segment.init_layer},
                {"x": segment.final_x, "y": segment.final_y, "layer": segment.final_layer},
            ],
        }
        if include_resources:
            status["resource_edges"] = [
                self.fastroute_core.getEdgeResourceRecord(x1, y1, x2, y2, layer)
                for x1, y1, x2, y2, layer in self._segment_unit_edges(segment)
            ]
        return status

    def validateSegment(self, segment: GSegment, *, net: Any = None, index: Optional[int] = None) -> Dict[str, Any]:
        """校验单个 segment 的边界合法性，返回结构化问题列表。"""

        issues: List[Dict[str, Any]] = []
        if segment.init_layer <= 0 or segment.final_layer <= 0:
            issues.append({"type": "non_positive_layer", "message": "routing layer 应为正数"})
        if segment.init_layer != segment.final_layer and not segment.isVia():
            issues.append({"type": "layer_change_not_via", "message": "跨层 segment 必须保持同一 x/y"})
        if (
            segment.init_layer == segment.final_layer
            and segment.init_x != segment.final_x
            and segment.init_y != segment.final_y
        ):
            issues.append({"type": "non_manhattan", "message": "同层 segment 必须水平或垂直"})
        if segment.init_x == segment.final_x and segment.init_y == segment.final_y and segment.init_layer == segment.final_layer:
            issues.append({"type": "zero_length", "message": "同点同层 segment 没有线长或 via 含义"})
        if self.grid.x_grids and (
            min(segment.init_x, segment.final_x) < 0 or max(segment.init_x, segment.final_x) >= self.grid.x_grids
        ):
            issues.append({"type": "x_out_of_grid", "message": "segment x 坐标超出 grid 范围"})
        if self.grid.y_grids and (
            min(segment.init_y, segment.final_y) < 0 or max(segment.init_y, segment.final_y) >= self.grid.y_grids
        ):
            issues.append({"type": "y_out_of_grid", "message": "segment y 坐标超出 grid 范围"})
        if self.grid.num_layers and max(segment.init_layer, segment.final_layer) > self.grid.num_layers:
            issues.append({"type": "layer_out_of_grid", "message": "segment layer 超出 grid layer 范围"})
        return {
            "format": "winroad-grt-segment-validation",
            "version": 1,
            "valid": not issues,
            "issue_count": len(issues),
            "net": _object_name(net) if net is not None else "",
            "index": index,
            "issues": issues,
        }

    def validateRoute(self, db_net: Any) -> Dict[str, Any]:
        """校验单 net 的当前 route。

        覆盖轻量边界：segment 几何、端点连通性、pin 是否被已有 segment 覆盖。
        不调用 pin access、maze routing 或 OpenDB wire 修复逻辑。
        """

        route = self.routes.get(db_net, [])
        issues: List[Dict[str, Any]] = []
        segment_reports = []
        for index, segment in enumerate(route):
            seg_report = self.validateSegment(segment, net=db_net, index=index)
            segment_reports.append(seg_report)
            for issue in seg_report["issues"]:
                issues.append({"type": issue["type"], "segment_index": index, "message": issue["message"]})
        if not route:
            issues.append({"type": "empty_route", "message": "net 没有保存任何 global-route segment"})
        elif not self.isConnected(db_net):
            issues.append({"type": "disconnected_route", "message": "route segment 端点图不连通"})

        net = self.db_net_map.get(db_net)
        uncovered_pins: List[str] = []
        if net is not None:
            for pin in net.getPins():
                if not any(self.segmentCoversPin(segment, pin) for segment in route):
                    uncovered_pins.append(pin.getName())
            if uncovered_pins:
                issues.append(
                    {
                        "type": "uncovered_pins",
                        "message": "已有 route 未覆盖部分 pin 的 on-grid 坐标",
                        "pins": uncovered_pins,
                    }
                )
        return {
            "format": "winroad-grt-route-validation",
            "version": 1,
            "net": _object_name(db_net),
            "valid": not issues,
            "issue_count": len(issues),
            "issues": issues,
            "segments": segment_reports,
            "uncovered_pins": uncovered_pins,
        }

    def validateRoutes(self, nets: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
        """批量校验 routes，返回全局和逐 net 结果。"""

        selected_nets = list(nets) if nets is not None else list(self.routes)
        net_reports = [self.validateRoute(db_net) for db_net in selected_nets]
        resource_report = self.fastroute_core.validateResources()
        issue_count = sum(report["issue_count"] for report in net_reports) + resource_report["issue_count"]
        return {
            "format": "winroad-grt-routes-validation",
            "version": 1,
            "valid": issue_count == 0,
            "issue_count": issue_count,
            "net_count": len(net_reports),
            "nets": net_reports,
            "resources": resource_report,
        }

    def getNetRouteStatus(self, db_net: Any, *, include_segments: bool = True) -> Dict[str, Any]:
        """返回单 net 的 route/guide/net 状态汇总。"""

        net = self.db_net_map.get(db_net)
        route = self.routes.get(db_net, [])
        status = {
            "net": _object_name(db_net),
            "registered": net is not None,
            "pin_count": net.getNumPins() if net is not None else 0,
            "layer_range": list(self.getNetLayerRange(db_net)),
            "alpha_beta_gamma": list(self.getNetAlphaBetaGamma(db_net)),
            "metrics": self.getNetRouteMetrics(db_net),
            "validation": self.validateRoute(db_net),
            "has_route": bool(route),
            "partial_segment_count": len(self.partial_routes.get(db_net, [])),
        }
        if include_segments:
            status["segments"] = [
                self.getSegmentStatus(segment, net=db_net, index=index)
                for index, segment in enumerate(route)
            ]
        return status

    def getRoutesStatus(self, nets: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
        """批量返回 routes 状态，作为 report/序列化的统一入口。"""

        selected_nets = list(nets) if nets is not None else list(self.routes)
        return {
            "format": "winroad-grt-routes-status",
            "version": 1,
            "net_count": len(selected_nets),
            "metrics": self.getRouteMetrics(),
            "validation": self.validateRoutes(selected_nets),
            "resource_summary": self.fastroute_core.getResourceSummary(),
            "congestion": self.createCongestionReport(),
            "nets": [self.getNetRouteStatus(db_net) for db_net in selected_nets],
        }

    def createRouteReport(self, nets: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
        """创建 JSON 安全 route report。"""

        report = self.getRoutesStatus(nets)
        report["format"] = "winroad-grt-route-report"
        report["state_format"] = "winroad-grt-state"
        return report

    def writeRouteReport(self, file_name: str, nets: Optional[Sequence[Any]] = None) -> None:
        """写出 route/net/segment/resource/congestion 聚合 report。"""

        with open(file_name, "w", encoding="utf-8") as out:
            json.dump(self.createRouteReport(nets), out, indent=2)
            out.write("\n")

    def writeBatchReports(self, reports: Dict[str, str], nets: Optional[Sequence[Any]] = None) -> Dict[str, str]:
        """批量写 report 文件。

        ``reports`` 的 key 是 report 类型，value 是输出文件名；支持
        ``route``、``resource``、``congestion``、``state`` 和 ``validation``。
        返回实际写出的类型到文件名映射。
        """

        written: Dict[str, str] = {}
        for report_type, file_name in reports.items():
            if report_type == "route":
                self.writeRouteReport(file_name, nets)
            elif report_type == "resource":
                self.writeResourceReport(file_name)
            elif report_type == "congestion":
                self.writeCongestionReport(file_name)
            elif report_type == "state":
                self.saveState(file_name)
            elif report_type == "validation":
                with open(file_name, "w", encoding="utf-8") as out:
                    json.dump(self.validateRoutes(nets), out, indent=2)
                    out.write("\n")
            else:
                raise ValueError(f"未知 grt report 类型: {report_type}")
            written[report_type] = file_name
        return written

    def getEdgeResourceRecord(self, x1: int, y1: int, x2: int, y2: int, layer: int) -> Dict[str, int]:
        """GlobalRouter 侧转发单 edge resource 查询。"""

        return self.fastroute_core.getEdgeResourceRecord(x1, y1, x2, y2, layer)

    def getEdgeResourceRecords(self) -> List[Dict[str, int]]:
        """返回所有 edge resource records。"""

        return self.fastroute_core.iterEdgeResourceRecords()

    def applyEdgeResourceRecords(self, records: Sequence[Dict[str, int]], *, clear: bool = False) -> int:
        """批量导入 edge resource records。"""

        return self.fastroute_core.applyEdgeResourceRecords(records, clear=clear)

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

    def setRoute(self, db_net: Any, route: Sequence[GSegment]) -> None:
        """设置单 net route，并同步 FastRouteCore。"""

        self.routes[db_net] = list(route)
        self.fastroute_core.routes[db_net] = self.routes[db_net]

    def getRoute(self, db_net: Any) -> GRoute:
        """返回单 net route 副本。"""

        return list(self.routes.get(db_net, []))

    def clearRoute(self, db_net: Any) -> None:
        """清空单 net route。"""

        self.routes.pop(db_net, None)
        self.partial_routes.pop(db_net, None)
        self.fastroute_core.clearNetRoute(db_net)

    def clearRoutes(self) -> None:
        """清空所有 route，但保留 grid/config 状态。"""

        self.routes.clear()
        self.partial_routes.clear()
        self.fastroute_core.routes.clear()
        self.fastroute_core.planar_routes.clear()

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
        """更新已保存 route/core route 中精确匹配 segment 的层号。"""

        for route in (self.routes.get(db_net, []), self.partial_routes.get(db_net, [])):
            for segment in route:
                if (
                    segment.init_x,
                    segment.init_y,
                    segment.final_x,
                    segment.final_y,
                    segment.init_layer,
                    segment.final_layer,
                ) == (init_x, init_y, final_x, final_y, layer_level, layer_level):
                    segment.init_layer = new_layer_level
                    segment.final_layer = new_layer_level
        self.fastroute_core.updateRouteGridsLayer(
            init_x,
            init_y,
            final_x,
            final_y,
            layer_level,
            new_layer_level,
            db_net,
        )

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

    def createCongestionReport(self) -> Dict[str, Any]:
        """返回 JSON 安全的 congestion report。"""

        return self.fastroute_core.createCongestionReport()

    def writeCongestionReport(self, file_name: str) -> None:
        """写出 JSON congestion report。"""

        self.fastroute_core.writeCongestionMap(file_name)

    def getResourceSnapshot(self) -> Dict[str, Any]:
        """返回 FastRouteCore 最近一次 resource snapshot。"""

        return self.fastroute_core.getResourceSnapshot()

    def createResourceSnapshot(self) -> Dict[str, Any]:
        """创建并返回当前 resource snapshot。"""

        return self.fastroute_core.createResourceSnapshot()

    def writeResourceReport(self, file_name: str) -> None:
        """写出 JSON resource report。"""

        self.fastroute_core.writeResourceReport(file_name)

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

    def toStateDict(self) -> Dict[str, Any]:
        """序列化可落地的 GlobalRouter/FastRouteCore 状态。

        仅保存 Python grt 边界状态；不序列化 OpenDB/STA/logger 等外部对象。
        """

        resource_snapshot = self.fastroute_core.createResourceSnapshot()
        return {
            "format": "winroad-grt-state",
            "version": 1,
            "grid_origin": list(self.grid_origin),
            "grid": {
                "die_area": list(self.grid.die_area),
                "tile_size": self.grid.tile_size,
                "x_grids": self.grid.x_grids,
                "y_grids": self.grid.y_grids,
                "perfect_regular_x": self.grid.perfect_regular_x,
                "perfect_regular_y": self.grid.perfect_regular_y,
                "num_layers": self.grid.num_layers,
                "track_pitches": list(self.grid.track_pitches),
            },
            "routing_layers": dict(self.routing_layers),
            "routes": self._route_payload(),
            "partial_routes": routes_to_guide_file(self.partial_routes, _object_name).toDict(),
            "adjustments": [
                {
                    "min_x": adj.min_x,
                    "min_y": adj.min_y,
                    "max_x": adj.max_x,
                    "max_y": adj.max_y,
                    "layer": adj.layer,
                    "adjustment": adj.adjustment,
                }
                for adj in self.region_adjustments
            ],
            "config": {
                "infinite_capacity": self.infinite_capacity,
                "adjustment": self.adjustment,
                "congestion_iterations": self.congestion_iterations,
                "congestion_report_iter_step": self.congestion_report_iter_step,
                "congestion_file_name": self.congestion_file_name,
                "allow_congestion": self.allow_congestion,
                "resistance_aware": self.resistance_aware,
                "snapshot_batched_width": self.snapshot_batched_width,
                "num_threads": self.num_threads,
                "macro_extension": self.macro_extension,
                "initialized": self.initialized,
                "is_congested": self.is_congested,
                "use_cugr": self.use_cugr,
                "skip_large_fanout": self.skip_large_fanout,
                "check_pin_placement": self.check_pin_placement,
                "verbose": self.verbose,
                "seed": self.seed,
                "caps_perturbation_percentage": self.caps_perturbation_percentage,
                "perturbation_amount": self.perturbation_amount,
                "is_incremental": self.is_incremental,
            },
            "fastroute": {
                "x_grid": self.fastroute_core.x_grid,
                "y_grid": self.fastroute_core.y_grid,
                "num_layers": self.fastroute_core.num_layers,
                "x_corner": self.fastroute_core.x_corner,
                "y_corner": self.fastroute_core.y_corner,
                "tile_size_value": self.fastroute_core.tile_size_value,
                "x_grid_max": self.fastroute_core.x_grid_max,
                "y_grid_max": self.fastroute_core.y_grid_max,
                "resistance_aware": self.fastroute_core.resistance_aware,
                "layer_directions": {
                    str(layer): str(direction)
                    for layer, direction in self.fastroute_core.layer_directions.items()
                },
                "v_capacity_3D": list(self.fastroute_core.v_capacity_3D),
                "h_capacity_3D": list(self.fastroute_core.h_capacity_3D),
                "last_col_v_capacity_3D": list(self.fastroute_core.last_col_v_capacity_3D),
                "last_row_h_capacity_3D": list(self.fastroute_core.last_row_h_capacity_3D),
                "cap_per_layer": list(self.fastroute_core.cap_per_layer),
                "usage_per_layer": list(self.fastroute_core.usage_per_layer),
                "overflow_per_layer": list(self.fastroute_core.overflow_per_layer),
                "max_h_overflow": list(self.fastroute_core.max_h_overflow),
                "max_v_overflow": list(self.fastroute_core.max_v_overflow),
                "edge_capacities": resource_snapshot["edge_capacity_records"],
                "edge_usage": resource_snapshot["edge_usage_records"],
                "total_overflow_value": self.fastroute_core.total_overflow_value,
                "has_2d_overflow": self.fastroute_core.has_2d_overflow,
            },
        }

    def loadStateDict(self, state: Dict[str, Any]) -> None:
        """从 ``toStateDict`` 结果恢复可落地状态。"""

        self.grid_origin = tuple(state.get("grid_origin", (0, 0)))  # type: ignore[assignment]
        grid_state = state.get("grid", {})
        self.grid.die_area = tuple(grid_state.get("die_area", (0, 0, 0, 0)))  # type: ignore[assignment]
        self.grid.tile_size = int(grid_state.get("tile_size", 0))
        self.grid.x_grids = int(grid_state.get("x_grids", 0))
        self.grid.y_grids = int(grid_state.get("y_grids", 0))
        self.grid.perfect_regular_x = bool(grid_state.get("perfect_regular_x", True))
        self.grid.perfect_regular_y = bool(grid_state.get("perfect_regular_y", True))
        self.grid.num_layers = int(grid_state.get("num_layers", 0))
        self.grid.track_pitches = [int(value) for value in grid_state.get("track_pitches", [])]
        self.routing_layers = dict(state.get("routing_layers", {}))

        self.routes.clear()
        self.fastroute_core.routes.clear()
        self._load_route_payload(state.get("routes", {}))
        self.partial_routes = {}
        for guide in GuideFile.fromDict(state.get("partial_routes", {})).guides:
            self.partial_routes[self._net_key_from_name(guide.net)] = list(guide.segments)

        self.region_adjustments = [
            RegionAdjustment(
                int(item.get("min_x", 0)),
                int(item.get("min_y", 0)),
                int(item.get("max_x", 0)),
                int(item.get("max_y", 0)),
                int(item.get("layer", 0)),
                float(item.get("adjustment", 0.0)),
            )
            for item in state.get("adjustments", [])
        ]
        self._syncFastRouteAdjustments()

        for key, value in state.get("config", {}).items():
            if hasattr(self, key):
                setattr(self, key, value)

        fr_state = state.get("fastroute", {})
        for key, value in fr_state.items():
            if key in {"edge_capacities", "edge_usage"}:
                continue
            if hasattr(self.fastroute_core, key):
                setattr(self.fastroute_core, key, value)
        self.fastroute_core.edge_capacities.clear()
        for rec in fr_state.get("edge_capacities", []):
            self.fastroute_core.setEdgeCapacity(
                rec["x1"], rec["y1"], rec["x2"], rec["y2"], rec["layer"], rec["value"]
            )
        self.fastroute_core.edge_usage.clear()
        for rec in fr_state.get("edge_usage", []):
            key = self.fastroute_core._edge_key(rec["x1"], rec["y1"], rec["x2"], rec["y2"], rec["layer"])
            self.fastroute_core.edge_usage[key] = int(rec["value"])

    @staticmethod
    def _state_route_map(state: Dict[str, Any], key: str = "routes") -> Dict[str, List[Dict[str, Any]]]:
        routes: Dict[str, List[Dict[str, Any]]] = {}
        for guide in GuideFile.fromDict(state.get(key, {})).guides:
            routes[guide.net] = [segment.toDict() for segment in guide.segments]
        return routes

    @staticmethod
    def _state_adjustment_map(state: Dict[str, Any]) -> Dict[Tuple[int, int, int, int, int], float]:
        result: Dict[Tuple[int, int, int, int, int], float] = {}
        for item in state.get("adjustments", []):
            key = (
                int(item.get("min_x", 0)),
                int(item.get("min_y", 0)),
                int(item.get("max_x", 0)),
                int(item.get("max_y", 0)),
                int(item.get("layer", 0)),
            )
            result[key] = float(item.get("adjustment", 0.0))
        return result

    def diffStateDict(self, other_state: Dict[str, Any]) -> Dict[str, Any]:
        """比较当前状态和另一个 state dict，返回高层差异。"""

        current = self.toStateDict()
        current_routes = self._state_route_map(current)
        other_routes = self._state_route_map(other_state)
        current_route_names = set(current_routes)
        other_route_names = set(other_routes)
        changed_routes = sorted(
            name
            for name in current_route_names & other_route_names
            if current_routes[name] != other_routes[name]
        )

        current_adjustments = self._state_adjustment_map(current)
        other_adjustments = self._state_adjustment_map(other_state)
        adjustment_keys = set(current_adjustments) | set(other_adjustments)
        changed_adjustments = [
            {
                "min_x": key[0],
                "min_y": key[1],
                "max_x": key[2],
                "max_y": key[3],
                "layer": key[4],
                "current": current_adjustments.get(key),
                "other": other_adjustments.get(key),
            }
            for key in sorted(adjustment_keys)
            if current_adjustments.get(key) != other_adjustments.get(key)
        ]

        config_keys = set(current.get("config", {})) | set(other_state.get("config", {}))
        changed_config = {
            key: {
                "current": current.get("config", {}).get(key),
                "other": other_state.get("config", {}).get(key),
            }
            for key in sorted(config_keys)
            if current.get("config", {}).get(key) != other_state.get("config", {}).get(key)
        }

        return {
            "format": "winroad-grt-state-diff",
            "version": 1,
            "routes_added": sorted(current_route_names - other_route_names),
            "routes_removed": sorted(other_route_names - current_route_names),
            "routes_changed": changed_routes,
            "adjustments_changed": changed_adjustments,
            "config_changed": changed_config,
            "grid_changed": current.get("grid") != other_state.get("grid"),
            "fastroute_resource_changed": current.get("fastroute", {}).get("edge_capacities")
            != other_state.get("fastroute", {}).get("edge_capacities")
            or current.get("fastroute", {}).get("edge_usage")
            != other_state.get("fastroute", {}).get("edge_usage"),
        }

    def diffState(self, file_name: str) -> Dict[str, Any]:
        """比较当前状态和磁盘 state JSON。"""

        with open(file_name, "r", encoding="utf-8") as src:
            return self.diffStateDict(json.load(src))

    def mergeStateDict(
        self,
        state: Dict[str, Any],
        *,
        routes: str = "replace",
        config: bool = True,
        resources: bool = True,
        adjustments: str = "replace",
    ) -> None:
        """把另一个 state 合并到当前 GlobalRouter。

        ``routes`` 支持 ``replace``/``append``/``keep``；``adjustments`` 支持
        ``replace``/``append``/``keep``。
        """

        if routes not in {"replace", "append", "keep"}:
            raise ValueError("routes 必须是 'replace'、'append' 或 'keep'")
        if adjustments not in {"replace", "append", "keep"}:
            raise ValueError("adjustments 必须是 'replace'、'append' 或 'keep'")

        merged = deepcopy(self.toStateDict())
        if config:
            merged["config"].update(state.get("config", {}))
            merged["grid"] = deepcopy(state.get("grid", merged.get("grid", {})))
            merged["grid_origin"] = deepcopy(state.get("grid_origin", merged.get("grid_origin", [0, 0])))
            merged["routing_layers"] = deepcopy(state.get("routing_layers", merged.get("routing_layers", {})))
        if resources:
            merged["fastroute"].update(state.get("fastroute", {}))

        if routes == "replace":
            merged["routes"] = deepcopy(state.get("routes", merged.get("routes", {})))
            merged["partial_routes"] = deepcopy(state.get("partial_routes", merged.get("partial_routes", {})))
        elif routes == "append":
            route_map = self._state_route_map(merged)
            for name, segments in self._state_route_map(state).items():
                route_map.setdefault(name, []).extend(segments)
            merged["routes"] = {
                "format": "winroad-grt-routes",
                "version": 1,
                "routes": [{"net": name, "segments": segments} for name, segments in route_map.items()],
            }
        if adjustments == "replace":
            merged["adjustments"] = deepcopy(state.get("adjustments", merged.get("adjustments", [])))
        elif adjustments == "append":
            merged["adjustments"] = list(merged.get("adjustments", [])) + list(state.get("adjustments", []))

        self.loadStateDict(merged)

    def mergeState(self, file_name: str, **kwargs: Any) -> None:
        """从磁盘 state JSON 合并状态。"""

        with open(file_name, "r", encoding="utf-8") as src:
            self.mergeStateDict(json.load(src), **kwargs)

    def saveState(self, file_name: str) -> None:
        """把当前 grt 状态写成 JSON。"""

        with open(file_name, "w", encoding="utf-8") as out:
            json.dump(self.toStateDict(), out, indent=2)
            out.write("\n")

    def loadState(self, file_name: str) -> None:
        """读取 ``saveState`` 生成的 JSON 状态。"""

        with open(file_name, "r", encoding="utf-8") as src:
            self.loadStateDict(json.load(src))

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
