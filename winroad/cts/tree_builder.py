"""CTS tree builder boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .clock import Clock, ClockInst, ClockSubNet
from .options import CtsOptions
from .tech_char import TechChar
from .types import (
    Box,
    Point,
    TreeType,
    _not_translated,
    fuzzyEqual,
    fuzzyEqualOrGreater,
    fuzzyEqualOrSmaller,
)


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
        merged: List[Box] = []
        for blockage in sorted(self.blockages, key=lambda box: (box.x_min, box.y_min, box.x_max, box.y_max)):
            for idx, existing in enumerate(merged):
                if self._boxesOverlapOrTouch(existing, blockage):
                    merged[idx] = Box(
                        min(existing.x_min, blockage.x_min),
                        min(existing.y_min, blockage.y_min),
                        max(existing.x_max, blockage.x_max),
                        max(existing.y_max, blockage.y_max),
                    )
                    break
            else:
                merged.append(blockage)
        self.blockages = merged

    def initBlockages(self) -> None:
        _not_translated("TreeBuilder::initBlockages")

    def setTechChar(self, tech_char: TechChar) -> None:
        self.tech_char = tech_char

    def getTechChar(self) -> Optional[TechChar]:
        return self.tech_char

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

    def getLogger(self) -> Any:
        return self.logger

    def addBlockage(self, blockage: Box) -> None:
        self.blockages.append(blockage)

    def getBlockages(self) -> List[Box]:
        return list(self.blockages)

    def clearBlockages(self) -> None:
        self.blockages.clear()

    def setBufferSize(self, width: float, height: float) -> None:
        self.buffer_width = width
        self.buffer_height = height

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
        buffer_box = self._bufferBox(buffer_loc, scaling_unit)
        for blockage in self.blockages:
            if self._boxesOverlap(buffer_box, blockage):
                return (blockage.x_min, blockage.y_min, blockage.x_max, blockage.y_max)
        return None

    def legalizeOneBuffer(self, buffer_loc: Point, buffer_name: str) -> Point:
        scaling_factor = max(1, int(round(max(self.buffer_width, self.buffer_height, 1.0))))
        for candidate in self.getLegalizationCandidates(buffer_loc, scaling_factor):
            if self.checkLegalityLoc(candidate, scaling_factor):
                self.commitLoc(candidate)
                return candidate
        raise ValueError(f"无法为 {buffer_name} 找到合法位置")

    def getLegalizationCandidates(
        self, buffer_loc: Point, scaling_factor: int
    ) -> List[Point]:
        candidates: List[Point] = []
        scaling = float(scaling_factor)
        self.addCandidatePoint(buffer_loc.x, buffer_loc.y, buffer_loc, candidates)
        self.addCandidatePoint(buffer_loc.x + scaling, buffer_loc.y, buffer_loc, candidates)
        self.addCandidatePoint(buffer_loc.x - scaling, buffer_loc.y, buffer_loc, candidates)
        self.addCandidatePoint(buffer_loc.x, buffer_loc.y + scaling, buffer_loc, candidates)
        self.addCandidatePoint(buffer_loc.x, buffer_loc.y - scaling, buffer_loc, candidates)
        return candidates

    def reportLegalizationCandidates(
        self, buffer_loc: Point, scaling_factor: int, buffer_name: str = ""
    ) -> Dict[str, Any]:
        candidates = self.getLegalizationCandidates(buffer_loc, scaling_factor)
        return {
            "buffer_name": buffer_name,
            "requested_location": self._pointReport(buffer_loc),
            "scaling_factor": scaling_factor,
            "candidates": [
                self._candidateReport(candidate, scaling_factor) for candidate in candidates
            ],
        }

    def reportCandidateLegalization(
        self, buffer_loc: Point, buffer_name: str = ""
    ) -> Dict[str, Any]:
        scaling_factor = max(1, int(round(max(self.buffer_width, self.buffer_height, 1.0))))
        report = self.reportLegalizationCandidates(buffer_loc, scaling_factor, buffer_name)
        report["selected"] = None
        for candidate in self.getLegalizationCandidates(buffer_loc, scaling_factor):
            if self.checkLegalityLoc(candidate, scaling_factor):
                report["selected"] = self._pointReport(candidate)
                break
        return report

    def addCandidatePoint(
        self, x: float, y: float, point: Point, candidates: List[Point]
    ) -> None:
        candidate = Point(x, y)
        if candidate not in candidates:
            candidates.append(candidate)

    def getBufferWidth(self) -> float:
        return self.buffer_width

    def getBufferHeight(self) -> float:
        return self.buffer_height

    def checkLegalityLoc(self, buffer_loc: Point, scaling_factor: int) -> bool:
        if self.isOccupiedLoc(buffer_loc):
            return False
        return self.findBlockage(buffer_loc, float(scaling_factor)) is None

    def isOccupiedLoc(self, buffer_loc: Point) -> bool:
        return buffer_loc in self.occupied_locations

    def getOccupiedLocs(self) -> Set[Point]:
        return set(self.occupied_locations)

    def clearOccupiedLocs(self) -> None:
        self.occupied_locations.clear()

    def commitLoc(self, buffer_loc: Point) -> None:
        self.occupied_locations.add(buffer_loc)

    def uncommitLoc(self, buffer_loc: Point) -> None:
        self.occupied_locations.discard(buffer_loc)

    def commitMoveLoc(self, old_loc: Point, new_loc: Point) -> None:
        self.uncommitLoc(old_loc)
        self.commitLoc(new_loc)

    def resetLegalizationState(self) -> None:
        self.clearOccupiedLocs()
        self.sink_insertion_delays.clear()

    def reportLegalizationState(self) -> Dict[str, Any]:
        return {
            "num_blockages": len(self.blockages),
            "num_occupied_locations": len(self.occupied_locations),
            "buffer_width": self.buffer_width,
            "buffer_height": self.buffer_height,
            "num_sink_insertion_delays": len(self.sink_insertion_delays),
            "blockages": [self._boxReport(blockage) for blockage in self.blockages],
            "occupied_locations": [self._pointReport(point) for point in sorted(
                self.occupied_locations, key=lambda loc: (loc.x, loc.y)
            )],
            "sink_insertion_delays": [
                {"point": self._pointReport(point), "delay": delay}
                for point, delay in sorted(
                    self.sink_insertion_delays.items(), key=lambda item: (item[0].x, item[0].y)
                )
            ],
        }

    def sinkHasInsertionDelay(self, sink: Point) -> bool:
        return sink in self.sink_insertion_delays

    def setSinkInsertionDelay(self, sink: Point, ins_delay: float) -> None:
        self.sink_insertion_delays[sink] = ins_delay

    def getSinkInsertionDelay(self, sink: Point) -> float:
        return self.sink_insertion_delays[sink]

    def computeDist(self, x: Point, y: Point) -> float:
        return x.computeDist(y)

    def _bufferBox(self, loc: Point, scaling_unit: float) -> Box:
        half_width = (self.buffer_width or scaling_unit) / 2.0
        half_height = (self.buffer_height or scaling_unit) / 2.0
        return Box(loc.x - half_width, loc.y - half_height, loc.x + half_width, loc.y + half_height)

    def _boxesOverlap(self, lhs: Box, rhs: Box) -> bool:
        return not (
            fuzzyEqualOrSmaller(lhs.x_max, rhs.x_min)
            or fuzzyEqualOrGreater(lhs.x_min, rhs.x_max)
            or fuzzyEqualOrSmaller(lhs.y_max, rhs.y_min)
            or fuzzyEqualOrGreater(lhs.y_min, rhs.y_max)
        )

    def _boxesOverlapOrTouch(self, lhs: Box, rhs: Box) -> bool:
        return not (
            lhs.x_max < rhs.x_min
            or lhs.x_min > rhs.x_max
            or lhs.y_max < rhs.y_min
            or lhs.y_min > rhs.y_max
        )

    def _candidateReport(self, candidate: Point, scaling_factor: int) -> Dict[str, Any]:
        blockage = self.findBlockage(candidate, float(scaling_factor))
        return {
            "location": self._pointReport(candidate),
            "legal": self.checkLegalityLoc(candidate, scaling_factor),
            "occupied": self.isOccupiedLoc(candidate),
            "blockage": blockage,
        }

    def _pointReport(self, point: Point) -> Dict[str, float]:
        return {"x": point.x, "y": point.y}

    def _boxReport(self, box: Box) -> Dict[str, float]:
        return {
            "x_min": box.x_min,
            "y_min": box.y_min,
            "x_max": box.x_max,
            "y_max": box.y_max,
        }

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
