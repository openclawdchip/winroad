"""Detailed routing maze grid graph boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

from .fr import frTechObject
from .types import (
    Point,
    Rect,
    RouterConfiguration,
    dbTechLayerDir,
    frCoord,
    frDirEnum,
    frLayerNum,
    frMIdx,
    _unsupported,
)

@dataclass(frozen=True, order=True)
class FlexMazeIdx:
    """对应 ``FlexMazeTypes.h`` 的 maze 三维索引。"""

    x_: frMIdx = 0
    y_: frMIdx = 0
    z_: frMIdx = 0

    def x(self) -> frMIdx:
        return self.x_

    def y(self) -> frMIdx:
        return self.y_

    def z(self) -> frMIdx:
        return self.z_


@dataclass
class FlexGridGraphNode:
    """FlexGridGraph 内部节点的轻量状态位。"""

    has_east_edge: bool = False
    has_north_edge: bool = False
    has_up_edge: bool = False
    is_blocked_east: bool = False
    is_blocked_north: bool = False
    is_blocked_up: bool = False
    has_grid_cost_east: bool = False
    has_grid_cost_north: bool = False
    has_grid_cost_up: bool = False
    has_special_via: bool = False


class FlexGridGraph:
    """对应 ``dr/FlexGridGraph.h`` 的 detailed routing maze graph。

    本轮实现坐标/维度/边状态这类纯数据访问；A* wavefront、cost 更新、
    DRC blockage 初始化和路径回溯属于核心 maze 算法，保留入口抛错。
    """

    def __init__(
        self,
        tech: Optional[frTechObject] = None,
        logger: Any = None,
        worker: Any = None,
        router_cfg: Optional[RouterConfiguration] = None,
    ):
        self.tech_ = tech or frTechObject()
        self.logger_ = logger
        self.drWorker_ = worker
        self.router_cfg_ = router_cfg or RouterConfiguration()
        self.xCoords_: List[frCoord] = []
        self.yCoords_: List[frCoord] = []
        self.zCoords_: List[frLayerNum] = []
        self.zHeights_: List[frCoord] = []
        self.layerRouteDirections_: List[dbTechLayerDir] = []
        self.nodes_: List[FlexGridGraphNode] = []

    def getTech(self) -> frTechObject:
        return self.tech_

    def getDRWorker(self) -> Any:
        return self.drWorker_

    def setCoords(self, x_coords: Sequence[frCoord], y_coords: Sequence[frCoord], z_coords: Sequence[frLayerNum]) -> None:
        self.xCoords_ = sorted(x_coords)
        self.yCoords_ = sorted(y_coords)
        self.zCoords_ = sorted(z_coords)
        self.nodes_ = [FlexGridGraphNode() for _ in range(len(self.xCoords_) * len(self.yCoords_) * len(self.zCoords_))]

    def getDim(self) -> Tuple[frMIdx, frMIdx, frMIdx]:
        return (len(self.xCoords_), len(self.yCoords_), len(self.zCoords_))

    def getBBox(self) -> Rect:
        if not self.xCoords_ or not self.yCoords_:
            return (0, 0, 0, 0)
        return (self.xCoords_[0], self.yCoords_[0], self.xCoords_[-1], self.yCoords_[-1])

    def getPoint(self, x: frMIdx, y: frMIdx) -> Point:
        return (self.xCoords_[x], self.yCoords_[y])

    def getLayerNum(self, z: frMIdx) -> frLayerNum:
        return self.zCoords_[z]

    def getMinLayerNum(self) -> frLayerNum:
        return self.zCoords_[0]

    def getMaxLayerNum(self) -> frLayerNum:
        return self.zCoords_[-1]

    def hasMazeXIdx(self, coord: frCoord) -> bool:
        return coord in self.xCoords_

    def hasMazeYIdx(self, coord: frCoord) -> bool:
        return coord in self.yCoords_

    def hasMazeZIdx(self, layer_num: frLayerNum) -> bool:
        return layer_num in self.zCoords_

    def hasIdx(self, point: Point, layer_num: frLayerNum) -> bool:
        return self.hasMazeXIdx(point[0]) and self.hasMazeYIdx(point[1]) and self.hasMazeZIdx(layer_num)

    def getMazeXIdx(self, coord: frCoord) -> frMIdx:
        return self.xCoords_.index(coord)

    def getMazeYIdx(self, coord: frCoord) -> frMIdx:
        return self.yCoords_.index(coord)

    def getMazeZIdx(self, layer_num: frLayerNum) -> frMIdx:
        return self.zCoords_.index(layer_num)

    def getMazeIdx(self, point: Point, layer_num: frLayerNum) -> FlexMazeIdx:
        return FlexMazeIdx(self.getMazeXIdx(point[0]), self.getMazeYIdx(point[1]), self.getMazeZIdx(layer_num))

    def getIdx(self, x: frMIdx, y: frMIdx, z: frMIdx) -> int:
        x_dim, y_dim, _ = self.getDim()
        return z * x_dim * y_dim + y * x_dim + x

    def hasEdge(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum) -> bool:
        node = self.nodes_[self.getIdx(x, y, z)]
        if direction == frDirEnum.E:
            return node.has_east_edge
        if direction == frDirEnum.N:
            return node.has_north_edge
        if direction == frDirEnum.U:
            return node.has_up_edge
        return False

    def isBlocked(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum) -> bool:
        node = self.nodes_[self.getIdx(x, y, z)]
        if direction == frDirEnum.E:
            return node.is_blocked_east
        if direction == frDirEnum.N:
            return node.is_blocked_north
        if direction == frDirEnum.U:
            return node.is_blocked_up
        return False

    def init(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGridGraph::init")

    def search(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGridGraph::search")

    def traceBackPath(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGridGraph::traceBackPath")

    def updatePrevNodeCost(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGridGraph::updatePrevNodeCost")

__all__ = ["FlexGridGraph", "FlexGridGraphNode", "FlexMazeIdx"]
