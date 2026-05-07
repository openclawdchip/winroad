"""WinRoad global routing package."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Set, Tuple


Point = Tuple[int, int]
Rect = Tuple[int, int, int, int]
LayerId = int
SegmentIndex = int
GRoute = List["GSegment"]
NetRouteMap = Dict[Any, GRoute]
CapacityReductionData = List[List[List["CapacityReduction"]]]
TileSet = Set[Tuple[int, int]]
NetsPerCongestedArea = Dict[Tuple[int, int, int], Set[Any]]


def _object_name(obj: Any) -> str:
    """返回 OpenDB-like 对象或普通 key 的稳定名称。"""

    if obj is None:
        return ""
    name = getattr(obj, "name", None)
    if name is not None:
        return str(name)
    get_name = getattr(obj, "getName", None)
    if callable(get_name):
        return str(get_name())
    return str(obj)


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


