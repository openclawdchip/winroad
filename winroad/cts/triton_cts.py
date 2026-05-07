"""TritonCTS top-level entry point."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .clock import Clock, ClockInst, ClockSubNet
from .options import CtsOptions
from .tech_char import TechChar
from .tree_builder import HTreeBuilder, TreeBuilder
from .types import NdrStrategy, _not_translated


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
    net2builder: Dict[Any, TreeBuilder] = field(default_factory=dict)
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
    clock_roots: List[Any] = field(default_factory=list)
    db_written_builders: List[TreeBuilder] = field(default_factory=list)
    ndr_applied_builders: List[TreeBuilder] = field(default_factory=list)

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
        self.tech_char.db = db
        self.tech_char.db_network = network
        self.tech_char.open_sta = sta

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
            "num_clock_roots": len(self.clock_roots),
            "num_db_written_builders": len(self.db_written_builders),
            "num_ndr_applied_builders": len(self.ndr_applied_builders),
            "dummy_load_index": self.dummy_load_index,
            "num_sta_clock_nets": len(self.sta_clock_nets),
            "num_visited_clock_nets": len(self.visited_clock_nets),
            "num_inst_clock_buffers": len(self.inst2clkbuf),
            "num_driver_subnets": len(self.driver2subnet),
        }

    def report(self) -> Dict[str, Any]:
        return {
            "metrics": self.reportCtsMetrics(),
            "options": self.options.toProfile(),
            "clock_roots": [self._objectName(root) for root in self.clock_roots],
            "builders": [self.reportClockNetwork(builder.getClock()) for builder in self.builders],
        }

    def snapshotState(self, include_lut: bool = False) -> Dict[str, Any]:
        snapshot = {
            "metrics": self.reportCtsMetrics(),
            "options": self.options.toProfile(),
            "tech_char": self.tech_char.exportLut() if include_lut else self.tech_char.report(),
            "clock_roots": [self._objectName(root) for root in self.clock_roots],
            "root_buffers": list(self.root_buffers),
            "sink_buffers": list(self.sink_buffers),
            "ndr_strategy": self.ndr_strategy.value,
            "db_written_builders": [self._builderName(builder) for builder in self.db_written_builders],
            "ndr_applied_builders": [self._builderName(builder) for builder in self.ndr_applied_builders],
            "sta_clock_nets": [self._objectName(net) for net in self.sta_clock_nets],
            "visited_clock_nets": [self._objectName(net) for net in self.visited_clock_nets],
            "builders": [self._builderSnapshot(builder) for builder in self.builders],
        }
        return snapshot

    def dumpStateSnapshot(self, path: str, include_lut: bool = False) -> Dict[str, Any]:
        snapshot = self.snapshotState(include_lut=include_lut)
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(snapshot, stream, indent=2, sort_keys=True)
        return snapshot

    def reportStateSnapshot(self) -> Dict[str, Any]:
        return self.snapshotState(include_lut=False)

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

    def getSinkBufferToString(self) -> str:
        return " ".join(self.sink_buffers)

    def resetSinkBuffer(self) -> None:
        self.sink_buffers.clear()
        self.options.setSinkBuffer("")

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
        if top_input_net is not None:
            self.net2builder[top_input_net] = builder
        self.options.setNumClockSubnets(sum(len(b.getClock().sub_nets) for b in self.builders))
        return builder

    def forEachBuilder(self, func: Callable[[TreeBuilder], None]) -> None:
        for builder in self.builders:
            func(builder)

    def getBuilders(self) -> List[TreeBuilder]:
        return list(self.builders)

    def getBuilderForNet(self, net: Any) -> Optional[TreeBuilder]:
        return self.net2builder.get(net)

    def setupCharacterization(self) -> None:
        self.tech_char.options = self.options
        self.tech_char.db = self.db
        self.tech_char.db_network = self.network
        self.tech_char.open_sta = self.open_sta
        self.tech_char.initCharacterization()

    def checkCharacterization(self) -> None:
        _not_translated("TritonCTS::checkCharacterization")

    def findClockRoots(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::findClockRoots")

    def addClockRoot(self, root: Any) -> None:
        self.clock_roots.append(root)
        self.options.setNumClockRoots(len(self.clock_roots))

    def getClockRoots(self) -> List[Any]:
        return list(self.clock_roots)

    def clearClockRoots(self) -> None:
        self.clock_roots.clear()
        self.options.setNumClockRoots(0)

    def buildClockTrees(self) -> None:
        _not_translated("TritonCTS::buildClockTrees")

    def writeDataToDb(self) -> None:
        _not_translated("TritonCTS::writeDataToDb")

    def markBuilderWrittenToDb(self, builder: TreeBuilder) -> None:
        if builder not in self.db_written_builders:
            self.db_written_builders.append(builder)

    def getDbWrittenBuilders(self) -> List[TreeBuilder]:
        return list(self.db_written_builders)

    def getAllClockTreeLevels(self, clock_net: Clock) -> List[int]:
        levels: Set[int] = set()
        for builder in self.builders:
            if builder.getClock() is clock_net:
                levels.add(builder.getTreeBufLevels())
                for child in builder.getChildren():
                    levels.add(child.getTreeBufLevels())
        return sorted(levels)

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

    def setNdrStrategy(self, strategy: NdrStrategy) -> None:
        self.ndr_strategy = strategy
        self.options.setApplyNDR(strategy)

    def getNdrStrategy(self) -> NdrStrategy:
        return self.ndr_strategy

    def markBuilderNdrApplied(self, builder: TreeBuilder) -> None:
        if builder not in self.ndr_applied_builders:
            self.ndr_applied_builders.append(builder)

    def masterExists(self, master: str) -> bool:
        finder = getattr(self.db, "findMaster", None)
        return bool(finder(master)) if finder else False

    def populateTritonCTS(self) -> None:
        _not_translated("TritonCTS::populateTritonCTS")

    def addClockNet(self, net: Any, sta_clock: bool = False) -> None:
        self.visited_clock_nets.add(net)
        if sta_clock:
            self.sta_clock_nets.add(net)
        self.num_clk_nets = len(self.visited_clock_nets)

    def addFixedNet(self, net: Any) -> None:
        self.num_fixed_nets += 1
        self.visited_clock_nets.add(net)

    def registerClockInst(self, inst: Any, clock_inst: ClockInst) -> None:
        self.inst2clkbuf[inst] = clock_inst

    def registerDriverSubNet(self, driver: ClockInst, subnet: ClockSubNet) -> None:
        self.driver2subnet[driver] = subnet
        self.options.setNumClockSubnets(len(self.driver2subnet))

    def getSubNetForDriver(self, driver: ClockInst) -> Optional[ClockSubNet]:
        return self.driver2subnet.get(driver)

    def destroyClockModNet(self, pin_driver: Any) -> None:
        _not_translated("TritonCTS::destroyClockModNet")

    def writeClockNetsToDb(self, builder: TreeBuilder, clk_leaf_nets: Set[Any]) -> None:
        _not_translated("TritonCTS::writeClockNetsToDb")

    def writeClockNDRsToDb(self, builder: TreeBuilder) -> None:
        _not_translated("TritonCTS::writeClockNDRsToDb")

    def getClockLeafNets(self, builder: TreeBuilder) -> Set[Any]:
        _not_translated("TritonCTS::getClockLeafNets")

    def getNetSpacing(self, layer: Any, width1: int, width2: int) -> int:
        _not_translated("TritonCTS::getNetSpacing")

    def incrementNumClocks(self) -> None:
        self.number_of_clocks += 1

    def setNumClocks(self, num_clocks: int) -> None:
        self.number_of_clocks = num_clocks

    def clearNumClocks(self) -> None:
        self.number_of_clocks = 0

    def getNumClocks(self) -> int:
        return self.number_of_clocks

    def getNumClockNets(self) -> int:
        return self.num_clk_nets

    def getNumFixedNets(self) -> int:
        return self.num_fixed_nets

    def clearClockBookkeeping(self) -> None:
        self.sta_clock_nets.clear()
        self.visited_clock_nets.clear()
        self.inst2clkbuf.clear()
        self.driver2subnet.clear()
        self.net2builder.clear()
        self.number_of_clocks = 0
        self.num_clk_nets = 0
        self.num_fixed_nets = 0
        self.options.setNumClockSubnets(0)

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

    def initClockRoot(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::initClockRoot")

    def initClockTree(self, *args: Any, **kwargs: Any) -> TreeBuilder:
        _not_translated("TritonCTS::initClockTree")

    def disconnectAllSinksFromNet(self, net: Any) -> None:
        _not_translated("TritonCTS::disconnectAllSinksFromNet")

    def disconnectAllPinsFromNet(self, net: Any) -> None:
        _not_translated("TritonCTS::disconnectAllPinsFromNet")

    def checkUpstreamConnections(self, net: Any) -> None:
        _not_translated("TritonCTS::checkUpstreamConnections")

    def createClockBuffers(self, clock_net: Clock, parent: Any = None) -> None:
        _not_translated("TritonCTS::createClockBuffers")

    def createRootBuffer(self, *args: Any, **kwargs: Any) -> Any:
        _not_translated("TritonCTS::createRootBuffer")

    def createTreeBuffer(self, *args: Any, **kwargs: Any) -> Any:
        _not_translated("TritonCTS::createTreeBuffer")

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

    def nextDummyLoadName(self) -> str:
        name = f"{self.options.getDummyLoadPrefix()}_{self.dummy_load_index}"
        self.dummy_load_index += 1
        return name

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

    def reportClockNetwork(self, clock_net: Clock) -> Dict[str, Any]:
        return clock_net.report()

    def setAllClocksPropagated(self) -> None:
        _not_translated("TritonCTS::setAllClocksPropagated")

    def repairClockNets(self) -> None:
        _not_translated("TritonCTS::repairClockNets")

    def repairClockNet(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::repairClockNet")

    def balanceMacroRegisterLatencies(self) -> None:
        _not_translated("TritonCTS::balanceMacroRegisterLatencies")

    def balanceLatency(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TritonCTS::balanceLatency")

    def clear(self) -> None:
        self.builders.clear()
        self.sta_clock_nets.clear()
        self.visited_clock_nets.clear()
        self.inst2clkbuf.clear()
        self.driver2subnet.clear()
        self.net2builder.clear()
        self.clock_roots.clear()
        self.db_written_builders.clear()
        self.ndr_applied_builders.clear()
        self.root_buffers.clear()
        self.sink_buffers.clear()
        self.number_of_clocks = 0
        self.num_clk_nets = 0
        self.num_fixed_nets = 0
        self.dummy_load_index = 0

    def _builderSnapshot(self, builder: TreeBuilder) -> Dict[str, Any]:
        return {
            "name": self._builderName(builder),
            "tree_type": builder.getTreeTypeAsString(),
            "tree_buf_levels": builder.getTreeBufLevels(),
            "parent": self._builderName(builder.getParent()) if builder.getParent() else None,
            "num_children": len(builder.getChildren()),
            "top_buffer_name": builder.getTopBufferName(),
            "top_input_net": self._objectName(builder.getTopInputNet()),
            "driving_net": self._objectName(builder.getDrivingNet()),
            "ave_sink_arrival": builder.getAveSinkArrival(),
            "n_dummies": builder.getNDummies(),
            "clock": builder.getClock().toDict(),
            "legalization": builder.reportLegalizationState(),
        }

    def _builderName(self, builder: TreeBuilder) -> str:
        return builder.getClock().getName()

    def _objectName(self, obj: Any) -> Any:
        if obj is None:
            return None
        for attr in ("name", "getName"):
            value = getattr(obj, attr, None)
            if callable(value):
                return value()
            if value is not None:
                return value
        return str(obj)


def initTritonCts() -> TritonCTS:
    """对应 `initTritonCts`，返回 CTS 顶层对象。"""

    return TritonCTS()
