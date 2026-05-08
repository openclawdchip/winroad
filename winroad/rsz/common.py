"""Shared declarations for :mod:`winroad.rsz`."""

from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


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

def _json_value(obj: Any) -> Any:
    """把 rsz 状态报告压成 JSON-safe 值。

    rsz 当前保存的 pin/cell/net 往往还是外部 STA/DB 对象；报告面只承诺状态
    可导出，不承诺序列化这些对象本体，所以对象统一退化为可读名称。
    """

    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, tuple):
        return [_json_value(item) for item in obj]
    if isinstance(obj, list):
        return [_json_value(item) for item in obj]
    if isinstance(obj, set):
        return sorted(_json_value(item) for item in obj)
    if isinstance(obj, dict):
        return {str(_json_value(key)): _json_value(value) for key, value in obj.items()}
    as_dict = getattr(obj, "as_dict", None)
    if callable(as_dict):
        return _json_value(as_dict())
    if is_dataclass(obj):
        return _json_value(obj.__dict__)
    return _name_of(obj)

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

class RepairFlowPhase(Enum):
    """Repair flow 的轻量状态机阶段。

    C++ repair pass 会在收集 violator、尝试 move、提交/回滚之间切换；Python
    接口层只记录这些阶段，不执行真实 STA 查询或 DB 修改。
    """

    IDLE = "idle"
    CONFIGURED = "configured"
    COLLECTING = "collecting"
    REPAIRING = "repairing"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"

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
class RepairPhaseEvent:
    """Repair flow 状态机的一次阶段切换记录。"""

    phase: RepairFlowPhase
    reason: str = ""
    order: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {"phase": self.phase.value, "reason": self.reason, "order": self.order}

@dataclass
class EndpointRepairState:
    """单个 endpoint 在 setup repair 调度中的状态。"""

    endpoint: Any
    repair_count: int = 0
    committed_count: int = 0
    rejected_count: int = 0
    last_phase: RepairFlowPhase = RepairFlowPhase.IDLE
    last_reason: str = ""

    def begin(self) -> None:
        self.repair_count += 1
        self.last_phase = RepairFlowPhase.REPAIRING
        self.last_reason = ""

    def finish(self, committed: bool, reason: str = "") -> None:
        if committed:
            self.committed_count += 1
            self.last_phase = RepairFlowPhase.COMMITTED
        else:
            self.rejected_count += 1
            self.last_phase = RepairFlowPhase.ROLLED_BACK
        self.last_reason = reason

    def as_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": _json_value(self.endpoint),
            "repair_count": self.repair_count,
            "committed_count": self.committed_count,
            "rejected_count": self.rejected_count,
            "last_phase": self.last_phase.value,
            "last_reason": self.last_reason,
        }

@dataclass
class NetBufferRelation:
    """记录一次 net repair 中 endpoint/net/buffer 的关系。

    这是报告面和 smoke test 可用的数据结构；buffer insertion 和 netlist mutation
    仍由未翻译的 C++ 边界负责。
    """

    net: Any
    driver_pin: Any = None
    load_pins: List[Any] = field(default_factory=list)
    inserted_buffers: List[Any] = field(default_factory=list)
    removed_buffers: List[Any] = field(default_factory=list)
    endpoint_pins: List[Any] = field(default_factory=list)
    buffer_to_loads: Dict[Any, List[Any]] = field(default_factory=dict)

    def add_buffer_loads(self, buffer: Any, loads: List[Any]) -> None:
        self.buffer_to_loads[_obj_key(buffer)] = list(loads)
        if buffer not in self.inserted_buffers:
            self.inserted_buffers.append(buffer)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "net": _json_value(self.net),
            "driver_pin": _json_value(self.driver_pin),
            "load_pins": _json_value(self.load_pins),
            "inserted_buffers": _json_value(self.inserted_buffers),
            "removed_buffers": _json_value(self.removed_buffers),
            "endpoint_pins": _json_value(self.endpoint_pins),
            "buffer_to_loads": _json_value(self.buffer_to_loads),
        }

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

    def as_dict(self) -> Dict[str, Any]:
        return {
            "max_wire_length": self.max_wire_length,
            "max_slew": self.max_slew,
            "max_cap": self.max_cap,
            "max_fanout": self.max_fanout,
            "slew_margin": self.slew_margin,
            "cap_margin": self.cap_margin,
            "corner": _json_value(self.corner),
            "buffer_cells": _json_value(self.buffer_cells),
        }

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

def _move_type_from_value(value: Any) -> MoveType:
    """把配置导入里的字符串/枚举归一化为 ``MoveType``。

    这里不调用 ``Resizer.parseMove``，避免 common.py 反向依赖顶层入口；别名只覆盖
    OpenROAD Tcl/日志里常见写法，未知值直接报错，防止批处理配置静默漏项。
    """

    if isinstance(value, MoveType):
        return value
    normalized = str(value).strip().lower().replace("-", "_")
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
        raise ValueError(f"unknown rsz move: {value}")
    return aliases[normalized]

@dataclass
class RepairSetupConfig:
    """RepairSetup 一轮优化使用的轻量配置。"""

    setup_slack_margin: float = 0.0
    verbose: bool = False
    skip_pin_swap: bool = False
    skip_gate_cloning: bool = False
    skip_size_down: bool = False
    skip_buffering: bool = False
    skip_buffer_removal: bool = False
    skip_vt_swap: bool = False
    max_repairs_per_pass: int = 1
    max_end_repairs: int = -1
    move_sequence: List[MoveType] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "setup_slack_margin": self.setup_slack_margin,
            "verbose": self.verbose,
            "skip_pin_swap": self.skip_pin_swap,
            "skip_gate_cloning": self.skip_gate_cloning,
            "skip_size_down": self.skip_size_down,
            "skip_buffering": self.skip_buffering,
            "skip_buffer_removal": self.skip_buffer_removal,
            "skip_vt_swap": self.skip_vt_swap,
            "max_repairs_per_pass": self.max_repairs_per_pass,
            "max_end_repairs": self.max_end_repairs,
            "move_sequence": [move.value for move in self.move_sequence],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepairSetupConfig":
        """从 JSON-safe dict 恢复 setup 配置。

        调用方常从 Tcl/Python 批处理读入字符串 move 名称；这里统一转为枚举，但不
        启动任何优化动作。
        """

        moves = [_move_type_from_value(move) for move in data.get("move_sequence", [])]
        return cls(
            setup_slack_margin=float(data.get("setup_slack_margin", 0.0)),
            verbose=bool(data.get("verbose", False)),
            skip_pin_swap=bool(data.get("skip_pin_swap", False)),
            skip_gate_cloning=bool(data.get("skip_gate_cloning", False)),
            skip_size_down=bool(data.get("skip_size_down", False)),
            skip_buffering=bool(data.get("skip_buffering", False)),
            skip_buffer_removal=bool(data.get("skip_buffer_removal", False)),
            skip_vt_swap=bool(data.get("skip_vt_swap", False)),
            max_repairs_per_pass=int(data.get("max_repairs_per_pass", 1)),
            max_end_repairs=int(data.get("max_end_repairs", -1)),
            move_sequence=moves,
        )

@dataclass
class RepairHoldConfig:
    """RepairHold 的 pass limit、buffer 和 setup 保护配置。"""

    buffer_cell: Any = None
    max_passes: int = 0
    max_repairs_per_pass: int = 0
    allow_setup_violations: bool = False
    setup_slack_margin: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "buffer_cell": _json_value(self.buffer_cell),
            "max_passes": self.max_passes,
            "max_repairs_per_pass": self.max_repairs_per_pass,
            "allow_setup_violations": self.allow_setup_violations,
            "setup_slack_margin": self.setup_slack_margin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepairHoldConfig":
        """从导出 dict 恢复 hold 配置；buffer cell 保留为导入对象/名称。"""

        return cls(
            buffer_cell=data.get("buffer_cell"),
            max_passes=int(data.get("max_passes", 0)),
            max_repairs_per_pass=int(data.get("max_repairs_per_pass", 0)),
            allow_setup_violations=bool(data.get("allow_setup_violations", False)),
            setup_slack_margin=float(data.get("setup_slack_margin", 0.0)),
        )

@dataclass
class RecoverPowerConfig:
    """RecoverPower 的轻量配置，不触发 cell swap / size-down。"""

    recover_power_percent: float = 0.0
    match_cell_footprint: bool = False
    verbose: bool = False
    scene: Any = None
    setup_slack_margin: float = 1e-11

    def as_dict(self) -> Dict[str, Any]:
        return {
            "recover_power_percent": self.recover_power_percent,
            "match_cell_footprint": self.match_cell_footprint,
            "verbose": self.verbose,
            "scene": _json_value(self.scene),
            "setup_slack_margin": self.setup_slack_margin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecoverPowerConfig":
        """从 JSON-safe dict 恢复 power recovery 配置。"""

        return cls(
            recover_power_percent=float(data.get("recover_power_percent", 0.0)),
            match_cell_footprint=bool(data.get("match_cell_footprint", False)),
            verbose=bool(data.get("verbose", False)),
            scene=data.get("scene"),
            setup_slack_margin=float(data.get("setup_slack_margin", 1e-11)),
        )

@dataclass
class RepairFlowState:
    """Repair* 流程通用状态快照。

    C++ 对象通常把配置、计数器和当前工作集散落在成员变量里；Python 接口层提供
    一个只读快照对象，便于测试、批处理日志和后续 Tcl report 复用。
    """

    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    counters: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    phase: RepairFlowPhase = RepairFlowPhase.IDLE
    history: List[RepairPhaseEvent] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.phase.value,
            "config": _json_value(self.config),
            "counters": _json_value(self.counters),
            "details": _json_value(self.details),
            "history": [event.as_dict() for event in self.history],
        }

@dataclass
class BufferedNetState:
    """BufferedNet 的树和指标快照。"""

    tree: Dict[str, Any]
    metrics: Dict[str, Any]
    text: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"tree": self.tree, "metrics": self.metrics, "text": self.text}

@dataclass
class MoveTrackerState:
    """MoveTracker 的 endpoint、violator 和 move 统计快照。"""

    current_endpoint: Any
    move_summary: Dict[str, int]
    move_summary_by_type: Dict[str, Dict[str, int]]
    critical_pins: List[Any] = field(default_factory=list)
    violators: List[Any] = field(default_factory=list)
    pending_count: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "current_endpoint": _json_value(self.current_endpoint),
            "critical_pins": _json_value(self.critical_pins),
            "violators": _json_value(self.violators),
            "move_summary": self.move_summary,
            "move_summary_by_type": self.move_summary_by_type,
            "pending_count": self.pending_count,
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
