"""OpenROAD grt 模块的 Python 复刻骨架。

本文件按 OpenROAD ``src/grt`` 的核心对象边界翻译：

- ``GSegment`` / ``GRoute``：全局布线 guide/segment 的基础表达。
- ``Pin`` / ``Net`` / ``Grid`` / ``RoutingTracks``：GlobalRouter 与 FastRoute
  之间共享的网表、网格和 pin 抽象。
- ``FastRouteCore``：FastRoute 4.x 核心算法入口类的状态与公开接口。
- ``GlobalRouter``：OpenROAD grt 顶层编排类，连接 OpenDB、FastRoute、
  congestion/resource 更新、guide 读写和增量布线。

这里不做估算 demo，不伪造布线结果。尚未翻译的 C++ 主算法保留等价接口，
并显式抛出 ``NotImplementedError``，方便后续逐函数继续移植。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


Point = Tuple[int, int]
Rect = Tuple[int, int, int, int]
LayerId = int
SegmentIndex = int
GRoute = List["GSegment"]
NetRouteMap = Dict[Any, GRoute]
CapacityReductionData = List[List[List["CapacityReduction"]]]
TileSet = Set[Tuple[int, int]]


def _unsupported(name: str) -> None:
    """统一标记还没有从 C++ 移植的算法入口。"""

    raise NotImplementedError(f"OpenROAD grt::{name} 尚未翻译为 Python")


class NetType(str, Enum):
    """对应 OpenROAD grt::NetType。"""

    CLOCK = "Clock"
    SIGNAL = "Signal"
    ANTENNA = "Antenna"
    ALL = "All"


class PinEdge(str, Enum):
    """对应 grt::PinEdge。

    对 iterm pin，这是 pin 所在 macro/pad cell 的边；对 bterm pin，
    这是 pin 所在 block 的边；标准单元普通 pin 为 none。
    """

    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NONE = "none"


@dataclass(frozen=True, order=True)
class RoutePt:
    """对应 ``grt/RoutePt.h`` 的 RoutePt。

    C++ 版本只保存 x/y/layer，并定义排序和相等比较。dataclass 的 frozen
    + order 提供了等价的值语义，字段名保留 Python 可读形式。
    """

    x_: int = 0
    y_: int = 0
    layer_: int = 0

    def x(self) -> int:
        """返回 grid x 坐标。"""

        return self.x_

    def y(self) -> int:
        """返回 grid y 坐标。"""

        return self.y_

    def layer(self) -> int:
        """返回 routing layer。"""

        return self.layer_


@dataclass
class GSegment:
    """对应 ``grt/GRoute.h`` 的 GSegment。

    一个 segment 可以是同层线段，也可以是同 x/y 的 via stack。OpenROAD
    用 grid 坐标和 routing layer index 表示两端点。
    """

    init_x: int = 0
    init_y: int = 0
    init_layer: int = 0
    final_x: int = 0
    final_y: int = 0
    final_layer: int = 0
    is_jumper: bool = False
    is_3d_route: bool = False

    def isVia(self) -> bool:
        """对应 C++ ``isVia()``。"""

        return self.init_x == self.final_x and self.init_y == self.final_y

    def isJumper(self) -> bool:
        """对应 C++ ``isJumper()``。"""

        return self.is_jumper

    def is3DRoute(self) -> bool:
        """对应 C++ ``is3DRoute()``。"""

        return self.is_3d_route

    def setIs3DRoute(self, is_3d: bool) -> None:
        """对应 C++ ``setIs3DRoute()``。"""

        self.is_3d_route = is_3d

    def length(self) -> int:
        """返回曼哈顿线长；via 的平面长度为 0。"""

        return abs(self.init_x - self.final_x) + abs(self.init_y - self.final_y)

    def endpoints(self) -> Tuple[RoutePt, RoutePt]:
        """返回两端 RoutePt，供连通性检查使用。"""

        return (
            RoutePt(self.init_x, self.init_y, self.init_layer),
            RoutePt(self.final_x, self.final_y, self.final_layer),
        )


@dataclass
class TileCongestion:
    """对应 grt::TileCongestion。"""

    capacity: int = 0
    usage: int = 0


@dataclass
class TileInformation:
    """对应 grt::TileInformation。"""

    nets: Set[Any] = field(default_factory=set)
    congestion: TileCongestion = field(default_factory=TileCongestion)


@dataclass
class CongestionInformation:
    """对应 grt::CongestionInformation。"""

    segment: GSegment = field(default_factory=GSegment)
    congestion: TileCongestion = field(default_factory=TileCongestion)
    sources: Set[Any] = field(default_factory=set)


@dataclass
class CapacityReduction:
    """对应 grt::CapacityReduction。"""

    capacity: int = 0
    reduction: int = 0


@dataclass
class RegionAdjustment:
    """对应 GlobalRouter.h 的 RegionAdjustment。"""

    min_x: int
    min_y: int
    max_x: int
    max_y: int
    layer: int
    adjustment: float

    @property
    def region(self) -> Rect:
        """返回 OpenDB Rect 等价 tuple。"""

        return (self.min_x, self.min_y, self.max_x, self.max_y)

    def getRegion(self) -> Rect:
        """对应 C++ ``getRegion()``。"""

        return self.region

    def getLayer(self) -> int:
        """对应 C++ ``getLayer()``。"""

        return self.layer

    def getAdjustment(self) -> float:
        """对应 C++ ``getAdjustment()``。"""

        return self.adjustment


@dataclass
class RoutePointPins:
    """对应 GlobalRouter.h 的 RoutePointPins。"""

    pins: List["Pin"] = field(default_factory=list)
    connected: bool = False


@dataclass
class PinGridLocation:
    """对应 ``grt/PinGridLocation.h``。

    iterm 与 bterm 二选一；pt 是真实坐标，grid_pt 是映射到 GCell grid 后的
    坐标，conn_layer 是连接层。
    """

    iterm: Any = None
    bterm: Any = None
    pt: Point = (0, 0)
    grid_pt: Point = (0, 0)
    conn_layer: int = 0


@dataclass
class Pin:
    """对应 ``src/grt/src/Pin.h`` 的 Pin。

    OpenROAD 里 iterm/bterm 通过 union 存储；Python 里显式保留两个字段，
    并用 ``is_port`` 区分 bterm pin。
    """

    iterm: Any = None
    bterm: Any = None
    position: Point = (0, 0)
    layers: List[int] = field(default_factory=list)
    boxes_per_layer: Dict[int, List[Rect]] = field(default_factory=dict)
    connected_to_pad_or_macro: bool = False
    die_center: Optional[Point] = None
    connection_layer: int = 0
    edge: PinEdge = PinEdge.NONE
    on_grid_position: Point = (0, 0)
    is_port: bool = False

    @classmethod
    def from_iterm(
        cls,
        iterm: Any,
        position: Point,
        layers: Sequence[int],
        boxes_per_layer: Optional[Dict[int, List[Rect]]] = None,
        connected_to_pad_or_macro: bool = False,
    ) -> "Pin":
        """复刻 iterm pin 构造函数。"""

        return cls(
            iterm=iterm,
            position=position,
            layers=list(layers),
            boxes_per_layer=boxes_per_layer or {},
            connected_to_pad_or_macro=connected_to_pad_or_macro,
            connection_layer=min(layers) if layers else 0,
            is_port=False,
        )

    @classmethod
    def from_bterm(
        cls,
        bterm: Any,
        position: Point,
        layers: Sequence[int],
        boxes_per_layer: Optional[Dict[int, List[Rect]]] = None,
        die_center: Optional[Point] = None,
    ) -> "Pin":
        """复刻 bterm pin 构造函数。"""

        return cls(
            bterm=bterm,
            position=position,
            layers=list(layers),
            boxes_per_layer=boxes_per_layer or {},
            die_center=die_center,
            connection_layer=min(layers) if layers else 0,
            is_port=True,
        )

    def getITerm(self) -> Any:
        """对应 C++ ``getITerm()``。"""

        return self.iterm

    def getBTerm(self) -> Any:
        """对应 C++ ``getBTerm()``。"""

        return self.bterm

    def getName(self) -> str:
        """返回 pin 名称；兼容对象或字符串形式的 iterm/bterm。"""

        obj = self.bterm if self.is_port else self.iterm
        if obj is None:
            return ""
        name = getattr(obj, "name", None)
        if name is not None:
            return str(name)
        get_name = getattr(obj, "getName", None)
        if callable(get_name):
            return str(get_name())
        return str(obj)

    def getPosition(self) -> Point:
        """对应 C++ ``getPosition()``。"""

        return self.position

    def getLayers(self) -> List[int]:
        """对应 C++ ``getLayers()``。"""

        return self.layers

    def getNumLayers(self) -> int:
        """对应 C++ ``getNumLayers()``。"""

        return len(self.layers)

    def getConnectionLayer(self) -> int:
        """对应 C++ ``getConnectionLayer()``。"""

        return self.connection_layer

    def setConnectionLayer(self, layer: int) -> None:
        """对应 C++ ``setConnectionLayer()``。"""

        self.connection_layer = layer

    def getEdge(self) -> PinEdge:
        """对应 C++ ``getEdge()``。"""

        return self.edge

    def getBoxes(self) -> Dict[int, List[Rect]]:
        """对应 C++ ``getBoxes()``。"""

        return self.boxes_per_layer

    def isPort(self) -> bool:
        """对应 C++ ``isPort()``。"""

        return self.is_port

    def isConnectedToPadOrMacro(self) -> bool:
        """对应 C++ ``isConnectedToPadOrMacro()``。"""

        return self.connected_to_pad_or_macro

    def getOnGridPosition(self) -> Point:
        """对应 C++ ``getOnGridPosition()``。"""

        return self.on_grid_position

    def setOnGridPosition(self, on_grid_pos: Point) -> None:
        """对应 C++ ``setOnGridPosition()``。"""

        self.on_grid_position = on_grid_pos

    def isDriver(self) -> bool:
        """判断是否 driver pin。

        真实 OpenROAD 依赖 OpenDB/STA term 方向；这里只读取已有对象字段或方法，
        不推断缺失信息。
        """

        obj = self.iterm or self.bterm
        direction = getattr(obj, "direction", None) or getattr(obj, "io_type", None)
        if direction is None and hasattr(obj, "getIoType"):
            direction = obj.getIoType()
        return str(direction).lower() in {"output", "inout", "feedthru"}

    def isCorePin(self) -> bool:
        """对应 C++ ``isCorePin()`` 的边界判断。"""

        return self.edge == PinEdge.NONE and not self.connected_to_pad_or_macro

    def getPositionNearInstEdge(self, pin_box: Rect, rect_middle: Point) -> Point:
        """返回 pin box 中靠近实例边缘的点。

        C++ 会结合 ``PinEdge`` 和 pin 几何。这里仅按已保存的 edge 做确定性
        几何选择，不发明额外物理信息。
        """

        x_min, y_min, x_max, y_max = pin_box
        mid_x, mid_y = rect_middle
        if self.edge == PinEdge.NORTH:
            return (mid_x, y_max)
        if self.edge == PinEdge.SOUTH:
            return (mid_x, y_min)
        if self.edge == PinEdge.EAST:
            return (x_max, mid_y)
        if self.edge == PinEdge.WEST:
            return (x_min, mid_y)
        return rect_middle


@dataclass
class Net:
    """对应 ``src/grt/src/Net.h`` 的 Net。"""

    net: Any
    has_wires: bool = False
    pins: List[Pin] = field(default_factory=list)
    slack: float = 0.0
    parent_segment_indices: List[int] = field(default_factory=list)
    last_pin_positions: List[Point] = field(default_factory=list)
    merged_net: Any = None
    is_merged_net: bool = False
    is_dirty_net: bool = False
    is_clk: bool = False
    restore_route_from_guides: bool = False
    are_segments_restored: bool = False
    is_connected_to_pad_or_macro: bool = False

    def getDbNet(self) -> Any:
        """对应 C++ ``getDbNet()``。"""

        return self.net

    def getName(self) -> str:
        """返回 dbNet 名称。"""

        name = getattr(self.net, "name", None)
        if name is not None:
            return str(name)
        get_name = getattr(self.net, "getName", None)
        if callable(get_name):
            return str(get_name())
        return str(self.net)

    def getConstName(self) -> str:
        """对应 C++ ``getConstName()``。"""

        return self.getName()

    def getSignalType(self) -> Any:
        """对应 C++ ``getSignalType()``。"""

        return getattr(self.net, "sig_type", getattr(self.net, "signal_type", None))

    def addPin(self, pin: Pin) -> None:
        """对应 C++ ``addPin()``。"""

        self.pins.append(pin)

    def deleteSegment(self, seg_id: int, routes: GRoute) -> None:
        """从 route 中删除一个 segment。"""

        del routes[seg_id]

    def getPins(self) -> List[Pin]:
        """对应 C++ ``getPins()``。"""

        return self.pins

    def getNumPins(self) -> int:
        """对应 C++ ``getNumPins()``。"""

        return len(self.pins)

    def getSlack(self) -> float:
        """对应 C++ ``getSlack()``。"""

        return self.slack

    def setSlack(self, slack: float) -> None:
        """对应 C++ ``setSlack()``。"""

        self.slack = slack

    def setHasWires(self, value: bool) -> None:
        """对应 C++ ``setHasWires()``。"""

        self.has_wires = value

    def hasWires(self) -> bool:
        """对应 C++ ``hasWires()``。"""

        return self.has_wires

    def setSegmentParent(self, segment_parent: Sequence[int]) -> None:
        """对应 C++ ``setSegmentParent()``。"""

        self.parent_segment_indices = list(segment_parent)

    def getSegmentParent(self) -> List[int]:
        """对应 C++ ``getSegmentParent()``。"""

        return self.parent_segment_indices

    def buildSegmentsGraph(self) -> List[List[int]]:
        """为 parent_segment_indices 建立邻接表。

        C++ 版本基于 segment parent 关系构图；这里保留同样数据边界。
        """

        graph = [[] for _ in self.parent_segment_indices]
        for child, parent in enumerate(self.parent_segment_indices):
            if parent >= 0 and parent < len(graph):
                graph[child].append(parent)
                graph[parent].append(child)
        return graph

    def isLocal(self) -> bool:
        """判断所有 pin 是否落在同一个 on-grid 坐标。"""

        if not self.pins:
            return False
        first = self.pins[0].getOnGridPosition()
        return all(pin.getOnGridPosition() == first for pin in self.pins)

    def destroyPins(self) -> None:
        """对应 C++ ``destroyPins()``。"""

        self.pins.clear()

    def destroyITermPin(self, iterm: Any) -> None:
        """删除指定 iterm 的 pin。"""

        self.pins = [pin for pin in self.pins if pin.getITerm() is not iterm]

    def destroyBTermPin(self, bterm: Any) -> None:
        """删除指定 bterm 的 pin。"""

        self.pins = [pin for pin in self.pins if pin.getBTerm() is not bterm]

    def hasStackedVias(self, max_routing_layer: Any) -> bool:
        """检查 pin 连接层是否超过给定 max routing layer。"""

        max_layer = getattr(max_routing_layer, "number", max_routing_layer)
        if max_layer is None:
            return False
        return any(pin.getConnectionLayer() > int(max_layer) for pin in self.pins)

    def saveLastPinPositions(self) -> None:
        """保存当前 pin grid 坐标，用于增量布线变化检查。"""

        self.last_pin_positions = [pin.getOnGridPosition() for pin in self.pins]

    def clearLastPinPositions(self) -> None:
        """对应 C++ ``clearLastPinPositions()``。"""

        self.last_pin_positions.clear()

    def getLastPinPositions(self) -> List[Point]:
        """对应 C++ ``getLastPinPositions()``。"""

        return self.last_pin_positions

    def setMergedNet(self, merged_net: Any) -> None:
        """对应 C++ ``setMergedNet()``。"""

        self.merged_net = merged_net

    def getMergedNet(self) -> Any:
        """对应 C++ ``getMergedNet()``。"""

        return self.merged_net

    def setIsMergedNet(self, merged_net: bool) -> None:
        """对应 C++ ``setIsMergedNet()``。"""

        self.is_merged_net = merged_net

    def isMergedNet(self) -> bool:
        """对应 C++ ``isMergedNet()``。"""

        return self.is_merged_net

    def setDirtyNet(self, is_dirty_net: bool) -> None:
        """对应 C++ ``setDirtyNet()``。"""

        self.is_dirty_net = is_dirty_net

    def isDirtyNet(self) -> bool:
        """对应 C++ ``isDirtyNet()``。"""

        return self.is_dirty_net

    def setIsClockNet(self, is_clk: bool) -> None:
        """对应 C++ ``setIsClockNet()``。"""

        self.is_clk = is_clk

    def isClockNet(self) -> bool:
        """对应 C++ ``isClockNet()``。"""

        return self.is_clk

    def setRestoreRouteFromGuides(self, restore_route_from_guides: bool) -> None:
        """对应 C++ ``setRestoreRouteFromGuides()``。"""

        self.restore_route_from_guides = restore_route_from_guides

    def restoreRouteFromGuides(self) -> bool:
        """对应 C++ ``restoreRouteFromGuides()``。"""

        return self.restore_route_from_guides

    def setAreSegmentsRestored(self, are_segments_restored: bool) -> None:
        """对应 C++ ``setAreSegmentsRestored()``。"""

        self.are_segments_restored = are_segments_restored

    def areSegmentsRestored(self) -> bool:
        """对应 C++ ``areSegmentsRestored()``。"""

        return self.are_segments_restored

    def setIsConnectedToPadOrMacro(self, is_connected: bool) -> None:
        """对应 C++ ``setIsConnectedToPadOrMacro()``。"""

        self.is_connected_to_pad_or_macro = is_connected

    def isConnectedToPadOrMacro(self) -> bool:
        """对应 C++ ``isConnectedToPadOrMacro()``。"""

        return self.is_connected_to_pad_or_macro


@dataclass
class Grid:
    """对应 ``src/grt/src/Grid.h`` 的 Grid。"""

    die_area: Rect = (0, 0, 0, 0)
    tile_size: int = 0
    x_grids: int = 0
    y_grids: int = 0
    perfect_regular_x: bool = True
    perfect_regular_y: bool = True
    num_layers: int = 0
    track_pitches: List[int] = field(default_factory=list)

    def init(
        self,
        die_area: Rect,
        tile_size: int,
        x_grids: int,
        y_grids: int,
        perfect_regular_x: bool,
        perfect_regular_y: bool,
        num_layers: int,
    ) -> None:
        """对应 C++ ``Grid::init``。"""

        self.die_area = die_area
        self.tile_size = tile_size
        self.x_grids = x_grids
        self.y_grids = y_grids
        self.perfect_regular_x = perfect_regular_x
        self.perfect_regular_y = perfect_regular_y
        self.num_layers = num_layers
        self.track_pitches = [0 for _ in range(num_layers + 1)]

    def clear(self) -> None:
        """清空 grid 状态。"""

        self.die_area = (0, 0, 0, 0)
        self.tile_size = 0
        self.x_grids = 0
        self.y_grids = 0
        self.num_layers = 0
        self.track_pitches.clear()

    def getXMin(self) -> int:
        return self.die_area[0]

    def getYMin(self) -> int:
        return self.die_area[1]

    def setXMin(self, x: int) -> None:
        self.die_area = (x, self.die_area[1], self.die_area[2], self.die_area[3])

    def setYMin(self, y: int) -> None:
        self.die_area = (self.die_area[0], y, self.die_area[2], self.die_area[3])

    def getXMax(self) -> int:
        return self.die_area[2]

    def getYMax(self) -> int:
        return self.die_area[3]

    def getTileSize(self) -> int:
        return self.tile_size

    def getXGrids(self) -> int:
        return self.x_grids

    def getYGrids(self) -> int:
        return self.y_grids

    def setXGrids(self, x_grids: int) -> None:
        self.x_grids = x_grids

    def setYGrids(self, y_grids: int) -> None:
        self.y_grids = y_grids

    def isPerfectRegularX(self) -> bool:
        return self.perfect_regular_x

    def isPerfectRegularY(self) -> bool:
        return self.perfect_regular_y

    def getNumLayers(self) -> int:
        return self.num_layers

    def getTrackPitches(self) -> List[int]:
        return self.track_pitches

    def addTrackPitch(self, value: int, layer: int) -> None:
        """对应 C++ ``addTrackPitch``。"""

        while len(self.track_pitches) <= layer:
            self.track_pitches.append(0)
        self.track_pitches[layer] = value

    def getPositionOnGrid(self, position: Point) -> Point:
        """将真实坐标映射为 grid index。"""

        if self.tile_size <= 0:
            return (0, 0)
        x = max(0, min(self.x_grids - 1, (position[0] - self.getXMin()) // self.tile_size))
        y = max(0, min(self.y_grids - 1, (position[1] - self.getYMin()) // self.tile_size))
        return (x, y)

    def getPositionFromGridPoint(self, x: int, y: int) -> Point:
        """返回 grid tile 中心附近的真实坐标。"""

        return (
            self.getXMin() + x * self.tile_size + self.tile_size // 2,
            self.getYMin() + y * self.tile_size + self.tile_size // 2,
        )

    def getMiddle(self) -> Point:
        """返回 grid area 中点。"""

        return ((self.getXMin() + self.getXMax()) // 2, (self.getYMin() + self.getYMax()) // 2)

    def getGridArea(self) -> Rect:
        """对应 C++ ``getGridArea()``。"""

        return self.die_area

    def getBlockedTiles(self, obstruction: Rect) -> Tuple[Rect, Rect, Point, Point]:
        """返回 obstruction 覆盖的首尾 tile。

        C++ 版本通过引用返回四个值；Python 返回 tuple。
        """

        first_tile = self.getPositionOnGrid((obstruction[0], obstruction[1]))
        last_tile = self.getPositionOnGrid((obstruction[2], obstruction[3]))
        first_tile_bds = (*self.getPositionFromGridPoint(*first_tile), *first_tile)
        last_tile_bds = (*self.getPositionFromGridPoint(*last_tile), *last_tile)
        return first_tile_bds, last_tile_bds, first_tile, last_tile

    def computeTileReduce(self, *args: Any, **kwargs: Any) -> int:
        """容量削减算法入口，待按 C++ 继续移植。"""

        _unsupported("Grid::computeTileReduce")

    def computeTileReduceInterval(self, *args: Any, **kwargs: Any) -> Any:
        """容量削减 interval 算法入口，待按 C++ 继续移植。"""

        _unsupported("Grid::computeTileReduceInterval")


@dataclass
class RoutingTracks:
    """对应 ``src/grt/src/RoutingTracks.h``。"""

    layer_index: int = 0
    track_pitch: int = 0
    line_2_via_pitch_up: int = 0
    line_2_via_pitch_down: int = 0
    location: int = 0
    num_tracks: int = 0

    def getLayerIndex(self) -> int:
        return self.layer_index

    def getTrackPitch(self) -> int:
        return self.track_pitch

    def getLineToViaPitch(self) -> int:
        return max(self.line_2_via_pitch_up, self.line_2_via_pitch_down)

    def getUsePitch(self) -> int:
        return max(self.track_pitch, self.line_2_via_pitch_up, self.line_2_via_pitch_down)

    def getLocation(self) -> int:
        return self.location

    def getNumTracks(self) -> int:
        return self.num_tracks


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
    edge_capacities: Dict[Tuple[int, int, int, int, int], int] = field(default_factory=dict)
    edge_usage: Dict[Tuple[int, int, int, int, int], int] = field(default_factory=dict)
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
    regular_x: bool = True
    regular_y: bool = True
    incremental_grt: bool = False
    debug: DebugSetting = field(default_factory=DebugSetting)

    def clear(self) -> None:
        """对应 C++ ``clear()``，清理运行态数据。"""

        self.edge_capacities.clear()
        self.edge_usage.clear()
        self.nets.clear()
        self.net_ids.clear()
        self.routes.clear()
        self.planar_routes.clear()
        self.total_overflow_value = 0
        self.has_2d_overflow = False

    def saveCongestion(self, iter: int = -1) -> None:
        """拥塞快照输出入口，待移植文件格式。"""

        _unsupported("FastRouteCore::saveCongestion")

    def setGridsAndLayers(self, x: int, y: int, nLayers: int) -> None:
        """对应 C++ ``setGridsAndLayers()``。"""

        self.x_grid = x
        self.y_grid = y
        self.num_layers = nLayers
        self.v_capacity_3D = [0 for _ in range(nLayers + 1)]
        self.h_capacity_3D = [0 for _ in range(nLayers + 1)]
        self.last_col_v_capacity_3D = [0 for _ in range(nLayers + 1)]
        self.last_row_h_capacity_3D = [0 for _ in range(nLayers + 1)]

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

    def setEdgeCapacity(self, x1: int, y1: int, x2: int, y2: int, layer: int, capacity: int) -> None:
        self.edge_capacities[(x1, y1, x2, y2, layer)] = capacity

    def getEdgeCapacity(self, x1: int, y1: int, x2: int, y2: int, layer: int) -> int:
        return self.edge_capacities.get((x1, y1, x2, y2, layer), 0)

    def getAvailableResources(self, x1: int, y1: int, x2: int, y2: int, layer: int) -> int:
        key = (x1, y1, x2, y2, layer)
        return self.edge_capacities.get(key, 0) - self.edge_usage.get(key, 0)

    def incrementEdge3DUsage(self, x1: int, y1: int, x2: int, y2: int, layer: int) -> None:
        key = (x1, y1, x2, y2, layer)
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
        key = (x1, y1, x2, y2, layer)
        self.edge_usage[key] = self.edge_usage.get(key, 0) + used

    def hasAvailableResources(self, x1: int, y1: int, x2: int, y2: int, layer: int, db_net: Any) -> bool:
        return self.getAvailableResources(x1, y1, x2, y2, layer) > 0

    def run(self) -> NetRouteMap:
        """执行 FastRoute 主算法。

        这里不能返回伪造 route；需后续按 FastRoute.cpp 继续移植。
        """

        _unsupported("FastRouteCore::run")

    def totalOverflow(self) -> int:
        return self.total_overflow_value

    def has2Doverflow(self) -> bool:
        return self.has_2d_overflow

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

    def setIncrementalGrt(self, is_incremental: bool) -> None:
        self.incremental_grt = is_incremental

    def writeCongestionMap(self, filename: str) -> None:
        """拥塞图写出入口，待移植。"""

        _unsupported("FastRouteCore::writeCongestionMap")


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
        _unsupported("GlobalRouter::readGuides")

    def loadGuidesFromDB(self) -> None:
        _unsupported("GlobalRouter::loadGuidesFromDB")

    def updateNetResources(self, net: Net, release_resources: bool) -> None:
        _unsupported("GlobalRouter::updateNetResources")

    def ensurePinsPositions(self, db_net: Any) -> None:
        _unsupported("GlobalRouter::ensurePinsPositions")

    def findCoveredAccessPoint(self, net: Net, pin: Pin) -> bool:
        _unsupported("GlobalRouter::findCoveredAccessPoint")

    def updateUncoveredPinsPositions(self, db_net: Any, pins_not_covered: str = "") -> bool:
        _unsupported("GlobalRouter::updateUncoveredPinsPositions")

    def saveGuidesFromDB(self, guides: Dict[Any, Any]) -> None:
        _unsupported("GlobalRouter::saveGuidesFromFile")

    def saveGuides(self, nets: Sequence[Any]) -> None:
        _unsupported("GlobalRouter::saveGuides")

    def writeSegments(self, file_name: str) -> None:
        _unsupported("GlobalRouter::writeSegments")

    def readSegments(self, file_name: str) -> None:
        _unsupported("GlobalRouter::readSegments")

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
        _unsupported("GlobalRouter::reportNetLayerWirelengths")

    def reportLayerWireLengths(self, global_route: bool, detailed_route: bool) -> None:
        _unsupported("GlobalRouter::reportLayerWireLengths")

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
        _unsupported("GlobalRouter::reportNetWireLength")

    def reportNetDetailedRouteWL(self, wire: Any, out: Any) -> None:
        _unsupported("GlobalRouter::reportNetDetailedRouteWL")

    def createWLReportFile(self, file_name: str, verbose: bool) -> None:
        _unsupported("GlobalRouter::createWLReportFile")

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


def print_groute(groute: GRoute) -> str:
    """对应 grt::print(GRoute&) 的可测试 Python 版本。"""

    return "\n".join(
        f"({seg.init_x}, {seg.init_y}, {seg.init_layer}) -> "
        f"({seg.final_x}, {seg.final_y}, {seg.final_layer})"
        for seg in groute
    )


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


__all__ = [
    "CapacityReduction",
    "CapacityReductionData",
    "CongestionInformation",
    "CostParams",
    "DebugSetting",
    "FastRouteCore",
    "GRoute",
    "GRouteDbCbk",
    "GSegment",
    "GlobalRouter",
    "Grid",
    "IncrementalGRoute",
    "LayerId",
    "Net",
    "NetRouteMap",
    "NetType",
    "Parent3D",
    "Pin",
    "PinEdge",
    "PinGridLocation",
    "Point",
    "Rect",
    "RegionAdjustment",
    "RoutePointPins",
    "RoutePt",
    "RoutingTracks",
    "SegmentIndex",
    "TileCongestion",
    "TileInformation",
    "TileSet",
    "create_global_router",
    "getITermName",
    "getLayerName",
    "print_groute",
]
