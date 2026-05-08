"""drt private design database objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

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

def _rect_is_valid(box: Rect) -> bool:
    return box[0] <= box[2] and box[1] <= box[3]


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

    def setPitch(self, pitch: frUInt4) -> None:
        self.pitch = pitch

    def getPitch(self) -> frUInt4:
        return 0 if self.fake_cut or self.fake_masterslice else self.pitch

    def setDir(self, direction: dbTechLayerDir) -> None:
        self.direction = direction

    def getDir(self) -> dbTechLayerDir:
        return dbTechLayerDir.NONE if self.fake_cut or self.fake_masterslice else self.direction

    def setType(self, layer_type: dbTechLayerType) -> None:
        self.layer_type = layer_type

    def getType(self) -> dbTechLayerType:
        return self.layer_type

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

    def addSecondaryViaDef(self, via_def: "frViaDef") -> None:
        if via_def not in self.secondary_via_defs:
            self.secondary_via_defs.append(via_def)

    def getSecondaryViaDefs(self) -> List["frViaDef"]:
        return self.secondary_via_defs

    def getConstraints(self) -> List[Any]:
        return self.constraints

    def validate(self) -> List[str]:
        """只检查 Python 边界内的 layer 状态，不推导 PDK 规则。"""

        errors: List[str] = []
        if not self.getName():
            errors.append("layer name is empty")
        if self.layer_num < 0:
            errors.append(f"layer {self.getName()} has negative layer_num")
        if self.width < 0 or self.min_width < 0 or self.pitch < 0:
            errors.append(f"layer {self.getName()} has negative width/min_width/pitch")
        if self.isRoutable() and self.getDir() == dbTechLayerDir.NONE:
            errors.append(f"routing layer {self.getName()} has no preferred direction")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """返回 layer 的 Python 状态快照；约束仅保存名称，避免假装解析 LEF 语义。"""

        return {
            "name": self.getName(),
            "layer_num": self.layer_num,
            "width": self.width,
            "min_width": self.min_width,
            "pitch": self.getPitch(),
            "direction": self.getDir().value,
            "layer_type": self.layer_type.value,
            "unidirectional": self.unidirectional,
            "default_via_def": self.default_via_def.getName() if self.default_via_def else None,
            "secondary_via_defs": [via_def.getName() for via_def in self.secondary_via_defs],
            "constraints": [_object_name(constraint) for constraint in self.constraints],
        }


@dataclass
class frViaDef:
    """对应 ``db/tech/frViaDef.h`` 的轻量 via definition。"""

    name: str
    layer1_num: frLayerNum = 0
    cut_layer_num: frLayerNum = 0
    layer2_num: frLayerNum = 0
    is_default: bool = False
    owner: Optional["frTechObject"] = None

    def getName(self) -> str:
        return self.name

    def getLayer1Num(self) -> frLayerNum:
        return self.layer1_num

    def getCutLayerNum(self) -> frLayerNum:
        return self.cut_layer_num

    def getLayer2Num(self) -> frLayerNum:
        return self.layer2_num

    def getTech(self) -> Optional["frTechObject"]:
        return self.owner

    def isDefault(self) -> bool:
        return self.is_default

    def validate(self) -> List[str]:
        """检查 via def 的层号顺序；不检查 cut/metal 几何。"""

        errors: List[str] = []
        if not self.name:
            errors.append("via def name is empty")
        if self.layer1_num > self.layer2_num:
            errors.append(f"via def {self.name} has layer1 above layer2")
        if self.cut_layer_num and not (self.layer1_num <= self.cut_layer_num <= self.layer2_num):
            errors.append(f"via def {self.name} cut layer is outside metal layer span")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """返回 via def 的边界状态，不展开 cut/metal shape。"""

        return {
            "name": self.name,
            "layer1_num": self.layer1_num,
            "cut_layer_num": self.cut_layer_num,
            "layer2_num": self.layer2_num,
            "is_default": self.is_default,
        }


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

    def getNet(self) -> Optional[Any]:
        return self.owner

    def addToNet(self, net: "frNet") -> None:
        self.owner = net

    def removeFromNet(self) -> None:
        self.owner = None

    def typeId(self) -> frBlockObjectEnum:
        return frBlockObjectEnum.frcVia

    def getBBox(self) -> Rect:
        x, y = self.origin
        return (x, y, x, y)

    def validate(self) -> List[str]:
        """检查 via 实例是否有 via def；不展开真实 via bbox。"""

        return ["via has no via_def"] if self.via_def is None else []

    def to_dict(self) -> Dict[str, Any]:
        """返回 via 实例快照；真实 via 几何仍由后续 frViaDef 翻译负责。"""

        return {
            "via_def": self.via_def.getName() if self.via_def else None,
            "origin": self.origin,
            "owner": _object_name(self.owner),
        }


@dataclass
class frShape:
    """frRect/frPathSeg/frPolygon 的共同轻量基类。"""

    layer_num: frLayerNum = 0
    bbox: Rect = (0, 0, 0, 0)
    owner: Optional[Any] = None

    def addToNet(self, net: "frNet") -> None:
        self.owner = net

    def removeFromNet(self) -> None:
        self.owner = None

    def getLayerNum(self) -> frLayerNum:
        return self.layer_num

    def getBBox(self) -> Rect:
        return self.bbox

    def getNet(self) -> Optional[Any]:
        return self.owner

    def setLayerNum(self, layer_num: frLayerNum) -> None:
        self.layer_num = layer_num

    def setBBox(self, bbox: Rect) -> None:
        self.bbox = bbox

    def validate(self) -> List[str]:
        """检查 shape 的基本 bbox/layer 合法性，不做 DRC。"""

        errors: List[str] = []
        if self.layer_num < 0:
            errors.append("shape has negative layer_num")
        if not _rect_is_valid(self.bbox):
            errors.append(f"shape has invalid bbox {self.bbox}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """返回 shape 边界状态；不区分 rect/pathseg/polygon 的内部点列。"""

        return {"layer_num": self.layer_num, "bbox": self.bbox, "owner": _object_name(self.owner)}


@dataclass
class frGuide(frShape):
    """对应 ``db/obj/frGuide.h`` 的 guide box。"""

    begin_layer_num: frLayerNum = 0
    end_layer_num: frLayerNum = 0

    def __post_init__(self) -> None:
        if self.begin_layer_num == 0:
            self.begin_layer_num = self.layer_num
        if self.end_layer_num == 0:
            self.end_layer_num = self.layer_num

    def getBeginLayerNum(self) -> frLayerNum:
        return self.begin_layer_num

    def getEndLayerNum(self) -> frLayerNum:
        return self.end_layer_num

    def setBeginLayerNum(self, layer_num: frLayerNum) -> None:
        self.begin_layer_num = layer_num

    def setEndLayerNum(self, layer_num: frLayerNum) -> None:
        self.end_layer_num = layer_num

    def validate(self) -> List[str]:
        """检查 guide 的层范围和 bbox；不计算 guide 覆盖率。"""

        errors = super().validate()
        if self.begin_layer_num > self.end_layer_num:
            errors.append(f"guide has invalid layer span {self.begin_layer_num}>{self.end_layer_num}")
        if self.layer_num and not (self.begin_layer_num <= self.layer_num <= self.end_layer_num):
            errors.append("guide layer_num is outside begin/end layer span")
        return errors

    def typeId(self) -> frBlockObjectEnum:
        return frBlockObjectEnum.frcGuide

    def to_dict(self) -> Dict[str, Any]:
        """返回 guide box 状态，供 route guide report/snapshot 使用。"""

        data = super().to_dict()
        data.update({"begin_layer_num": self.begin_layer_num, "end_layer_num": self.end_layer_num})
        return data


@dataclass
class frMarker:
    """对应 ``db/obj/frMarker.h`` 的 DRC marker 基础表达。"""

    bbox: Rect = (0, 0, 0, 0)
    layer_num: frLayerNum = 0
    constraint: Optional[Any] = None
    sources: List[Any] = field(default_factory=list)
    owner: Optional[Any] = None

    def getBBox(self) -> Rect:
        return self.bbox

    def getLayerNum(self) -> frLayerNum:
        return self.layer_num

    def setBBox(self, bbox: Rect) -> None:
        self.bbox = bbox

    def setLayerNum(self, layer_num: frLayerNum) -> None:
        self.layer_num = layer_num

    def addSrc(self, obj: Any) -> None:
        if obj not in self.sources:
            self.sources.append(obj)

    def getSrcs(self) -> List[Any]:
        return self.sources

    def setConstraint(self, constraint: Any) -> None:
        self.constraint = constraint

    def getConstraint(self) -> Optional[Any]:
        return self.constraint

    def getOwner(self) -> Optional[Any]:
        return self.owner

    def validate(self) -> List[str]:
        """检查 marker 的基本状态；不判定违规类别或生成 marker。"""

        errors: List[str] = []
        if self.layer_num < 0:
            errors.append("marker has negative layer_num")
        if not _rect_is_valid(self.bbox):
            errors.append(f"marker has invalid bbox {self.bbox}")
        return errors

    def typeId(self) -> frBlockObjectEnum:
        return frBlockObjectEnum.frcMarker

    def to_dict(self) -> Dict[str, Any]:
        """返回 marker 状态；不执行 DRC 分类或几何重算。"""

        return {
            "bbox": self.bbox,
            "layer_num": self.layer_num,
            "constraint": _object_name(self.constraint),
            "sources": [_object_name(src) for src in self.sources],
            "owner": _object_name(self.owner),
            "type_id": int(self.typeId()),
        }


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

    def getLoc(self) -> Point:
        return self.loc

    def getLayerNum(self) -> frLayerNum:
        return self.layer_num

    def to_dict(self) -> Dict[str, Any]:
        """返回拓扑节点快照；父子关系使用 id，避免递归展开。"""

        return {
            "id": self.id,
            "loc": self.loc,
            "layer_num": self.layer_num,
            "parent": self.parent.getId() if self.parent is not None else None,
            "children": [child.getId() for child in self.children],
        }


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
    owner: Optional["frBlock"] = None

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
        if shape in self.shapes:
            return
        shape.addToNet(self)
        self.shapes.append(shape)

    def addVia(self, via: frVia) -> None:
        if via in self.vias:
            return
        via.addToNet(self)
        self.vias.append(via)

    def addPatchWire(self, shape: frShape) -> None:
        if shape in self.patch_wires:
            return
        shape.addToNet(self)
        self.patch_wires.append(shape)

    def addGuide(self, guide: frGuide) -> None:
        if guide in self.guides:
            return
        guide.addToNet(self)
        self.guides.append(guide)

    def addNode(self, node: frNode) -> None:
        node.setId(len(self.nodes))
        self.nodes.append(node)

    def addGRShape(self, shape: Any) -> None:
        self.gr_shapes.append(shape)

    def addGRVia(self, via: Any) -> None:
        self.gr_vias.append(via)

    def getShapes(self) -> List[frShape]:
        return self.shapes

    def getVias(self) -> List[frVia]:
        return self.vias

    def getPatchWires(self) -> List[frShape]:
        return self.patch_wires

    def getGuides(self) -> List[frGuide]:
        return self.guides

    def getOrigGuides(self) -> List[frShape]:
        return self.orig_guides

    def setOrigGuides(self, guides: Iterable[frShape]) -> None:
        self.orig_guides = list(guides)

    def addOrigGuide(self, guide: frShape) -> None:
        self.orig_guides.append(guide)

    def getNodes(self) -> List[frNode]:
        return self.nodes

    def getGRShapes(self) -> List[Any]:
        return self.gr_shapes

    def getGRVias(self) -> List[Any]:
        return self.gr_vias

    def getRoot(self) -> Optional[frNode]:
        return self.root

    def setRoot(self, node: Optional[frNode]) -> None:
        self.root = node

    def getRootGCellNode(self) -> Optional[frNode]:
        return self.root_gcell_node

    def setRootGCellNode(self, node: Optional[frNode]) -> None:
        self.root_gcell_node = node

    def getFirstNonRPinNode(self) -> Optional[frNode]:
        return self.first_non_rpin_node

    def setFirstNonRPinNode(self, node: Optional[frNode]) -> None:
        self.first_non_rpin_node = node

    def getRouteObjCount(self) -> int:
        return len(self.shapes) + len(self.vias) + len(self.patch_wires)

    def getGuideCount(self) -> int:
        return len(self.guides)

    def removeShape(self, shape: frShape) -> None:
        if shape in self.shapes:
            self.shapes.remove(shape)
            shape.removeFromNet()

    def removeVia(self, via: frVia) -> None:
        if via in self.vias:
            self.vias.remove(via)
            via.removeFromNet()

    def clearRoutes(self) -> None:
        for shape in self.shapes:
            shape.removeFromNet()
        for via in self.vias:
            via.removeFromNet()
        for shape in self.patch_wires:
            shape.removeFromNet()
        self.shapes.clear()
        self.vias.clear()
        self.patch_wires.clear()

    def clearGRShapes(self) -> None:
        self.gr_shapes.clear()

    def clearGRVias(self) -> None:
        self.gr_vias.clear()

    def clearGuides(self) -> None:
        for guide in self.guides:
            guide.removeFromNet()
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

    def setHasInitialRouting(self, value: bool) -> None:
        self.has_initial_routing = value

    def hasInitialRouting(self) -> bool:
        return self.has_initial_routing

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

    def getNondefaultRule(self) -> Optional[Any]:
        return self.nondefault_rule

    def setSpecial(self, value: bool) -> None:
        self.is_special = value

    def isSpecial(self) -> bool:
        return self.is_special

    def setConnectedByAbutment(self, value: bool) -> None:
        self.is_connected_by_abutment = value

    def isConnectedByAbutment(self) -> bool:
        return self.is_connected_by_abutment

    def setHasJumpers(self, value: bool) -> None:
        self.has_jumpers = value

    def hasJumpers(self) -> bool:
        return self.has_jumpers

    def getAbsPriorityLvl(self) -> int:
        return self.abs_priority_lvl

    def setAbsPriorityLvl(self, value: int) -> None:
        self.abs_priority_lvl = value

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

    def getOwner(self) -> Optional["frBlock"]:
        return self.owner

    def getGuideSummary(self) -> Dict[str, Any]:
        """返回单 net 的 guide/route 摘要，不尝试评估真实覆盖。"""

        layers: Dict[frLayerNum, int] = {}
        for guide in self.guides:
            for layer_num in range(guide.getBeginLayerNum(), guide.getEndLayerNum() + 1):
                layers[layer_num] = layers.get(layer_num, 0) + 1
        return {
            "net": self.name,
            "guides": len(self.guides),
            "orig_guides": len(self.orig_guides),
            "guide_layers": layers,
            "route_objs": self.getRouteObjCount(),
            "modified": self.modified,
        }

    def validateGuides(self) -> List[str]:
        """检查 net guide 容器关系和基础几何；不做覆盖率或连通性判断。"""

        errors: List[str] = []
        for idx, guide in enumerate(self.guides):
            for error in guide.validate():
                errors.append(f"net {self.name} guide[{idx}]: {error}")
            if guide.getNet() is not self:
                errors.append(f"net {self.name} guide[{idx}] owner mismatch")
        return errors

    def validateRoutes(self) -> List[str]:
        """检查 route 对象 owner 和基础 bbox；不修复拓扑。"""

        errors: List[str] = []
        for idx, shape in enumerate(self.shapes):
            if hasattr(shape, "validate"):
                for error in shape.validate():
                    errors.append(f"net {self.name} shape[{idx}]: {error}")
            if getattr(shape, "getNet", lambda: None)() is not self:
                errors.append(f"net {self.name} shape[{idx}] owner mismatch")
        for idx, via in enumerate(self.vias):
            if hasattr(via, "validate"):
                for error in via.validate():
                    errors.append(f"net {self.name} via[{idx}]: {error}")
            if via.getNet() is not self:
                errors.append(f"net {self.name} via[{idx}] owner mismatch")
        return errors

    def validate(self) -> List[str]:
        """检查 net 的 Python 容器一致性，不运行 detailed routing。"""

        errors: List[str] = []
        if not self.name:
            errors.append("net name is empty")
        errors.extend(self.validateGuides())
        errors.extend(self.validateRoutes())
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """返回 net 的对象计数和状态位；不推导连通性或修复布线。"""

        return {
            "name": self.name,
            "inst_terms": len(self.inst_terms),
            "bterms": len(self.bterms),
            "shapes": [shape.to_dict() if hasattr(shape, "to_dict") else _object_name(shape) for shape in self.shapes],
            "vias": [via.to_dict() if hasattr(via, "to_dict") else _object_name(via) for via in self.vias],
            "patch_wires": len(self.patch_wires),
            "guides": [guide.to_dict() if hasattr(guide, "to_dict") else _object_name(guide) for guide in self.guides],
            "orig_guides": len(self.orig_guides),
            "gr_shapes": len(self.gr_shapes),
            "gr_vias": len(self.gr_vias),
            "nodes": [node.to_dict() for node in self.nodes],
            "modified": self.modified,
            "is_fake": self.is_fake_net,
            "is_fixed": self.is_fixed,
            "has_initial_routing": self.has_initial_routing,
            "is_clock": self.is_clock,
            "is_special": self.is_special,
            "is_connected_by_abutment": self.is_connected_by_abutment,
            "has_jumpers": self.has_jumpers,
            "abs_priority_lvl": self.abs_priority_lvl,
            "nondefault_rule": _object_name(self.nondefault_rule),
        }


@dataclass
class frTechObject:
    """对应 ``db/tech/frTechObject.h`` 的顶层 tech 容器。"""

    layers: List[frLayer] = field(default_factory=list)
    via_defs: Dict[str, frViaDef] = field(default_factory=dict)

    def addLayer(self, layer: frLayer) -> None:
        self.layers = [item for item in self.layers if item.getLayerNum() != layer.getLayerNum() and item.getName() != layer.getName()]
        self.layers.append(layer)
        self.layers.sort(key=lambda item: item.getLayerNum())

    def getLayers(self) -> List[frLayer]:
        return self.layers

    def getLayer(self, layer_num: frLayerNum) -> Optional[frLayer]:
        for layer in self.layers:
            if layer.getLayerNum() == layer_num:
                return layer
        return None

    def getLayerByName(self, name: str) -> Optional[frLayer]:
        for layer in self.layers:
            if layer.getName() == name:
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
        via_def.owner = self
        self.via_defs[via_def.getName()] = via_def
        if via_def.is_default:
            layer = self.getLayer(via_def.layer1_num)
            if layer is not None:
                layer.setDefaultViaDef(via_def)
        else:
            layer = self.getLayer(via_def.layer1_num)
            if layer is not None:
                layer.addSecondaryViaDef(via_def)

    def getViaDef(self, name: str) -> Optional[frViaDef]:
        return self.via_defs.get(name)

    def getViaDefs(self) -> List[frViaDef]:
        return list(self.via_defs.values())

    def validate(self) -> List[str]:
        """检查 tech 容器中的 layer/via def 基本关系。"""

        errors: List[str] = []
        seen_nums: Dict[frLayerNum, str] = {}
        seen_names: Dict[str, frLayerNum] = {}
        for layer in self.layers:
            for error in layer.validate():
                errors.append(f"tech layer {layer.getName()}: {error}")
            if layer.getLayerNum() in seen_nums:
                errors.append(f"duplicate layer_num {layer.getLayerNum()} for {seen_nums[layer.getLayerNum()]} and {layer.getName()}")
            seen_nums[layer.getLayerNum()] = layer.getName()
            if layer.getName() in seen_names:
                errors.append(f"duplicate layer name {layer.getName()}")
            seen_names[layer.getName()] = layer.getLayerNum()
        for via_def in self.getViaDefs():
            for error in via_def.validate():
                errors.append(f"tech via {via_def.getName()}: {error}")
            if via_def.getLayer1Num() and self.getLayer(via_def.getLayer1Num()) is None:
                errors.append(f"via def {via_def.getName()} references missing layer1 {via_def.getLayer1Num()}")
            if via_def.getLayer2Num() and self.getLayer(via_def.getLayer2Num()) is None:
                errors.append(f"via def {via_def.getName()} references missing layer2 {via_def.getLayer2Num()}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """返回 tech 容器快照；只包含已加载到 Python 边界的 layer/via def。"""

        return {
            "layers": [layer.to_dict() for layer in self.layers],
            "via_defs": [via_def.to_dict() for via_def in self.getViaDefs()],
        }


@dataclass
class frBlock:
    """对应 ``db/obj/frBlock.h`` 的顶层 block 轻量容器。"""

    name: str = ""
    nets: List[frNet] = field(default_factory=list)
    markers: List[frMarker] = field(default_factory=list)
    track_patterns: Dict[Tuple[frLayerNum, bool], List[Any]] = field(default_factory=dict)
    owner: Optional["frDesign"] = None

    def addNet(self, net: frNet) -> None:
        existing = self.findNet(net.getName())
        if existing is net:
            return
        if existing is not None:
            self.nets.remove(existing)
            existing.owner = None
        net.owner = self
        self.nets.append(net)

    def getNets(self) -> List[frNet]:
        return self.nets

    def findNet(self, name: str) -> Optional[frNet]:
        for net in self.nets:
            if net.getName() == name:
                return net
        return None

    def addMarker(self, marker: frMarker) -> None:
        marker.owner = self
        self.markers.append(marker)

    def getMarkers(self) -> List[frMarker]:
        return self.markers

    def getMarkerCount(self) -> int:
        return len(self.markers)

    def clearMarkers(self) -> None:
        for marker in self.markers:
            marker.owner = None
        self.markers.clear()

    def removeMarker(self, marker: frMarker) -> None:
        if marker in self.markers:
            self.markers.remove(marker)
            marker.owner = None

    def setTrackPatterns(self, layer_num: frLayerNum, is_vertical: bool, patterns: Iterable[Any]) -> None:
        self.track_patterns[(layer_num, is_vertical)] = list(patterns)

    def getTrackPatterns(self, layer_num: frLayerNum, is_vertical: bool) -> List[Any]:
        return self.track_patterns.get((layer_num, is_vertical), [])

    def removeNet(self, net: frNet) -> None:
        if net in self.nets:
            self.nets.remove(net)
            net.owner = None

    def clearNets(self) -> None:
        for net in self.nets:
            net.owner = None
        self.nets.clear()

    def getName(self) -> str:
        return self.name

    def getGuideSummary(self) -> List[Dict[str, Any]]:
        return [net.getGuideSummary() for net in self.nets]

    def getMarkerSummary(self) -> Dict[str, Any]:
        by_layer: Dict[frLayerNum, int] = {}
        for marker in self.markers:
            by_layer[marker.getLayerNum()] = by_layer.get(marker.getLayerNum(), 0) + 1
        return {"count": len(self.markers), "by_layer": by_layer}

    def validate(self) -> List[str]:
        """检查 block 下对象 owner 与基础几何；不做 DRC/连通性。"""

        errors: List[str] = []
        seen_nets: set[str] = set()
        for net in self.nets:
            if net.getName() in seen_nets:
                errors.append(f"duplicate net {net.getName()}")
            seen_nets.add(net.getName())
            if net.getOwner() is not self:
                errors.append(f"net {net.getName()} owner mismatch")
            errors.extend(net.validate())
        for idx, marker in enumerate(self.markers):
            for error in marker.validate():
                errors.append(f"marker[{idx}]: {error}")
            if marker.getOwner() is not self:
                errors.append(f"marker[{idx}] owner mismatch")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """返回 block 快照；track pattern 仅记录数量，不展开 PDK 轨道对象。"""

        return {
            "name": self.name,
            "nets": [net.to_dict() for net in self.nets],
            "markers": [marker.to_dict() for marker in self.markers],
            "track_patterns": {
                f"{layer_num}:{int(is_vertical)}": len(patterns)
                for (layer_num, is_vertical), patterns in self.track_patterns.items()
            },
        }


class frRegionQuery:
    """对应 ``frRegionQuery.h`` 的边界对象。

    Region query 的 R-tree 索引属于后续优化；本轮用线性索引提供可落地
    容器查询，不执行任何 DRC 判断。
    """

    def __init__(self, design: "frDesign", logger: Any = None, router_cfg: Optional[RouterConfiguration] = None):
        self.design = design
        self.logger = logger
        self.router_cfg = router_cfg
        self.objects_: List[Any] = []

    def init(self) -> None:
        self.objects_.clear()
        block = self.design.getTopBlock()
        if block is None:
            return
        for net in block.getNets():
            self.objects_.extend(net.getShapes())
            self.objects_.extend(net.getVias())
            self.objects_.extend(net.getPatchWires())
            self.objects_.extend(net.getGuides())
        self.objects_.extend(block.getMarkers())

    def query(self, box: Rect, layer_num: frLayerNum) -> List[Any]:
        return [
            obj
            for obj in self.objects_
            if getattr(obj, "getLayerNum", lambda: None)() == layer_num
            and _rect_intersects(getattr(obj, "getBBox")(), box)
        ]

    def add(self, obj: Any) -> None:
        if obj not in self.objects_:
            self.objects_.append(obj)

    def remove(self, obj: Any) -> None:
        if obj in self.objects_:
            self.objects_.remove(obj)

    def getObjects(self) -> List[Any]:
        return self.objects_

    def snapshot(self) -> Dict[str, Any]:
        """返回 region query 当前线性索引摘要；不构建或模拟 R-tree。"""

        by_layer: Dict[frLayerNum, int] = {}
        for obj in self.objects_:
            layer_num = getattr(obj, "getLayerNum", lambda: None)()
            if layer_num is not None:
                by_layer[layer_num] = by_layer.get(layer_num, 0) + 1
        return {"objects": len(self.objects_), "by_layer": by_layer}


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
        block.owner = self
        self.topBlock_ = block

    def getTech(self) -> frTechObject:
        return self.tech_

    def setTech(self, tech: frTechObject) -> None:
        self.tech_ = tech
        self.rq_.design = self

    def getRegionQuery(self) -> frRegionQuery:
        return self.rq_

    def addMaster(self, master: Any) -> None:
        name = _object_name(master)
        self.name2master_[name] = master
        self.masters_.append(master)

    def getMasters(self) -> List[Any]:
        return self.masters_

    def getMaster(self, name: str) -> Optional[Any]:
        return self.name2master_.get(name)

    def addUserSelectedVia(self, via_name: str) -> None:
        if via_name not in self.user_selected_vias_:
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

    def getTopBlockName(self) -> str:
        return self.topBlock_.getName() if self.topBlock_ is not None else ""

    def resolveLayerNum(self, layer_name: str) -> frLayerNum:
        """按 layer 名称查层号；找不到时返回 0，保持轻量查询语义。"""

        layer = self.tech_.getLayerByName(layer_name)
        return layer.getLayerNum() if layer is not None else 0

    def getGuideSummary(self) -> List[Dict[str, Any]]:
        block = self.getTopBlock()
        return block.getGuideSummary() if block is not None else []

    def getMarkerSummary(self) -> Dict[str, Any]:
        block = self.getTopBlock()
        return block.getMarkerSummary() if block is not None else {"count": 0, "by_layer": {}}

    def validate(self) -> List[str]:
        """检查 frDesign Python 状态一致性；不读取或写回 ODB。"""

        errors = self.tech_.validate()
        if self.topBlock_ is not None:
            if self.topBlock_.owner is not self:
                errors.append("top block owner mismatch")
            errors.extend(self.topBlock_.validate())
        return errors

    def snapshot(self) -> Dict[str, Any]:
        """返回 frDesign 的状态快照；用于 Python 接口层报告和 smoke 验证。"""

        block = self.getTopBlock()
        return {
            "version": self.version_,
            "top_block": block.to_dict() if block is not None else None,
            "tech": self.tech_.to_dict(),
            "masters": [_object_name(master) for master in self.masters_],
            "updates": sum(len(bucket) for bucket in self.updates_),
            "update_buckets": len(self.updates_),
            "user_selected_vias": list(self.user_selected_vias_),
            "region_query": self.rq_.snapshot(),
        }


def _rect_intersects(lhs: Rect, rhs: Rect) -> bool:
    return not (lhs[2] < rhs[0] or rhs[2] < lhs[0] or lhs[3] < rhs[1] or rhs[3] < lhs[1])

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
