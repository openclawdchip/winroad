"""WinRoad global routing package."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

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


def _layer_to_int(token: Any) -> int:
    """解析数字层或 ``M2``/``metal2`` 这类轻量层名。"""

    if isinstance(token, int):
        return token
    text = str(token).strip()
    try:
        return int(text)
    except ValueError:
        match = re.search(r"(\d+)$", text)
        if match:
            return int(match.group(1))
        raise ValueError(f"无法解析 routing layer: {text!r}") from None


def _segment_from_any(data: Any) -> GSegment:
    """把 dict/list/GSegment 恢复为 GSegment。"""

    if isinstance(data, GSegment):
        return data
    if isinstance(data, dict):
        if {"rect", "layer"} <= set(data):
            x1, y1, x2, y2 = data["rect"]
            layer = _layer_to_int(data["layer"])
            via_layer = data.get("via_layer", layer)
            return GSegment(int(x1), int(y1), layer, int(x2), int(y2), _layer_to_int(via_layer))
        return GSegment.fromDict(data)
    if isinstance(data, (list, tuple)) and len(data) >= 6:
        values = [int(value) for value in data[:6]]
        return GSegment(*values)
    raise TypeError(f"无法转换为 GSegment: {data!r}")


@dataclass
class Guide:
    """单个 net 的 guide/segment 集合。"""

    net: str
    segments: GRoute = field(default_factory=list)

    def toDict(self) -> Dict[str, Any]:
        return {"net": self.net, "segments": [segment.toDict() for segment in self.segments]}

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "Guide":
        return cls(str(data.get("net", "")), [_segment_from_any(seg) for seg in data.get("segments", [])])

    def toGuideText(self) -> str:
        """写出 OpenROAD guide 风格的轻量文本。"""

        lines = [self.net, "("]
        for segment in self.segments:
            lines.append(
                f"  {segment.init_x} {segment.init_y} "
                f"{segment.final_x} {segment.final_y} {segment.init_layer}"
            )
            if segment.init_layer != segment.final_layer:
                lines.append(
                    f"  {segment.final_x} {segment.final_y} "
                    f"{segment.final_x} {segment.final_y} {segment.final_layer}"
                )
        lines.append(")")
        return "\n".join(lines)


@dataclass
class GuideFile:
    """WinRoad 轻量 guide 文件，可在 JSON 与可读文本间 round-trip。"""

    guides: List[Guide] = field(default_factory=list)
    format: str = "winroad-grt-routes"
    version: int = 1

    def toDict(self) -> Dict[str, Any]:
        return {
            "format": self.format,
            "version": self.version,
            "routes": [guide.toDict() for guide in self.guides],
        }

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "GuideFile":
        return cls([Guide.fromDict(item) for item in data.get("routes", [])])

    def toJson(self, **dump_kwargs: Any) -> str:
        kwargs = {"indent": 2}
        kwargs.update(dump_kwargs)
        return json.dumps(self.toDict(), **kwargs) + "\n"

    def toGuideText(self) -> str:
        return "\n".join(guide.toGuideText() for guide in self.guides) + ("\n" if self.guides else "")

    @classmethod
    def fromText(cls, text: str) -> "GuideFile":
        stripped = text.strip()
        if not stripped:
            return cls()
        if stripped[0] == "{":
            return cls.fromDict(json.loads(stripped))
        return cls(_parse_plain_guides(stripped.splitlines()))


def _parse_plain_guides(lines: Iterable[str]) -> List[Guide]:
    guides: List[Guide] = []
    current: Optional[Guide] = None
    in_block = False
    for line_no, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "(":
            if current is None:
                raise ValueError(f"guide:{line_no}: '(' 前缺少 net 名")
            in_block = True
            continue
        if line == ")":
            if current is not None:
                guides.append(current)
            current = None
            in_block = False
            continue
        if line.endswith(":"):
            if current is not None:
                guides.append(current)
            current = Guide(line[:-1].strip())
            in_block = True
            continue

        tokens = line.replace("(", " ").replace(")", " ").split()
        if len(tokens) == 1 and not in_block:
            if current is not None:
                guides.append(current)
            current = Guide(tokens[0])
            continue

        if in_block and len(tokens) == 5:
            if current is None:
                raise ValueError(f"guide:{line_no}: guide 矩形缺少 net 名")
            x1, y1, x2, y2 = [int(token) for token in tokens[:4]]
            layer = _layer_to_int(tokens[4])
            current.segments.append(GSegment(x1, y1, layer, x2, y2, layer))
            continue

        net_name, segment = GSegment.fromGuideTokens(tokens)
        if net_name is not None:
            if current is not None and current.net != net_name:
                guides.append(current)
                current = None
            current = current or Guide(net_name)
        if current is None:
            raise ValueError(f"guide:{line_no}: guide 行缺少 net 名")
        current.segments.append(segment)

    if current is not None:
        guides.append(current)
    return guides


def routes_to_guide_file(route_map: Dict[Any, GRoute], name_resolver: Callable[[Any], str]) -> GuideFile:
    """把 route map 转为 GuideFile。"""

    return GuideFile([Guide(name_resolver(net), list(route)) for net, route in route_map.items()])


def print_groute(groute: GRoute) -> str:
    """对应 grt::print(GRoute&) 的可测试 Python 版本。"""

    return "\n".join(
        f"({seg.init_x}, {seg.init_y}, {seg.init_layer}) -> "
        f"({seg.final_x}, {seg.final_y}, {seg.final_layer})"
        for seg in groute
    )
