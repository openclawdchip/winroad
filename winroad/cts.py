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

    def __hash__(self) -> int:
        return id(self)

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
    observer: Any = None
    clock_nets: str = ""
    root_buffer: str = ""
    sink_buffer: str = ""
    tree_buffer: str = ""
    buffer_list: List[str] = field(default_factory=list)
    db_units: int = -1
    wire_segment_unit: int = 0
    plot_solution: bool = False
    sink_clustering_enable: bool = True
    sink_clustering_use_max_cap: bool = False
    num_max_leaf_sinks: int = 15
    max_slew: int = 4
    max_wl: int = 0
    max_char_slew: float = 0.0
    max_char_cap: float = 0.0
    char_wirelength_iterations: int = 4
    cap_steps: int = 20
    slew_steps: int = 7
    clock_tree_max_depth: int = 100
    enable_fake_lut_entries: bool = True
    force_buffers_on_leaf_level: bool = True
    buf_dist_ratio: float = 0.1
    clock_nets_objs: List[Any] = field(default_factory=list)
    skip_nets: List[Any] = field(default_factory=list)
    metrics_file: str = ""
    clock_roots: int = 0
    clock_subnets: int = 0
    buffers_inserted: int = 0
    sinks: int = 0
    clustering_power: int = 4
    clustering_capacity: float = 0.6
    max_fanout: int = 0
    buffer_distance: Optional[int] = None
    vertex_buffer_distance: Optional[int] = None
    vertex_buffers_enable: bool = False
    simple_segments_enable: bool = False
    max_diameter: float = 50.0
    max_diameter_set: bool = False
    sink_clusters_size: int = 30
    sink_clusters_size_set: bool = False
    sink_clustering_levels: int = 0
    macro_max_diameter: float = 50.0
    macro_max_diameter_set: bool = False
    macro_sink_clusters_size: int = 4
    macro_sink_clusters_size_set: bool = True
    num_static_layers: int = 0
    balance_levels: bool = False
    sink_buffer_input_cap: float = 0.0
    obstruction_aware: bool = True
    insertion_delay: bool = True
    buffer_list_inferred: bool = False
    sink_buffer_inferred: bool = False
    root_buffer_inferred: bool = False
    sink_buffer_max_cap_derate_default: float = 0.01
    sink_buffer_max_cap_derate: float = 0.01
    sink_buffer_max_cap_derate_set: bool = False
    delay_buffer_derate: float = 1.0
    dummy_load: bool = True
    dummyload_prefix: str = "clkload"
    cts_library: str = ""
    repair_clock_nets: bool = False
    ndr_strategy: NdrStrategy = NdrStrategy.HALF
    buffer_count: Dict[Any, int] = field(default_factory=dict)
    dummy_count: Dict[Any, int] = field(default_factory=dict)

    def setClockNets(self, clock_nets: str) -> None:
        self.clock_nets = clock_nets

    def getClockNets(self) -> str:
        return self.clock_nets

    def setRootBuffer(self, buffer: str) -> None:
        self.root_buffer = buffer

    def getRootBuffer(self) -> str:
        return self.root_buffer

    def setSinkBuffer(self, buffer: str) -> None:
        self.sink_buffer = buffer

    def getSinkBuffer(self) -> str:
        return self.sink_buffer

    def setTreeBuffer(self, buffer: str) -> None:
        self.tree_buffer = buffer

    def resetTreeBuffer(self) -> None:
        self.tree_buffer = ""

    def getTreeBuffer(self) -> str:
        return self.tree_buffer

    def setBufferList(self, buffers: Iterable[str]) -> None:
        self.buffer_list = [buf for buf in buffers if buf]

    def getBufferList(self) -> List[str]:
        return list(self.buffer_list)

    def getBufferListToString(self) -> str:
        return " ".join(self.buffer_list)

    def resetBufferList(self) -> None:
        self.buffer_list.clear()

    def setDbUnits(self, units: int) -> None:
        self.db_units = units

    def getDbUnits(self) -> int:
        return self.db_units

    def setWireSegmentUnit(self, wire_segment_unit: int) -> None:
        self.wire_segment_unit = wire_segment_unit

    def resetWireSegmentUnit(self) -> None:
        self.wire_segment_unit = 0

    def getWireSegmentUnit(self) -> int:
        return self.wire_segment_unit

    def setPlotSolution(self, plot: bool) -> None:
        self.plot_solution = plot

    def getPlotSolution(self) -> bool:
        return self.plot_solution

    def setObserver(self, observer: Any) -> None:
        self.observer = observer

    def getObserver(self) -> Any:
        return self.observer

    def setSinkClustering(self, enable: bool) -> None:
        self.sink_clustering_enable = enable

    def getSinkClustering(self) -> bool:
        return self.sink_clustering_enable

    def setNumMaxLeafSinks(self, num_sinks: int) -> None:
        self.num_max_leaf_sinks = num_sinks

    def getNumMaxLeafSinks(self) -> int:
        return self.num_max_leaf_sinks

    def setMaxSlew(self, slew: int) -> None:
        self.max_slew = slew

    def getMaxSlew(self) -> int:
        return self.max_slew

    def setMaxWl(self, wl: int) -> None:
        self.max_wl = wl

    def getMaxWl(self) -> int:
        return self.max_wl

    def setMaxCharSlew(self, slew: float) -> None:
        self.max_char_slew = slew

    def getMaxCharSlew(self) -> float:
        return self.max_char_slew

    def setMaxCharCap(self, cap: float) -> None:
        self.max_char_cap = cap

    def getMaxCharCap(self) -> float:
        return self.max_char_cap

    def setCharWirelengthIterations(self, iterations: int) -> None:
        self.char_wirelength_iterations = iterations

    def getCharWirelengthIterations(self) -> int:
        return self.char_wirelength_iterations

    def setCapSteps(self, steps: int) -> None:
        self.cap_steps = steps

    def getCapSteps(self) -> int:
        return self.cap_steps

    def setSlewSteps(self, steps: int) -> None:
        self.slew_steps = steps

    def getSlewSteps(self) -> int:
        return self.slew_steps

    def setClockTreeMaxDepth(self, depth: int) -> None:
        self.clock_tree_max_depth = depth

    def getClockTreeMaxDepth(self) -> int:
        return self.clock_tree_max_depth

    def setEnableFakeLutEntries(self, enable: bool) -> None:
        self.enable_fake_lut_entries = enable

    def isFakeLutEntriesEnabled(self) -> bool:
        return self.enable_fake_lut_entries

    def setForceBuffersOnLeafLevel(self, force: bool) -> None:
        self.force_buffers_on_leaf_level = force

    def forceBuffersOnLeafLevel(self) -> bool:
        return self.force_buffers_on_leaf_level

    def setBufDistRatio(self, ratio: float) -> None:
        self.buf_dist_ratio = ratio

    def getBufDistRatio(self) -> float:
        return self.buf_dist_ratio

    def setClockNetsObjs(self, nets: Iterable[Any]) -> None:
        self.clock_nets_objs = list(nets)

    def getClockNetsObjs(self) -> List[Any]:
        return list(self.clock_nets_objs)

    def setSkipNets(self, net: Any) -> None:
        self.skip_nets.append(net)

    def getSkipNets(self) -> List[Any]:
        return list(self.skip_nets)

    def getSkipNetsToString(self) -> str:
        return " ".join(getattr(net, "name", str(net)) for net in self.skip_nets)

    def resetSkipNets(self) -> None:
        self.skip_nets.clear()

    def setMetricsFile(self, metrics_file: str) -> None:
        self.metrics_file = metrics_file

    def getMetricsFile(self) -> str:
        return self.metrics_file

    def setNumClockRoots(self, roots: int) -> None:
        self.clock_roots = roots

    def getNumClockRoots(self) -> int:
        return self.clock_roots

    def setNumClockSubnets(self, nets: int) -> None:
        self.clock_subnets = nets

    def getNumClockSubnets(self) -> int:
        return self.clock_subnets

    def setNumBuffersInserted(self, buffers: int) -> None:
        self.buffers_inserted = buffers

    def getNumBuffersInserted(self) -> int:
        return self.buffers_inserted

    def setNumSinks(self, sinks: int) -> None:
        self.sinks = sinks

    def getNumSinks(self) -> int:
        return self.sinks

    def getClusteringPower(self) -> int:
        return self.clustering_power

    def setClusteringPower(self, power: int) -> None:
        self.clustering_power = power

    def resetClusteringPower(self) -> None:
        self.clustering_power = 4

    def getClusteringCapacity(self) -> float:
        return self.clustering_capacity

    def setClusteringCapacity(self, capacity: float) -> None:
        self.clustering_capacity = capacity

    def resetClusteringCapacity(self) -> None:
        self.clustering_capacity = 0.6

    def setMaxFanout(self, max_fanout: int) -> None:
        self.max_fanout = max_fanout

    def getMaxFanout(self) -> int:
        return self.max_fanout

    def getBufferDistance(self) -> int:
        if self.buffer_distance is not None:
            return self.buffer_distance
        if self.db_units == -1:
            raise ValueError("必须先设置 db_units")
        return 100 * self.db_units

    def setBufferDistance(self, distance_dbu: int) -> None:
        self.buffer_distance = distance_dbu

    def resetBufferDistance(self) -> None:
        self.buffer_distance = None

    def getVertexBufferDistance(self) -> int:
        if self.vertex_buffer_distance is not None:
            return self.vertex_buffer_distance
        if self.db_units == -1:
            raise ValueError("必须先设置 db_units")
        return 240 * self.db_units

    def setVertexBufferDistance(self, distance_dbu: int) -> None:
        self.vertex_buffer_distance = distance_dbu

    def resetVertexBufferDistance(self) -> None:
        self.vertex_buffer_distance = None

    def isVertexBuffersEnabled(self) -> bool:
        return self.vertex_buffers_enable

    def setVertexBuffersEnabled(self, enable: bool) -> None:
        self.vertex_buffers_enable = enable

    def isSimpleSegmentEnabled(self) -> bool:
        return self.simple_segments_enable

    def setSimpleSegmentsEnabled(self, enable: bool) -> None:
        self.simple_segments_enable = enable

    def getMaxDiameter(self) -> float:
        return self.max_diameter

    def setMaxDiameter(self, distance: float) -> None:
        self.max_diameter = distance
        self.max_diameter_set = True

    def resetMaxDiameter(self) -> None:
        self.max_diameter = 50.0
        self.max_diameter_set = False

    def isMaxDiameterSet(self) -> bool:
        return self.max_diameter_set

    def getSinkClusteringSize(self) -> int:
        return self.sink_clusters_size

    def setSinkClusteringSize(self, size: int) -> None:
        self.sink_clusters_size = size
        self.sink_clusters_size_set = True

    def resetSinkClusteringSize(self) -> None:
        self.sink_clusters_size = 30
        self.sink_clusters_size_set = False

    def isSinkClusteringSizeSet(self) -> bool:
        return self.sink_clusters_size_set

    def limitSinkClusteringSizes(self, limit: int) -> None:
        self.sink_clusters_size = min(self.sink_clusters_size, limit)
        self.macro_sink_clusters_size = min(self.macro_sink_clusters_size, limit)

    def getSinkClusteringLevels(self) -> int:
        return self.sink_clustering_levels

    def setSinkClusteringLevels(self, levels: int) -> None:
        self.sink_clustering_levels = levels

    def resetSinkClusteringLevels(self) -> None:
        self.sink_clustering_levels = 0

    def getMacroMaxDiameter(self) -> float:
        return self.macro_max_diameter

    def setMacroMaxDiameter(self, distance: float) -> None:
        self.macro_max_diameter = distance
        self.macro_max_diameter_set = True

    def resetMacroMaxDiameter(self) -> None:
        self.macro_max_diameter = 50.0
        self.macro_max_diameter_set = False

    def isMacroMaxDiameterSet(self) -> bool:
        return self.macro_max_diameter_set

    def getMacroSinkClusteringSize(self) -> int:
        return self.macro_sink_clusters_size

    def setMacroClusteringSize(self, size: int) -> None:
        self.macro_sink_clusters_size = size
        self.macro_sink_clusters_size_set = True

    def resetMacroClusteringSize(self) -> None:
        self.macro_sink_clusters_size = 4
        self.macro_sink_clusters_size_set = False

    def isMacroSinkClusteringSizeSet(self) -> bool:
        return self.macro_sink_clusters_size_set

    def getNumStaticLayers(self) -> int:
        return self.num_static_layers

    def setNumStaticLayers(self, num: int) -> None:
        self.num_static_layers = num

    def resetNumStaticLayers(self) -> None:
        self.num_static_layers = 0

    def setSinkBufferInputCap(self, cap: float) -> None:
        self.sink_buffer_input_cap = cap

    def getSinkBufferInputCap(self) -> float:
        return self.sink_buffer_input_cap

    def getLogger(self) -> Any:
        return self.logger

    def setObstructionAware(self, obs: bool) -> None:
        self.obstruction_aware = obs

    def getObstructionAware(self) -> bool:
        return self.obstruction_aware

    def enableInsertionDelay(self, ins_delay: bool) -> None:
        self.insertion_delay = ins_delay

    def insertionDelayEnabled(self) -> bool:
        return self.insertion_delay

    def setBufferListInferred(self, inferred: bool) -> None:
        self.buffer_list_inferred = inferred

    def isBufferListInferred(self) -> bool:
        return self.buffer_list_inferred

    def setSinkBufferInferred(self, inferred: bool) -> None:
        self.sink_buffer_inferred = inferred

    def isSinkBufferInferred(self) -> bool:
        return self.sink_buffer_inferred

    def setRootBufferInferred(self, inferred: bool) -> None:
        self.root_buffer_inferred = inferred

    def isRootBufferInferred(self) -> bool:
        return self.root_buffer_inferred

    def setSinkBufferMaxCapDerate(self, derate: float) -> None:
        self.sink_buffer_max_cap_derate = derate
        self.sink_buffer_max_cap_derate_set = True

    def resetSinkBufferMaxCapDerate(self) -> None:
        self.sink_buffer_max_cap_derate = self.sink_buffer_max_cap_derate_default
        self.sink_buffer_max_cap_derate_set = False

    def getSinkBufferMaxCapDerate(self) -> float:
        return self.sink_buffer_max_cap_derate

    def isSinkBufferMaxCapDerateSet(self) -> bool:
        return self.sink_buffer_max_cap_derate_set

    def setDelayBufferDerate(self, derate: float) -> None:
        self.delay_buffer_derate = derate

    def resetDelayBufferDerate(self) -> None:
        self.delay_buffer_derate = 1.0

    def getDelayBufferDerate(self) -> float:
        return self.delay_buffer_derate

    def enableDummyLoad(self, dummy_load: bool) -> None:
        self.dummy_load = dummy_load

    def dummyLoadEnabled(self) -> bool:
        return self.dummy_load

    def getDummyLoadPrefix(self) -> str:
        return self.dummyload_prefix

    def setCtsLibrary(self, name: str) -> None:
        self.cts_library = name

    def resetCtsLibrary(self) -> None:
        self.cts_library = ""

    def getCtsLibrary(self) -> str:
        return self.cts_library

    def isCtsLibrarySet(self) -> bool:
        return bool(self.cts_library)

    def setRepairClockNets(self, value: bool) -> None:
        self.repair_clock_nets = value

    def getRepairClockNets(self) -> bool:
        return self.repair_clock_nets

    def setApplyNDR(self, strategy: NdrStrategy) -> None:
        self.ndr_strategy = strategy

    def resetApplyNDR(self) -> None:
        self.ndr_strategy = NdrStrategy.HALF

    def getApplyNdr(self) -> NdrStrategy:
        return self.ndr_strategy

    def getApplyNdrName(self) -> str:
        return self.ndr_strategy.value

    def recordBuffer(self, master: Any, master_type: MasterType) -> None:
        table = self.dummy_count if master_type is MasterType.DUMMY else self.buffer_count
        table[master] = table.get(master, 0) + 1

    def getBufferCount(self) -> Dict[Any, int]:
        return dict(self.buffer_count)

    def getDummyCount(self) -> Dict[Any, int]:
        return dict(self.dummy_count)

    def getType(self, inst: Any) -> MasterType:
        master = getattr(inst, "master", None)
        if master in self.dummy_count:
            return MasterType.DUMMY
        return MasterType.TREE


@dataclass
class TechChar:
    """对应 `TechChar`，保存 CTS characterization 的外层状态。"""

    options: Optional[CtsOptions] = None
    db: Any = None
    open_sta: Any = None
    db_network: Any = None
    delay_lut: Dict[Tuple[int, int, int], List[int]] = field(default_factory=dict)
    slew_lut: Dict[Tuple[int, int, int], List[int]] = field(default_factory=dict)
    wire_segments: List["WireSegment"] = field(default_factory=list)
    key_to_wire_segments: Dict[Tuple[int, int, int], List[int]] = field(default_factory=dict)
    length_unit: int = 0
    length_unit_ratio: int = 0
    min_segment_length: int = 0
    max_segment_length: int = 0
    min_capacitance: int = 0
    max_capacitance: int = 0
    min_slew: int = 0
    max_slew: int = 0
    actual_min_input_cap: int = 0
    res_per_dbu: float = 0.0
    cap_per_dbu: float = 0.0
    char_slew_step_size: float = 0.0
    char_cap_step_size: float = 0.0
    master_names: List[str] = field(default_factory=list)
    wirelengths_to_test: List[float] = field(default_factory=list)
    loads_to_test: List[float] = field(default_factory=list)
    slews_to_test: List[float] = field(default_factory=list)
    solution_map: Dict[Any, List[Any]] = field(default_factory=dict)

    def characterize(self) -> None:
        _not_translated("TechChar::characterize")

    def create(self) -> None:
        _not_translated("TechChar::create")

    def report(self) -> None:
        _not_translated("TechChar::report")

    def reportSegment(self, key: int) -> None:
        _not_translated("TechChar::reportSegment")

    def reportSegments(self, length: int, load: int, output_slew: int) -> None:
        _not_translated("TechChar::reportSegments")

    def createWireSegment(self, length: float, cap: float = 0.0, res: float = 0.0) -> "WireSegment":
        """创建 wire segment 记录。"""

        segment = WireSegment(length=length, cap=cap, res=res)
        self.wire_segments.append(segment)
        return segment

    def addWireSegment(self, key: Tuple[int, int, int], segment: "WireSegment") -> int:
        idx = len(self.wire_segments)
        self.wire_segments.append(segment)
        self.key_to_wire_segments.setdefault(key, []).append(idx)
        return idx

    def forEachWireSegment(self, func: Callable[["WireSegment"], None]) -> None:
        for segment in self.wire_segments:
            func(segment)

    def forEachWireSegmentByKey(
        self, key: Tuple[int, int, int], func: Callable[[int, "WireSegment"], None]
    ) -> None:
        for idx in self.key_to_wire_segments.get(key, []):
            func(idx, self.wire_segments[idx])

    def getWireSegment(self, idx: int) -> "WireSegment":
        return self.wire_segments[idx]

    def getMinSegmentLength(self) -> int:
        return self.min_segment_length

    def getMaxSegmentLength(self) -> int:
        return self.max_segment_length

    def getMaxCapacitance(self) -> int:
        return self.max_capacitance

    def getMaxSlew(self) -> int:
        return self.max_slew

    def setActualMinInputCap(self, cap: int) -> None:
        self.actual_min_input_cap = cap

    def getActualMinInputCap(self) -> int:
        return self.actual_min_input_cap

    def getLengthUnit(self) -> int:
        return self.length_unit

    def setLengthUnit(self, length: int) -> None:
        self.length_unit = length

    def createFakeEntries(self, length: int, fake_length: int) -> None:
        _not_translated("TechChar::createFakeEntries")

    def getCapPerDBU(self) -> float:
        return self.cap_per_dbu

    def printCharacterization(self) -> None:
        _not_translated("TechChar::printCharacterization")

    def printSolution(self) -> None:
        _not_translated("TechChar::printSolution")

    def compileLut(self, lut_solutions: Iterable[Any]) -> None:
        _not_translated("TechChar::compileLut")

    def computeKey(self, length: int, load: int, output_slew: int) -> int:
        return (length << 20) | (load << 10) | output_slew

    def makeKey(self, length: int, load: int, output_slew: int) -> Tuple[int, int, int]:
        return (length, load, output_slew)

    def initLengthUnits(self) -> None:
        _not_translated("TechChar::initLengthUnits")

    def toInternalLengthUnit(self, length: int) -> int:
        if self.length_unit <= 0:
            return length
        return int(round(length / self.length_unit))

    def reset(self) -> None:
        self.delay_lut.clear()
        self.slew_lut.clear()
        self.wire_segments.clear()
        self.key_to_wire_segments.clear()
        self.solution_map.clear()


@dataclass
class WireSegment:
    """对应 `TechChar.h` 中用于特征化的 wire segment。"""

    length: float
    power: float = 0.0
    segment_delay: int = 0
    cap: float = 0.0
    res: float = 0.0
    delay: float = 0.0
    slew: float = 0.0
    buffer_locations: List[float] = field(default_factory=list)
    buffer_masters: List[str] = field(default_factory=list)
    wl2_first_buffer: int = 0
    last_wl: int = 0

    def addBuffer(self, location: float) -> None:
        self.buffer_locations.append(location)

    def addBufferMaster(self, name: str) -> None:
        self.buffer_masters.append(name)

    def setWl2FirstBuffer(self, wl: int) -> None:
        self.wl2_first_buffer = wl

    def setLastWl(self, wl: int) -> None:
        self.last_wl = wl

    def getPower(self) -> float:
        return self.power

    def getDelay(self) -> int:
        return self.segment_delay

    def getWl2FirstBuffer(self) -> int:
        return self.wl2_first_buffer

    def getLastWl(self) -> int:
        return self.last_wl

    def isBuffered(self) -> bool:
        return bool(self.buffer_locations)

    def getNumBuffers(self) -> int:
        return len(self.buffer_locations)

    def getBufferLocations(self) -> List[float]:
        return list(self.buffer_locations)

    def getBufferMasters(self) -> List[str]:
        return list(self.buffer_masters)

    def getBufferLocation(self, idx: int) -> float:
        return self.buffer_locations[idx]

    def getBufferMaster(self, idx: int) -> str:
        return self.buffer_masters[idx]


@dataclass
class TreeBuilder:
    """对应 `TreeBuilder` 抽象基类。"""

    options: CtsOptions
    clock: Clock
    parent: Optional["TreeBuilder"] = None
    logger: Any = None
    db: Any = None
    tech_char: Optional[TechChar] = None
    children: List["TreeBuilder"] = field(default_factory=list)
    tree_buf_levels: int = 0
    first_level_sink_drivers: Set[ClockInst] = field(default_factory=set)
    second_level_sink_drivers: Set[ClockInst] = field(default_factory=set)
    tree_level_buffers: Set[ClockInst] = field(default_factory=set)
    blockages: List[Box] = field(default_factory=list)
    occupied_locations: Set[Point] = field(default_factory=set)
    sink_insertion_delays: Dict[Point, float] = field(default_factory=dict)
    buffer_width: float = 0.0
    buffer_height: float = 0.0
    type: TreeType = TreeType.REGULAR_TREE
    ave_arrival: float = 0.0
    n_dummies: int = 0
    top_buffer: Any = None
    top_buffer_name: str = ""
    driving_net: Any = None
    top_input_net: Any = None

    def __post_init__(self) -> None:
        if self.parent is not None:
            self.parent.children.append(self)

    def run(self) -> None:
        _not_translated("TreeBuilder::run")

    def mergeBlockages(self) -> None:
        _not_translated("TreeBuilder::mergeBlockages")

    def initBlockages(self) -> None:
        _not_translated("TreeBuilder::initBlockages")

    def setTechChar(self, tech_char: TechChar) -> None:
        self.tech_char = tech_char

    def getClock(self) -> Clock:
        return self.clock

    def addChild(self, child: "TreeBuilder") -> None:
        self.children.append(child)

    def getChildren(self) -> List["TreeBuilder"]:
        return list(self.children)

    def getParent(self) -> Optional["TreeBuilder"]:
        return self.parent

    def isLeafTree(self) -> bool:
        return not self.children

    def getTreeBufLevels(self) -> int:
        return self.tree_buf_levels

    def addFirstLevelSinkDriver(self, inst: ClockInst) -> None:
        self.first_level_sink_drivers.add(inst)

    def addSecondLevelSinkDriver(self, inst: ClockInst) -> None:
        self.second_level_sink_drivers.add(inst)

    def addTreeLevelBuffer(self, inst: ClockInst) -> None:
        self.tree_level_buffers.add(inst)

    def isAnyTreeBuffer(self, inst: ClockInst) -> bool:
        return self.isLeafBuffer(inst) or self.isLevelBuffer(inst)

    def isLeafBuffer(self, inst: ClockInst) -> bool:
        return self.isFirstLevelSinkDriver(inst) or self.isSecondLevelSinkDriver(inst)

    def isFirstLevelSinkDriver(self, inst: ClockInst) -> bool:
        return inst in self.first_level_sink_drivers

    def isSecondLevelSinkDriver(self, inst: ClockInst) -> bool:
        return inst in self.second_level_sink_drivers

    def isLevelBuffer(self, inst: ClockInst) -> bool:
        return inst in self.tree_level_buffers

    def setDb(self, db: Any) -> None:
        self.db = db

    def setLogger(self, logger: Any) -> None:
        self.logger = logger

    def isInsideBbox(
        self, x: float, y: float, x1: float, y1: float, x2: float, y2: float
    ) -> bool:
        return Box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)).contains(Point(x, y))

    def isAlongBbox(
        self, x: float, y: float, x1: float, y1: float, x2: float, y2: float
    ) -> bool:
        return self.isInsideBbox(x, y, x1, y1, x2, y2) and (
            fuzzyEqual(x, x1) or fuzzyEqual(x, x2) or fuzzyEqual(y, y1) or fuzzyEqual(y, y2)
        )

    def checkLegalitySpecial(
        self,
        loc: Point,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        scaling_factor: int,
    ) -> bool:
        _not_translated("TreeBuilder::checkLegalitySpecial")

    def findBlockage(
        self, buffer_loc: Point, scaling_unit: float
    ) -> Optional[Tuple[float, float, float, float]]:
        _not_translated("TreeBuilder::findBlockage")

    def legalizeOneBuffer(self, buffer_loc: Point, buffer_name: str) -> Point:
        _not_translated("TreeBuilder::legalizeOneBuffer")

    def addCandidatePoint(
        self, x: float, y: float, point: Point, candidates: List[Point]
    ) -> None:
        candidates.append(Point(x, y))

    def getBufferWidth(self) -> float:
        return self.buffer_width

    def getBufferHeight(self) -> float:
        return self.buffer_height

    def checkLegalityLoc(self, buffer_loc: Point, scaling_factor: int) -> bool:
        _not_translated("TreeBuilder::checkLegalityLoc")

    def isOccupiedLoc(self, buffer_loc: Point) -> bool:
        return buffer_loc in self.occupied_locations

    def commitLoc(self, buffer_loc: Point) -> None:
        self.occupied_locations.add(buffer_loc)

    def uncommitLoc(self, buffer_loc: Point) -> None:
        self.occupied_locations.discard(buffer_loc)

    def commitMoveLoc(self, old_loc: Point, new_loc: Point) -> None:
        self.uncommitLoc(old_loc)
        self.commitLoc(new_loc)

    def sinkHasInsertionDelay(self, sink: Point) -> bool:
        return sink in self.sink_insertion_delays

    def setSinkInsertionDelay(self, sink: Point, ins_delay: float) -> None:
        self.sink_insertion_delays[sink] = ins_delay

    def getSinkInsertionDelay(self, sink: Point) -> float:
        return self.sink_insertion_delays[sink]

    def computeDist(self, x: Point, y: Point) -> float:
        return x.computeDist(y)

    def getTreeType(self) -> TreeType:
        return self.type

    def setTreeType(self, type: TreeType) -> None:
        self.type = type

    def getTreeTypeAsString(self) -> str:
        return self.type.value

    def getAveSinkArrival(self) -> float:
        return self.ave_arrival

    def setAveSinkArrival(self, arrival: float) -> None:
        self.ave_arrival = arrival

    def getNDummies(self) -> int:
        return self.n_dummies

    def setNDummies(self, n_dummies: int) -> None:
        self.n_dummies = n_dummies

    def getTopBuffer(self) -> Any:
        return self.top_buffer

    def setTopBuffer(self, inst: Any) -> None:
        self.top_buffer = inst

    def getTopBufferName(self) -> str:
        return self.top_buffer_name

    def setTopBufferName(self, name: str) -> None:
        self.top_buffer_name = name

    def getTopInputNet(self) -> Any:
        return self.top_input_net

    def setTopInputNet(self, net: Any) -> None:
        self.top_input_net = net

    def getDrivingNet(self) -> Any:
        return self.driving_net

    def setDrivingNet(self, net: Any) -> None:
        self.driving_net = net


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
    inst_prefix: str = ""
    net_prefix: str = ""
    tech_char_wires: List[int] = field(default_factory=list)
    driving_subnet: Optional[ClockSubNet] = None
    num_buffer_levels: int = 0

    def length(self) -> float:
        return self.start.computeDist(self.end)

    def build(self, force_buffer: str = "") -> None:
        _not_translated("SegmentBuilder::build")

    def forceBufferInSegment(self, master: str) -> None:
        _not_translated("SegmentBuilder::forceBufferInSegment")

    def getDrivingSubNet(self) -> Optional[ClockSubNet]:
        return self.driving_subnet

    def getNumBufferLevels(self) -> int:
        return self.num_buffer_levels


@dataclass
class HTreeBuilder(TreeBuilder):
    """对应 `HTreeBuilder`。"""

    level_topologies: List[LevelTopology] = field(default_factory=list)
    wire_segments: List[SegmentBuilder] = field(default_factory=list)
    sink_region: Optional[Box] = None
    branch_point_locs: List[Point] = field(default_factory=list)
    branch_point_parents: List[int] = field(default_factory=list)
    branch_driving_subnets: List[Optional[ClockSubNet]] = field(default_factory=list)
    branch_sink_locs: List[List[Point]] = field(default_factory=list)
    output_slew: int = 0
    output_cap: int = 0
    remaining_length: int = 0
    curr_wl: int = 0
    wire_segment_unit: int = 0
    min_input_cap: int = 0
    num_max_leaf_sinks: int = 0
    min_length_sink_region: int = 0
    clock_tree_max_depth: int = 0
    cluster_diameters_: List[int] = field(default_factory=lambda: [50, 100, 200])
    cluster_sizes_: List[int] = field(default_factory=lambda: [10, 20, 30])

    def run(self) -> None:
        _not_translated("HTreeBuilder::run")

    def addWireSegment(self, segment: SegmentBuilder) -> None:
        self.wire_segments.append(segment)

    def addBranchingPoint(self, loc: Point, parent: int) -> int:
        self.branch_point_locs.append(loc)
        self.branch_point_parents.append(parent)
        self.branch_driving_subnets.append(None)
        self.branch_sink_locs.append([])
        return len(self.branch_point_locs) - 1

    def addSinkToBranch(self, branch_idx: int, sink_loc: Point) -> None:
        self.branch_sink_locs[branch_idx].append(sink_loc)

    def getBranchingPointSize(self) -> int:
        return len(self.branch_point_locs)

    def getBranchingPoint(self, idx: int) -> Point:
        return self.branch_point_locs[idx]

    def getBranchingPointParentIdx(self, idx: int) -> int:
        return self.branch_point_parents[idx]

    def forEachBranchingPoint(self, func: Callable[[int, Point], None]) -> None:
        for idx, loc in enumerate(self.branch_point_locs):
            func(idx, loc)

    def getBranchDrivingSubNet(self, idx: int) -> Optional[ClockSubNet]:
        return self.branch_driving_subnets[idx]

    def setBranchDrivingSubNet(self, idx: int, subnet: ClockSubNet) -> None:
        self.branch_driving_subnets[idx] = subnet

    def getWireSegments(self) -> List[SegmentBuilder]:
        return list(self.wire_segments)

    def getBranchSinksLocations(self, branch_idx: int) -> List[Point]:
        return list(self.branch_sink_locs[branch_idx])

    def setOutputSlew(self, slew: int) -> None:
        self.output_slew = slew

    def getOutputSlew(self) -> int:
        return self.output_slew

    def setOutputCap(self, cap: int) -> None:
        self.output_cap = cap

    def getOutputCap(self) -> int:
        return self.output_cap

    def setRemainingLength(self, length: int) -> None:
        self.remaining_length = length

    def getRemainingLength(self) -> int:
        return self.remaining_length

    def setCurrWl(self, wl: int) -> None:
        self.curr_wl = wl

    def getCurrWl(self) -> int:
        return self.curr_wl

    def getSinkRegion(self) -> Optional[Box]:
        return self.sink_region

    def legalizeOneBuffer(self, buffer_loc: Point, buffer_name: str) -> Point:
        _not_translated("HTreeBuilder::legalizeOneBuffer")

    def findLegalLocations(
        self,
        parent_point: Point,
        branch_point: Point,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        points: List[Point],
    ) -> None:
        _not_translated("HTreeBuilder::findLegalLocations")

    def findBestLegalLocation(self, *args: Any, **kwargs: Any) -> Point:
        _not_translated("HTreeBuilder::findBestLegalLocation")

    def legalize(self) -> None:
        _not_translated("HTreeBuilder::legalize")

    def legalizeDummy(self) -> None:
        _not_translated("HTreeBuilder::legalizeDummy")

    def printHTree(self) -> None:
        _not_translated("HTreeBuilder::printHTree")

    def plotSolution(self) -> None:
        _not_translated("HTreeBuilder::plotSolution")

    def plotHTree(self) -> str:
        _not_translated("HTreeBuilder::plotHTree")

    def findSibling(self, topology: LevelTopology, i: int, par: int) -> int:
        _not_translated("HTreeBuilder::findSibling")

    def getTopologyVector(self) -> List[LevelTopology]:
        return list(self.level_topologies)

    def getWireSegmentUnit(self) -> int:
        return self.wire_segment_unit

    def computeMinDelaySegment(self, *args: Any, **kwargs: Any) -> int:
        _not_translated("HTreeBuilder::computeMinDelaySegment")

    def initSinkRegion(self) -> None:
        _not_translated("HTreeBuilder::initSinkRegion")

    def computeLevelTopology(self, level: int, width: float, height: float) -> None:
        _not_translated("HTreeBuilder::computeLevelTopology")

    def computeNumberOfSinksPerSubRegion(self, level: int) -> int:
        _not_translated("HTreeBuilder::computeNumberOfSinksPerSubRegion")

    def createClockSubNets(self) -> None:
        _not_translated("HTreeBuilder::createClockSubNets")

    def createSingleBufferClockNet(self) -> None:
        _not_translated("HTreeBuilder::createSingleBufferClockNet")

    def preSinkClustering(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("HTreeBuilder::preSinkClustering")

    def assignSinksToBranches(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("HTreeBuilder::assignSinksToBranches")

    def weightedDistance(self, new_loc: Point, old_loc: Point, sinks: List[Point]) -> float:
        if not sinks:
            return new_loc.computeDist(old_loc)
        return sum(new_loc.computeDist(sink) for sink in sinks) / len(sinks)

    def clusterDiameters(self) -> List[int]:
        return list(self.cluster_diameters_)

    def clusterSizes(self) -> List[int]:
        return list(self.cluster_sizes_)

    def resolveLocationCollision(self, legal_center: Point) -> Point:
        _not_translated("HTreeBuilder::resolveLocationCollision")


@dataclass
class Matching:
    """对应 `SinkClustering` 中的 matching 结果。"""

    left: Point
    right: Point
    cost: float = 0.0
    p0: int = 0
    p1: int = 0

    def getP0(self) -> int:
        return self.p0

    def getP1(self) -> int:
        return self.p1


@dataclass
class SinkClustering:
    """对应 `SinkClustering`。"""

    options: Optional[CtsOptions] = None
    tech_char: Optional[TechChar] = None
    points: List[Point] = field(default_factory=list)
    caps: List[float] = field(default_factory=list)
    theta_index_vector: List[Tuple[float, int]] = field(default_factory=list)
    matchings: List[Matching] = field(default_factory=list)
    sink_clusters: Dict[int, List[Point]] = field(default_factory=dict)
    best_solution: List[List[int]] = field(default_factory=list)
    solution: List[Point] = field(default_factory=list)
    max_internal_diameter: float = 0.0
    cap_per_unit: float = 0.0
    use_max_diameter: bool = False
    use_max_size: bool = False
    use_max_cap_limit: bool = False
    scale_factor: int = 1
    first_run: bool = True
    x_span: float = 0.0
    y_span: float = 0.0
    max_diameter: float = 0.0
    max_size: int = 0
    best_solution_cost: float = float("inf")
    scale: float = 1.0

    def addPoint(self, point: Point, cap: float = 0.0) -> None:
        self.points.append(point)
        self.caps.append(cap)

    def addCap(self, cap: float) -> None:
        self.caps.append(cap)

    def run(
        self,
        group_size: Optional[int] = None,
        max_diameter: Optional[float] = None,
        scale_factor: Optional[int] = None,
    ) -> None:
        _not_translated("SinkClustering::run")

    def getNumPoints(self) -> int:
        return len(self.points)

    def allMatchings(self) -> List[Matching]:
        return list(self.matchings)

    def sinkClusteringSolution(self) -> List[List[int]]:
        return [list(cluster) for cluster in self.best_solution]

    def getSolution(self) -> List[Point]:
        return list(self.solution)

    def getWireLength(self, points: Optional[List[Point]] = None) -> float:
        if points is None:
            return sum(match.cost for match in self.matchings)
        return sum(points[i - 1].computeDist(points[i]) for i in range(1, len(points)))

    def getScaleFactor(self) -> int:
        return self.scale_factor

    def getMaxDiameter(self) -> float:
        return self.max_diameter

    def getMaxSize(self) -> int:
        return self.max_size

    def normalizePoints(self, max_diameter: float = 10) -> None:
        _not_translated("SinkClustering::normalizePoints")

    def computeAllThetas(self) -> None:
        _not_translated("SinkClustering::computeAllThetas")

    def sortPoints(self) -> None:
        self.theta_index_vector.sort()

    def writePlotFile(self, group_size: Optional[int] = None) -> None:
        _not_translated("SinkClustering::writePlotFile")

    def findBestMatching(self, group_size: int) -> bool:
        _not_translated("SinkClustering::findBestMatching")

    def computeTheta(self, x: float, y: float) -> float:
        _not_translated("SinkClustering::computeTheta")

    def numVertex(self, x: int, y: int) -> int:
        _not_translated("SinkClustering::numVertex")

    def isLimitExceeded(
        self, size: int, cost: float, cap_cost: float, size_limit: int
    ) -> bool:
        if self.use_max_size and size > size_limit:
            return True
        if self.use_max_diameter and cost > self.max_diameter:
            return True
        if self.use_max_cap_limit and cap_cost > self.max_internal_diameter:
            return True
        return False


@dataclass
class GraphNode:
    """对应 latency balancer graph node。"""

    name: str
    id: int = 0
    delay: float = 0.0
    arrival: float = 0.0
    n_buff_insert: int = -1
    input_term: Any = None
    children: List["GraphNode"] = field(default_factory=list)
    children_ids: List[int] = field(default_factory=list)

    def addChild(self, child: "GraphNode") -> None:
        self.children.append(child)
        self.children_ids.append(child.id)


@dataclass
class LatencyBalancer:
    """对应 `LatencyBalancer`。"""

    options: Optional[CtsOptions] = None
    db: Any = None
    network: Any = None
    open_sta: Any = None
    timing_graph: Any = None
    wire_segment_unit: float = 0.0
    buffer_delay: float = 0.0
    cap_per_dbu: float = 0.0
    worse_delay: float = 0.0
    delay_buf_index: int = 0
    root: Optional[GraphNode] = None
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    graph: List[GraphNode] = field(default_factory=list)
    inst2builder: Dict[str, TreeBuilder] = field(default_factory=dict)

    def makeNode(self, name: str, delay: float = 0.0) -> GraphNode:
        node = GraphNode(name=name, id=len(self.graph), delay=delay)
        self.nodes[name] = node
        self.graph.append(node)
        if self.root is None:
            self.root = node
        return node

    def run(self) -> int:
        _not_translated("LatencyBalancer::run")

    def initSta(self) -> None:
        _not_translated("LatencyBalancer::initSta")

    def findLeafBuilders(self, builder: TreeBuilder) -> None:
        _not_translated("LatencyBalancer::findLeafBuilders")

    def buildGraph(self, clk_input_net: Any) -> None:
        _not_translated("LatencyBalancer::buildGraph")

    def getFirstInput(self, inst: Any) -> Any:
        _not_translated("LatencyBalancer::getFirstInput")

    def getVertexClkArrival(self, sink_vertex: Any, top_net: Any, iterm: Any) -> float:
        _not_translated("LatencyBalancer::getVertexClkArrival")

    def computeBufferDelay(self, extra_out_cap: float) -> float:
        _not_translated("LatencyBalancer::computeBufferDelay")

    def computeAveSinkArrivals(self, builder: TreeBuilder) -> float:
        _not_translated("LatencyBalancer::computeAveSinkArrivals")

    def computeSinkArrivalRecur(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("LatencyBalancer::computeSinkArrivalRecur")

    def computeNumberOfDelayBuffers(self, node_id: int, src_x: int, src_y: int) -> None:
        _not_translated("LatencyBalancer::computeNumberOfDelayBuffers")

    def balanceLatencies(self, node_id: int) -> None:
        _not_translated("LatencyBalancer::balanceLatencies")

    def insertDelayBuffers(
        self, num_buffers: int, src_x: int, src_y: int, sinks_input: List[Any]
    ) -> Any:
        _not_translated("LatencyBalancer::insertDelayBuffers")

    def propagateClock(self, input: Any) -> bool:
        _not_translated("LatencyBalancer::propagateClock")

    def isSink(self, iterm: Any) -> bool:
        _not_translated("LatencyBalancer::isSink")

    def showGraph(self) -> None:
        _not_translated("LatencyBalancer::showGraph")


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

    def getBufferFanoutLimit(self, buffer_name: str) -> int:
        _not_translated("TritonCTS::getBufferFanoutLimit")

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

    def getBlock(self) -> Any:
        if self.block is not None:
            return self.block
        chip = getattr(self.db, "getChip", lambda: None)()
        return getattr(chip, "getBlock", lambda: None)()

    def setClockNets(self, names: str) -> int:
        self.options.setClockNets(names)
        return len([name for name in names.split() if name])

    def setBufferList(self, buffers: str) -> None:
        self.options.setBufferList(buffers.split())

    def setRootBuffer(self, buffers: str) -> None:
        self.root_buffers = [buf for buf in buffers.split() if buf]
        self.options.setRootBuffer(self.root_buffers[0] if self.root_buffers else "")

    def setSinkBuffer(self, buffers: str) -> None:
        self.sink_buffers = [buf for buf in buffers.split() if buf]
        self.options.setSinkBuffer(self.sink_buffers[0] if self.sink_buffers else "")

    def getRootBufferToString(self) -> str:
        return " ".join(self.root_buffers)

    def resetRootBuffer(self) -> None:
        self.root_buffers.clear()
        self.options.setRootBuffer("")

    def selectRootBuffer(self, buffers: List[str]) -> str:
        if not buffers:
            return ""
        selected = buffers[self.reg_tree_root_buf_index % len(buffers)]
        self.reg_tree_root_buf_index += 1
        return selected

    def selectSinkBuffer(self, buffers: List[str]) -> str:
        if not buffers:
            return ""
        selected = buffers[0]
        return selected

    def selectBestMaxCapBuffer(self, buffers: List[str], total_cap: float) -> str:
        _not_translated("TritonCTS::selectBestMaxCapBuffer")

    def addBuilder(
        self,
        builder_or_options: Any,
        net: Optional[Clock] = None,
        top_input_net: Any = None,
        parent: Optional[TreeBuilder] = None,
        logger: Any = None,
        db: Any = None,
    ) -> TreeBuilder:
        if isinstance(builder_or_options, TreeBuilder):
            builder = builder_or_options
        else:
            if net is None:
                raise ValueError("addBuilder 需要 Clock net")
            builder = HTreeBuilder(
                options=builder_or_options,
                clock=net,
                parent=parent,
                logger=logger,
                db=db,
            )
            builder.setTopInputNet(top_input_net)
        self.builders.append(builder)
        return builder

    def forEachBuilder(self, func: Callable[[TreeBuilder], None]) -> None:
        for builder in self.builders:
            func(builder)

    def setupCharacterization(self) -> None:
        _not_translated("TritonCTS::setupCharacterization")

    def checkCharacterization(self) -> None:
        _not_translated("TritonCTS::checkCharacterization")

    def findClockRoots(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::findClockRoots")

    def buildClockTrees(self) -> None:
        _not_translated("TritonCTS::buildClockTrees")

    def writeDataToDb(self) -> None:
        _not_translated("TritonCTS::writeDataToDb")

    def getAllClockTreeLevels(self, clock_net: Clock) -> List[int]:
        _not_translated("TritonCTS::getAllClockTreeLevels")

    def applyNDRToClockLevels(
        self, clock_net: Clock, clock_ndr: Any, target_levels: List[int]
    ) -> int:
        _not_translated("TritonCTS::applyNDRToClockLevels")

    def applyNDRToClockLevelRange(
        self, clock_net: Clock, clock_ndr: Any, min_level: int, max_level: int
    ) -> int:
        _not_translated("TritonCTS::applyNDRToClockLevelRange")

    def applyNDRToFirstHalfLevels(self, clock_net: Clock, clock_ndr: Any) -> int:
        _not_translated("TritonCTS::applyNDRToFirstHalfLevels")

    def masterExists(self, master: str) -> bool:
        finder = getattr(self.db, "findMaster", None)
        return bool(finder(master)) if finder else False

    def populateTritonCTS(self) -> None:
        _not_translated("TritonCTS::populateTritonCTS")

    def destroyClockModNet(self, pin_driver: Any) -> None:
        _not_translated("TritonCTS::destroyClockModNet")

    def writeClockNetsToDb(self, builder: TreeBuilder, clk_leaf_nets: Set[Any]) -> None:
        _not_translated("TritonCTS::writeClockNetsToDb")

    def writeClockNDRsToDb(self, builder: TreeBuilder) -> None:
        _not_translated("TritonCTS::writeClockNDRsToDb")

    def getNetSpacing(self, layer: Any, width1: int, width2: int) -> int:
        _not_translated("TritonCTS::getNetSpacing")

    def incrementNumClocks(self) -> None:
        self.number_of_clocks += 1

    def clearNumClocks(self) -> None:
        self.number_of_clocks = 0

    def getNumClocks(self) -> int:
        return self.number_of_clocks

    def cloneClockGaters(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::cloneClockGaters")

    def findLongEdges(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::findLongEdges")

    def resolveLocationCollision(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::resolveLocationCollision")

    def initOneClockTree(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::initOneClockTree")

    def initClock(self, *args: Any, **kwargs: Any) -> TreeBuilder:
        _not_translated("TritonCTS::initClock")

    def disconnectAllSinksFromNet(self, net: Any) -> None:
        _not_translated("TritonCTS::disconnectAllSinksFromNet")

    def disconnectAllPinsFromNet(self, net: Any) -> None:
        _not_translated("TritonCTS::disconnectAllPinsFromNet")

    def checkUpstreamConnections(self, net: Any) -> None:
        _not_translated("TritonCTS::checkUpstreamConnections")

    def createClockBuffers(self, clock_net: Clock, parent: Any = None) -> None:
        _not_translated("TritonCTS::createClockBuffers")

    def initClockTreeForMacrosAndRegs(self, *args: Any, **kwargs: Any) -> TreeBuilder:
        _not_translated("TritonCTS::initClockTreeForMacrosAndRegs")

    def separateMacroRegSinks(self, *args: Any, **kwargs: Any) -> bool:
        _not_translated("TritonCTS::separateMacroRegSinks")

    def addClockSinks(self, *args: Any, **kwargs: Any) -> TreeBuilder:
        _not_translated("TritonCTS::addClockSinks")

    def forkRegisterClockNetwork(self, *args: Any, **kwargs: Any) -> Clock:
        _not_translated("TritonCTS::forkRegisterClockNetwork")

    def computeITermPosition(self, term: Any) -> Tuple[int, int]:
        _not_translated("TritonCTS::computeITermPosition")

    def countSinksPostDbWrite(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::countSinksPostDbWrite")

    def branchBufferCount(self, inst: ClockInst, buf_counter: int, clock_net: Clock) -> Tuple[int, int]:
        _not_translated("TritonCTS::branchBufferCount")

    def getFirstInput(self, inst: Any) -> Any:
        _not_translated("TritonCTS::getFirstInput")

    def getSingleOutput(self, inst: Any, input: Any = None) -> Any:
        _not_translated("TritonCTS::getSingleOutput")

    def getClockFromInst(self, inst: Any) -> Optional[ClockInst]:
        return self.inst2clkbuf.get(inst)

    def getInputPinCap(self, iterm: Any) -> float:
        _not_translated("TritonCTS::getInputPinCap")

    def isSink(self, iterm: Any) -> bool:
        _not_translated("TritonCTS::isSink")

    def hasInsertionDelay(self, inst: Any, mterm: Any) -> bool:
        _not_translated("TritonCTS::hasInsertionDelay")

    def computeInsertionDelay(self, name: str, inst: Any, mterm: Any) -> float:
        _not_translated("TritonCTS::computeInsertionDelay")

    def writeDummyLoadsToDb(self, clock_net: Clock, dummies: Set[Any]) -> int:
        _not_translated("TritonCTS::writeDummyLoadsToDb")

    def computeIdealOutputCaps(self, clock_net: Clock) -> bool:
        _not_translated("TritonCTS::computeIdealOutputCaps")

    def findCandidateDummyCells(self, dummy_candidates: List[Any]) -> None:
        _not_translated("TritonCTS::findCandidateDummyCells")

    def insertDummyCell(
        self, clock_net: Clock, inst: ClockInst, dummy_candidates: List[Any]
    ) -> Any:
        _not_translated("TritonCTS::insertDummyCell")

    def placeDummyCell(
        self, clock_net: Clock, inst: ClockInst, dummy_cell: Any, dummy_inst: Any = None
    ) -> ClockInst:
        _not_translated("TritonCTS::placeDummyCell")

    def connectDummyCell(
        self, inst: ClockInst, dummy_inst: Any, subnet: ClockSubNet, dummy_clock: ClockInst
    ) -> None:
        _not_translated("TritonCTS::connectDummyCell")

    def printClockNetwork(self, clock_net: Clock) -> None:
        _not_translated("TritonCTS::printClockNetwork")

    def setAllClocksPropagated(self) -> None:
        _not_translated("TritonCTS::setAllClocksPropagated")

    def repairClockNets(self) -> None:
        _not_translated("TritonCTS::repairClockNets")

    def balanceMacroRegisterLatencies(self) -> None:
        _not_translated("TritonCTS::balanceMacroRegisterLatencies")


def initTritonCts() -> TritonCTS:
    """对应 `initTritonCts`，返回 CTS 顶层对象。"""

    return TritonCTS()
