"""Shared CTS utility types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


def _not_translated(name: str) -> None:
    """标记尚未从 C++ 翻译的 CTS 算法边界。"""

    raise NotImplementedError(f"OpenROAD cts::{name} 尚未翻译为 Python")


def fuzzyEqual(lhs: float, rhs: float, eps: float = 1.0e-9) -> bool:
    """对应 `Util.h` 的浮点近似相等判断。"""

    return abs(lhs - rhs) <= eps


def fuzzyEqualOrGreater(lhs: float, rhs: float, eps: float = 1.0e-9) -> bool:
    """对应 `Util.h` 的近似大于等于判断。"""

    return lhs > rhs or fuzzyEqual(lhs, rhs, eps)


def fuzzyEqualOrSmaller(lhs: float, rhs: float, eps: float = 1.0e-9) -> bool:
    """对应 `Util.h` 的近似小于等于判断。"""

    return lhs < rhs or fuzzyEqual(lhs, rhs, eps)


@dataclass(frozen=True)
class Point:
    """对应 CTS `Point<T>`。"""

    x: float = 0.0
    y: float = 0.0

    def getX(self) -> float:
        return self.x

    def getY(self) -> float:
        return self.y

    def computeDist(self, other: "Point") -> float:
        """CTS 使用的 Manhattan 距离。"""

        return abs(self.x - other.x) + abs(self.y - other.y)


@dataclass
class Box:
    """对应 CTS `Box<T>`。"""

    x_min: float = 0.0
    y_min: float = 0.0
    x_max: float = 0.0
    y_max: float = 0.0

    def contains(self, point: Point) -> bool:
        return (
            fuzzyEqualOrGreater(point.x, self.x_min)
            and fuzzyEqualOrSmaller(point.x, self.x_max)
            and fuzzyEqualOrGreater(point.y, self.y_min)
            and fuzzyEqualOrSmaller(point.y, self.y_max)
        )


class InstType(Enum):
    """对应 `InstType`。"""

    CLOCK_BUFFER = "clock_buffer"
    CLOCK_SINK = "clock_sink"


class TreeType(Enum):
    """对应 `TreeType`。"""

    REGULAR_TREE = "regular"
    MACRO_TREE = "macro"
    REGISTER_TREE = "register"


class MasterType(Enum):
    """对应 `CtsOptions::MasterType`。"""

    DUMMY = "dummy"
    TREE = "tree"


class NdrStrategy(Enum):
    """对应 CTS NDR 策略选项。"""

    NONE = "none"
    ROOT_ONLY = "root_only"
    HALF = "half"
    FULL = "full"
