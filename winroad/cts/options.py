"""CTS option and statistics container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .types import MasterType, NdrStrategy


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

    def resetClockNets(self) -> None:
        self.clock_nets = ""

    def getClockNets(self) -> str:
        return self.clock_nets

    def setRootBuffer(self, buffer: str) -> None:
        self.root_buffer = buffer

    def resetRootBuffer(self) -> None:
        self.root_buffer = ""
        self.root_buffer_inferred = False

    def getRootBuffer(self) -> str:
        return self.root_buffer

    def setSinkBuffer(self, buffer: str) -> None:
        self.sink_buffer = buffer

    def resetSinkBuffer(self) -> None:
        self.sink_buffer = ""
        self.sink_buffer_inferred = False

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

    def setSinkClusteringUseMaxCap(self, enable: bool) -> None:
        self.sink_clustering_use_max_cap = enable

    def getSinkClusteringUseMaxCap(self) -> bool:
        return self.sink_clustering_use_max_cap

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

    def resetClockNetsObjs(self) -> None:
        self.clock_nets_objs.clear()

    def setSkipNets(self, net: Any) -> None:
        self.skip_nets.append(net)

    def addSkipNet(self, net: Any) -> None:
        self.setSkipNets(net)

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

    def setBalanceLevels(self, balance: bool) -> None:
        self.balance_levels = balance

    def getBalanceLevels(self) -> bool:
        return self.balance_levels

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

    def setDummyLoadPrefix(self, prefix: str) -> None:
        self.dummyload_prefix = prefix

    def resetDummyLoadPrefix(self) -> None:
        self.dummyload_prefix = "clkload"

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

    def resetCounts(self) -> None:
        self.clock_roots = 0
        self.clock_subnets = 0
        self.buffers_inserted = 0
        self.sinks = 0
        self.buffer_count.clear()
        self.dummy_count.clear()

    def getType(self, inst: Any) -> MasterType:
        master = getattr(inst, "master", None)
        if master in self.dummy_count:
            return MasterType.DUMMY
        return MasterType.TREE
