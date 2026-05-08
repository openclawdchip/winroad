"""Detailed routing maze grid graph boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence, Tuple

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

    def to_dict(self) -> dict[str, bool]:
        """返回节点三方向状态；W/S/D 由相邻节点映射得到。"""

        return {
            "has_east_edge": self.has_east_edge,
            "has_north_edge": self.has_north_edge,
            "has_up_edge": self.has_up_edge,
            "is_blocked_east": self.is_blocked_east,
            "is_blocked_north": self.is_blocked_north,
            "is_blocked_up": self.is_blocked_up,
            "has_grid_cost_east": self.has_grid_cost_east,
            "has_grid_cost_north": self.has_grid_cost_north,
            "has_grid_cost_up": self.has_grid_cost_up,
            "has_special_via": self.has_special_via,
        }

    def has_edge(self, direction: frDirEnum) -> bool:
        if direction == frDirEnum.E:
            return self.has_east_edge
        if direction == frDirEnum.N:
            return self.has_north_edge
        if direction == frDirEnum.U:
            return self.has_up_edge
        return False

    def set_edge(self, direction: frDirEnum, value: bool) -> None:
        if direction == frDirEnum.E:
            self.has_east_edge = value
        elif direction == frDirEnum.N:
            self.has_north_edge = value
        elif direction == frDirEnum.U:
            self.has_up_edge = value

    def is_blocked(self, direction: frDirEnum) -> bool:
        if direction == frDirEnum.E:
            return self.is_blocked_east
        if direction == frDirEnum.N:
            return self.is_blocked_north
        if direction == frDirEnum.U:
            return self.is_blocked_up
        return False

    def set_blocked(self, direction: frDirEnum, value: bool) -> None:
        if direction == frDirEnum.E:
            self.is_blocked_east = value
        elif direction == frDirEnum.N:
            self.is_blocked_north = value
        elif direction == frDirEnum.U:
            self.is_blocked_up = value

    def has_grid_cost(self, direction: frDirEnum) -> bool:
        if direction == frDirEnum.E:
            return self.has_grid_cost_east
        if direction == frDirEnum.N:
            return self.has_grid_cost_north
        if direction == frDirEnum.U:
            return self.has_grid_cost_up
        return False

    def set_grid_cost(self, direction: frDirEnum, value: bool) -> None:
        if direction == frDirEnum.E:
            self.has_grid_cost_east = value
        elif direction == frDirEnum.N:
            self.has_grid_cost_north = value
        elif direction == frDirEnum.U:
            self.has_grid_cost_up = value


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
        self.xCoords_ = sorted(dict.fromkeys(x_coords))
        self.yCoords_ = sorted(dict.fromkeys(y_coords))
        self.zCoords_ = sorted(dict.fromkeys(z_coords))
        self.nodes_ = [FlexGridGraphNode() for _ in range(len(self.xCoords_) * len(self.yCoords_) * len(self.zCoords_))]
        self.zHeights_ = [0 for _ in self.zCoords_]
        self.layerRouteDirections_ = [
            (self.tech_.getLayer(layer_num).getDir() if self.tech_.getLayer(layer_num) is not None else dbTechLayerDir.NONE)
            for layer_num in self.zCoords_
        ]

    def setLayerRouteDirections(self, directions: Iterable[dbTechLayerDir]) -> None:
        self.layerRouteDirections_ = list(directions)

    def getLayerRouteDirection(self, z: frMIdx) -> dbTechLayerDir:
        return self.layerRouteDirections_[z]

    def setZHeights(self, heights: Iterable[frCoord]) -> None:
        self.zHeights_ = list(heights)

    def getZHeight(self, z: frMIdx) -> frCoord:
        return self.zHeights_[z]

    def getXCoords(self) -> List[frCoord]:
        return self.xCoords_

    def getYCoords(self) -> List[frCoord]:
        return self.yCoords_

    def getZCoords(self) -> List[frLayerNum]:
        return self.zCoords_

    def getNodes(self) -> List[FlexGridGraphNode]:
        return self.nodes_

    def getNode(self, x: frMIdx, y: frMIdx, z: frMIdx) -> FlexGridGraphNode:
        return self.nodes_[self.getIdx(x, y, z)]

    def getXCoord(self, x: frMIdx) -> frCoord:
        return self.xCoords_[x]

    def getYCoord(self, y: frMIdx) -> frCoord:
        return self.yCoords_[y]

    def getZCoord(self, z: frMIdx) -> frLayerNum:
        return self.zCoords_[z]

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
        if not self.zCoords_:
            return 0
        return self.zCoords_[0]

    def getMaxLayerNum(self) -> frLayerNum:
        if not self.zCoords_:
            return 0
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
        self._check_idx(x, y, z)
        return z * x_dim * y_dim + y * x_dim + x

    def hasEdge(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum) -> bool:
        mapped = self._map_direction(x, y, z, direction)
        if mapped is None:
            return False
        mx, my, mz, mdir = mapped
        return self.getNode(mx, my, mz).has_edge(mdir)

    def setEdge(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum, value: bool = True) -> None:
        mapped = self._map_direction(x, y, z, direction)
        if mapped is None:
            raise IndexError("edge direction leaves FlexGridGraph bounds")
        mx, my, mz, mdir = mapped
        self.getNode(mx, my, mz).set_edge(mdir, value)

    def clearEdge(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum) -> None:
        self.setEdge(x, y, z, direction, False)

    def addEdge(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum) -> None:
        self.setEdge(x, y, z, direction, True)

    def hasGridCost(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum) -> bool:
        mapped = self._map_direction(x, y, z, direction)
        if mapped is None:
            return False
        mx, my, mz, mdir = mapped
        return self.getNode(mx, my, mz).has_grid_cost(mdir)

    def setGridCost(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum, value: bool = True) -> None:
        mapped = self._map_direction(x, y, z, direction)
        if mapped is None:
            raise IndexError("grid-cost direction leaves FlexGridGraph bounds")
        mx, my, mz, mdir = mapped
        self.getNode(mx, my, mz).set_grid_cost(mdir, value)

    def setSpecialVia(self, x: frMIdx, y: frMIdx, z: frMIdx, value: bool = True) -> None:
        self.getNode(x, y, z).has_special_via = value

    def hasSpecialVia(self, x: frMIdx, y: frMIdx, z: frMIdx) -> bool:
        return self.getNode(x, y, z).has_special_via

    def setBlocked(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum, value: bool = True) -> None:
        mapped = self._map_direction(x, y, z, direction)
        if mapped is None:
            raise IndexError("blockage direction leaves FlexGridGraph bounds")
        mx, my, mz, mdir = mapped
        self.getNode(mx, my, mz).set_blocked(mdir, value)

    def clearBlocked(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum) -> None:
        self.setBlocked(x, y, z, direction, False)

    def reset(self) -> None:
        self.nodes_ = [FlexGridGraphNode() for _ in self.nodes_]

    def clear(self) -> None:
        self.xCoords_.clear()
        self.yCoords_.clear()
        self.zCoords_.clear()
        self.zHeights_.clear()
        self.layerRouteDirections_.clear()
        self.nodes_.clear()

    def snapshot(self) -> dict[str, Any]:
        """返回 grid graph 状态摘要；不执行 maze search 或 cost propagation。"""

        edge_count = sum(int(node.has_east_edge) + int(node.has_north_edge) + int(node.has_up_edge) for node in self.nodes_)
        blocked_count = sum(int(node.is_blocked_east) + int(node.is_blocked_north) + int(node.is_blocked_up) for node in self.nodes_)
        grid_cost_count = sum(int(node.has_grid_cost_east) + int(node.has_grid_cost_north) + int(node.has_grid_cost_up) for node in self.nodes_)
        return {
            "dim": self.getDim(),
            "bbox": self.getBBox(),
            "min_layer_num": self.getMinLayerNum(),
            "max_layer_num": self.getMaxLayerNum(),
            "edges": edge_count,
            "blocked_edges": blocked_count,
            "grid_cost_edges": grid_cost_count,
            "special_vias": sum(int(node.has_special_via) for node in self.nodes_),
            "validation_errors": self.validate(),
        }

    def validate(self) -> List[str]:
        """检查 grid graph 容器维度一致性；不运行 maze search。"""

        errors: List[str] = []
        x_dim, y_dim, z_dim = self.getDim()
        expected_nodes = x_dim * y_dim * z_dim
        if len(self.nodes_) != expected_nodes:
            errors.append(f"nodes size {len(self.nodes_)} != dim product {expected_nodes}")
        if self.xCoords_ != sorted(set(self.xCoords_)):
            errors.append("x coordinates are not sorted/unique")
        if self.yCoords_ != sorted(set(self.yCoords_)):
            errors.append("y coordinates are not sorted/unique")
        if self.zCoords_ != sorted(set(self.zCoords_)):
            errors.append("z coordinates are not sorted/unique")
        if len(self.zHeights_) not in (0, z_dim):
            errors.append(f"zHeights size {len(self.zHeights_)} != z dim {z_dim}")
        if len(self.layerRouteDirections_) not in (0, z_dim):
            errors.append(f"layerRouteDirections size {len(self.layerRouteDirections_)} != z dim {z_dim}")
        return errors

    def isValidIdx(self, x: frMIdx, y: frMIdx, z: frMIdx) -> bool:
        x_dim, y_dim, z_dim = self.getDim()
        return 0 <= x < x_dim and 0 <= y < y_dim and 0 <= z < z_dim

    def _check_idx(self, x: frMIdx, y: frMIdx, z: frMIdx) -> None:
        if not self.isValidIdx(x, y, z):
            raise IndexError(f"FlexGridGraph index out of range: ({x}, {y}, {z})")

    def _map_direction(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum) -> Optional[Tuple[frMIdx, frMIdx, frMIdx, frDirEnum]]:
        self._check_idx(x, y, z)
        if direction in (frDirEnum.E, frDirEnum.N, frDirEnum.U):
            return (x, y, z, direction)
        if direction == frDirEnum.W:
            return None if x == 0 else (x - 1, y, z, frDirEnum.E)
        if direction == frDirEnum.S:
            return None if y == 0 else (x, y - 1, z, frDirEnum.N)
        if direction == frDirEnum.D:
            return None if z == 0 else (x, y, z - 1, frDirEnum.U)
        return None

    def isBlocked(self, x: frMIdx, y: frMIdx, z: frMIdx, direction: frDirEnum) -> bool:
        mapped = self._map_direction(x, y, z, direction)
        if mapped is None:
            return False
        mx, my, mz, mdir = mapped
        return self.getNode(mx, my, mz).is_blocked(mdir)

    def init(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGridGraph::init")

    def search(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGridGraph::search")

    def traceBackPath(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGridGraph::traceBackPath")

    def updatePrevNodeCost(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGridGraph::updatePrevNodeCost")

__all__ = ["FlexGridGraph", "FlexGridGraphNode", "FlexMazeIdx"]
