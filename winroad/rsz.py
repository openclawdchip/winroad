"""OpenROAD rsz 模块的 Python 翻译骨架。

本文件按 OpenROAD ``src/rsz`` 的对象边界建立 Python 版本：
``Resizer`` 是顶层入口，``BufferedNet`` 表示修复/重缓冲使用的树，
``RepairDesign`` / ``RepairSetup`` / ``RepairHold`` / ``RecoverPower`` 保存
主要优化流程的类边界。

约定：
1. 方法名尽量贴近 C++，便于后续逐函数对照翻译。
2. 已经能不依赖 STA/OpenDB 内核完成的状态操作在这里直接实现。
3. 真实 timing / parasitics / placement 修复算法不做估算替代；尚未翻译
   的函数会明确抛出 ``NotImplementedError``。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import inf
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple


Point = Tuple[int, int]
Rect = Tuple[int, int, int, int]
RiseFallArray = Tuple[float, float]


def _obj_key(obj: Any) -> Any:
    """把 C++ 指针语义压成 Python 可哈希键。

    STA/OpenDB 对象后续会逐步翻译成 Python 类；当前阶段既要兼容字符串/
    dataclass，也要兼容外部对象。可哈希对象直接使用自身，不可哈希对象用
    ``id`` 保留“指针身份”语义。
    """

    try:
        hash(obj)
    except TypeError:
        return id(obj)
    return obj


def _name_of(obj: Any) -> str:
    """提取对象名，模拟 C++ 日志里常见的 network/db name 查询。"""

    return str(getattr(obj, "name", obj))


def _not_translated(name: str) -> None:
    """尚未从 OpenROAD C++ 翻译的真实算法边界。"""

    raise NotImplementedError(f"OpenROAD rsz::{name} 尚未翻译为 Python")


class BufferUse(Enum):
    """对应 ``enum class BufferUse``。"""

    DATA = "data"
    CLOCK = "clock"


class MoveType(Enum):
    """对应 ``enum class MoveType``，用于 setup repair move sequence。"""

    BUFFER = "buffer"
    UNBUFFER = "unbuffer"
    SWAP = "swap"
    SIZE = "size"
    SIZEUP = "sizeup"
    SIZEDOWN = "sizedown"
    CLONE = "clone"
    SPLIT = "split"
    VTSWAP_SPEED = "vtswap_speed"
    SIZEUP_MATCH = "sizeup_match"


class BufferedNetType(Enum):
    """对应 ``enum class BufferedNetType``。"""

    LOAD = "load"
    JUNCTION = "junction"
    WIRE = "wire"
    VIA = "via"
    BUFFER = "buffer"


class MoveStateType(Enum):
    """MoveTracker 记录优化动作状态。"""

    ATTEMPT = 0
    ATTEMPT_REJECT = 1
    ATTEMPT_COMMIT = 2


@dataclass(order=True, frozen=True)
class VTCategory:
    """Voltage Threshold 分类键，对应 C++ ``VTCategory``。"""

    vt_index: int
    vt_name: str


@dataclass
class VTLeakageStats:
    """单个 VT 分类下的 leakage 统计。"""

    cell_count: int = 0
    total_leakage: float = 0.0

    def get_average_leakage(self) -> float:
        """返回平均 leakage；无 cell 时与 C++ 一样返回 0。"""

        return self.total_leakage / self.cell_count if self.cell_count > 0 else 0.0

    def add_cell_leakage(self, cell_leak: Optional[float]) -> None:
        """累加一个 cell 的 leakage。"""

        self.cell_count += 1
        if cell_leak is not None:
            self.total_leakage += cell_leak


@dataclass
class LibraryAnalysisData:
    """Resizer 的 library 分析缓存。"""

    vt_leakage_by_category: Dict[VTCategory, VTLeakageStats] = field(default_factory=dict)
    cells_by_footprint: Dict[str, int] = field(default_factory=dict)
    cells_by_site: Dict[Any, int] = field(default_factory=dict)
    sorted_vt_categories: List[Tuple[VTCategory, VTLeakageStats]] = field(default_factory=list)

    def sort_vt_categories(self) -> None:
        """按平均 leakage 从低到高排序 VT 分类。"""

        self.sorted_vt_categories = sorted(
            self.vt_leakage_by_category.items(),
            key=lambda item: item[1].get_average_leakage(),
        )


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

    def maxLoadWireLength(self) -> int:
        """返回从该节点向下到任一 load 的最大 wire 长度。"""

        child_lengths = []
        if self.ref_ is not None:
            child_lengths.append(self.length() + self.ref_.maxLoadWireLength())
        if self.ref2_ is not None:
            x1, y1 = self.location_
            x2, y2 = self.ref2_.location()
            child_lengths.append(abs(x1 - x2) + abs(y1 - y2) + self.ref2_.maxLoadWireLength())
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

    def to_string(self, _resizer: Optional["Resizer"] = None) -> str:
        return f"{self.type_.value}@{self.location_}"

    def reportTree(self, resizer: Optional["Resizer"] = None, level: int = 0) -> str:
        """返回树形文本，替代 C++ 里直接打 logger 的 report。"""

        indent = "  " * level
        lines = [f"{indent}{self.to_string(resizer)} cap={self.cap_} fanout={self.fanout_}"]
        if self.ref_ is not None:
            lines.append(self.ref_.reportTree(resizer, level + 1))
        if self.ref2_ is not None:
            lines.append(self.ref2_.reportTree(resizer, level + 1))
        return "\n".join(lines)


def visitTree(func: Callable[..., Any], *args: Any) -> Any:
    """C++ ``visitTree`` 递归 lambda 辅助器的 Python 版本。"""

    def invoke(level: int, *inner_args: Any) -> Any:
        return func(invoke, level, *inner_args)

    return invoke(1, *args)


@dataclass
class LoadRegion:
    """fanout pin 分区区域，对应 ``RepairDesign::LoadRegion``。"""

    pins_: List[Any] = field(default_factory=list)
    bbox_: Rect = (0, 0, 0, 0)
    regions_: List["LoadRegion"] = field(default_factory=list)


@dataclass
class OptoParams:
    """setup repair 优化参数，对应 C++ ``OptoParams``。"""

    setup_slack_margin: float
    verbose: bool
    skip_pin_swap: bool
    skip_gate_cloning: bool
    skip_size_down: bool
    skip_buffering: bool
    skip_buffer_removal: bool
    skip_vt_swap: bool
    iteration: int = 0
    initial_tns: float = 0.0


@dataclass
class PinInfo:
    """MoveTracker 记录的 pin 级统计信息。"""

    endpoint: Any = None
    gate_type: str = "unknown"
    load_delay: float = 0.0
    intrinsic_delay: float = 0.0
    pin_slack: float = 0.0
    endpoint_slack: float = 0.0


@dataclass
class MoveStateData:
    """MoveTracker 记录的单次优化动作。"""

    pin: Any
    move_type: str
    state: MoveStateType
    order: int = 0


@dataclass
class RepairDesignLimits:
    """RepairDesign 一轮修复使用的 violation 边界参数。"""

    max_wire_length: Optional[float] = None
    max_slew: Optional[float] = None
    max_cap: Optional[float] = None
    max_fanout: Optional[int] = None
    slew_margin: float = 0.0
    cap_margin: float = 0.0
    corner: Any = None
    buffer_cells: List[Any] = field(default_factory=list)


@dataclass
class RepairDesignViolationCounters:
    """RepairDesign 的 long wire / max transition / cap / fanout 计数。"""

    repaired_nets: int = 0
    inserted_buffers: int = 0
    resized_drivers: int = 0
    long_wire: int = 0
    max_slew: int = 0
    max_cap: int = 0
    max_fanout: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "repaired_nets": self.repaired_nets,
            "inserted_buffers": self.inserted_buffers,
            "resized_drivers": self.resized_drivers,
            "long_wire": self.long_wire,
            "max_slew": self.max_slew,
            "max_cap": self.max_cap,
            "max_fanout": self.max_fanout,
        }


@dataclass
class SlackEstimatorParams:
    """BaseMove 估算 move slack 时传递的上下文。"""

    setup_slack_margin: float
    scene: Any
    driver_pin: Any = None
    prev_driver_pin: Any = None
    driver_input_pin: Any = None
    driver: Any = None
    driver_cell: Any = None
    driver_path: Any = None
    prev_driver_path: Any = None


class ResizerObserver:
    """图形/调试观察者接口，对应 ``ResizerObserver.hh``。"""

    def setNet(self, net: Any) -> None:
        pass

    def stopOnSubdivideStep(self, stop: bool) -> None:
        pass

    def subdivideStart(self, net: Any) -> None:
        pass

    def subdivide(self, line: Any) -> None:
        pass

    def subdivideDone(self) -> None:
        pass

    def repairNetStart(self, bnet: BufferedNet, net: Any) -> None:
        pass

    def makeBuffer(self, inst: Any) -> None:
        pass

    def repairNetDone(self) -> None:
        pass


class PreChecks:
    """修复前的 slew/cap 合理性检查边界。"""

    default_min_cap_load = 1e-18

    def __init__(self, resizer: "Resizer") -> None:
        self.logger_ = resizer.logger_
        self.sta_ = resizer.sta_
        self.resizer_ = resizer
        self.best_case_slew_ = -1.0
        self.best_case_slew_load_ = -1.0
        self.best_case_slew_computed_ = False
        self.min_cap_load_ = self.default_min_cap_load
        self.min_cap_load_computed_ = False

    def checkSlewLimit(self, ref_cap: float, max_load_slew: float) -> None:
        _not_translated("PreChecks::checkSlewLimit")

    def checkCapLimit(self, drvr_pin: Any) -> None:
        _not_translated("PreChecks::checkCapLimit")


class BaseMove:
    """setup 修复动作基类，对应 ``BaseMove``。

    这里先翻译 move 计数、提交/回滚集合等通用状态；具体动作在 C++ 中由
    BufferMove、SizeUpMove、SwapPinsMove 等派生类实现，后续应按类继续补。
    """

    def __init__(self, resizer: "Resizer") -> None:
        self.resizer_ = resizer
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.logger_ = resizer.logger_
        self.network_ = getattr(resizer.sta_, "network", None)
        self.db_network_ = resizer.db_network_
        self.sta_ = resizer.sta_
        self.db_ = resizer.db_
        self.dbu_ = resizer.dbu_
        self.opendp_ = resizer.opendp_
        self.scene_ = None
        self.all_inst_set_: Set[Any] = set()
        self.accepted_inst_set_: Set[Any] = set()
        self.pending_inst_set_: Set[Any] = set()
        self.all_count_ = 0
        self.pending_count_ = 0
        self.rejected_count_ = 0
        self.accepted_count_ = 0
        self.input_slew_map_: Dict[Any, RiseFallArray] = {}
        self.tgt_slews_: RiseFallArray = (inf, inf)

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        return False

    def name(self) -> str:
        raise NotImplementedError("BaseMove::name must be implemented by subclasses")

    def init(self) -> None:
        """刷新 STA/DB 依赖指针；对应 C++ init 边界。"""

        self.db_network_ = self.resizer_.db_network_
        self.sta_ = self.resizer_.sta_
        self.db_ = self.resizer_.db_
        self.dbu_ = self.resizer_.dbu_
        self.opendp_ = self.resizer_.opendp_

    def countMove(self, inst: Any, count: int = 1) -> None:
        key = _obj_key(inst)
        self.all_inst_set_.add(key)
        self.pending_inst_set_.add(key)
        self.all_count_ += count
        self.pending_count_ += count

    def commitMoves(self) -> None:
        self.accepted_inst_set_.update(self.pending_inst_set_)
        self.accepted_count_ += self.pending_count_
        self.pending_inst_set_.clear()
        self.pending_count_ = 0

    def undoMoves(self) -> None:
        self.rejected_count_ += self.pending_count_
        self.pending_inst_set_.clear()
        self.pending_count_ = 0

    def numPendingMoves(self) -> int:
        return self.pending_count_

    def hasPendingMoves(self, inst: Any) -> int:
        return int(_obj_key(inst) in self.pending_inst_set_)

    def numCommittedMoves(self) -> int:
        return self.accepted_count_

    def numRejectedMoves(self) -> int:
        return self.rejected_count_

    def hasMoves(self, inst: Any) -> int:
        key = _obj_key(inst)
        return int(key in self.all_inst_set_ or key in self.pending_inst_set_)

    def numMoves(self) -> int:
        return self.all_count_


class BufferMove(BaseMove):
    """对应 ``BufferMove``，setup repair 的重缓冲动作边界。"""

    def name(self) -> str:
        return "BufferMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("BufferMove::doMove")

    def rebufferNet(self, drvr_pin: Any) -> None:
        _not_translated("BufferMove::rebufferNet")

    def rebuffer(self, drvr_pin: Any) -> int:
        _not_translated("BufferMove::rebuffer")

    def debugCheckMultipleBuffers(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("BufferMove::debugCheckMultipleBuffers")

    def hasTopLevelOutputPort(self, net: Any) -> bool:
        _not_translated("BufferMove::hasTopLevelOutputPort")


class UnbufferMove(BaseMove):
    """对应 ``UnbufferMove``，buffer removal 动作边界。"""

    buffer_removal_max_fanout_ = 10

    def name(self) -> str:
        return "UnbufferMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("UnbufferMove::doMove")

    def removeBufferIfPossible(self, buffer: Any, honorDontTouchFixed: bool) -> bool:
        _not_translated("UnbufferMove::removeBufferIfPossible")

    def canRemoveBuffer(self, buffer: Any, honorDontTouchFixed: bool) -> bool:
        _not_translated("UnbufferMove::canRemoveBuffer")

    def removeBuffer(self, buffer: Any) -> bool:
        _not_translated("UnbufferMove::removeBuffer")

    def bufferBetweenPorts(self, buffer: Any) -> bool:
        _not_translated("UnbufferMove::bufferBetweenPorts")

    def bufferRemovalCreatesFeedthrough(self, ip_modnet: Any, op_modnet: Any) -> bool:
        _not_translated("UnbufferMove::bufferRemovalCreatesFeedthrough")


class SizeUpMove(BaseMove):
    """对应 ``SizeUpMove``。"""

    def name(self) -> str:
        return "SizeUpMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SizeUpMove::doMove")


class SizeUpMatchMove(BaseMove):
    """对应 ``SizeUpMatchMove``，匹配前级驱动强度的 size-up 动作。"""

    def name(self) -> str:
        return "SizeUpMoveMatch"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SizeUpMatchMove::doMove")


class SizeDownMove(BaseMove):
    """对应 ``SizeDownMove``。"""

    size_down_max_fanout_ = 10

    def name(self) -> str:
        return "SizeDownMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SizeDownMove::doMove")

    def downSizeGate(self, *_args: Any, **_kwargs: Any) -> Any:
        _not_translated("SizeDownMove::downSizeGate")


class SwapPinsMove(BaseMove):
    """对应 ``SwapPinsMove``，等价输入 pin swap 的动作边界。"""

    def __init__(self, resizer: "Resizer") -> None:
        super().__init__(resizer)
        self.equiv_pin_map_: Dict[Any, Set[Any]] = {}

    def name(self) -> str:
        return "SwapPinsMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SwapPinsMove::doMove")

    def reportSwappablePins(self) -> None:
        _not_translated("SwapPinsMove::reportSwappablePins")

    def swapPins(self, inst: Any, port1: Any, port2: Any) -> bool:
        _not_translated("SwapPinsMove::swapPins")

    def equivCellPins(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("SwapPinsMove::equivCellPins")

    def annotateInputSlews(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("SwapPinsMove::annotateInputSlews")

    def findSwapPinCandidate(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("SwapPinsMove::findSwapPinCandidate")

    def resetInputSlews(self) -> None:
        _not_translated("SwapPinsMove::resetInputSlews")


class CloneMove(BaseMove):
    """对应 ``CloneMove``，gate cloning 动作边界。"""

    def name(self) -> str:
        return "CloneMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("CloneMove::doMove")

    def computeCloneGateLocation(self, *_args: Any, **_kwargs: Any) -> Point:
        _not_translated("CloneMove::computeCloneGateLocation")

    def cloneDriver(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("CloneMove::cloneDriver")


class SplitLoadMove(BaseMove):
    """对应 ``SplitLoadMove``。"""

    split_load_min_fanout_ = 8

    def name(self) -> str:
        return "SplitLoadMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SplitLoadMove::doMove")


class VTSwapSpeedMove(BaseMove):
    """对应 ``VTSwapSpeedMove``，setup timing 用 VT swap 动作边界。"""

    def name(self) -> str:
        return "VTSwapSpeed"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("VTSwapSpeedMove::doMove")

    def isSwappable(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("VTSwapSpeedMove::isSwappable")


class MoveTracker:
    """记录 setup repair 尝试、提交、拒绝的 pin/move 状态。"""

    def __init__(self, logger: Any, sta: Any, db_network: Any, block: Any) -> None:
        self.logger_ = logger
        self.sta_ = sta
        self.db_network_ = db_network
        self.block_ = block
        self.current_endpoint_: Any = None
        self.critical_pins_: List[Any] = []
        self.violators_: List[Any] = []
        self.pin_infos_: Dict[Any, PinInfo] = {}
        self.moves_: List[MoveStateData] = []
        self.pending_moves_: List[MoveStateData] = []

    def inDbITermDestroy(self, iterm: Any) -> None:
        """OpenDB callback 边界；当前 Python 版本只保留接口。"""

    def inDbITermCreate(self, iterm: Any) -> None:
        """OpenDB callback 边界；当前 Python 版本只保留接口。"""

    def setCurrentEndpoint(self, endpoint_pin: Any) -> None:
        self.current_endpoint_ = endpoint_pin

    def currentEndpoint(self) -> Any:
        return self.current_endpoint_

    def trackCriticalPins(self, critical_pins: Sequence[Any]) -> None:
        self.critical_pins_.extend(critical_pins)

    def criticalPins(self) -> List[Any]:
        return list(self.critical_pins_)

    def trackViolator(self, pin: Any) -> None:
        self.violators_.append(pin)

    def violators(self) -> List[Any]:
        return list(self.violators_)

    def trackViolatorWithInfo(
        self,
        pin: Any,
        gate_type: str,
        load_delay: float,
        intrinsic_delay: float,
        pin_slack: float,
        endpoint_slack: float,
    ) -> None:
        self.trackViolator(pin)
        self.pin_infos_[_obj_key(pin)] = PinInfo(
            pin, gate_type, load_delay, intrinsic_delay, pin_slack, endpoint_slack
        )

    def pinInfo(self, pin: Any) -> Optional[PinInfo]:
        return self.pin_infos_.get(_obj_key(pin))

    def trackMove(self, pin: Any, move_type: str, state: MoveStateType) -> None:
        data = MoveStateData(pin=pin, order=len(self.moves_), move_type=move_type, state=state)
        self.moves_.append(data)
        if state is MoveStateType.ATTEMPT:
            self.pending_moves_.append(data)

    def moves(self) -> List[MoveStateData]:
        return list(self.moves_)

    def pendingMoves(self) -> List[MoveStateData]:
        return list(self.pending_moves_)

    def commitMoves(self) -> None:
        for data in self.pending_moves_:
            self.moves_.append(
                MoveStateData(data.pin, data.move_type, MoveStateType.ATTEMPT_COMMIT, len(self.moves_))
            )
        self.pending_moves_.clear()

    def rejectMoves(self) -> None:
        for data in self.pending_moves_:
            self.moves_.append(
                MoveStateData(data.pin, data.move_type, MoveStateType.ATTEMPT_REJECT, len(self.moves_))
            )
        self.pending_moves_.clear()

    def moveSummary(self) -> Dict[str, int]:
        summary = {state.name.lower(): 0 for state in MoveStateType}
        for move in self.moves_:
            summary[move.state.name.lower()] += 1
        summary["pending"] = len(self.pending_moves_)
        return summary


class Resizer:
    """rsz 顶层入口类，对应 ``class Resizer``。

    该类连接 OpenDB、OpenSTA、Steiner tree、global router、OpenDP 和 parasitics
    估算器。Python 版本先保存依赖、配置、统计和 public API 边界；所有需要
    STA graph/parasitics/placement 的真实修复流程委托给对应 Repair* 类或抛出
    未翻译错误。
    """

    kDefaultBufBaseName = "input"
    kDefaultNetBaseName = "net"

    def __init__(
        self,
        logger: Any = None,
        db: Any = None,
        sta: Any = None,
        stt_builder: Any = None,
        global_router: Any = None,
        opendp: Any = None,
        estimate_parasitics: Any = None,
    ) -> None:
        self.logger_ = logger
        self.db_ = db
        self.sta_ = sta
        self.stt_builder_ = stt_builder
        self.global_router_ = global_router
        self.opendp_ = opendp
        self.estimate_parasitics_ = estimate_parasitics
        self.db_network_ = getattr(sta, "db_network", None)
        self.block_ = None
        self.dbu_ = 0
        self.design_area_ = 0.0
        self.max_utilization_ = 1.0
        self.dont_use_: Set[Any] = set()
        self.dont_touch_insts_: Set[Any] = set()
        self.dont_touch_nets_: Set[Any] = set()
        self.debug_pin_ = None
        self.worst_slack_nets_percent_ = 0.0
        self.buffer_list_: List[Any] = []
        self.fast_buffer_sizes_: List[Any] = []
        self.clk_buffers_: List[Any] = []
        self.clock_buffer_string_ = ""
        self.clock_buffer_footprint_ = ""
        self.resize_slacks_: Dict[Any, float] = {}
        self.graphics_: Optional[ResizerObserver] = None
        self.lib_data_ = LibraryAnalysisData()
        self.parse_to_openroad_ = None
        self.resizer_ = None
        self.opcode_mapper_ = None
        self.swap_arith_modules_ = None
        self.tielib_port_ = None
        self.tiehi_cell_ = None
        self.tiehi_port_ = None
        self.tielo_cell_ = None
        self.tielo_port_ = None
        self.target_load_map_: Dict[Any, float] = {}
        self.input_slew_map_: Dict[Any, RiseFallArray] = {}
        self.tgt_slews_: RiseFallArray = (inf, inf)
        self.dont_use_changed_ = False
        self.dont_touch_changed_ = False
        self.repair_design_ = RepairDesign(self)
        self.repair_setup_ = RepairSetup(self)
        self.repair_hold_ = RepairHold(self)
        self.recover_power_ = RecoverPower(self)
        self.initBlock()

    def coreArea(self) -> float:
        """返回 core/die 面积；单位沿用 C++ 注释里的平方米。"""

        block = self.block_
        die = getattr(block, "die_area", None)
        if die is None:
            return 0.0
        lx, ly, ux, uy = die
        return self.dbuToMeters(max(0, ux - lx)) * self.dbuToMeters(max(0, uy - ly))

    def utilization(self) -> float:
        area = self.coreArea()
        return self.designArea() / area if area > 0.0 else 0.0

    def maxArea(self) -> float:
        return self.coreArea() * self.max_utilization_

    def orderedLoadPinVertices(self) -> List[Any]:
        _not_translated("Resizer::orderedLoadPinVertices")

    def setDontUse(self, cell: Any, dont_use: bool) -> None:
        key = _obj_key(cell)
        if dont_use:
            self.dont_use_.add(key)
        else:
            self.dont_use_.discard(key)
        self.dont_use_changed_ = True

    def resetDontUse(self) -> None:
        self.dont_use_.clear()
        self.dont_use_changed_ = True

    def dontUse(self, cell: Any) -> bool:
        return _obj_key(cell) in self.dont_use_

    def reportDontUse(self) -> List[str]:
        return sorted(_name_of(cell) for cell in self.dont_use_)

    def setDontTouch(self, obj: Any, dont_touch: bool) -> None:
        target = self.dont_touch_nets_ if getattr(obj, "is_net", False) else self.dont_touch_insts_
        key = _obj_key(obj)
        if dont_touch:
            target.add(key)
        else:
            target.discard(key)
        self.dont_touch_changed_ = True

    def dontTouch(self, obj: Any) -> bool:
        key = _obj_key(obj)
        return key in self.dont_touch_insts_ or key in self.dont_touch_nets_

    def insertBufferAfterDriver(self, *_args: Any, **_kwargs: Any) -> Any:
        _not_translated("Resizer::insertBufferAfterDriver")

    def insertBufferBeforeLoad(self, *_args: Any, **_kwargs: Any) -> Any:
        _not_translated("Resizer::insertBufferBeforeLoad")

    def insertBufferBeforeLoads(self, *_args: Any, **_kwargs: Any) -> Any:
        _not_translated("Resizer::insertBufferBeforeLoads")

    def reportDontTouch(self) -> Dict[str, List[str]]:
        return {
            "insts": sorted(_name_of(inst) for inst in self.dont_touch_insts_),
            "nets": sorted(_name_of(net) for net in self.dont_touch_nets_),
        }

    def reportFastBufferSizes(self) -> List[Any]:
        return list(self.fast_buffer_sizes_)

    def setMaxUtilization(self, max_utilization: float) -> None:
        self.max_utilization_ = max_utilization

    def removeBuffers(self, insts: Sequence[Any]) -> None:
        _not_translated("Resizer::removeBuffers")

    def unbufferNet(self, net: Any) -> None:
        _not_translated("Resizer::unbufferNet")

    def bufferInputs(self, buffer_cell: Any = None, verbose: bool = False) -> None:
        _not_translated("Resizer::bufferInputs")

    def bufferOutputs(self, buffer_cell: Any = None, verbose: bool = False) -> None:
        _not_translated("Resizer::bufferOutputs")

    def postReadLiberty(self) -> None:
        """STA dbNetworkObserver 回调；C++ 中会刷新 dont_use/buffer 列表。"""

        self.copyDontUseFromLiberty()
        self.findBuffers()

    def balanceRowUsage(self) -> None:
        _not_translated("Resizer::balanceRowUsage")

    def resizeDrvrToTargetSlew(self, drvr_pin: Any) -> None:
        _not_translated("Resizer::resizeDrvrToTargetSlew")

    def targetSlew(self, rf: Any) -> float:
        _not_translated("Resizer::targetSlew")

    def targetLoadCap(self, cell: Any) -> float:
        key = _obj_key(cell)
        if key in self.target_load_map_:
            return self.target_load_map_[key]
        _not_translated("Resizer::targetLoadCap")

    def repairSetup(self, *args: Any, **kwargs: Any) -> bool:
        return self.repair_setup_.repairSetup(*args, **kwargs)

    def reportSwappablePins(self) -> None:
        self.repair_setup_.reportSwappablePins()

    def reportSetupMoves(self) -> Dict[str, Any]:
        return self.repair_setup_.reportMoveSummary()

    def rebufferNet(self, drvr_pin: Any) -> None:
        _not_translated("Resizer::rebufferNet")

    def repairHold(self, *args: Any, **kwargs: Any) -> bool:
        return self.repair_hold_.repairHold(*args, **kwargs)

    def holdBufferCount(self) -> int:
        return self.repair_hold_.holdBufferCount()

    def reportHoldCounters(self) -> Dict[str, int]:
        return self.repair_hold_.reportCounters()

    def recoverPower(self, recover_power_percent: float, match_cell_footprint: bool = False, verbose: bool = False) -> bool:
        return self.recover_power_.recoverPower(recover_power_percent, match_cell_footprint, verbose)

    def reportRecoverPowerCounters(self) -> Dict[str, Any]:
        return self.recover_power_.reportCounters()

    def swapArithModules(self, path_count: int, target: str, slack_margin: float) -> None:
        _not_translated("Resizer::swapArithModules")

    def designArea(self) -> float:
        return self.design_area_

    def designAreaIncr(self, delta: float) -> None:
        self.design_area_ += delta

    def findFloatingNets(self) -> List[Any]:
        _not_translated("Resizer::findFloatingNets")

    def findFloatingPins(self) -> Set[Any]:
        _not_translated("Resizer::findFloatingPins")

    def findOverdrivenNets(self, include_parallel_driven: bool) -> List[Any]:
        _not_translated("Resizer::findOverdrivenNets")

    def repairTieFanout(self, tie_port: Any, separation: float, verbose: bool) -> None:
        _not_translated("Resizer::repairTieFanout")

    def bufferWireDelay(self, buffer_cell: Any, wire_length: float) -> Tuple[float, float]:
        _not_translated("Resizer::bufferWireDelay")

    def setDebugPin(self, pin: Any) -> None:
        self.debug_pin_ = pin

    def setWorstSlackNetsPercent(self, percent: float) -> None:
        self.worst_slack_nets_percent_ = percent

    def annotateInputSlews(self, inst: Any, scene: Any, min_max: Any) -> None:
        _not_translated("Resizer::annotateInputSlews")

    def resetInputSlews(self) -> None:
        _not_translated("Resizer::resetInputSlews")

    def repairDesign(self, *args: Any, **kwargs: Any) -> None:
        self.repair_design_.repairDesign(*args, **kwargs)

    def repairDesignBufferCount(self) -> int:
        return self.repair_design_.insertedBufferCount()

    def repairDesignViolationCounters(self) -> Dict[str, int]:
        return self.repair_design_.reportViolationCounters()

    def repairNet(self, *args: Any, **kwargs: Any) -> None:
        self.repair_design_.repairNet(*args, **kwargs)

    def repairClkNets(self, max_wire_length: float) -> None:
        self.repair_design_.repairClkNets(max_wire_length)

    def setClockBuffersList(self, clk_buffers: Sequence[Any]) -> None:
        self.clk_buffers_ = list(clk_buffers)

    def inferClockBufferList(self, lib_name: str, buffers: List[str]) -> None:
        _not_translated("Resizer::inferClockBufferList")

    def isClockCellCandidate(self, cell: Any) -> bool:
        name = _name_of(cell)
        return bool(self.clock_buffer_string_ and self.clock_buffer_string_ in name)

    def setClockBufferString(self, clk_str: str) -> None:
        self.clock_buffer_string_ = clk_str

    def setClockBufferFootprint(self, footprint: str) -> None:
        self.clock_buffer_footprint_ = footprint

    def resetClockBufferPattern(self) -> None:
        self.clock_buffer_string_ = ""
        self.clock_buffer_footprint_ = ""

    def hasClockBufferString(self) -> bool:
        return bool(self.clock_buffer_string_)

    def hasClockBufferFootprint(self) -> bool:
        return bool(self.clock_buffer_footprint_)

    def getClockBufferString(self) -> str:
        return self.clock_buffer_string_

    def getClockBufferFootprint(self) -> str:
        return self.clock_buffer_footprint_

    def getBufferUse(self, buffer: Any) -> BufferUse:
        return BufferUse.CLOCK if buffer in self.clk_buffers_ else BufferUse.DATA

    def repairClkInverters(self) -> None:
        self.repair_design_.repairClkInverters()

    def reportLongWires(self, count: int, digits: int) -> None:
        _not_translated("Resizer::reportLongWires")

    def findMaxWireLength(self, *args: Any, **kwargs: Any) -> float:
        _not_translated("Resizer::findMaxWireLength")

    def maxLoadManhattenDistance(self, net: Any) -> float:
        _not_translated("Resizer::maxLoadManhattenDistance")

    def resizeSlackPreamble(self) -> None:
        self.resize_slacks_.clear()

    def findResizeSlacks(self, run_journal_restore: bool) -> None:
        _not_translated("Resizer::findResizeSlacks")

    def resizeWorstSlackNets(self) -> List[Any]:
        return sorted(self.resize_slacks_, key=self.resize_slacks_.get)

    def resizeNetSlack(self, net: Any) -> Optional[float]:
        return self.resize_slacks_.get(_obj_key(net))

    def findFaninFanouts(self, end_pins: Set[Any]) -> Set[Any]:
        _not_translated("Resizer::findFaninFanouts")

    def findFanins(self, end_pins: Set[Any]) -> Set[Any]:
        _not_translated("Resizer::findFanins")

    def getDbNetwork(self) -> Any:
        return self.db_network_

    def getDbBlock(self) -> Any:
        return self.block_

    def dbuToMeters(self, dist: int) -> float:
        dbu = self.dbu_ or getattr(self.block_, "dbu_per_micron", 0)
        return dist / dbu * 1.0e-6 if dbu else 0.0

    def metersToDbu(self, dist: float) -> int:
        dbu = self.dbu_ or getattr(self.block_, "dbu_per_micron", 0)
        return int(round(dist * 1.0e6 * dbu)) if dbu else 0

    def makeEquivCells(self) -> None:
        _not_translated("Resizer::makeEquivCells")

    def cellVTType(self, master: Any) -> VTCategory:
        vt_index = int(getattr(master, "vt_index", 0))
        vt_name = str(getattr(master, "vt_name", ""))
        return VTCategory(vt_index, vt_name)

    def initBlock(self) -> None:
        chip = getattr(self.db_, "chip", None)
        self.block_ = getattr(chip, "block", None) or getattr(chip, "top_block", None)
        if self.block_ is None and hasattr(chip, "get_top_block"):
            self.block_ = chip.get_top_block()
        if self.block_ is None and hasattr(self.db_, "get_top_block"):
            self.block_ = self.db_.get_top_block()
        self.dbu_ = int(getattr(self.block_, "dbu_per_micron", 0) or 0)

    def journalBeginTest(self) -> None:
        _not_translated("Resizer::journalBeginTest")

    def journalRestoreTest(self) -> None:
        _not_translated("Resizer::journalRestoreTest")

    def logger(self) -> Any:
        return self.logger_

    def eliminateDeadLogic(self, clean_nets: bool) -> None:
        _not_translated("Resizer::eliminateDeadLogic")

    def cellLeakage(self, cell: Any) -> Optional[float]:
        return getattr(cell, "leakage", None)

    def reportEquivalentCells(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("Resizer::reportEquivalentCells")

    def reportBuffers(self, filtered: bool) -> List[Any]:
        if not filtered:
            return list(self.buffer_list_)
        return [cell for cell in self.buffer_list_ if not self.dontUse(cell)]

    def getBufferList(self, buffer_list: List[Any]) -> None:
        buffer_list.extend(self.buffer_list_)

    def setDebugGraphics(self, graphics: ResizerObserver) -> None:
        self.graphics_ = graphics
        self.repair_design_.setDebugGraphics(graphics)

    @staticmethod
    def parseMove(s: str) -> MoveType:
        normalized = s.strip().lower().replace("-", "_")
        aliases = {
            "buffer": MoveType.BUFFER,
            "unbuffer": MoveType.UNBUFFER,
            "swap": MoveType.SWAP,
            "size": MoveType.SIZE,
            "sizeup": MoveType.SIZEUP,
            "size_up": MoveType.SIZEUP,
            "sizedown": MoveType.SIZEDOWN,
            "size_down": MoveType.SIZEDOWN,
            "clone": MoveType.CLONE,
            "split": MoveType.SPLIT,
            "vtswap_speed": MoveType.VTSWAP_SPEED,
            "vt_swap_speed": MoveType.VTSWAP_SPEED,
            "sizeup_match": MoveType.SIZEUP_MATCH,
            "size_up_match": MoveType.SIZEUP_MATCH,
        }
        if normalized not in aliases:
            raise ValueError(f"unknown rsz move: {s}")
        return aliases[normalized]

    @staticmethod
    def parseMoveSequence(sequence: str) -> List[MoveType]:
        if not sequence.strip():
            return []
        tokens = [token for token in sequence.replace(",", " ").split() if token]
        return [Resizer.parseMove(token) for token in tokens]

    def fullyRebuffer(self, pin: Any) -> None:
        _not_translated("Resizer::fullyRebuffer")

    def hasFanout(self, drvr: Any) -> bool:
        fanout = getattr(drvr, "fanout", None)
        if callable(fanout):
            fanout = fanout()
        return bool(fanout)

    def getEstimateParasitics(self) -> Any:
        return self.estimate_parasitics_

    def getSlewRCFactor(self) -> float:
        return self.repair_design_.getSlewRCFactor()

    def findDriverSlewForLoad(self, *_args: Any, **_kwargs: Any) -> float:
        _not_translated("Resizer::findDriverSlewForLoad")

    def computeNewDelaysSlews(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("Resizer::computeNewDelaysSlews")

    def estimateSlewsAfterBufferRemoval(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("Resizer::estimateSlewsAfterBufferRemoval")

    def estimateSlewsInTree(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("Resizer::estimateSlewsInTree")

    def init(self) -> None:
        self.initBlock()

    def computeDesignArea(self) -> float:
        block = self.block_
        insts = getattr(block, "insts", {})
        area = 0.0
        for inst in getattr(insts, "values", lambda: [])():
            bbox = getattr(inst, "bbox", None)
            if bbox is not None:
                lx, ly, ux, uy = bbox
                area += self.dbuToMeters(max(0, ux - lx)) * self.dbuToMeters(max(0, uy - ly))
        return area

    def initDesignArea(self) -> None:
        self.design_area_ = self.computeDesignArea()

    def copyDontUseFromLiberty(self) -> None:
        """占位边界：后续从 Liberty cell dont_use 属性同步。"""

    def findBuffers(self) -> None:
        """占位边界：后续从 Liberty/LEF 识别 buffer/inverter。"""


class RepairDesign:
    """修复 max slew/cap/fanout/long wire 的流程边界。"""

    min_print_interval_ = 10
    max_print_interval_ = 1000

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.logger_ = resizer.logger_
        self.db_network_ = resizer.db_network_
        self.pre_checks_ = PreChecks(resizer)
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.dbu_ = resizer.dbu_
        self.initial_design_area_ = 0.0
        self.parasitics_src_ = None
        self.buffer_sizes_: List[Any] = []
        self.drvr_pin_ = None
        self.max_cap_ = 0.0
        self.max_length_ = 0
        self.max_wire_length_ = 0.0
        self.max_slew_ = 0.0
        self.max_cap_margin_ = 0.0
        self.max_fanout_ = 0
        self.slew_margin_ = 0.0
        self.cap_margin_ = 0.0
        self.corner_ = None
        self.resize_count_ = 0
        self.inserted_buffer_count_ = 0
        self.repaired_net_count_ = 0
        self.long_wire_count_ = 0
        self.max_slew_count_ = 0
        self.max_cap_count_ = 0
        self.max_fanout_count_ = 0
        self.print_interval_ = 0
        self.graphics_: Optional[ResizerObserver] = None
        self.r_strongest_buffer_ = 0.0
        self.slew_rc_factor_: Optional[float] = None
        self.limits_ = RepairDesignLimits()

    def init(self) -> None:
        self.db_network_ = self.resizer_.db_network_
        self.dbu_ = self.resizer_.dbu_

    def repairDesign(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("RepairDesign::repairDesign")

    def insertedBufferCount(self) -> int:
        return self.inserted_buffer_count_

    def configureLimits(
        self,
        max_wire_length: Optional[float] = None,
        max_slew: Optional[float] = None,
        max_cap: Optional[float] = None,
        max_fanout: Optional[int] = None,
        slew_margin: float = 0.0,
        cap_margin: float = 0.0,
        corner: Any = None,
        buffer_cells: Optional[Sequence[Any]] = None,
    ) -> RepairDesignLimits:
        """记录 repair_design 的 violation 参数，不触发真实 STA/DB 修复。"""

        self.limits_ = RepairDesignLimits(
            max_wire_length=max_wire_length,
            max_slew=max_slew,
            max_cap=max_cap,
            max_fanout=max_fanout,
            slew_margin=slew_margin,
            cap_margin=cap_margin,
            corner=corner,
            buffer_cells=list(buffer_cells or []),
        )
        self.max_wire_length_ = float(max_wire_length or 0.0)
        self.max_length_ = int(max_wire_length or 0)
        self.max_slew_ = float(max_slew or 0.0)
        self.max_cap_ = float(max_cap or 0.0)
        self.max_fanout_ = int(max_fanout or 0)
        self.slew_margin_ = slew_margin
        self.cap_margin_ = cap_margin
        self.corner_ = corner
        self.buffer_sizes_ = list(buffer_cells or [])
        return self.limits_

    def limits(self) -> RepairDesignLimits:
        return self.limits_

    def resetViolationCounters(self) -> None:
        self.resize_count_ = 0
        self.inserted_buffer_count_ = 0
        self.repaired_net_count_ = 0
        self.long_wire_count_ = 0
        self.max_slew_count_ = 0
        self.max_cap_count_ = 0
        self.max_fanout_count_ = 0

    def recordRepair(
        self,
        long_wire: int = 0,
        max_slew: int = 0,
        max_cap: int = 0,
        max_fanout: int = 0,
        inserted_buffers: int = 0,
        resized_drivers: int = 0,
        repaired_nets: int = 0,
    ) -> None:
        """累加 C++ repair pass 会维护的 counters。"""

        self.long_wire_count_ += long_wire
        self.max_slew_count_ += max_slew
        self.max_cap_count_ += max_cap
        self.max_fanout_count_ += max_fanout
        self.inserted_buffer_count_ += inserted_buffers
        self.resize_count_ += resized_drivers
        self.repaired_net_count_ += repaired_nets

    def violationCounters(self) -> RepairDesignViolationCounters:
        return RepairDesignViolationCounters(
            repaired_nets=self.repaired_net_count_,
            inserted_buffers=self.inserted_buffer_count_,
            resized_drivers=self.resize_count_,
            long_wire=self.long_wire_count_,
            max_slew=self.max_slew_count_,
            max_cap=self.max_cap_count_,
            max_fanout=self.max_fanout_count_,
        )

    def repairNet(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("RepairDesign::repairNet")

    def repairClkNets(self, max_wire_length: float) -> None:
        _not_translated("RepairDesign::repairClkNets")

    def repairClkInverters(self) -> None:
        _not_translated("RepairDesign::repairClkInverters")

    def reportViolationCounters(self, *_args: Any, **_kwargs: Any) -> Dict[str, int]:
        return self.violationCounters().as_dict()

    def setDebugGraphics(self, graphics: ResizerObserver) -> None:
        self.graphics_ = graphics

    def getSlewRCFactor(self) -> float:
        if self.slew_rc_factor_ is None:
            self.computeSlewRCFactor()
        return self.slew_rc_factor_ if self.slew_rc_factor_ is not None else 0.0

    def computeSlewRCFactor(self) -> None:
        _not_translated("RepairDesign::computeSlewRCFactor")


class RepairSetup:
    """setup timing repair 主流程边界。"""

    initial_decreasing_slack_max_passes_ = 6
    pass_limit_increment_ = 5
    print_interval_ = 10
    opto_small_interval_ = 100
    opto_large_interval_ = 1000
    inc_fix_rate_threshold_ = 0.0001
    max_last_gasp_passes_ = 10

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.logger_ = resizer.logger_
        self.db_network_ = resizer.db_network_
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.violator_collector_ = None
        self.move_tracker_: Optional[MoveTracker] = None
        self.fallback_ = False
        self.min_viol_ = 0.0
        self.max_viol_ = 0.0
        self.max_repairs_per_pass_ = 1
        self.removed_buffer_count_ = 0
        self.initial_design_area_ = 0.0
        self.move_sequence_: List[BaseMove] = []
        self.move_sequence_types_: List[MoveType] = []
        self.buffer_move_ = BufferMove(resizer)
        self.unbuffer_move_ = UnbufferMove(resizer)
        self.swap_pins_move_ = SwapPinsMove(resizer)
        self.sizeup_move_ = SizeUpMove(resizer)
        self.sizeup_match_move_ = SizeUpMatchMove(resizer)
        self.sizedown_move_ = SizeDownMove(resizer)
        self.clone_move_ = CloneMove(resizer)
        self.split_load_move_ = SplitLoadMove(resizer)
        self.vt_swap_move_ = VTSwapSpeedMove(resizer)
        self.endpoint_pass_counts_phase1_: Dict[Any, int] = {}
        self.wns_no_progress_count_ = 0
        self.rejected_pin_moves_current_endpoint_: Dict[Any, Set[BaseMove]] = {}
        self.overall_no_progress_count_ = 0
        self.max_end_repairs_ = -1
        self.equiv_pin_map_: Dict[Any, Set[Any]] = {}

    def init(self) -> None:
        self.db_network_ = self.resizer_.db_network_
        for move in self.allMoves():
            move.init()

    def allMoves(self) -> List[BaseMove]:
        return [
            self.buffer_move_,
            self.unbuffer_move_,
            self.swap_pins_move_,
            self.sizeup_move_,
            self.sizeup_match_move_,
            self.sizedown_move_,
            self.clone_move_,
            self.split_load_move_,
            self.vt_swap_move_,
        ]

    def setupMoveSequence(
        self,
        sequence: Sequence[MoveType],
        skip_pin_swap: bool,
        skip_gate_cloning: bool,
        skip_size_down: bool,
        skip_buffering: bool,
        skip_buffer_removal: bool,
        skip_vt_swap: bool,
    ) -> None:
        """保存 move sequence 边界。

        C++ 会创建具体 BaseMove 派生类；这些派生动作尚未翻译，所以这里先只
        保留筛选后的枚举序列，供文档/测试确认入口参数。
        """

        skipped = set()
        if skip_pin_swap:
            skipped.add(MoveType.SWAP)
        if skip_gate_cloning:
            skipped.add(MoveType.CLONE)
        if skip_size_down:
            skipped.add(MoveType.SIZEDOWN)
        if skip_buffering:
            skipped.update({MoveType.BUFFER, MoveType.SPLIT})
        if skip_buffer_removal:
            skipped.add(MoveType.UNBUFFER)
        if skip_vt_swap:
            skipped.add(MoveType.VTSWAP_SPEED)
        move_map: Dict[MoveType, BaseMove] = {
            MoveType.BUFFER: self.buffer_move_,
            MoveType.UNBUFFER: self.unbuffer_move_,
            MoveType.SWAP: self.swap_pins_move_,
            MoveType.SIZE: self.sizeup_move_,
            MoveType.SIZEUP: self.sizeup_move_,
            MoveType.SIZEUP_MATCH: self.sizeup_match_move_,
            MoveType.SIZEDOWN: self.sizedown_move_,
            MoveType.CLONE: self.clone_move_,
            MoveType.SPLIT: self.split_load_move_,
            MoveType.VTSWAP_SPEED: self.vt_swap_move_,
        }
        self.move_sequence_types_ = [move for move in sequence if move not in skipped]
        self.move_sequence_ = [move_map[move] for move in self.move_sequence_types_]

    def moveSequenceTypes(self) -> List[MoveType]:
        return list(self.move_sequence_types_)

    def setMoveTracker(self, tracker: Optional[MoveTracker]) -> None:
        self.move_tracker_ = tracker

    def makeMoveTracker(self) -> MoveTracker:
        self.move_tracker_ = MoveTracker(
            self.logger_,
            self.resizer_.sta_,
            self.db_network_,
            self.resizer_.block_,
        )
        return self.move_tracker_

    def moveTracker(self) -> Optional[MoveTracker]:
        return self.move_tracker_

    def beginEndpointRepair(self, endpoint_pin: Any) -> int:
        """记录当前 endpoint 的一次 repair 尝试，供上层调度/报告使用。"""

        key = _obj_key(endpoint_pin)
        count = self.endpoint_pass_counts_phase1_.get(key, 0) + 1
        self.endpoint_pass_counts_phase1_[key] = count
        self.rejected_pin_moves_current_endpoint_.clear()
        if self.move_tracker_ is not None:
            self.move_tracker_.setCurrentEndpoint(endpoint_pin)
        return count

    def endpointRepairCount(self, endpoint_pin: Any) -> int:
        return self.endpoint_pass_counts_phase1_.get(_obj_key(endpoint_pin), 0)

    def recordRejectedMove(self, pin: Any, move: BaseMove) -> None:
        key = _obj_key(pin)
        self.rejected_pin_moves_current_endpoint_.setdefault(key, set()).add(move)

    def rejectedMovesForPin(self, pin: Any) -> Set[BaseMove]:
        return set(self.rejected_pin_moves_current_endpoint_.get(_obj_key(pin), set()))

    def removedBufferCount(self) -> int:
        return self.removed_buffer_count_

    def reportMoveSummary(self) -> Dict[str, Any]:
        move_counts = {move.name(): move.numMoves() for move in self.allMoves()}
        return {
            "move_sequence": [move.value for move in self.move_sequence_types_],
            "removed_buffers": self.removed_buffer_count_,
            "endpoint_repairs": dict(self.endpoint_pass_counts_phase1_),
            "move_counts": move_counts,
            "tracker": self.move_tracker_.moveSummary() if self.move_tracker_ is not None else None,
        }

    def repairSetup(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RepairSetup::repairSetup")

    def repairEndpoint(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RepairSetup::repairEndpoint")

    def repairPins(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RepairSetup::repairPins")

    def fanout(self, vertex: Any) -> int:
        fanout = getattr(vertex, "fanout", 0)
        return int(fanout() if callable(fanout) else fanout)

    def hasTopLevelOutputPort(self, net: Any) -> bool:
        _not_translated("RepairSetup::hasTopLevelOutputPort")

    def reportSwappablePins(self) -> None:
        self.swap_pins_move_.reportSwappablePins()


class RepairHold:
    """hold timing repair 主流程边界。"""

    hold_slack_limit_ratio_max_ = 0.2
    print_interval_ = 10

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.logger_ = resizer.logger_
        self.db_network_ = resizer.db_network_
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.resize_count_ = 0
        self.inserted_buffer_count_ = 0
        self.cloned_gate_count_ = 0
        self.buffer_cell_ = None
        self.max_passes_ = 0
        self.max_repairs_per_pass_ = 0
        self.allow_setup_violations_ = False
        self.setup_slack_margin_ = 0.0
        self.initial_design_area_ = 0.0

    def init(self) -> None:
        self.db_network_ = self.resizer_.db_network_

    def repairHold(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RepairHold::repairHold")

    def setHoldBuffer(self, buffer_cell: Any) -> None:
        self.buffer_cell_ = buffer_cell

    def holdBuffer(self) -> Any:
        return self.buffer_cell_

    def recordInsertedBuffer(self, count: int = 1, buffer_cell: Any = None) -> None:
        if buffer_cell is not None:
            self.buffer_cell_ = buffer_cell
        self.inserted_buffer_count_ += count

    def recordResize(self, count: int = 1) -> None:
        self.resize_count_ += count

    def recordClonedGate(self, count: int = 1) -> None:
        self.cloned_gate_count_ += count

    def holdBufferCount(self) -> int:
        return self.inserted_buffer_count_

    def reportHoldBuffer(self) -> Any:
        return self.buffer_cell_

    def reportCounters(self) -> Dict[str, int]:
        return {
            "inserted_buffers": self.inserted_buffer_count_,
            "resized_drivers": self.resize_count_,
            "cloned_gates": self.cloned_gate_count_,
        }

    def resizeCount(self) -> int:
        return self.resize_count_

    def clonedGateCount(self) -> int:
        return self.cloned_gate_count_


class RecoverPower:
    """setup slack 充足路径上的 power recovery 流程边界。"""

    setup_slack_margin_ = 1e-11
    setup_slack_max_margin_ = 1e-4
    failed_move_threshold_limit_ = 500
    decreasing_slack_max_passes_ = 50
    rebuffer_max_fanout_ = 20
    split_load_min_fanout_ = 8
    rebuffer_buffer_penalty_ = 0.01
    min_print_interval_ = 10
    max_print_interval_ = 100

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.logger_ = resizer.logger_
        self.db_network_ = resizer.db_network_
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.scene_ = None
        self.resize_count_ = 0
        self.swapped_cell_count_ = 0
        self.sizedown_cell_count_ = 0
        self.recovered_power_ = 0.0
        self.match_cell_footprint_ = False
        self.verbose_ = False
        self.bad_vertices_: Set[Any] = set()
        self.initial_design_area_ = 0.0
        self.print_interval_ = 0

    def init(self) -> None:
        self.db_network_ = self.resizer_.db_network_

    def recoverPower(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RecoverPower::recoverPower")

    def configure(
        self,
        match_cell_footprint: bool = False,
        verbose: bool = False,
        scene: Any = None,
    ) -> None:
        self.match_cell_footprint_ = match_cell_footprint
        self.verbose_ = verbose
        self.scene_ = scene

    def recordSwap(self, count: int = 1, recovered_power: float = 0.0) -> None:
        self.swapped_cell_count_ += count
        self.recovered_power_ += recovered_power

    def recordSizeDown(self, count: int = 1, recovered_power: float = 0.0) -> None:
        self.sizedown_cell_count_ += count
        self.resize_count_ += count
        self.recovered_power_ += recovered_power

    def markBadVertex(self, vertex: Any) -> None:
        self.bad_vertices_.add(_obj_key(vertex))

    def isBadVertex(self, vertex: Any) -> bool:
        return _obj_key(vertex) in self.bad_vertices_

    def recoveredPower(self) -> float:
        return self.recovered_power_

    def resizeCount(self) -> int:
        return self.resize_count_

    def swappedCellCount(self) -> int:
        return self.swapped_cell_count_

    def sizeDownCount(self) -> int:
        return self.sizedown_cell_count_

    def reportCounters(self) -> Dict[str, Any]:
        return {
            "swapped_cells": self.swapped_cell_count_,
            "sizedown_cells": self.sizedown_cell_count_,
            "resized_cells": self.resize_count_,
            "recovered_power": self.recovered_power_,
            "bad_vertices": len(self.bad_vertices_),
            "match_cell_footprint": self.match_cell_footprint_,
        }


class SwapArithModules:
    """算术模块替换抽象接口，对应 ``SwapArithModules``。"""

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.db_network_ = None
        self.logger_ = None

    def replaceArithModules(self, path_count: int, target: str, slack_threshold: float) -> bool:
        raise NotImplementedError

    def collectArithInstsOnPath(self, path: Any, arithInsts: Set[Any]) -> None:
        raise NotImplementedError

    def isArithInstance(self, inst: Any) -> Tuple[bool, Any]:
        raise NotImplementedError

    def hasArithOperatorProperty(self, mod_inst: Any) -> bool:
        raise NotImplementedError

    def findCriticalInstances(self, path_count: int, target: str, slack_threshold: float, insts: Set[Any]) -> None:
        raise NotImplementedError

    def doSwapInstances(self, insts: Set[Any], target: str) -> bool:
        raise NotImplementedError


def initResizer(tcl_interp: Any = None) -> Resizer:
    """对应 ``MakeResizer.hh`` 的入口函数。

    C++ 版本向 Tcl 注册命令；Python 版本返回一个顶层 ``Resizer``，调用方可再
    注入 db/sta/router 等依赖。
    """

    return Resizer()


__all__ = [
    "BaseMove",
    "BufferMove",
    "BufferUse",
    "BufferedNet",
    "BufferedNetMetrics",
    "BufferedNetType",
    "CloneMove",
    "FixedDelay",
    "LibraryAnalysisData",
    "LoadRegion",
    "MoveStateData",
    "MoveStateType",
    "MoveTracker",
    "MoveType",
    "OptoParams",
    "PinInfo",
    "PreChecks",
    "RecoverPower",
    "RepairDesign",
    "RepairDesignLimits",
    "RepairDesignViolationCounters",
    "RepairHold",
    "RepairSetup",
    "Resizer",
    "ResizerObserver",
    "SizeDownMove",
    "SizeUpMatchMove",
    "SizeUpMove",
    "SlackEstimatorParams",
    "SplitLoadMove",
    "SwapArithModules",
    "SwapPinsMove",
    "UnbufferMove",
    "VTSwapSpeedMove",
    "VTCategory",
    "VTLeakageStats",
    "initResizer",
    "visitTree",
]
