"""drt private design database objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .types import (
    Point,
    Rect,
    RouterConfiguration,
    dbTechLayerDir,
    dbTechLayerType,
    frBlockObjectEnum,
    frCoord,
    frLayerNum,
    frUInt4,
    _object_name,
    _unsupported,
)

@dataclass
class frLayer:
    """对应 ``db/tech/frLayer.h`` 的 routing/cut layer 对象。

    本轮仅保存不依赖 odb 的 layer 属性和约束列表；真实 LEF/ODB 层对象、
    cut class 与 spacing table 解析在后续 tech 翻译中补齐。
    """

    name: str = ""
    layer_num: frLayerNum = 0
    width: frUInt4 = 0
    min_width: frUInt4 = 0
    pitch: frUInt4 = 0
    direction: dbTechLayerDir = dbTechLayerDir.NONE
    layer_type: dbTechLayerType = dbTechLayerType.OTHER
    fake_cut: bool = False
    fake_masterslice: bool = False
    unidirectional: bool = False
    default_via_def: Optional["frViaDef"] = None
    secondary_via_defs: List["frViaDef"] = field(default_factory=list)
    constraints: List[Any] = field(default_factory=list)

    def setLayerNum(self, layer_num: frLayerNum) -> None:
        self.layer_num = layer_num

    def getLayerNum(self) -> frLayerNum:
        return self.layer_num

    def getName(self) -> str:
        if self.fake_cut:
            return "Fr_VIA"
        if self.fake_masterslice:
            return "FR_MASTERSLICE"
        return self.name

    def setWidth(self, width: frUInt4) -> None:
        self.width = width

    def getWidth(self) -> frUInt4:
        return self.width

    def setMinWidth(self, width: frUInt4) -> None:
        self.min_width = width

    def getMinWidth(self) -> frUInt4:
        return self.min_width

    def getPitch(self) -> frUInt4:
        return 0 if self.fake_cut or self.fake_masterslice else self.pitch

    def getDir(self) -> dbTechLayerDir:
        return dbTechLayerDir.NONE if self.fake_cut or self.fake_masterslice else self.direction

    def isVertical(self) -> bool:
        return self.getDir() == dbTechLayerDir.VERTICAL

    def isHorizontal(self) -> bool:
        return self.getDir() == dbTechLayerDir.HORIZONTAL

    def isRoutable(self) -> bool:
        return (not self.fake_cut and not self.fake_masterslice and self.layer_type == dbTechLayerType.ROUTING)

    def isUnidirectional(self) -> bool:
        return self.unidirectional

    def addConstraint(self, constraint: Any) -> None:
        self.constraints.append(constraint)

    def setDefaultViaDef(self, via_def: Optional["frViaDef"]) -> None:
        self.default_via_def = via_def

    def getDefaultViaDef(self) -> Optional["frViaDef"]:
        return self.default_via_def


@dataclass
class frViaDef:
    """对应 ``db/tech/frViaDef.h`` 的轻量 via definition。"""

    name: str
    layer1_num: frLayerNum = 0
    cut_layer_num: frLayerNum = 0
    layer2_num: frLayerNum = 0
    is_default: bool = False

    def getName(self) -> str:
        return self.name


@dataclass
class frVia:
    """对应 ``db/obj/frVia.h`` 的设计内 via 实例。"""

    via_def: Optional[frViaDef] = None
    origin: Point = (0, 0)
    owner: Optional[Any] = None

    def setViaDef(self, via_def: Optional[frViaDef]) -> None:
        self.via_def = via_def

    def getViaDef(self) -> Optional[frViaDef]:
        return self.via_def

    def setOrigin(self, origin: Point) -> None:
        self.origin = origin

    def getOrigin(self) -> Point:
        return self.origin

    def addToNet(self, net: "frNet") -> None:
        self.owner = net

    def typeId(self) -> frBlockObjectEnum:
        return frBlockObjectEnum.frcVia


@dataclass
class frShape:
    """frRect/frPathSeg/frPolygon 的共同轻量基类。"""

    layer_num: frLayerNum = 0
    bbox: Rect = (0, 0, 0, 0)
    owner: Optional[Any] = None

    def addToNet(self, net: "frNet") -> None:
        self.owner = net

    def getLayerNum(self) -> frLayerNum:
        return self.layer_num

    def getBBox(self) -> Rect:
        return self.bbox


@dataclass
class frGuide(frShape):
    """对应 ``db/obj/frGuide.h`` 的 guide box。"""

    begin_layer_num: frLayerNum = 0
    end_layer_num: frLayerNum = 0


@dataclass
class frMarker:
    """对应 ``db/obj/frMarker.h`` 的 DRC marker 基础表达。"""

    bbox: Rect = (0, 0, 0, 0)
    layer_num: frLayerNum = 0
    constraint: Optional[Any] = None
    sources: Set[Any] = field(default_factory=set)

    def getBBox(self) -> Rect:
        return self.bbox

    def getLayerNum(self) -> frLayerNum:
        return self.layer_num


@dataclass
class frNode:
    """对应 ``db/obj/frNode.h`` 的 net topology node 轻量对象。"""

    loc: Point = (0, 0)
    layer_num: frLayerNum = 0
    parent: Optional["frNode"] = None
    children: List["frNode"] = field(default_factory=list)
    id: int = -1

    def setId(self, node_id: int) -> None:
        self.id = node_id

    def getId(self) -> int:
        return self.id


@dataclass
class frNet:
    """对应 ``db/obj/frNet.h`` 的设计 net。

    这里只管理 net 的对象集合和状态位；route topology、TA/DR 连接修复、
    NDR/clock 优先级细节保留接口边界。
    """

    name: str
    router_cfg: Optional[RouterConfiguration] = None
    inst_terms: List[Any] = field(default_factory=list)
    bterms: List[Any] = field(default_factory=list)
    shapes: List[frShape] = field(default_factory=list)
    vias: List[frVia] = field(default_factory=list)
    patch_wires: List[frShape] = field(default_factory=list)
    gr_shapes: List[Any] = field(default_factory=list)
    gr_vias: List[Any] = field(default_factory=list)
    nodes: List[frNode] = field(default_factory=list)
    rpins: List[Any] = field(default_factory=list)
    guides: List[frGuide] = field(default_factory=list)
    orig_guides: List[frShape] = field(default_factory=list)
    root: Optional[frNode] = None
    root_gcell_node: Optional[frNode] = None
    first_non_rpin_node: Optional[frNode] = None
    modified: bool = False
    is_fake_net: bool = False
    is_fixed: bool = False
    has_initial_routing: bool = False
    is_clock: bool = False
    is_special: bool = False
    is_connected_by_abutment: bool = False
    has_jumpers: bool = False
    abs_priority_lvl: int = 0
    nondefault_rule: Optional[Any] = None

    def getName(self) -> str:
        return self.name

    def setName(self, name: str) -> None:
        self.name = name

    def addInstTerm(self, term: Any) -> None:
        self.inst_terms.append(term)

    def getInstTerms(self) -> List[Any]:
        return self.inst_terms

    def addBTerm(self, term: Any) -> None:
        self.bterms.append(term)

    def getBTerms(self) -> List[Any]:
        return self.bterms

    def addShape(self, shape: frShape) -> None:
        shape.addToNet(self)
        self.shapes.append(shape)

    def addVia(self, via: frVia) -> None:
        via.addToNet(self)
        self.vias.append(via)

    def addPatchWire(self, shape: frShape) -> None:
        shape.addToNet(self)
        self.patch_wires.append(shape)

    def addGuide(self, guide: frGuide) -> None:
        guide.addToNet(self)
        self.guides.append(guide)

    def addNode(self, node: frNode) -> None:
        node.setId(len(self.nodes))
        self.nodes.append(node)

    def clearRoutes(self) -> None:
        self.shapes.clear()
        self.vias.clear()
        self.patch_wires.clear()

    def clearGRShapes(self) -> None:
        self.gr_shapes.clear()

    def clearGRVias(self) -> None:
        self.gr_vias.clear()

    def clearGuides(self) -> None:
        self.guides.clear()

    def hasGuides(self) -> bool:
        return bool(self.guides)

    def isModified(self) -> bool:
        return self.modified

    def setModified(self, value: bool) -> None:
        self.modified = value

    def isFake(self) -> bool:
        return self.is_fake_net

    def setIsFake(self, value: bool) -> None:
        self.is_fake_net = value

    def setFixed(self, value: bool) -> None:
        self.is_fixed = value

    def isFixed(self) -> bool:
        return self.is_fixed

    def updateIsClock(self, value: bool) -> None:
        self.is_clock = value
        self.updateAbsPriority()

    def isClock(self) -> bool:
        return self.is_clock

    def updateNondefaultRule(self, rule: Any) -> None:
        self.nondefault_rule = rule
        self.updateAbsPriority()

    def hasNDR(self) -> bool:
        return self.nondefault_rule is not None

    def updateAbsPriority(self) -> None:
        if self.router_cfg is None:
            return
        priority = self.abs_priority_lvl
        if self.hasNDR():
            priority = max(priority, self.router_cfg.NDR_NETS_ABS_PRIORITY)
        if self.isClock():
            priority = max(priority, self.router_cfg.CLOCK_NETS_ABS_PRIORITY)
        self.abs_priority_lvl = priority

    def typeId(self) -> frBlockObjectEnum:
        return frBlockObjectEnum.frcNet


@dataclass
class frTechObject:
    """对应 ``db/tech/frTechObject.h`` 的顶层 tech 容器。"""

    layers: List[frLayer] = field(default_factory=list)
    via_defs: Dict[str, frViaDef] = field(default_factory=dict)

    def addLayer(self, layer: frLayer) -> None:
        self.layers.append(layer)
        self.layers.sort(key=lambda item: item.getLayerNum())

    def getLayers(self) -> List[frLayer]:
        return self.layers

    def getLayer(self, layer_num: frLayerNum) -> Optional[frLayer]:
        for layer in self.layers:
            if layer.getLayerNum() == layer_num:
                return layer
        return None

    def getTopLayerNum(self) -> frLayerNum:
        return self.layers[-1].getLayerNum() if self.layers else 0

    def isHorizontalLayer(self, layer_num: frLayerNum) -> bool:
        layer = self.getLayer(layer_num)
        return bool(layer and layer.isHorizontal())

    def isVerticalLayer(self, layer_num: frLayerNum) -> bool:
        layer = self.getLayer(layer_num)
        return bool(layer and layer.isVertical())

    def addViaDef(self, via_def: frViaDef) -> None:
        self.via_defs[via_def.getName()] = via_def

    def getViaDef(self, name: str) -> Optional[frViaDef]:
        return self.via_defs.get(name)


@dataclass
class frBlock:
    """对应 ``db/obj/frBlock.h`` 的顶层 block 轻量容器。"""

    name: str = ""
    nets: List[frNet] = field(default_factory=list)
    markers: List[frMarker] = field(default_factory=list)
    track_patterns: Dict[Tuple[frLayerNum, bool], List[Any]] = field(default_factory=dict)

    def addNet(self, net: frNet) -> None:
        self.nets.append(net)

    def getNets(self) -> List[frNet]:
        return self.nets

    def findNet(self, name: str) -> Optional[frNet]:
        for net in self.nets:
            if net.getName() == name:
                return net
        return None

    def addMarker(self, marker: frMarker) -> None:
        self.markers.append(marker)

    def getMarkers(self) -> List[frMarker]:
        return self.markers

    def getTrackPatterns(self, layer_num: frLayerNum, is_vertical: bool) -> List[Any]:
        return self.track_patterns.get((layer_num, is_vertical), [])


class frRegionQuery:
    """对应 ``frRegionQuery.h`` 的边界对象。

    Region query 的 R-tree 索引和几何查询属于 DRC/route 核心算法，本轮只
    保留 init/query/update 入口。
    """

    def __init__(self, design: "frDesign", logger: Any = None, router_cfg: Optional[RouterConfiguration] = None):
        self.design = design
        self.logger = logger
        self.router_cfg = router_cfg

    def init(self) -> None:
        _unsupported("frRegionQuery::init")

    def query(self, box: Rect, layer_num: frLayerNum) -> List[Any]:
        _unsupported("frRegionQuery::query")

    def add(self, obj: Any) -> None:
        _unsupported("frRegionQuery::add")

    def remove(self, obj: Any) -> None:
        _unsupported("frRegionQuery::remove")


class frDesign:
    """对应 ``frDesign.h`` 的 drt 私有设计对象。"""

    def __init__(self, logger: Any = None, router_cfg: Optional[RouterConfiguration] = None):
        self.logger = logger
        self.router_cfg = router_cfg or RouterConfiguration()
        self.topBlock_: Optional[frBlock] = None
        self.tech_ = frTechObject()
        self.rq_ = frRegionQuery(self, logger, self.router_cfg)
        self.masters_: List[Any] = []
        self.name2master_: Dict[str, Any] = {}
        self.updates_: List[List[Any]] = []
        self.updates_sz_: int = 0
        self.user_selected_vias_: List[str] = []
        self.version_: int = 0

    def getTopBlock(self) -> Optional[frBlock]:
        return self.topBlock_

    def setTopBlock(self, block: frBlock) -> None:
        self.topBlock_ = block

    def getTech(self) -> frTechObject:
        return self.tech_

    def setTech(self, tech: frTechObject) -> None:
        self.tech_ = tech

    def getRegionQuery(self) -> frRegionQuery:
        return self.rq_

    def addMaster(self, master: Any) -> None:
        name = _object_name(master)
        self.name2master_[name] = master
        self.masters_.append(master)

    def getMasters(self) -> List[Any]:
        return self.masters_

    def addUserSelectedVia(self, via_name: str) -> None:
        self.user_selected_vias_.append(via_name)

    def getUserSelectedVias(self) -> List[str]:
        return self.user_selected_vias_

    def isHorizontalLayer(self, layer_num: frLayerNum) -> bool:
        return self.tech_.isHorizontalLayer(layer_num)

    def isVerticalLayer(self, layer_num: frLayerNum) -> bool:
        return self.tech_.isVerticalLayer(layer_num)

    def getPrefDirTracks(self, layer_num: frLayerNum) -> List[Any]:
        if self.topBlock_ is None:
            return []
        return self.topBlock_.getTrackPatterns(layer_num, self.isVerticalLayer(layer_num))

    def getNonPrefDirTracks(self, layer_num: frLayerNum) -> List[Any]:
        if self.topBlock_ is None:
            return []
        return self.topBlock_.getTrackPatterns(layer_num, not self.isVerticalLayer(layer_num))

    def addUpdate(self, update: Any) -> None:
        if not self.updates_:
            self.updates_ = [[] for _ in range(max(1, self.router_cfg.MAX_THREADS * 2))]
        self.updates_[self.updates_sz_ % len(self.updates_)].append(update)
        self.updates_sz_ += 1

    def getUpdates(self) -> List[List[Any]]:
        return self.updates_

    def hasUpdates(self) -> bool:
        return self.updates_sz_ != 0

    def clearUpdates(self) -> None:
        self.updates_.clear()
        self.updates_sz_ = 0

    def incrementVersion(self) -> None:
        self.version_ += 1

    def getVersion(self) -> int:
        return self.version_

__all__ = [
    "frBlock",
    "frDesign",
    "frGuide",
    "frLayer",
    "frMarker",
    "frNet",
    "frNode",
    "frRegionQuery",
    "frShape",
    "frTechObject",
    "frVia",
    "frViaDef",
]
