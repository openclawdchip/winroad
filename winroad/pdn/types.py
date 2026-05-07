"""基础类型、枚举、Shape 与共享工具。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

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


def _validate_rect(rect: Rect, name: str = "rect") -> Rect:
    if len(rect) != 4:
        raise ValueError(f"{name} must contain four coordinates")
    lx, ly, ux, uy = (int(value) for value in rect)
    if lx > ux or ly > uy:
        raise ValueError(f"{name} has inverted coordinates: {rect!r}")
    return (lx, ly, ux, uy)


def _validate_halo(halo: Halo, name: str = "halo") -> Halo:
    if len(halo) != 4:
        raise ValueError(f"{name} must contain four offsets")
    normalized = tuple(int(value) for value in halo)
    if any(value < 0 for value in normalized):
        raise ValueError(f"{name} offsets must be non-negative: {halo!r}")
    return normalized  # type: ignore[return-value]


def _validate_non_negative(value: int, name: str) -> int:
    normalized = int(value)
    if normalized < 0:
        raise ValueError(f"{name} must be non-negative")
    return normalized


def _validate_positive(value: int, name: str) -> int:
    normalized = int(value)
    if normalized <= 0:
        raise ValueError(f"{name} must be positive")
    return normalized


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

    def __post_init__(self) -> None:
        if self.layer is None:
            raise ValueError("shape layer is required")
        self.rect = _validate_rect(self.rect)

    def getLayer(self) -> Any:
        return self.layer

    def getNet(self) -> Any:
        return self.net

    def setNet(self, net: Any) -> None:
        self.net = net

    def getRect(self) -> Rect:
        return self.rect

    def setRect(self, rect: Rect) -> None:
        self.rect = _validate_rect(rect)

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
        if via not in self.vias:
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

    def report(self) -> Dict[str, Any]:
        return {
            "layer": _name(self.layer),
            "net": _name(self.net) if self.net is not None else None,
            "rect": self.rect,
            "wire_type": _name(self.wire_type) if self.wire_type is not None else None,
            "shape_type": self.shape_type.value,
            "locked": self.locked,
            "via_count": len(self.vias),
        }

