"""OpenROAD cts 模块的 Python 翻译骨架。

本文件对照 OpenROAD `src/cts` 的主要 C++ 边界：
`TritonCTS`、`CtsOptions`、`Clock`、`ClockInst`、`ClockSubNet`、
`TreeBuilder`、`TechChar` 等。

真实 CTS 构树、合法化、写库、STA/OpenDB 联动算法暂不伪造，
尚未翻译的重算法入口统一抛出 `NotImplementedError`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple


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


@dataclass
class ClockInst:
    """对应 `ClockInst`，表示 CTS 内部的 buffer 或 sink。"""

    name: str
    master: str
    type: InstType
    x: int
    y: int
    input_pin_obj: Any = None
    input_cap: float = 0.0
    insertion_delay: float = 0.0
    output_cap: float = 0.0
    ideal_output_cap: float = 0.0
    inst_obj: Any = None

    def getName(self) -> str:
        return self.name

    def getMaster(self) -> str:
        return self.master

    def getX(self) -> int:
        return self.x

    def getY(self) -> int:
        return self.y

    def getLocation(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def isClockBuffer(self) -> bool:
        return self.type is InstType.CLOCK_BUFFER


@dataclass
class ClockSubNet:
    """对应 `ClockSubNet`，第一个实例为 driver，后续实例为 sink。"""

    name: str
    instances: List[ClockInst] = field(default_factory=list)
    leaf_level: bool = False

    def setLeafLevel(self, is_leaf: bool) -> None:
        self.leaf_level = is_leaf

    def isLeafLevel(self) -> bool:
        return self.leaf_level

    def addInst(self, inst: ClockInst) -> None:
        self.instances.append(inst)

    def getName(self) -> str:
        return self.name

    def getNumSinks(self) -> int:
        return max(0, len(self.instances) - 1)

    def getDriver(self) -> ClockInst:
        if not self.instances:
            raise IndexError("ClockSubNet 没有 driver")
        return self.instances[0]

    def forEachSink(self, func: Callable[[ClockInst], None]) -> None:
        for inst in self.instances[1:]:
            func(inst)


@dataclass
class Clock:
    """对应 `Clock`，保存一个 CTS clock network。"""

    net_name: str
    clock_pin: str
    sdc_clock_name: str
    clock_pin_x: int
    clock_pin_y: int
    clock_buffers: List[ClockInst] = field(default_factory=list)
    sinks: List[ClockInst] = field(default_factory=list)
    sub_nets: List[ClockSubNet] = field(default_factory=list)
    name_to_inst: Dict[str, ClockInst] = field(default_factory=dict)

    def addClockBuffer(self, name: str, master: str, x: int, y: int) -> ClockInst:
        full_name = f"{name}_{self.getName()}"
        inst = ClockInst(full_name, master, InstType.CLOCK_BUFFER, x, y)
        self.clock_buffers.append(inst)
        self.name_to_inst[full_name] = inst
        return inst

    def findClockByName(self, name: str) -> Optional[ClockInst]:
        return self.name_to_inst.get(name)

    def addSubNet(self, name: str) -> ClockSubNet:
        subnet = ClockSubNet(f"{name}_{self.getName()}")
        self.sub_nets.append(subnet)
        return subnet

    def addSink(
        self,
        name: str,
        x: int,
        y: int,
        pin_obj: Any = None,
        input_cap: float = 0.0,
        ins_delay: float = 0.0,
    ) -> None:
        self.sinks.append(
            ClockInst(
                name,
                "",
                InstType.CLOCK_SINK,
                x,
                y,
                pin_obj,
                input_cap,
                ins_delay,
            )
        )

    def getName(self) -> str:
        return self.net_name

    def getSdcName(self) -> str:
        return self.sdc_clock_name

    def getNumSinks(self) -> int:
        return len(self.sinks)


@dataclass
class CtsOptions:
    """对应 `CtsOptions`，保存 CTS 参数和统计计数。"""

    logger: Any = None
    stt_builder: Any = None
    clock_nets: str = ""
    root_buffer: str = ""
    sink_buffer: str = ""
    tree_buffer: str = ""
    buffer_list: List[str] = field(default_factory=list)
    db_units: int = -1
    wire_segment_unit: int = 0
    plot_solution: bool = False
    sink_clustering_enable: bool = False
    sink_clustering_use_max_cap: bool = False
    num_max_leaf_sinks: int = 0
    max_slew: int = 0
    max_char_slew: float = 0.0
    max_char_cap: float = 0.0
    char_wirelength_iterations: int = 0
    cap_steps: int = 0
    slew_steps: int = 0
    clock_tree_max_depth: int = 0
    enable_fake_lut_entries: bool = False
    force_buffers_on_leaf_level: bool = False
    buf_dist_ratio: float = 0.0
    clock_nets_objs: List[Any] = field(default_factory=list)
    metrics_file: str = ""
    clock_roots: int = 0
    clock_subnets: int = 0
    buffers_inserted: int = 0
    sinks: int = 0
    clustering_power: int = 0
    clustering_capacity: float = 0.0
    max_fanout: int = 0
    buffer_distance: Optional[int] = None
    vertex_buffer_distance: Optional[int] = None
    vertex_buffers_enable: bool = False
    simple_segments_enable: bool = False
    max_diameter: float = 0.0
    max_diameter_set: bool = False
    sink_clusters_size: int = 0
    sink_clusters_size_set: bool = False
    sink_clustering_levels: int = 0
    macro_max_diameter: float = 0.0
    macro_max_diameter_set: bool = False
    macro_sink_clusters_size: int = 0
    macro_sink_clusters_size_set: bool = False
    num_static_layers: int = 0
    balance_levels: bool = False
    sink_buffer_input_cap: float = 0.0
    obstruction_aware: bool = False
    apply_ndr: bool = False
    insertion_delay: bool = False
    buffer_list_inferred: bool = False
    sink_buffer_inferred: bool = False
    root_buffer_inferred: bool = False
    sink_buffer_max_cap_derate: float = 1.0
    sink_buffer_max_cap_derate_set: bool = False
    delay_buffer_derate: float = 1.0
    dummy_load: bool = False
    dummyload_prefix: str = ""
    cts_library: str = ""
    buffer_count: Dict[Any, int] = field(default_factory=dict)
    dummy_count: Dict[Any, int] = field(default_factory=dict)

    def getBufferDistance(self) -> int:
        if self.buffer_distance is not None:
            return self.buffer_distance
        if self.db_units == -1:
            raise ValueError("必须先设置 db_units")
        return 100 * self.db_units

    def getVertexBufferDistance(self) -> int:
        if self.vertex_buffer_distance is not None:
            return self.vertex_buffer_distance
        if self.db_units == -1:
            raise ValueError("必须先设置 db_units")
        return 240 * self.db_units

    def recordBuffer(self, master: Any, master_type: MasterType) -> None:
        table = self.dummy_count if master_type is MasterType.DUMMY else self.buffer_count
        table[master] = table.get(master, 0) + 1


@dataclass
class TechChar:
    """对应 `TechChar`，保存 CTS characterization 的外层状态。"""

    options: Optional[CtsOptions] = None
    delay_lut: Dict[Tuple[str, float, float], float] = field(default_factory=dict)
    slew_lut: Dict[Tuple[str, float, float], float] = field(default_factory=dict)
    wire_segments: List["WireSegment"] = field(default_factory=list)

    def characterize(self) -> None:
        _not_translated("TechChar::characterize")

    def createWireSegment(self, length: float, cap: float = 0.0, res: float = 0.0) -> "WireSegment":
        """创建 wire segment 记录。"""

        segment = WireSegment(length=length, cap=cap, res=res)
        self.wire_segments.append(segment)
        return segment

    def forEachWireSegment(self, func: Callable[["WireSegment"], None]) -> None:
        for segment in self.wire_segments:
            func(segment)

    def makeKey(self, master: str, slew: float, cap: float) -> Tuple[str, float, float]:
        return (master, slew, cap)


@dataclass
class WireSegment:
    """对应 `TechChar.h` 中用于特征化的 wire segment。"""

    length: float
    cap: float = 0.0
    res: float = 0.0
    delay: float = 0.0
    slew: float = 0.0


@dataclass
class TreeBuilder:
    """对应 `TreeBuilder` 抽象基类。"""

    options: CtsOptions
    clock: Clock
    parent: Optional["TreeBuilder"] = None
    logger: Any = None
    db: Any = None
    children: List["TreeBuilder"] = field(default_factory=list)
    tree_buf_levels: int = 0
    first_level_sink_drivers: Set[ClockInst] = field(default_factory=set)
    second_level_sink_drivers: Set[ClockInst] = field(default_factory=set)
    tree_level_buffers: Set[ClockInst] = field(default_factory=set)
    type: TreeType = TreeType.REGULAR_TREE
    ave_arrival: float = 0.0
    top_buffer_delay: float = 0.0

    def __post_init__(self) -> None:
        if self.parent is not None:
            self.parent.children.append(self)

    def run(self) -> None:
        _not_translated("TreeBuilder::run")

    def getClock(self) -> Clock:
        return self.clock

    def addChild(self, child: "TreeBuilder") -> None:
        self.children.append(child)

    def getChildren(self) -> List["TreeBuilder"]:
        return list(self.children)

    def getParent(self) -> Optional["TreeBuilder"]:
        return self.parent

    def getTreeTypeAsString(self) -> str:
        return self.type.value


class LevelTopology(Enum):
    """对应 H-tree 每层拓扑选择。"""

    NONE = "none"
    H_TREE = "h_tree"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


@dataclass
class SegmentBuilder:
    """对应 `HTreeBuilder` 内部 segment 构造边界。"""

    start: Point
    end: Point
    level: int = 0
    topology: LevelTopology = LevelTopology.NONE

    def length(self) -> float:
        return self.start.computeDist(self.end)


@dataclass
class HTreeBuilder(TreeBuilder):
    """对应 `HTreeBuilder`。"""

    level_topologies: List[LevelTopology] = field(default_factory=list)
    wire_segments: List[SegmentBuilder] = field(default_factory=list)
    sink_region: Optional[Box] = None

    def run(self) -> None:
        _not_translated("HTreeBuilder::run")

    def addWireSegment(self, segment: SegmentBuilder) -> None:
        self.wire_segments.append(segment)

    def getSinkRegion(self) -> Optional[Box]:
        return self.sink_region


@dataclass
class Matching:
    """对应 `SinkClustering` 中的 matching 结果。"""

    left: Point
    right: Point
    cost: float = 0.0


@dataclass
class SinkClustering:
    """对应 `SinkClustering`。"""

    points: List[Point] = field(default_factory=list)
    caps: List[float] = field(default_factory=list)
    matchings: List[Matching] = field(default_factory=list)
    solution: List[Point] = field(default_factory=list)
    max_diameter: float = 0.0
    max_size: int = 0
    scale: float = 1.0

    def addPoint(self, point: Point, cap: float = 0.0) -> None:
        self.points.append(point)
        self.caps.append(cap)

    def run(self) -> None:
        _not_translated("SinkClustering::run")

    def getSolution(self) -> List[Point]:
        return list(self.solution)

    def getWireLength(self) -> float:
        return sum(match.cost for match in self.matchings)


@dataclass
class GraphNode:
    """对应 latency balancer graph node。"""

    name: str
    delay: float = 0.0
    children: List["GraphNode"] = field(default_factory=list)

    def addChild(self, child: "GraphNode") -> None:
        self.children.append(child)


@dataclass
class LatencyBalancer:
    """对应 `LatencyBalancer`。"""

    root: Optional[GraphNode] = None
    nodes: Dict[str, GraphNode] = field(default_factory=dict)

    def makeNode(self, name: str, delay: float = 0.0) -> GraphNode:
        node = GraphNode(name=name, delay=delay)
        self.nodes[name] = node
        if self.root is None:
            self.root = node
        return node

    def run(self) -> None:
        _not_translated("LatencyBalancer::run")


@dataclass
class TritonCTS:
    """对应 `TritonCTS` 顶层入口。"""

    open_sta: Any = None
    network: Any = None
    logger: Any = None
    options: CtsOptions = field(default_factory=CtsOptions)
    tech_char: TechChar = field(default_factory=TechChar)
    resizer: Any = None
    builders: List[TreeBuilder] = field(default_factory=list)
    sta_clock_nets: Set[Any] = field(default_factory=set)
    visited_clock_nets: Set[Any] = field(default_factory=set)
    inst2clkbuf: Dict[Any, ClockInst] = field(default_factory=dict)
    driver2subnet: Dict[ClockInst, ClockSubNet] = field(default_factory=dict)
    db: Any = None
    block: Any = None
    number_of_clocks: int = 0
    num_clk_nets: int = 0
    num_fixed_nets: int = 0
    dummy_load_index: int = 0
    root_buffers: List[str] = field(default_factory=list)
    sink_buffers: List[str] = field(default_factory=list)
    reg_tree_root_buf_index: int = 0
    delay_buf_index: int = 0
    ndr_strategy: NdrStrategy = NdrStrategy.NONE

    def init(
        self,
        logger: Any,
        db: Any,
        network: Any,
        sta: Any,
        st_builder: Any,
        resizer: Any,
    ) -> None:
        self.logger = logger
        self.db = db
        self.network = network
        self.open_sta = sta
        self.resizer = resizer
        self.options.logger = logger
        self.options.stt_builder = st_builder
        self.tech_char.options = self.options

    def runTritonCts(self) -> None:
        _not_translated("TritonCTS::runTritonCts")

    def reportCtsMetrics(self) -> Dict[str, int]:
        return {
            "number_of_clocks": self.number_of_clocks,
            "num_clk_nets": self.num_clk_nets,
            "num_fixed_nets": self.num_fixed_nets,
            "num_builders": len(self.builders),
        }

    def getParms(self) -> CtsOptions:
        return self.options

    def getCharacterization(self) -> TechChar:
        return self.tech_char

    def setClockNets(self, names: str) -> int:
        self.options.clock_nets = names
        return len([name for name in names.split() if name])

    def setBufferList(self, buffers: str) -> None:
        self.options.buffer_list = [buf for buf in buffers.split() if buf]

    def setRootBuffer(self, buffers: str) -> None:
        self.root_buffers = [buf for buf in buffers.split() if buf]
        self.options.root_buffer = self.root_buffers[0] if self.root_buffers else ""

    def setSinkBuffer(self, buffers: str) -> None:
        self.sink_buffers = [buf for buf in buffers.split() if buf]
        self.options.sink_buffer = self.sink_buffers[0] if self.sink_buffers else ""

    def getRootBufferToString(self) -> str:
        return " ".join(self.root_buffers)

    def resetRootBuffer(self) -> None:
        self.root_buffers.clear()
        self.options.root_buffer = ""

    def addBuilder(self, builder: TreeBuilder) -> TreeBuilder:
        self.builders.append(builder)
        return builder

    def forEachBuilder(self, func: Callable[[TreeBuilder], None]) -> None:
        for builder in self.builders:
            func(builder)

    def setupCharacterization(self) -> None:
        _not_translated("TritonCTS::setupCharacterization")

    def checkCharacterization(self) -> None:
        _not_translated("TritonCTS::checkCharacterization")


def initTritonCts() -> TritonCTS:
    """对应 `initTritonCts`，返回 CTS 顶层对象。"""

    return TritonCTS()
