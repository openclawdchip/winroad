"""OpenROAD pdn 电源网络模块的 Python 翻译骨架。

本文件按 OpenROAD `src/pdn` 的 C++ 源码边界建立 Python 等价对象：

- `PdnGen` 对应 `pdn::PdnGen`，是 Tcl 命令和内部算法的顶层入口。
- `VoltageDomain`、`Grid`、`GridComponent` 及 ring/strap/connect/via
  对象保留 C++ 所需的所有一层对象关系。
- 本轮不触碰 OpenDB 写库，不生成 demo 几何；真实 PDN 生成、修复、
  via 构造、sroute 写线等算法入口均保留同名函数并抛
  `NotImplementedError`。

字段名尽量保留 C++ 成员语义，必要时使用 Python 风格后缀 `_`，
方便后续继续逐文件翻译 `src/pdn`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


Rect = Tuple[int, int, int, int]
Halo = Tuple[int, int, int, int]


class ExtensionMode(Enum):
    """对应 `pdn::ExtensionMode`，控制 stripe/followpin 延伸边界。"""

    CORE = "CORE"
    RINGS = "RINGS"
    BOUNDARY = "BOUNDARY"
    FIXED = "FIXED"


class StartsWith(Enum):
    """对应 `pdn::StartsWith`，决定交替 PG 图形从哪类 net 开始。"""

    GRID = "GRID"
    POWER = "POWER"
    GROUND = "GROUND"


class PowerSwitchNetworkType(Enum):
    """对应 `pdn::PowerSwitchNetworkType`。"""

    STAR = "STAR"
    DAISY = "DAISY"


class GridType(Enum):
    """对应 `pdn::Grid::Type`。"""

    CORE = "Core"
    INSTANCE = "Instance"
    EXISTING = "Existing"


class GridComponentType(Enum):
    """对应 `pdn::GridComponent::Type`。"""

    RING = "Ring"
    STRAP = "Strap"
    FOLLOWPIN = "Followpin"
    PAD_CONNECT = "PadConnect"
    REPAIR_CHANNEL = "RepairChannel"


class ShapeType(Enum):
    """对应 `pdn::Shape::ShapeType`。"""

    SHAPE = "SHAPE"
    GRID_OBS = "GRID_OBS"
    BLOCK_OBS = "BLOCK_OBS"
    MACRO_OBS = "MACRO_OBS"
    OBS = "OBS"
    FIXED = "FIXED"


class FailedViaReason(Enum):
    """对应 `pdn::failedViaReason`。"""

    OBSTRUCTED = "OBSTRUCTED"
    OVERLAPPING = "OVERLAPPING"
    BUILD = "BUILD"
    RIPUP = "RIPUP"
    RECHECK = "RECHECK"
    OTHER = "OTHER"


@dataclass(frozen=True)
class SplitCut:
    """对应 `pdn::Connect::SplitCut`。"""

    pitch: int = 0
    stagger: bool = False


def _normalize_starts_with(value: StartsWith | str | bool) -> StartsWith:
    """兼容 Tcl 字符串、C++ 枚举语义和内部布尔形式。"""

    if isinstance(value, StartsWith):
        return value
    if isinstance(value, bool):
        return StartsWith.POWER if value else StartsWith.GROUND
    upper = value.upper()
    if upper in StartsWith.__members__:
        return StartsWith[upper]
    raise ValueError(f"unknown StartsWith value: {value!r}")


def _starts_with_power(value: StartsWith | str | bool) -> bool:
    """`GRID` 在 C++ 中继承 grid 当前顺序，这里默认按 POWER 处理。"""

    return _normalize_starts_with(value) != StartsWith.GROUND


def _normalize_extension_mode(value: ExtensionMode | str) -> ExtensionMode:
    if isinstance(value, ExtensionMode):
        return value
    upper = value.upper()
    if upper in ExtensionMode.__members__:
        return ExtensionMode[upper]
    raise ValueError(f"unknown ExtensionMode value: {value!r}")


def _normalize_power_switch_network(value: PowerSwitchNetworkType | str) -> PowerSwitchNetworkType:
    if isinstance(value, PowerSwitchNetworkType):
        return value
    upper = value.upper()
    if upper in PowerSwitchNetworkType.__members__:
        return PowerSwitchNetworkType[upper]
    for item in PowerSwitchNetworkType:
        if item.value.upper() == upper:
            return item
    raise ValueError(f"unknown PowerSwitchNetworkType value: {value!r}")


def _rect_intersects(a: Rect, b: Rect) -> bool:
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def _name(obj: Any) -> str:
    """取得 ODB/WinRoad 对象名；不依赖 odb 具体类型。"""

    if obj is None:
        return "None"
    if hasattr(obj, "getName"):
        return str(obj.getName())
    if hasattr(obj, "get_name"):
        return str(obj.get_name())
    return str(getattr(obj, "name", obj))


def _not_implemented(name: str) -> None:
    """统一提示：边界已建立，真实 C++ 算法后续翻译。"""

    raise NotImplementedError(f"pdn::{name} 尚未翻译：本轮只建立源码边界。")


@dataclass
class Shape:
    """对应 `pdn::Shape`，仅保存形状元数据，不构造 OpenDB box。"""

    layer: Any
    net: Any = None
    rect: Rect = (0, 0, 0, 0)
    wire_type: Any = None
    shape_type: ShapeType = ShapeType.SHAPE
    locked: bool = False
    obstruction: Optional[Rect] = None
    vias: List["Via"] = field(default_factory=list)
    iterm_connections: Set[Rect] = field(default_factory=set)
    bterm_connections: Set[Rect] = field(default_factory=set)
    grid_component: Optional["GridComponent"] = None

    def getLayer(self) -> Any:
        return self.layer

    def getNet(self) -> Any:
        return self.net

    def setNet(self, net: Any) -> None:
        self.net = net

    def getRect(self) -> Rect:
        return self.rect

    def setRect(self, rect: Rect) -> None:
        self.rect = rect

    def getLength(self) -> int:
        lx, ly, ux, uy = self.rect
        return max(abs(ux - lx), abs(uy - ly))

    def getWidth(self) -> int:
        lx, ly, ux, uy = self.rect
        return min(abs(ux - lx), abs(uy - ly))

    def isHorizontal(self) -> bool:
        lx, ly, ux, uy = self.rect
        return abs(ux - lx) > abs(uy - ly)

    def isVertical(self) -> bool:
        lx, ly, ux, uy = self.rect
        return abs(ux - lx) < abs(uy - ly)

    def setLocked(self) -> None:
        self.locked = True

    def clearLocked(self) -> None:
        self.locked = False

    def addVia(self, via: "Via") -> None:
        self.vias.append(via)

    def removeVia(self, via: "Via") -> None:
        if via in self.vias:
            self.vias.remove(via)

    def generateObstruction(self) -> None:
        _not_implemented("Shape::generateObstruction")

    def cut(self, obstructions: Any, ignore_grid: Optional["Grid"] = None) -> List["Shape"]:
        _not_implemented("Shape::cut")

    def writeToDb(self, swire: Any, add_pins: bool, make_rect_as_pin: bool) -> List[Any]:
        _not_implemented("Shape::writeToDb")


@dataclass
class Via:
    """对应 `pdn::Via`，记录上下形状交点与失败状态。"""

    connect: "Connect"
    net: Any
    area: Rect
    lower: Optional[Shape]
    upper: Optional[Shape]
    failed: bool = False
    failed_reason: Optional[FailedViaReason] = None

    def getNet(self) -> Any:
        return self.net

    def getArea(self) -> Rect:
        return self.area

    def getLowerShape(self) -> Optional[Shape]:
        return self.lower

    def getUpperShape(self) -> Optional[Shape]:
        return self.upper

    def getConnect(self) -> "Connect":
        return self.connect

    def getGrid(self) -> "Grid":
        return self.connect.getGrid()

    def markFailed(self, reason: FailedViaReason) -> None:
        self.failed = True
        self.failed_reason = reason

    def writeToDb(self, wire: Any, block: Any, obstructions: Any) -> None:
        _not_implemented("Via::writeToDb")


@dataclass
class Enclosure:
    """对应 `pdn::Enclosure`，保留 via enclosure 检查所需字段。"""

    x: int = 0
    y: int = 0
    allow_swap: bool = False

    def check(self, x: int, y: int) -> bool:
        return x >= self.x and y >= self.y

    def snap(self, tech: Any) -> None:
        _not_implemented("Enclosure::snap")


@dataclass
class DbVia:
    """对应 `pdn::DbVia`，所有 OpenDB via 构造留待后续翻译。"""

    generator: Optional["ViaGenerator"] = None

    def generate(self, block: Any, wire: Any, wire_type: Any, x: int, y: int, ongrid: Iterable[Any], logger: Any) -> Any:
        _not_implemented("DbVia::generate")

    def requiresPatch(self) -> bool:
        return False

    def getViaReport(self) -> Dict[str, int]:
        _not_implemented("DbVia::getViaReport")


@dataclass
class DbBaseVia(DbVia):
    """对应 `pdn::DbBaseVia`，TechVia/GenerateVia 的公共计数层。"""

    count: int = 0

    def getName(self) -> str:
        _not_implemented("DbBaseVia::getName")

    def getViaRect(self, include_enclosure: bool, include_via_shape: bool, include_bottom: bool = True, include_top: bool = True) -> Rect:
        _not_implemented("DbBaseVia::getViaRect")

    def getCount(self) -> int:
        return self.count

    def incrementCount(self, count: int = 1) -> None:
        self.count += count

    def getViaReport(self) -> Dict[str, int]:
        try:
            name = self.getName()
        except NotImplementedError:
            name = type(self).__name__
        return {name: self.count}


@dataclass
class DbTechVia(DbBaseVia):
    """对应 `pdn::DbTechVia`，封装固定 dbTechVia 或 via array。"""

    via: Any = None
    rows: int = 1
    row_pitch: int = 0
    cols: int = 1
    col_pitch: int = 0
    required_bottom_enc: Optional[Enclosure] = None
    required_top_enc: Optional[Enclosure] = None

    def requiresPatch(self) -> bool:
        return self.rows > 1 or self.cols > 1


@dataclass
class DbGenerateVia(DbBaseVia):
    """对应 `pdn::DbGenerateVia`，封装 LEF/tech generate via rule。"""

    rect: Rect = (0, 0, 0, 0)
    rule: Any = None
    rows: int = 1
    columns: int = 1
    cut_pitch_x: int = 0
    cut_pitch_y: int = 0
    bottom_enclosure_x: int = 0
    bottom_enclosure_y: int = 0
    top_enclosure_x: int = 0
    top_enclosure_y: int = 0
    bottom: Any = None
    cut: Any = None
    top: Any = None


@dataclass
class DbSplitCutVia(DbVia):
    """对应 `pdn::DbSplitCutVia`，处理 split cut array 组合。"""

    via: Optional[DbBaseVia] = None
    rows: int = 1
    row_pitch: int = 0
    cols: int = 1
    col_pitch: int = 0
    bottom: Any = None
    top: Any = None


@dataclass
class DbArrayVia(DbVia):
    """对应 `pdn::DbArrayVia`，处理 ARRAYSPACING 规则下的 via array。"""

    core_via: Optional[DbBaseVia] = None
    end_of_row: Optional[DbBaseVia] = None
    end_of_column: Optional[DbBaseVia] = None
    end_of_row_column: Optional[DbBaseVia] = None
    rows: int = 1
    columns: int = 1
    array_spacing_x: int = 0
    array_spacing_y: int = 0

    def requiresPatch(self) -> bool:
        return True


@dataclass
class DbGenerateStackedVia(DbVia):
    """对应 `pdn::DbGenerateStackedVia`，封装多层 stacked via。"""

    vias: List[DbVia] = field(default_factory=list)
    bottom: Any = None
    block: Any = None

    def requiresPatch(self) -> bool:
        return any(via.requiresPatch() for via in self.vias)

    def getViaReport(self) -> Dict[str, int]:
        report: Dict[str, int] = {}
        for via in self.vias:
            for name, count in via.getViaReport().items():
                report[name] = report.get(name, 0) + count
        return report


@dataclass
class DbGenerateDummyVia(DbVia):
    """对应 `pdn::DbGenerateDummyVia`，用于记录无法生成 via 的位置。"""

    connect: Optional["Connect"] = None
    shape: Rect = (0, 0, 0, 0)
    bottom: Any = None
    top: Any = None
    add_report: bool = True

    def getViaReport(self) -> Dict[str, int]:
        return {}


@dataclass
class ViaGenerator:
    """对应 `pdn::ViaGenerator`，只保存约束与 cut/via 数组参数。"""

    logger: Any
    lower_rect: Rect
    lower_constraint: Mapping[str, bool]
    upper_rect: Rect
    upper_constraint: Mapping[str, bool]
    cut_pitch_x: int = 0
    cut_pitch_y: int = 0
    max_rows: int = 0
    max_columns: int = 0

    def build(self, bottom_is_internal_layer: bool, top_is_internal_layer: bool) -> bool:
        _not_implemented("ViaGenerator::build")

    def generate(self, block: Any) -> DbVia:
        _not_implemented("ViaGenerator::generate")


@dataclass
class GenerateViaGenerator(ViaGenerator):
    """对应 `pdn::GenerateViaGenerator`。"""

    rule: Any = None


@dataclass
class TechViaGenerator(ViaGenerator):
    """对应 `pdn::TechViaGenerator`。"""

    via: Any = None


@dataclass
class GridComponent:
    """对应 `pdn::GridComponent`，ring/strap/followpin 的公共基类。"""

    grid: "Grid"
    starts_with_power: bool = True
    nets: List[Any] = field(default_factory=list)
    shapes: List[Shape] = field(default_factory=list)

    def getGrid(self) -> "Grid":
        return self.grid

    def setGrid(self, grid: "Grid") -> None:
        self.grid = grid

    def getDomain(self) -> "VoltageDomain":
        return self.grid.getDomain()

    def getShapes(self) -> List[Shape]:
        return list(self.shapes)

    def addShape(self, shape: Shape) -> None:
        shape.grid_component = self
        self.shapes.append(shape)

    def clearShapes(self) -> None:
        self.shapes.clear()

    def getShapeCount(self) -> int:
        return len(self.shapes)

    def setStartWithPower(self, value: bool) -> None:
        self.starts_with_power = value

    def getStartsWithPower(self) -> bool:
        return self.starts_with_power

    def setNets(self, nets: Sequence[Any]) -> None:
        self.nets = list(nets)

    def getNets(self) -> List[Any]:
        if self.nets:
            return list(self.nets)
        return self.grid.getNets(self.starts_with_power)

    def makeShapes(self, other_shapes: Any) -> None:
        _not_implemented(f"{type(self).__name__}::makeShapes")

    def build(self, other_shapes: Any = None, obstructions: Any = None) -> None:
        self.checkLayerSpecifications()
        self.makeShapes(other_shapes)
        self.refineShapes(other_shapes, obstructions)
        if obstructions is not None:
            self.cutShapes(obstructions)

    def refineShapes(self, all_shapes: Any, all_obstructions: Any) -> bool:
        return False

    def cutShapes(self, obstructions: Any) -> None:
        _not_implemented(f"{type(self).__name__}::cutShapes")

    def writeToDb(self, net_map: Mapping[Any, Any], add_pins: bool, convert_layer_to_pin: Iterable[Any]) -> Dict[Shape, List[Any]]:
        _not_implemented("GridComponent::writeToDb")

    def report(self) -> Dict[str, Any]:
        return {
            "type": self.type().value,
            "grid": self.grid.getName(),
            "nets": [_name(net) for net in self.getNets()],
            "shape_count": len(self.shapes),
        }

    def type(self) -> GridComponentType:
        raise NotImplementedError

    def checkLayerSpecifications(self) -> None:
        _not_implemented(f"{type(self).__name__}::checkLayerSpecifications")


@dataclass
class RingLayer:
    """对应 `pdn::Rings::Layer`。"""

    layer: Any = None
    width: int = 0
    spacing: int = 0


@dataclass
class Rings(GridComponent):
    """对应 `pdn::Rings`。"""

    layers: Tuple[RingLayer, RingLayer] = field(default_factory=lambda: (RingLayer(), RingLayer()))
    offset: Halo = (0, 0, 0, 0)
    pad_offset: Halo = (0, 0, 0, 0)
    extend_to_boundary: bool = False
    allow_outside_die: bool = False

    def setOffset(self, offset: Halo) -> None:
        self.offset = tuple(offset)  # type: ignore[assignment]

    def getOffset(self) -> Halo:
        return self.offset

    def setPadOffset(self, offset: Halo) -> None:
        self.pad_offset = tuple(offset)  # type: ignore[assignment]

    def setExtendToBoundary(self, value: bool) -> None:
        self.extend_to_boundary = value

    def setAllowOutsideDieArea(self) -> None:
        self.allow_outside_die = True

    def getLayers(self) -> List[Any]:
        return [layer.layer for layer in self.layers if layer.layer is not None]

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update(
            {
                "layers": [
                    {"layer": _name(layer.layer), "width": layer.width, "spacing": layer.spacing}
                    for layer in self.layers
                ],
                "offset": self.offset,
                "pad_offset": self.pad_offset,
                "extend_to_boundary": self.extend_to_boundary,
                "allow_outside_die": self.allow_outside_die,
            }
        )
        return data

    def type(self) -> GridComponentType:
        return GridComponentType.RING


@dataclass
class Straps(GridComponent):
    """对应 `pdn::Straps`，也作为 stripe 的 Python 边界。"""

    layer: Any = None
    width: int = 0
    pitch: int = 0
    spacing: int = 0
    number_of_straps: int = 0
    offset: int = 0
    snap: bool = False
    extend_mode: ExtensionMode = ExtensionMode.CORE
    strap_start: int = 0
    strap_end: int = 0
    direction: Any = None

    def setOffset(self, offset: int) -> None:
        self.offset = offset

    def setSnapToGrid(self, snap: bool) -> None:
        self.snap = snap

    def setExtend(self, mode: ExtensionMode) -> None:
        self.extend_mode = _normalize_extension_mode(mode)

    def setStrapStartEnd(self, start: int, end: int) -> None:
        self.strap_start = start
        self.strap_end = end

    def getStrapGroupWidth(self) -> int:
        if self.number_of_straps <= 1:
            return self.width
        return self.number_of_straps * self.width + (self.number_of_straps - 1) * self.spacing

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update(
            {
                "layer": _name(self.layer),
                "width": self.width,
                "pitch": self.pitch,
                "spacing": self.spacing,
                "number_of_straps": self.number_of_straps,
                "offset": self.offset,
                "snap": self.snap,
                "extend_mode": self.extend_mode.value,
                "strap_start": self.strap_start,
                "strap_end": self.strap_end,
                "direction": _name(self.direction) if self.direction is not None else None,
            }
        )
        return data

    def type(self) -> GridComponentType:
        return GridComponentType.STRAP


@dataclass
class FollowPins(Straps):
    """对应 `pdn::FollowPins`。"""

    def type(self) -> GridComponentType:
        return GridComponentType.FOLLOWPIN

    def determineWidth(self) -> None:
        _not_implemented("FollowPins::determineWidth")


@dataclass
class PadDirectConnectionStraps(Straps):
    """对应 `pdn::PadDirectConnectionStraps`。"""

    iterm: Any = None
    connect_pad_layers: List[Any] = field(default_factory=list)

    def canConnect(self) -> bool:
        _not_implemented("PadDirectConnectionStraps::canConnect")

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update({"iterm": _name(self.iterm), "connect_pad_layers": [_name(layer) for layer in self.connect_pad_layers]})
        return data

    def type(self) -> GridComponentType:
        return GridComponentType.PAD_CONNECT


@dataclass
class RepairChannelStraps(Straps):
    """对应 `pdn::RepairChannelStraps`。"""

    target: Optional[Straps] = None
    connect_to: Any = None
    area: Rect = (0, 0, 0, 0)
    available_area: Rect = (0, 0, 0, 0)
    obs_check_area: Rect = (0, 0, 0, 0)
    repair_nets: Set[Any] = field(default_factory=set)
    invalid: bool = False

    def type(self) -> GridComponentType:
        return GridComponentType.REPAIR_CHANNEL

    def isRepairValid(self) -> bool:
        return not self.invalid

    def continueRepairs(self, other_shapes: Any) -> None:
        _not_implemented("RepairChannelStraps::continueRepairs")

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update(
            {
                "target": _name(self.target.layer) if self.target is not None else None,
                "connect_to": _name(self.connect_to),
                "area": self.area,
                "available_area": self.available_area,
                "obs_check_area": self.obs_check_area,
                "repair_nets": [_name(net) for net in self.repair_nets],
                "valid": self.isRepairValid(),
            }
        )
        return data

    @staticmethod
    def repairGridChannels(grid: "Grid", global_shapes: Any, obstructions: Any, allow: bool, renderer: Any = None) -> None:
        _not_implemented("RepairChannelStraps::repairGridChannels")


@dataclass
class Connect:
    """对应 `pdn::Connect`，描述两层或多层之间 via 连接规则。"""

    grid: "Grid"
    layer0: Any
    layer1: Any
    fixed_generate_vias: List[Any] = field(default_factory=list)
    fixed_tech_vias: List[Any] = field(default_factory=list)
    cut_pitch_x: int = 0
    cut_pitch_y: int = 0
    max_rows: int = 0
    max_columns: int = 0
    ongrid: Set[Any] = field(default_factory=set)
    split_cuts: Dict[Any, SplitCut] = field(default_factory=dict)
    vias: List[Via] = field(default_factory=list)
    failed_vias: Dict[FailedViaReason, List[Tuple[Any, Rect]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.setSplitCuts(self.split_cuts)

    def addFixedVia(self, via: Any) -> None:
        self.fixed_generate_vias.append(via)

    def addFixedTechVia(self, via: Any) -> None:
        self.fixed_tech_vias.append(via)

    def setCutPitch(self, x: int, y: int) -> None:
        self.cut_pitch_x = x
        self.cut_pitch_y = y

    def setMaxRows(self, rows: int) -> None:
        self.max_rows = rows

    def setMaxColumns(self, cols: int) -> None:
        self.max_columns = cols

    def setOnGrid(self, layers: Sequence[Any]) -> None:
        self.ongrid = set(layers)

    def setSplitCuts(self, splits: Mapping[Any, Any]) -> None:
        self.split_cuts = {layer: self._normalize_split_cut(value) for layer, value in splits.items()}

    def getSplitCut(self, layer: Any) -> SplitCut:
        return self.split_cuts.get(layer, SplitCut())

    def getSplitCutPitch(self, layer: Any) -> int:
        return self.getSplitCut(layer).pitch

    def isSplitCutStaggered(self, layer: Any) -> bool:
        return self.getSplitCut(layer).stagger

    def getLowerLayer(self) -> Any:
        return self.layer0

    def getUpperLayer(self) -> Any:
        return self.layer1

    def isSingleLayerVia(self) -> bool:
        return self.layer0 == self.layer1

    def isMultiLayerVia(self) -> bool:
        return not self.isSingleLayerVia()

    def hasCutPitch(self) -> bool:
        return self.cut_pitch_x != 0 or self.cut_pitch_y != 0

    def setGrid(self, grid: "Grid") -> None:
        self.grid = grid

    def getGrid(self) -> "Grid":
        return self.grid

    def clearShapes(self) -> None:
        self.vias.clear()

    def getVias(self) -> List[Via]:
        return list(self.vias)

    def addVia(self, via: Via) -> None:
        self.vias.append(via)

    def makeVia(self, wire: Any, lower: Shape, upper: Shape, wire_type: Any, via_shapes: Any) -> None:
        _not_implemented("Connect::makeVia")

    def filterVias(self, filter_text: str) -> None:
        _not_implemented("Connect::filterVias")

    def addFailedVia(self, reason: FailedViaReason, rect: Rect, net: Any) -> None:
        self.failed_vias.setdefault(reason, []).append((net, rect))

    def clearFailedVias(self) -> None:
        self.failed_vias.clear()

    def printViaReport(self) -> Dict[str, int]:
        return {reason.value: len(items) for reason, items in self.failed_vias.items()}

    def report(self) -> Dict[str, Any]:
        return {
            "grid": self.grid.getName(),
            "layers": [_name(self.layer0), _name(self.layer1)],
            "fixed_generate_vias": [_name(via) for via in self.fixed_generate_vias],
            "fixed_tech_vias": [_name(via) for via in self.fixed_tech_vias],
            "cut_pitch": (self.cut_pitch_x, self.cut_pitch_y),
            "max_rows": self.max_rows,
            "max_columns": self.max_columns,
            "ongrid": [_name(layer) for layer in self.ongrid],
            "split_cuts": {
                _name(layer): {"pitch": split.pitch, "stagger": split.stagger}
                for layer, split in self.split_cuts.items()
            },
            "via_count": len(self.vias),
            "failed_vias": self.printViaReport(),
        }

    @staticmethod
    def _normalize_split_cut(value: Any) -> SplitCut:
        if isinstance(value, SplitCut):
            return value
        if isinstance(value, Mapping):
            return SplitCut(int(value.get("pitch", 0)), bool(value.get("stagger", False)))
        if isinstance(value, tuple):
            pitch = int(value[0]) if len(value) > 0 else 0
            stagger = bool(value[1]) if len(value) > 1 else False
            return SplitCut(pitch, stagger)
        return SplitCut(int(value), False)


@dataclass
class Grid:
    """对应 `pdn::Grid`，负责持有 ring/strap/connect 组件。"""

    domain: "VoltageDomain"
    name: str
    starts_with_power: bool = True
    generate_obstructions: List[Any] = field(default_factory=list)
    rings: List[Rings] = field(default_factory=list)
    straps: List[Straps] = field(default_factory=list)
    connect: List[Connect] = field(default_factory=list)
    pin_layers: Set[Any] = field(default_factory=set)
    allow_repair_channels: bool = False
    vias: List[Via] = field(default_factory=list)
    switched_power_cell: Optional["GridSwitchedPower"] = None

    def getName(self) -> str:
        return self.name

    def getLongName(self) -> str:
        return self.getName()

    def getDomain(self) -> "VoltageDomain":
        return self.domain

    def setDomain(self, domain: "VoltageDomain") -> None:
        self.domain = domain

    def type(self) -> GridType:
        raise NotImplementedError

    def addRing(self, ring: Rings) -> None:
        ring.setGrid(self)
        self.rings.append(ring)

    def addStrap(self, strap: Straps) -> None:
        strap.setGrid(self)
        self.straps.append(strap)

    def addConnect(self, connect: Connect) -> None:
        connect.setGrid(self)
        self.connect.append(connect)

    def removeStrap(self, strap: Straps) -> None:
        if strap in self.straps:
            self.straps.remove(strap)

    def setPinLayers(self, layers: Sequence[Any]) -> None:
        self.pin_layers = set(layers)

    def getPinLayers(self) -> Set[Any]:
        return set(self.pin_layers)

    def setAllowRepairChannels(self, allow: bool) -> None:
        self.allow_repair_channels = allow

    def getNets(self, starts_with_power: Optional[bool] = None) -> List[Any]:
        return self.domain.getNets(self.starts_with_power if starts_with_power is None else starts_with_power)

    def getRings(self) -> List[Rings]:
        return list(self.rings)

    def getStraps(self) -> List[Straps]:
        return list(self.straps)

    def getConnect(self) -> List[Connect]:
        return list(self.connect)

    def getGridComponents(self) -> List[GridComponent]:
        return [*self.rings, *self.straps]

    def getShapes(self) -> List[Shape]:
        return [shape for component in self.getGridComponents() for shape in component.getShapes()]

    def getVias(self) -> List[Via]:
        return [via for connect in self.connect for via in connect.getVias()]

    def findComponent(self, component_type: Optional[GridComponentType] = None, layer: Any = None) -> List[GridComponent]:
        components = self.getGridComponents()
        if component_type is not None:
            components = [component for component in components if component.type() == component_type]
        if layer is not None:
            components = [
                component
                for component in components
                if (isinstance(component, Rings) and layer in component.getLayers())
                or (isinstance(component, Straps) and component.layer == layer)
            ]
        return components

    def findConnect(self, layer0: Any = None, layer1: Any = None) -> List[Connect]:
        result = self.connect
        if layer0 is not None and layer1 is None:
            result = [connect for connect in result if connect.layer0 == layer0 or connect.layer1 == layer0]
        if layer1 is not None:
            if layer0 is None:
                result = [connect for connect in result if connect.layer0 == layer1 or connect.layer1 == layer1]
            else:
                result = [connect for connect in result if {connect.layer0, connect.layer1} == {layer0, layer1}]
        return list(result)

    def makeShapes(self, global_shapes: Any, obstructions: Any) -> None:
        _not_implemented("Grid::makeShapes")

    def makeVias(self, global_shapes: Any, obstructions: Any, local_obstructions: Any = None) -> None:
        _not_implemented("Grid::makeVias")

    def build(self, global_shapes: Any = None, obstructions: Any = None, local_obstructions: Any = None) -> None:
        self.checkSetup()
        self.makeShapes(global_shapes, obstructions)
        self.makeVias(global_shapes, obstructions, local_obstructions)

    def writeToDb(self, net_map: Mapping[Any, Any], do_pins: bool, obstructions: Any) -> Dict[Shape, List[Any]]:
        _not_implemented("Grid::writeToDb")

    def resetShapes(self) -> None:
        for component in [*self.rings, *self.straps]:
            component.clearShapes()
        for connect in self.connect:
            connect.clearShapes()
        self.vias.clear()

    def ripup(self) -> None:
        self.resetShapes()

    def checkSetup(self) -> None:
        if self.domain is None:
            raise ValueError(f"grid {self.name!r} has no voltage domain")
        for component in self.getGridComponents():
            if component.getGrid() is not self:
                raise ValueError(f"component {component.type().value} is attached to the wrong grid")
        for connect in self.connect:
            if connect.getGrid() is not self:
                raise ValueError(f"connect {_name(connect.layer0)}->{_name(connect.layer1)} is attached to the wrong grid")

    def report(self) -> Dict[str, Any]:
        return {
            "name": self.getLongName(),
            "type": self.type().value,
            "domain": self.domain.getName(),
            "starts_with_power": self.starts_with_power,
            "generate_obstructions": [_name(layer) for layer in self.generate_obstructions],
            "pin_layers": [_name(layer) for layer in self.pin_layers],
            "allow_repair_channels": self.allow_repair_channels,
            "rings": [ring.report() for ring in self.rings],
            "straps": [strap.report() for strap in self.straps],
            "connect": [connect.report() for connect in self.connect],
            "shape_count": len(self.getShapes()),
            "via_count": len(self.getVias()),
            "switched_power_cell": self.switched_power_cell.report() if self.switched_power_cell is not None else None,
        }


@dataclass
class CoreGrid(Grid):
    """对应 `pdn::CoreGrid`。"""

    def type(self) -> GridType:
        return GridType.CORE

    def setupDirectConnect(self, connect_pad_layers: Sequence[Any]) -> None:
        _not_implemented("CoreGrid::setupDirectConnect")


@dataclass
class InstanceGrid(Grid):
    """对应 `pdn::InstanceGrid`，服务 macro/bump/instance grid。"""

    inst: Any = None
    halos: Halo = (0, 0, 0, 0)
    grid_to_boundary: bool = False
    replaceable: bool = False

    def getLongName(self) -> str:
        return f"{self.name}:{_name(self.inst)}"

    def type(self) -> GridType:
        return GridType.INSTANCE

    def getInstance(self) -> Any:
        return self.inst

    def addHalo(self, halos: Halo) -> None:
        self.halos = tuple(halos)  # type: ignore[assignment]

    def setGridToBoundary(self, value: bool) -> None:
        self.grid_to_boundary = value

    def setReplaceable(self, replaceable: bool) -> None:
        self.replaceable = replaceable

    def isReplaceable(self) -> bool:
        return self.replaceable

    def isValid(self) -> bool:
        return self.inst is not None


@dataclass
class BumpGrid(InstanceGrid):
    """对应 `pdn::BumpGrid`。"""

    def isValid(self) -> bool:
        _not_implemented("BumpGrid::isValid")


@dataclass
class ExistingGrid(Grid):
    """对应 `pdn::ExistingGrid`，用于读取已有 SPECIALNET 作为 grid。"""

    pdngen: Optional["PdnGen"] = None
    block: Any = None
    logger: Any = None
    shapes: List[Shape] = field(default_factory=list)

    def type(self) -> GridType:
        return GridType.EXISTING

    def populate(self) -> None:
        _not_implemented("ExistingGrid::populate")


@dataclass
class VoltageDomain:
    """对应 `pdn::VoltageDomain`，维护 power/ground/secondary 与 grids。"""

    pdngen: "PdnGen"
    name: str
    block: Any = None
    power: Any = None
    ground: Any = None
    secondary: List[Any] = field(default_factory=list)
    region: Any = None
    logger: Any = None
    switched_power: Any = None
    grids: List[Grid] = field(default_factory=list)

    def getName(self) -> str:
        return self.name

    def getPower(self) -> Any:
        return self.switched_power if self.switched_power is not None else self.power

    def getGround(self) -> Any:
        return self.ground

    def getAlwaysOnPower(self) -> Any:
        return self.power

    def getSwitchedPower(self) -> Any:
        return self.switched_power

    def setSwitchedPower(self, switched_power: Any) -> None:
        self.switched_power = switched_power

    def hasSwitchedPower(self) -> bool:
        return self.switched_power is not None

    def hasRegion(self) -> bool:
        return self.region is not None

    def getNets(self, start_with_power: bool = True) -> List[Any]:
        power_nets = [net for net in [self.getPower(), *self.secondary] if net is not None]
        ground_nets = [self.ground] if self.ground is not None else []
        return [*power_nets, *ground_nets] if start_with_power else [*ground_nets, *power_nets]

    def addGrid(self, grid: Grid) -> None:
        grid.setDomain(self)
        self.grids.append(grid)

    def resetGrids(self) -> None:
        for grid in self.grids:
            grid.resetShapes()

    def clearGrids(self) -> None:
        self.grids.clear()

    def removeGrid(self, grid: Grid) -> None:
        if grid in self.grids:
            self.grids.remove(grid)

    def getGrids(self) -> List[Grid]:
        return list(self.grids)

    def findGrid(self, name: str) -> List[Grid]:
        return [grid for grid in self.grids if grid.getName() == name or grid.getLongName() == name]

    def getGridByName(self, name: str) -> Optional[Grid]:
        matches = self.findGrid(name)
        return matches[0] if matches else None

    def getDomainArea(self) -> Rect:
        _not_implemented("VoltageDomain::getDomainArea")

    def getRows(self) -> List[Any]:
        _not_implemented("VoltageDomain::getRows")

    def checkSetup(self) -> None:
        if self.power is None and self.switched_power is None:
            raise ValueError(f"voltage domain {self.name!r} has no power net")
        if self.ground is None:
            raise ValueError(f"voltage domain {self.name!r} has no ground net")

    def report(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "power": _name(self.power),
            "switched_power": _name(self.switched_power) if self.switched_power is not None else None,
            "ground": _name(self.ground),
            "secondary": [_name(net) for net in self.secondary],
            "region": _name(self.region) if self.region is not None else None,
            "grids": [grid.report() for grid in self.grids],
        }


@dataclass
class PowerCell:
    """对应 `pdn::PowerCell`，保存 power switch cell 的 master/pin 映射。"""

    logger: Any
    master: Any
    control: Any
    acknowledge: Any
    switched_power: Any
    alwayson_power: Any
    ground: Any
    alwayson_power_positions: Set[int] = field(default_factory=set)

    def getName(self) -> str:
        return _name(self.master)

    def hasAcknowledge(self) -> bool:
        return self.acknowledge is not None

    def appliesToRow(self, row: Any) -> bool:
        _not_implemented("PowerCell::appliesToRow")

    def populateAlwaysOnPinPositions(self, site_width: int) -> None:
        _not_implemented("PowerCell::populateAlwaysOnPinPositions")

    def report(self) -> Dict[str, Any]:
        return {
            "name": self.getName(),
            "control": _name(self.control),
            "acknowledge": _name(self.acknowledge) if self.acknowledge is not None else None,
            "switched_power": _name(self.switched_power),
            "alwayson_power": _name(self.alwayson_power),
            "ground": _name(self.ground),
        }


@dataclass
class GridSwitchedPower:
    """对应 `pdn::GridSwitchedPower`。"""

    grid: Grid
    cell: PowerCell
    control: Any
    network: PowerSwitchNetworkType

    def build(self) -> None:
        _not_implemented("GridSwitchedPower::build")

    def ripup(self) -> None:
        _not_implemented("GridSwitchedPower::ripup")

    def report(self) -> Dict[str, Any]:
        return {
            "grid": self.grid.getName(),
            "cell": self.cell.getName(),
            "control": _name(self.control),
            "network": self.network.value,
        }


@dataclass
class SRoute:
    """对应 `pdn::SRoute`，仅保留 add_sroute_connect 的内部边界。"""

    pdngen: "PdnGen"
    connects: List[Dict[str, Any]] = field(default_factory=list)

    def addSrouteConnect(self, **params: Any) -> Dict[str, Any]:
        self.connects.append(dict(params))
        return self.connects[-1]

    def getSrouteConnects(self) -> List[Dict[str, Any]]:
        return [dict(connect) for connect in self.connects]

    def createSrouteWires(self, *args: Any, **kwargs: Any) -> None:
        _not_implemented("SRoute::createSrouteWires")


@dataclass
class PDNRenderer:
    """对应 `pdn::PDNRenderer`，图形调试后端占位。"""

    enabled: bool = False
    block: Any = None
    logger: Any = None
    grids: List[Grid] = field(default_factory=list)
    selected: List[Any] = field(default_factory=list)

    def setBlock(self, block: Any) -> None:
        self.block = block

    def setLogger(self, logger: Any) -> None:
        self.logger = logger

    def setGrids(self, grids: Sequence[Grid]) -> None:
        self.grids = list(grids)

    def select(self, item: Any) -> None:
        self.selected.append(item)

    def clear(self) -> None:
        self.selected.clear()

    def report(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "block": _name(self.block) if self.block is not None else None,
            "grids": [grid.getLongName() for grid in self.grids],
            "selected_count": len(self.selected),
        }

    def redraw(self) -> None:
        _not_implemented("PDNRenderer::redraw")


@dataclass
class PdnGen:
    """对应 `pdn::PdnGen` 顶层入口。"""

    db: Any = None
    logger: Any = None
    sroute: Optional[SRoute] = None
    debug_renderer: Optional[PDNRenderer] = None
    core_domain: Optional[VoltageDomain] = None
    domains: List[VoltageDomain] = field(default_factory=list)
    switched_power_cells: List[PowerCell] = field(default_factory=list)
    allow_repair_channels: bool = False

    def init(self, db: Any, logger: Any = None) -> None:
        self.db = db
        self.logger = logger
        self.sroute = SRoute(self)

    def reset(self) -> None:
        self.core_domain = None
        self.domains.clear()
        self.switched_power_cells.clear()

    def resetShapes(self) -> None:
        for domain in self.getDomains():
            domain.resetGrids()

    def report(self) -> Dict[str, Any]:
        return {
            "domains": [domain.report() for domain in self.getDomains()],
            "switched_power_cells": [cell.report() for cell in self.switched_power_cells],
            "allow_repair_channels": self.allow_repair_channels,
            "sroute_connects": self.sroute.getSrouteConnects() if self.sroute is not None else [],
            "debug_renderer": self.debug_renderer.report() if self.debug_renderer is not None else None,
        }

    def findSwitchedPowerCell(self, name: str) -> Optional[PowerCell]:
        return next((cell for cell in self.switched_power_cells if cell.getName() == name), None)

    def makeSwitchedPowerCell(self, master: Any, control: Any, acknowledge: Any, switched_power: Any, alwayson_power: Any, ground: Any) -> PowerCell:
        cell = PowerCell(self.logger, master, control, acknowledge, switched_power, alwayson_power, ground)
        self.switched_power_cells.append(cell)
        return cell

    def getDomains(self) -> List[VoltageDomain]:
        domains: List[VoltageDomain] = []
        if self.core_domain is not None:
            domains.append(self.core_domain)
        domains.extend(self.domains)
        return domains

    def findDomain(self, name: str) -> Optional[VoltageDomain]:
        return next((domain for domain in self.getDomains() if domain.getName() == name), None)

    def setCoreDomain(self, power: Any, switched_power: Any, ground: Any, secondary: Sequence[Any] = ()) -> VoltageDomain:
        domain = VoltageDomain(
            pdngen=self,
            name="Core",
            block=self._get_block(),
            power=power,
            ground=ground,
            secondary=list(secondary),
            logger=self.logger,
            switched_power=switched_power,
        )
        self.core_domain = domain
        return domain

    def makeRegionVoltageDomain(self, name: str, power: Any, switched_power: Any, ground: Any, secondary_nets: Sequence[Any], region: Any) -> VoltageDomain:
        domain = VoltageDomain(
            pdngen=self,
            name=name,
            block=self._get_block(),
            power=power,
            ground=ground,
            secondary=list(secondary_nets),
            region=region,
            logger=self.logger,
            switched_power=switched_power,
        )
        self.domains.append(domain)
        return domain

    def buildGrids(self, trim: bool = True) -> None:
        self.checkSetup()
        for domain in self.getDomains():
            for grid in domain.getGrids():
                grid.checkSetup()
        _not_implemented("PdnGen::buildGrids")

    def findGrid(self, name: str) -> List[Grid]:
        return [
            grid
            for domain in self.getDomains()
            for grid in domain.getGrids()
            if grid.getName() == name or grid.getLongName() == name
        ]

    def getGridByName(self, name: str, domain: Optional[VoltageDomain | str] = None) -> Optional[Grid]:
        if isinstance(domain, str):
            domain = self.findDomain(domain)
        domains = [domain] if domain is not None else self.getDomains()
        for voltage_domain in domains:
            if voltage_domain is None:
                continue
            grid = voltage_domain.getGridByName(name)
            if grid is not None:
                return grid
        return None

    def findGridForInstance(self, inst: Any) -> Optional[InstanceGrid]:
        for domain in self.getDomains():
            for grid in domain.getGrids():
                if isinstance(grid, InstanceGrid) and grid.getInstance() is inst:
                    return grid
        return None

    def findGridContainingRect(self, rect: Rect) -> List[Grid]:
        matches: List[Grid] = []
        for domain in self.getDomains():
            for grid in domain.getGrids():
                if any(_rect_intersects(shape.getRect(), rect) for shape in grid.getShapes()):
                    matches.append(grid)
        return matches

    def makeCoreGrid(
        self,
        domain: VoltageDomain,
        name: str,
        starts_with: StartsWith | str | bool = StartsWith.POWER,
        pin_layers: Sequence[Any] = (),
        generate_obstructions: Sequence[Any] = (),
        powercell: Optional[PowerCell] = None,
        powercontrol: Any = None,
        powercontrolnetwork: Optional[str] = None,
    ) -> CoreGrid:
        grid = CoreGrid(domain, name, _starts_with_power(starts_with), list(generate_obstructions))
        grid.setPinLayers(pin_layers)
        if powercell is not None:
            network = _normalize_power_switch_network(powercontrolnetwork or PowerSwitchNetworkType.STAR)
            grid.switched_power_cell = GridSwitchedPower(grid, powercell, powercontrol, network)
        domain.addGrid(grid)
        return grid

    def makeInstanceGrid(
        self,
        domain: VoltageDomain,
        name: str,
        starts_with: StartsWith | str | bool,
        inst: Any,
        halo: Halo = (0, 0, 0, 0),
        pg_pins_to_boundary: bool = False,
        default_grid: bool = False,
        generate_obstructions: Sequence[Any] = (),
        is_bump: bool = False,
    ) -> InstanceGrid:
        cls = BumpGrid if is_bump else InstanceGrid
        grid = cls(domain, name, _starts_with_power(starts_with), list(generate_obstructions), inst=inst)
        grid.addHalo(halo)
        grid.setGridToBoundary(pg_pins_to_boundary)
        grid.setReplaceable(default_grid)
        domain.addGrid(grid)
        return grid

    def makeExistingGrid(self, name: str, generate_obstructions: Sequence[Any] = ()) -> ExistingGrid:
        domain = VoltageDomain(self, f"{name}_domain", self._get_block(), logger=self.logger)
        grid = ExistingGrid(domain, name, True, list(generate_obstructions), pdngen=self, block=self._get_block(), logger=self.logger)
        domain.addGrid(grid)
        self.domains.append(domain)
        return grid

    def makeRing(
        self,
        grid: Grid,
        layer0: Any,
        width0: int,
        spacing0: int,
        layer1: Any,
        width1: int,
        spacing1: int,
        starts_with: StartsWith | str | bool = StartsWith.GRID,
        offset: Halo = (0, 0, 0, 0),
        pad_offset: Halo = (0, 0, 0, 0),
        extend: bool = False,
        pad_pin_layers: Sequence[Any] = (),
        nets: Sequence[Any] = (),
        allow_out_of_die: bool = False,
    ) -> Rings:
        ring = Rings(
            grid=grid,
            starts_with_power=_starts_with_power(starts_with),
            nets=list(nets),
            layers=(RingLayer(layer0, width0, spacing0), RingLayer(layer1, width1, spacing1)),
            offset=offset,
            pad_offset=pad_offset,
            extend_to_boundary=extend,
            allow_outside_die=allow_out_of_die,
        )
        grid.addRing(ring)
        if pad_pin_layers:
            _not_implemented("PdnGen::makeRing pad direct connection")
        return ring

    def makeFollowpin(self, grid: Grid, layer: Any, width: int = 0, extend: ExtensionMode = ExtensionMode.CORE) -> FollowPins:
        followpin = FollowPins(grid=grid, layer=layer, width=width, pitch=0, extend_mode=extend)
        grid.addStrap(followpin)
        return followpin

    def makeStrap(
        self,
        grid: Grid,
        layer: Any,
        width: int,
        spacing: int,
        pitch: int,
        offset: int,
        number_of_straps: int,
        snap: bool,
        starts_with: StartsWith | str | bool,
        extend: ExtensionMode,
        nets: Sequence[Any] = (),
    ) -> Straps:
        strap = Straps(
            grid=grid,
            starts_with_power=_starts_with_power(starts_with),
            nets=list(nets),
            layer=layer,
            width=width,
            pitch=pitch,
            spacing=spacing,
            number_of_straps=number_of_straps,
            offset=offset,
            snap=snap,
            extend_mode=extend,
        )
        grid.addStrap(strap)
        return strap

    def makeConnect(
        self,
        grid: Grid,
        layer0: Any,
        layer1: Any,
        cut_pitch_x: int = 0,
        cut_pitch_y: int = 0,
        vias: Sequence[Any] = (),
        techvias: Sequence[Any] = (),
        max_rows: int = 0,
        max_columns: int = 0,
        ongrid: Sequence[Any] = (),
        split_cuts: Mapping[Any, Any] = {},
        dont_use_vias: str = "",
    ) -> Connect:
        connect = Connect(grid, layer0, layer1, list(vias), list(techvias), cut_pitch_x, cut_pitch_y, max_rows, max_columns, set(ongrid), dict(split_cuts))
        grid.addConnect(connect)
        if dont_use_vias:
            connect.filterVias(dont_use_vias)
        return connect

    def writeToDb(self, add_pins: bool, report_file: str = "") -> None:
        self.checkSetup()
        _not_implemented("PdnGen::writeToDb")

    def ripUp(self, net: Any) -> None:
        _not_implemented("PdnGen::ripUp")

    def setDebugRenderer(self, on: bool) -> None:
        self.debug_renderer = PDNRenderer(on, block=self._get_block(), logger=self.logger) if on else None
        if self.debug_renderer is not None:
            self.debug_renderer.setGrids([grid for domain in self.getDomains() for grid in domain.getGrids()])

    def rendererRedraw(self) -> None:
        if self.debug_renderer is not None:
            self.debug_renderer.redraw()

    def setAllowRepairChannels(self, allow: bool) -> None:
        self.allow_repair_channels = allow
        for domain in self.getDomains():
            for grid in domain.getGrids():
                grid.setAllowRepairChannels(allow)

    def filterVias(self, filter_text: str) -> None:
        for domain in self.getDomains():
            for grid in domain.getGrids():
                for connect in grid.getConnect():
                    connect.filterVias(filter_text)

    def checkSetup(self) -> None:
        if self.db is None:
            raise ValueError("PdnGen has not been initialized with db")
        for domain in self.getDomains():
            domain.checkSetup()
            for grid in domain.getGrids():
                grid.checkSetup()

    def repairVias(self, nets: Set[Any]) -> None:
        self.checkSetup()
        _not_implemented("PdnGen::repairVias")

    def addSrouteConnect(self, **params: Any) -> Dict[str, Any]:
        if self.sroute is None:
            self.sroute = SRoute(self)
        return self.sroute.addSrouteConnect(**params)

    def createSrouteWires(self, *args: Any, **kwargs: Any) -> None:
        if self.sroute is None:
            self.sroute = SRoute(self)
        self.sroute.createSrouteWires(*args, **kwargs)

    def trimShapes(self) -> None:
        _not_implemented("PdnGen::trimShapes")

    def updateVias(self) -> None:
        _not_implemented("PdnGen::updateVias")

    def cleanupVias(self) -> None:
        _not_implemented("PdnGen::cleanupVias")

    def checkDesign(self, block: Any) -> None:
        _not_implemented("PdnGen::checkDesign")

    def ensureCoreDomain(self) -> VoltageDomain:
        if self.core_domain is None:
            _not_implemented("PdnGen::ensureCoreDomain")
        return self.core_domain

    def updateRenderer(self) -> None:
        if self.debug_renderer is not None:
            self.debug_renderer.redraw()

    def importUPF(self, target: Any, network_type: Optional[PowerSwitchNetworkType] = None) -> bool:
        _not_implemented("PdnGen::importUPF")

    def _get_block(self) -> Any:
        if self.db is None:
            return None
        chip = getattr(self.db, "chip", None)
        if chip is not None and hasattr(chip, "get_top_block"):
            return chip.get_top_block()
        if chip is not None:
            top = getattr(chip, "top", None)
            return getattr(chip, "blocks", {}).get(top) if top is not None else None
        return getattr(self.db, "block", None)


def make_pdn_gen(db: Any = None, logger: Any = None) -> PdnGen:
    """对应 `makePdnGen/initPdnGen` 的 Python 便捷入口。"""

    pdngen = PdnGen()
    pdngen.init(db, logger)
    return pdngen


def initPdnGen(pdngen: PdnGen, db: Any, logger: Any = None) -> None:
    """对应 `ord::initPdnGen`。"""

    pdngen.init(db, logger)


def makePdnGen() -> PdnGen:
    """对应 `ord::makePdnGen`。"""

    return PdnGen()


def deletePdnGen(pdngen: PdnGen) -> None:
    """对应 `ord::deletePdnGen`；Python 由 GC 管理，这里清空状态。"""

    pdngen.reset()


def pdngen(pdngen_obj: PdnGen, skip_trim: bool = False, dont_add_pins: bool = False, reset: bool = False, ripup: bool = False, report_only: bool = False, failed_via_report: str = "") -> Any:
    """对应 Tcl `pdngen` 命令。"""

    if reset:
        pdngen_obj.resetShapes()
    if report_only:
        return pdngen_obj.report()
    if ripup:
        _not_implemented("pdngen -ripup")
    pdngen_obj.buildGrids(trim=not skip_trim)
    pdngen_obj.writeToDb(add_pins=not dont_add_pins, report_file=failed_via_report)
    return None


def report_power_grid(pdngen_obj: PdnGen) -> Dict[str, Any]:
    """报告当前 Python PDN 对象树；不读取或写入 ODB。"""

    return pdngen_obj.report()


def check_power_grid(pdngen_obj: PdnGen) -> None:
    """对应 setup/check 边界，只检查已建对象必要关系。"""

    pdngen_obj.checkSetup()


def repair_pdn_vias(pdngen_obj: PdnGen, nets: Iterable[Any]) -> None:
    """对应 Tcl `repair_pdn_vias`。"""

    pdngen_obj.repairVias(set(nets))


def ripup_power_grid(pdngen_obj: PdnGen, net: Any) -> None:
    """对应 Tcl ripup 边界。"""

    pdngen_obj.ripUp(net)


def write_power_grid(pdngen_obj: PdnGen, add_pins: bool = True, report_file: str = "") -> None:
    """对应写库边界；真实 OpenDB 写入后续翻译。"""

    pdngen_obj.writeToDb(add_pins=add_pins, report_file=report_file)
