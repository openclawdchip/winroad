"""Buffered net tree data structures for :mod:`winroad.rsz`."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import inf
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from .common import BufferedNetType, Point, _json_value, _not_translated


@dataclass(frozen=True)
class FixedDelay:
    """BufferedNet 重缓冲使用的定点 delay。

    C++ 中用 femtoseconds 存整数，这里保留同样单位，避免 float 估算扩散到
    比较、加减等关键路径。
    """

    value_fs: int = 0
    second: float = 1.0e15

    @classmethod
    def from_seconds(cls, delay: float) -> "FixedDelay":
        return cls(int(delay * cls.second))

    @classmethod
    def from_fs(cls, value_fs: int) -> "FixedDelay":
        return cls(value_fs)

    def toSeconds(self) -> float:
        return self.value_fs / self.second

    def __add__(self, rhs: "FixedDelay") -> "FixedDelay":
        return FixedDelay.from_fs(self.value_fs + rhs.value_fs)

    def __sub__(self, rhs: "FixedDelay") -> "FixedDelay":
        return FixedDelay.from_fs(self.value_fs - rhs.value_fs)

    def __neg__(self) -> "FixedDelay":
        return FixedDelay.from_fs(-self.value_fs)

    def __lt__(self, rhs: "FixedDelay") -> bool:
        return self.value_fs < rhs.value_fs

    def __le__(self, rhs: "FixedDelay") -> bool:
        return self.value_fs <= rhs.value_fs

    def __gt__(self, rhs: "FixedDelay") -> bool:
        return self.value_fs > rhs.value_fs

    def __ge__(self, rhs: "FixedDelay") -> bool:
        return self.value_fs >= rhs.value_fs

    @staticmethod
    def lerp(a: "FixedDelay", b: "FixedDelay", t: float) -> "FixedDelay":
        if t == 1.0:
            return b
        return a + FixedDelay.from_fs(int((b.value_fs - a.value_fs) * t))

FixedDelay.INF = FixedDelay.from_seconds(100.0)  # type: ignore[attr-defined]
FixedDelay.ZERO = FixedDelay.from_fs(0)  # type: ignore[attr-defined]


@dataclass
class BufferedNetMetrics:
    """``BufferedNet::Metrics`` 的 Python 对应物。"""

    max_load_wl: int
    slack: FixedDelay = field(default_factory=lambda: FixedDelay.ZERO)
    cap: float = 0.0
    max_load_slew: float = inf
    fanout: float = 1.0

    def withMaxLoadWl(self, max_load_wl: int) -> "BufferedNetMetrics":
        return BufferedNetMetrics(max_load_wl, self.slack, self.cap, self.max_load_slew, self.fanout)

    def withSlack(self, slack: FixedDelay) -> "BufferedNetMetrics":
        return BufferedNetMetrics(self.max_load_wl, slack, self.cap, self.max_load_slew, self.fanout)

    def withCap(self, cap: float) -> "BufferedNetMetrics":
        return BufferedNetMetrics(self.max_load_wl, self.slack, cap, self.max_load_slew, self.fanout)

    def withMaxLoadSlew(self, max_load_slew: float) -> "BufferedNetMetrics":
        return BufferedNetMetrics(self.max_load_wl, self.slack, self.cap, max_load_slew, self.fanout)

    def withFanout(self, fanout: float) -> "BufferedNetMetrics":
        return BufferedNetMetrics(self.max_load_wl, self.slack, self.cap, self.max_load_slew, fanout)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "max_load_wl": self.max_load_wl,
            "slack_fs": self.slack.value_fs,
            "slack": self.slack.toSeconds(),
            "cap": self.cap,
            "max_load_slew": self.max_load_slew,
            "fanout": self.fanout,
        }

@dataclass
class BufferedNet:
    """修复/重缓冲阶段使用的二叉 routing tree 节点。

    C++ 注释里说明：叶子是 load，junction 是 Steiner 点，root 是 net source。
    ``WIRE``/``VIA``/``BUFFER``/``JUNCTION`` 节点通过 ``ref`` 和 ``ref2`` 指向
    下游，算法会沿树累计 cap、fanout、slack 和 delay。
    """

    type_: BufferedNetType
    location_: Point
    load_pin_: Any = None
    buffer_cell_: Any = None
    layer_: int = -1
    ref_layer_: int = -1
    ref_: Optional["BufferedNet"] = None
    ref2_: Optional["BufferedNet"] = None
    corner_: Any = None
    cap_: float = 0.0
    fanout_: float = 1.0
    max_load_slew_: float = inf
    area_: float = 0.0
    slack_transitions_: Any = None
    slack_: FixedDelay = field(default_factory=lambda: FixedDelay.ZERO)
    delay_: FixedDelay = field(default_factory=lambda: FixedDelay.ZERO)
    arrival_delay_: FixedDelay = field(default_factory=lambda: FixedDelay.ZERO)

    null_layer: int = -1

    def type(self) -> BufferedNetType:
        return self.type_

    def location(self) -> Point:
        return self.location_

    def cap(self) -> float:
        return self.cap_

    def setCapacitance(self, cap: float) -> None:
        self.cap_ = cap

    def fanout(self) -> float:
        return self.fanout_

    def setFanout(self, fanout: float) -> None:
        self.fanout_ = fanout

    def maxLoadSlew(self) -> float:
        return self.max_load_slew_

    def setMaxLoadSlew(self, max_slew: float) -> None:
        self.max_load_slew_ = max_slew

    def loadPin(self) -> Any:
        return self.load_pin_

    def isLeaf(self) -> bool:
        return self.ref_ is None and self.ref2_ is None

    def children(self) -> List["BufferedNet"]:
        children = []
        if self.ref_ is not None:
            children.append(self.ref_)
        if self.ref2_ is not None:
            children.append(self.ref2_)
        return children

    def setRef(self, ref: Optional["BufferedNet"]) -> None:
        self.ref_ = ref

    def setRef2(self, ref2: Optional["BufferedNet"]) -> None:
        self.ref2_ = ref2

    def setRefs(self, ref: Optional["BufferedNet"], ref2: Optional["BufferedNet"] = None) -> None:
        self.ref_ = ref
        self.ref2_ = ref2

    def length(self) -> int:
        """返回本 wire 到 ref 节点的 Manhattan 长度。"""

        if self.ref_ is None:
            return 0
        x1, y1 = self.location_
        x2, y2 = self.ref_.location()
        return abs(x1 - x2) + abs(y1 - y2)

    def wireRC(self, *_args: Any, **_kwargs: Any) -> Tuple[float, float]:
        _not_translated("BufferedNet::wireRC")

    def viaResistance(self, *_args: Any, **_kwargs: Any) -> float:
        _not_translated("BufferedNet::viaResistance")

    def layer(self) -> int:
        return self.layer_

    def refLayer(self) -> int:
        return self.ref_layer_

    def bufferCell(self) -> Any:
        return self.buffer_cell_

    def ref(self) -> Optional["BufferedNet"]:
        return self.ref_

    def ref2(self) -> Optional["BufferedNet"]:
        return self.ref2_

    def childLength(self, child: "BufferedNet") -> int:
        x1, y1 = self.location_
        x2, y2 = child.location()
        return abs(x1 - x2) + abs(y1 - y2)

    def maxLoadWireLength(self) -> int:
        """返回从该节点向下到任一 load 的最大 wire 长度。"""

        child_lengths = []
        if self.ref_ is not None:
            child_lengths.append(self.childLength(self.ref_) + self.ref_.maxLoadWireLength())
        if self.ref2_ is not None:
            child_lengths.append(self.childLength(self.ref2_) + self.ref2_.maxLoadWireLength())
        return max(child_lengths, default=0)

    def slackTransition(self) -> Any:
        return self.slack_transitions_

    def setSlackTransition(self, transitions: Any) -> None:
        self.slack_transitions_ = transitions

    def slack(self) -> FixedDelay:
        return self.slack_

    def setSlack(self, slack: FixedDelay) -> None:
        self.slack_ = slack

    def delay(self) -> FixedDelay:
        return self.delay_

    def setDelay(self, delay: FixedDelay) -> None:
        self.delay_ = delay

    def arrivalDelay(self) -> FixedDelay:
        return self.arrival_delay_

    def setArrivalDelay(self, delay: FixedDelay) -> None:
        self.arrival_delay_ = delay

    def bufferCount(self) -> int:
        count = 1 if self.type_ is BufferedNetType.BUFFER else 0
        if self.ref_ is not None:
            count += self.ref_.bufferCount()
        if self.ref2_ is not None:
            count += self.ref2_.bufferCount()
        return count

    def loadCount(self) -> int:
        if self.type_ is BufferedNetType.LOAD:
            return 1
        count = 0
        if self.ref_ is not None:
            count += self.ref_.loadCount()
        if self.ref2_ is not None:
            count += self.ref2_.loadCount()
        return count

    def nodeCount(self) -> int:
        return 1 + sum(child.nodeCount() for child in self.children())

    def totalWireLength(self) -> int:
        return sum(self.childLength(child) + child.totalWireLength() for child in self.children())

    def depth(self) -> int:
        return 1 + max((child.depth() for child in self.children()), default=0)

    def preorder(self) -> Iterator["BufferedNet"]:
        yield self
        for child in self.children():
            yield from child.preorder()

    def postorder(self) -> Iterator["BufferedNet"]:
        for child in self.children():
            yield from child.postorder()
        yield self

    def area(self) -> float:
        return self.area_

    def metrics(self) -> BufferedNetMetrics:
        return BufferedNetMetrics(
            self.maxLoadWireLength(),
            self.slack(),
            self.cap(),
            self.maxLoadSlew(),
            self.fanout(),
        )

    def fitsEnvelope(self, target: BufferedNetMetrics) -> bool:
        return (
            self.maxLoadWireLength() <= target.max_load_wl
            and self.slack() >= target.slack
            and self.cap() <= target.cap
            and self.maxLoadSlew() <= target.max_load_slew
            and self.fanout() <= target.fanout
        )

    def corner(self) -> Any:
        return self.corner_

    def as_dict(self, include_children: bool = True) -> Dict[str, Any]:
        data = {
            "type": self.type_.value,
            "location": _json_value(self.location_),
            "load_pin": _json_value(self.load_pin_),
            "buffer_cell": _json_value(self.buffer_cell_),
            "layer": self.layer_,
            "ref_layer": self.ref_layer_,
            "cap": self.cap_,
            "fanout": self.fanout_,
            "max_load_slew": self.max_load_slew_,
            "area": self.area_,
            "slack_fs": self.slack_.value_fs,
            "delay_fs": self.delay_.value_fs,
            "arrival_delay_fs": self.arrival_delay_.value_fs,
            "buffer_count": self.bufferCount(),
            "load_count": self.loadCount(),
            "node_count": self.nodeCount(),
            "total_wire_length": self.totalWireLength(),
            "max_load_wire_length": self.maxLoadWireLength(),
        }
        if include_children:
            data["children"] = [child.as_dict(True) for child in self.children()]
        return data

    def serialize(self, include_children: bool = True) -> Dict[str, Any]:
        """返回 JSON-safe tree snapshot。

        名称沿用序列化语义，和 ``as_dict`` 保持同一结构，方便调用方既可直接
        比较 dict，也可进一步 dump 成 JSON。
        """

        return self.as_dict(include_children)

    def to_json(self, include_children: bool = True, **json_kwargs: Any) -> str:
        kwargs = {"sort_keys": True}
        kwargs.update(json_kwargs)
        return json.dumps(self.serialize(include_children), **kwargs)

    def to_string(self, _resizer: Optional["Resizer"] = None) -> str:
        return f"{self.type_.value}@{self.location_}"

    def reportTree(self, resizer: Optional["Resizer"] = None, level: int = 0, include_metrics: bool = True) -> str:
        """返回树形文本，替代 C++ 里直接打 logger 的 report。"""

        indent = "  " * level
        if include_metrics:
            annotation = (
                f" cap={self.cap_} fanout={self.fanout_}"
                f" slew={self.max_load_slew_} slack_fs={self.slack_.value_fs}"
                f" delay_fs={self.delay_.value_fs}"
            )
        else:
            annotation = ""
        lines = [f"{indent}{self.to_string(resizer)}{annotation}"]
        if self.ref_ is not None:
            lines.append(self.ref_.reportTree(resizer, level + 1, include_metrics))
        if self.ref2_ is not None:
            lines.append(self.ref2_.reportTree(resizer, level + 1, include_metrics))
        return "\n".join(lines)

    def report(self) -> Dict[str, Any]:
        return {
            "tree": self.serialize(True),
            "metrics": self.metrics().as_dict(),
            "text": self.reportTree(),
        }

def visitTree(func: Callable[..., Any], *args: Any) -> Any:
    """C++ ``visitTree`` 递归 lambda 辅助器的 Python 版本。"""

    def invoke(level: int, *inner_args: Any) -> Any:
        return func(invoke, level, *inner_args)

    return invoke(1, *args)
