"""Latency balancing boundaries for CTS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .options import CtsOptions
from .tree_builder import TreeBuilder
from .types import _not_translated


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
