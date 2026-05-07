"""WinRoad global routing package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .guide import GSegment
from .types import GRoute, PinEdge, Point, Rect, _object_name


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
    alpha: float = 1.0
    beta: float = 1.0
    gamma: float = 1.0
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

    def setAlpha(self, alpha: float) -> None:
        """记录 FastRoute net alpha 参数。"""

        self.alpha = alpha

    def getAlpha(self) -> float:
        """返回 FastRoute net alpha 参数。"""

        return self.alpha

    def setBeta(self, beta: float) -> None:
        """记录 FastRoute net beta 参数。"""

        self.beta = beta

    def getBeta(self) -> float:
        """返回 FastRoute net beta 参数。"""

        return self.beta

    def setGamma(self, gamma: float) -> None:
        """记录 FastRoute net gamma 参数。"""

        self.gamma = gamma

    def getGamma(self) -> float:
        """返回 FastRoute net gamma 参数。"""

        return self.gamma

    def setCostParameters(self, alpha: float, beta: float, gamma: float) -> None:
        """一次性记录 net alpha/beta/gamma。"""

        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def getCostParameters(self) -> Tuple[float, float, float]:
        """返回 net alpha/beta/gamma。"""

        return self.alpha, self.beta, self.gamma

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


