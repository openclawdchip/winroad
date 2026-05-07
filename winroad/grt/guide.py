"""WinRoad global routing package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple

from .types import GRoute, RoutePt


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

    def toDict(self) -> Dict[str, Any]:
        """序列化为 guide/segment 文件中使用的轻量字典。"""

        return {
            "init_x": self.init_x,
            "init_y": self.init_y,
            "init_layer": self.init_layer,
            "final_x": self.final_x,
            "final_y": self.final_y,
            "final_layer": self.final_layer,
            "is_jumper": self.is_jumper,
            "is_3d_route": self.is_3d_route,
        }

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "GSegment":
        """从 ``toDict`` 的结果恢复 GSegment。"""

        return cls(
            int(data.get("init_x", 0)),
            int(data.get("init_y", 0)),
            int(data.get("init_layer", 0)),
            int(data.get("final_x", 0)),
            int(data.get("final_y", 0)),
            int(data.get("final_layer", 0)),
            bool(data.get("is_jumper", False)),
            bool(data.get("is_3d_route", False)),
        )

    def toGuideLine(self, net_name: str = "") -> str:
        """写出可读的 WinRoad guide 行。"""

        prefix = f"{net_name} " if net_name else ""
        flags = []
        if self.is_jumper:
            flags.append("jumper")
        if self.is_3d_route:
            flags.append("3d")
        suffix = (" " + " ".join(flags)) if flags else ""
        return (
            f"{prefix}{self.init_x} {self.init_y} {self.init_layer} "
            f"{self.final_x} {self.final_y} {self.final_layer}{suffix}"
        )

    @classmethod
    def fromGuideTokens(cls, tokens: Sequence[str]) -> Tuple[Optional[str], "GSegment"]:
        """解析 ``toGuideLine`` 风格的行，返回可选 net 名和 segment。"""

        if len(tokens) < 6:
            raise ValueError("guide segment 至少需要 6 个坐标/层字段")
        offset = 0
        net_name: Optional[str] = None
        try:
            int(tokens[0])
        except ValueError:
            if len(tokens) < 7:
                raise ValueError("带 net 名的 guide 行至少需要 7 个字段")
            net_name = tokens[0]
            offset = 1
        values = [int(token) for token in tokens[offset : offset + 6]]
        flags = {token.lower() for token in tokens[offset + 6 :]}
        return net_name, cls(*values, is_jumper="jumper" in flags, is_3d_route="3d" in flags)



def print_groute(groute: GRoute) -> str:
    """对应 grt::print(GRoute&) 的可测试 Python 版本。"""

    return "\n".join(
        f"({seg.init_x}, {seg.init_y}, {seg.init_layer}) -> "
        f"({seg.final_x}, {seg.final_y}, {seg.final_layer})"
        for seg in groute
    )
