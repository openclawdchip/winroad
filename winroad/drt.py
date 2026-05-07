"""OpenROAD drt 模块的 Python 顶层复刻骨架。

本文件按本机 OpenROAD ``src/drt`` 的 C++ 边界翻译第一轮对象：

- ``TritonRoute``：drt 顶层入口，持有设计、配置、debug、PA/GR/TA/DR/GC 阶段。
- ``FlexDR`` / ``FlexGR`` / ``FlexGridGraph`` / ``FlexPA`` / ``FlexGCWorker``：
  详细布线、全局详细布线、maze grid、pin access、geometry check 的类边界。
- ``frDesign`` / ``frNet`` / ``frVia`` / ``frLayer`` 等：drt 私有设计数据库对象。

这里不触碰 OpenDB，也不提供演示布线。真实 detailed routing、DRC、
search/maze、worker 并行和分布式算法保留同名入口并显式抛
``NotImplementedError``，方便后续逐 C++ 文件继续翻译。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


frCoord = int
frLayerNum = int
frUInt4 = int
frMIdx = int
Point = Tuple[int, int]
Rect = Tuple[int, int, int, int]


def _unsupported(name: str) -> None:
    """统一标记尚未从 OpenROAD C++ 移植的算法入口。"""

    raise NotImplementedError(f"OpenROAD drt::{name} 尚未翻译为 Python")


def _object_name(obj: Any) -> str:
    """返回 OpenDB-like 对象或 Python 对象的稳定名称。"""

    if obj is None:
        return ""
    name = getattr(obj, "name", None)
    if name is not None:
        return str(name)
    get_name = getattr(obj, "getName", None)
    if callable(get_name):
        return str(get_name())
    return str(obj)


class frDirEnum(IntEnum):
    """对应 ``frBaseTypes.h`` 的 frDirEnum。"""

    UNKNOWN = 0
    D = 1
    S = 2
    W = 3
    E = 4
    N = 5
    U = 6


class frBlockObjectEnum(IntEnum):
    """对应 ``frBaseTypes.h`` 中常用的对象类型编号。"""

    frcNet = 0
    frcBTerm = 1
    frcMTerm = 2
    frcInst = 3
    frcVia = 4
    frcBPin = 5
    frcMPin = 6
    frcInstTerm = 7
    frcRect = 8
    frcPolygon = 9
    frcGuide = 12
    frcMarker = 20
    frcNode = 21
    grcNode = 28
    grcNet = 29
    grcPin = 30
    drcNet = 35
    drcPin = 36
    drcVia = 39
    gccNet = 44
    gccPin = 45


class RipUpMode(str, Enum):
    """对应 DR/GR searchRepair 使用的 RipUpMode。"""

    DRC = "DRC"
    ALL = "ALL"
    NEARDRC = "NEARDRC"
    INCR = "INCR"


class dbTechLayerDir(str, Enum):
    """轻量替代 OpenDB dbTechLayerDir；本轮不依赖 odb。"""

    NONE = "NONE"
    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"


class dbTechLayerType(str, Enum):
    """轻量替代 OpenDB dbTechLayerType；用于 frLayer 查询。"""

    ROUTING = "ROUTING"
    CUT = "CUT"
    MASTERSLICE = "MASTERSLICE"
    OTHER = "OTHER"


@dataclass
class RouterConfiguration:
    """对应 ``global.h`` 的 RouterConfiguration。

    字段名保留 C++ 大写形式，便于和源码逐项对照。这里仅保存配置，不解析
    tech/db，也不推导 routing layer 编号。
    """

    DBPROCESSNODE: str = ""
    OUT_MAZE_FILE: str = ""
    DRC_RPT_FILE: str = ""
    DRC_RPT_ITER_STEP: Optional[int] = None
    CMAP_FILE: str = ""
    GUIDE_REPORT_FILE: str = ""
    OR_SEED: int = -1
    OR_K: float = 0.0
    MAX_THREADS: int = 1
    BATCHSIZE: int = 1024
    BATCHSIZETA: int = 8
    MTSAFEDIST: int = 2000
    DRCSAFEDIST: int = 500
    VERBOSE: int = 1
    BOTTOM_ROUTING_LAYER_NAME: str = ""
    TOP_ROUTING_LAYER_NAME: str = ""
    BOTTOM_ROUTING_LAYER: int = 2
    TOP_ROUTING_LAYER: int = 2**31 - 1
    ALLOW_PIN_AS_FEEDTHROUGH: bool = True
    USENONPREFTRACKS: bool = True
    USEMINSPACING_OBS: bool = True
    ENABLE_BOUNDARY_MAR_FIX: bool = True
    ENABLE_VIA_GEN: bool = True
    CLEAN_PATCHES: bool = False
    DO_PA: bool = True
    SINGLE_STEP_DR: bool = False
    SAVE_GUIDE_UPDATES: bool = False
    VIAINPIN_BOTTOMLAYER_NAME: str = ""
    VIAINPIN_TOPLAYER_NAME: str = ""
    VIAINPIN_BOTTOMLAYERNUM: frLayerNum = 2**31 - 1
    VIAINPIN_TOPLAYERNUM: frLayerNum = 2**31 - 1
    VIA_ACCESS_LAYER_NAME: str = ""
    VIA_ACCESS_LAYERNUM: frLayerNum = 2
    MINNUMACCESSPOINT_MACROCELLPIN: int = 3
    MINNUMACCESSPOINT_STDCELLPIN: int = 3
    ACCESS_PATTERN_END_ITERATION_NUM: int = 10
    CONGESTION_THRESHOLD: float = 0.4
    MAX_CLIPSIZE_INCREASE: int = 18
    END_ITERATION: int = 80
    NDR_NETS_RIPUP_HARDINESS: int = 3
    CLOCK_NETS_TRUNK_RIPUP_HARDINESS: int = 100
    CLOCK_NETS_LEAF_RIPUP_HARDINESS: int = 10
    AUTO_TAPER_NDR_NETS: bool = True
    TAPERBOX_RADIUS: int = 3
    NDR_NETS_ABS_PRIORITY: int = 2
    CLOCK_NETS_ABS_PRIORITY: int = 4
    TAPINCOST: frUInt4 = 4
    TAALIGNCOST: frUInt4 = 4
    TADRCCOST: frUInt4 = 32
    TASHAPEBLOATWIDTH: float = 1.5
    VIACOST: frUInt4 = 4
    GRIDCOST: frUInt4 = 2
    ROUTESHAPECOST: frUInt4 = 8
    MARKERCOST: frUInt4 = 32
    MARKERBLOATWIDTH: frUInt4 = 1
    BLOCKCOST: frUInt4 = 32
    GUIDECOST: frUInt4 = 1
    SHAPEBLOATWIDTH: float = 3.0
    CONGCOST: int = 8
    HISTCOST: int = 32
    REPAIR_PDN_LAYER_NAME: str = ""
    REPAIR_PDN_LAYER_NUM: frLayerNum = -1
    GC_IGNORE_PDN_LAYER_NUM: frLayerNum = -1


@dataclass
class ParamStruct:
    """对应 ``TritonRoute.h`` 的 ParamStruct。

    Tcl/Python 入口通常先组装 ParamStruct，再由 TritonRoute.setParams 写入
    RouterConfiguration。本对象只做参数承载。
    """

    outputMazeFile: str = ""
    outputDrcFile: str = ""
    drcReportIterStep: Optional[int] = None
    outputCmapFile: str = ""
    outputGuideCoverageFile: str = ""
    dbProcessNode: str = ""
    enableViaGen: bool = False
    drouteEndIter: int = -1
    viaInPinBottomLayer: str = ""
    viaInPinTopLayer: str = ""
    viaAccessLayer: str = ""
    orSeed: int = 0
    orK: float = 0.0
    bottomRoutingLayer: str = ""
    topRoutingLayer: str = ""
    verbose: int = 1
    cleanPatches: bool = False
    doPa: bool = False
    singleStepDR: bool = False
    minAccessPoints: int = -1
    saveGuideUpdates: bool = False
    repairPDNLayerName: str = ""
    num_threads: int = 1


@dataclass
class frDebugSettings:
    """对应 OpenROAD drt 的 debug 设置结构。

    C++ 中多个 setDebug* 接口直接写这个结构；Python 端保留相同状态，供
    后续图形调试和 worker 重放翻译使用。
    """

    debugDR: bool = False
    debugDumpDR: bool = False
    debugMaze: bool = False
    debugPA: bool = False
    debugTA: bool = False
    writeNetTracks: bool = False
    dumpLastWorker: bool = False
    netName: str = ""
    pinName: str = ""
    box: Rect = (0, 0, 0, 0)
    iter: int = -1
    paMarkers: bool = False
    paEdge: bool = False
    paCommit: bool = False
    mazeEndIter: int = -1
    drcCost: int = -1
    markerCost: int = -1
    fixedShapeCost: int = -1
    markerDecay: float = -1.0
    ripupMode: int = -1
    followGuide: int = -1
    dumpDir: str = ""
    snapshotDir: str = ""


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


@dataclass
class FlexDRViaData:
    """对应 ``FlexDR.h`` 的 FlexDRViaData。"""

    halfViaEncArea: List[Tuple[frCoord, frCoord]] = field(default_factory=list)


@dataclass
class FlexDRSearchRepairArgs:
    """对应 ``FlexDR::SearchRepairArgs``。"""

    size: int
    offset: int
    mazeEndIter: int
    workerDRCCost: frUInt4
    workerMarkerCost: frUInt4
    workerFixedShapeCost: frUInt4
    workerMarkerDecay: float
    ripupMode: RipUpMode = RipUpMode.INCR
    followGuide: bool = True

    def isEqualIgnoringSizeAndOffset(self, other: "FlexDRSearchRepairArgs") -> bool:
        return (
            self.mazeEndIter == other.mazeEndIter
            and self.workerDRCCost == other.workerDRCCost
            and self.workerMarkerCost == other.workerMarkerCost
            and self.workerFixedShapeCost == other.workerFixedShapeCost
            and self.workerMarkerDecay == other.workerMarkerDecay
            and self.ripupMode == other.ripupMode
            and self.followGuide == other.followGuide
        )


class FlexDR:
    """对应 ``dr/FlexDR.h`` 的 detailed routing 顶层编排类。"""

    def __init__(
        self,
        router: Optional["TritonRoute"],
        design: frDesign,
        logger: Any = None,
        db: Any = None,
        router_cfg: Optional[RouterConfiguration] = None,
    ):
        self.router_ = router
        self.design_ = design
        self.logger_ = logger
        self.db_ = db
        self.router_cfg_ = router_cfg or RouterConfiguration()
        self.via_data_ = FlexDRViaData()
        self.graphics_: Optional[Any] = None
        self.iter_: int = 0
        self.numViols_: List[int] = []
        self.distributed_: Dict[str, Any] = {}

    def getTech(self) -> frTechObject:
        return self.design_.getTech()

    def getDesign(self) -> frDesign:
        return self.design_

    def getRegionQuery(self) -> frRegionQuery:
        return self.design_.getRegionQuery()

    def getViaData(self) -> FlexDRViaData:
        return self.via_data_

    def setDebug(self, dr_graphics: Any) -> None:
        self.graphics_ = dr_graphics

    def getGraphics(self) -> Any:
        return self.graphics_

    def setDistributed(self, dist: Any, remote_ip: str, remote_port: int, directory: str) -> None:
        self.distributed_ = {"dist": dist, "remote_ip": remote_ip, "remote_port": remote_port, "dir": directory}

    def incIter(self) -> None:
        self.iter_ += 1

    def init(self) -> None:
        _unsupported("FlexDR::init")

    def main(self) -> int:
        _unsupported("FlexDR::main")

    def searchRepair(self, args: FlexDRSearchRepairArgs) -> None:
        _unsupported("FlexDR::searchRepair")

    def end(self, done: bool = False) -> None:
        _unsupported("FlexDR::end")

    def reportGuideCoverage(self) -> None:
        _unsupported("FlexDR::reportGuideCoverage")

    def fixMaxSpacing(self) -> None:
        _unsupported("FlexDR::fixMaxSpacing")


class FlexGR:
    """对应 ``gr/FlexGR.h`` 的 global detailed routing 阶段。"""

    def __init__(
        self,
        design: frDesign,
        logger: Any = None,
        stt_builder: Any = None,
        router_cfg: Optional[RouterConfiguration] = None,
    ):
        self.db_: Optional[Any] = None
        self.design_ = design
        self.cmap_: Optional[Any] = None
        self.cmap2D_: Optional[Any] = None
        self.logger_ = logger
        self.stt_builder_ = stt_builder
        self.router_cfg_ = router_cfg or RouterConfiguration()

    def getTech(self) -> frTechObject:
        return self.design_.getTech()

    def getDesign(self) -> frDesign:
        return self.design_

    def getRegionQuery(self) -> frRegionQuery:
        return self.design_.getRegionQuery()

    def getCMap(self, is2DCMap: bool) -> Any:
        return self.cmap2D_ if is2DCMap else self.cmap_

    def main(self, db: Any = None) -> None:
        _unsupported("FlexGR::main")

    def init(self) -> None:
        _unsupported("FlexGR::init")

    def searchRepair(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGR::searchRepair")

    def layerAssign(self) -> None:
        _unsupported("FlexGR::layerAssign")

    def writeToGuide(self) -> None:
        _unsupported("FlexGR::writeToGuide")

    def updateDb(self) -> None:
        _unsupported("FlexGR::updateDb")


class FlexPA:
    """对应 ``pa/FlexPA.h`` 的 pin access 阶段。"""

    def __init__(self, design: frDesign, logger: Any = None, dist: Any = None, router_cfg: Optional[RouterConfiguration] = None):
        self.design_ = design
        self.logger_ = logger
        self.dist_ = dist
        self.router_cfg_ = router_cfg or RouterConfiguration()
        self.graphics_: Optional[Any] = None
        self.target_insts_: List[Any] = []
        self.remote_host_: str = ""
        self.remote_port_: int = -1
        self.shared_vol_: str = ""
        self.cloud_sz_: int = -1

    def setDebug(self, pa_graphics: Any) -> None:
        self.graphics_ = pa_graphics

    def setTargetInstances(self, insts: Iterable[Any]) -> None:
        self.target_insts_ = list(insts)

    def setDistributed(self, remote_host: str, remote_port: int, shared_vol: str, cloud_sz: int) -> None:
        self.remote_host_ = remote_host
        self.remote_port_ = remote_port
        self.shared_vol_ = shared_vol
        self.cloud_sz_ = cloud_sz

    def addInst(self, inst: Any) -> None:
        if inst not in self.target_insts_:
            self.target_insts_.append(inst)

    def deleteInst(self, inst: Any) -> None:
        if inst in self.target_insts_:
            self.target_insts_.remove(inst)

    def main(self) -> int:
        _unsupported("FlexPA::main")

    def init(self) -> None:
        _unsupported("FlexPA::init")

    def genAllAccessPoints(self) -> None:
        _unsupported("FlexPA::genAllAccessPoints")


class FlexGCWorker:
    """对应 ``gc/FlexGC.h`` 的 geometry checker worker。"""

    def __init__(
        self,
        tech: Optional[frTechObject] = None,
        logger: Any = None,
        router_cfg: Optional[RouterConfiguration] = None,
        dr_worker: Any = None,
    ):
        self.tech_ = tech or frTechObject()
        self.logger_ = logger
        self.router_cfg_ = router_cfg or RouterConfiguration()
        self.dr_worker_ = dr_worker
        self.ext_box_: Rect = (0, 0, 0, 0)
        self.drc_box_: Rect = (0, 0, 0, 0)
        self.target_net_: Optional[Any] = None
        self.target_objs_: Set[Any] = set()
        self.markers_: List[frMarker] = []
        self.pwires_: List[Any] = []
        self.ignore_db_: bool = False
        self.ignore_min_area_: bool = False

    def setExtBox(self, box: Rect) -> None:
        self.ext_box_ = box

    def setDrcBox(self, box: Rect) -> None:
        self.drc_box_ = box

    def setTargetNet(self, net: Any) -> bool:
        self.target_net_ = net
        return True

    def getTargetNet(self) -> Any:
        return self.target_net_

    def resetTargetNet(self) -> None:
        self.target_net_ = None

    def addTargetObj(self, obj: Any) -> None:
        self.target_objs_.add(obj)

    def setTargetObjs(self, objs: Iterable[Any]) -> None:
        self.target_objs_ = set(objs)

    def setIgnoreDB(self) -> None:
        self.ignore_db_ = True

    def setIgnoreMinArea(self) -> None:
        self.ignore_min_area_ = True

    def getMarkers(self) -> List[frMarker]:
        return self.markers_

    def getPWires(self) -> List[Any]:
        return self.pwires_

    def init(self, design: frDesign) -> None:
        _unsupported("FlexGCWorker::init")

    def main(self) -> int:
        _unsupported("FlexGCWorker::main")

    def updateDRNet(self, net: Any) -> None:
        _unsupported("FlexGCWorker::updateDRNet")


class TritonRoute:
    """对应 ``include/triton_route/TritonRoute.h`` 的 drt 顶层模块。"""

    def __init__(self):
        self.design_: Optional[frDesign] = None
        self.debug_ = frDebugSettings()
        self.router_cfg_ = RouterConfiguration()
        self.db_: Optional[Any] = None
        self.logger_: Optional[Any] = None
        self.dist_: Optional[Any] = None
        self.stt_builder_: Optional[Any] = None
        self.num_drvs_: int = -1
        self.distributed_: bool = False
        self.dist_ip_: str = ""
        self.dist_port_: int = 0
        self.shared_volume_: str = ""
        self.workers_results_: List[Tuple[int, str]] = []
        self.results_sz_: int = 0
        self.cloud_sz_: int = 0
        self.dr_: Optional[FlexDR] = None
        self.pa_: Optional[FlexPA] = None
        self.graphics_factory_: Optional[Any] = None

    def init(self, db: Any = None, logger: Any = None, dist: Any = None, stt_builder: Any = None, graphics_factory: Any = None) -> None:
        """初始化顶层指针并创建空 frDesign；不从 odb 导入数据。"""

        self.db_ = db
        self.logger_ = logger
        self.dist_ = dist
        self.stt_builder_ = stt_builder
        self.graphics_factory_ = graphics_factory
        self.design_ = frDesign(logger, self.router_cfg_)

    def getDesign(self) -> Optional[frDesign]:
        return self.design_

    def getLogger(self) -> Any:
        return self.logger_

    def getRouterConfiguration(self) -> RouterConfiguration:
        return self.router_cfg_

    def getDb(self) -> Any:
        return self.db_

    def getDebugSettings(self) -> frDebugSettings:
        return self.debug_

    def setParams(self, params: ParamStruct) -> None:
        """按 C++ setParams 的职责写入 RouterConfiguration。"""

        self.router_cfg_.OUT_MAZE_FILE = params.outputMazeFile
        self.router_cfg_.DRC_RPT_FILE = params.outputDrcFile
        self.router_cfg_.DRC_RPT_ITER_STEP = params.drcReportIterStep
        self.router_cfg_.CMAP_FILE = params.outputCmapFile
        self.router_cfg_.GUIDE_REPORT_FILE = params.outputGuideCoverageFile
        self.router_cfg_.DBPROCESSNODE = params.dbProcessNode
        self.router_cfg_.ENABLE_VIA_GEN = params.enableViaGen
        if params.drouteEndIter >= 0:
            self.router_cfg_.END_ITERATION = params.drouteEndIter
        self.router_cfg_.VIAINPIN_BOTTOMLAYER_NAME = params.viaInPinBottomLayer
        self.router_cfg_.VIAINPIN_TOPLAYER_NAME = params.viaInPinTopLayer
        self.router_cfg_.VIA_ACCESS_LAYER_NAME = params.viaAccessLayer
        self.router_cfg_.OR_SEED = params.orSeed
        self.router_cfg_.OR_K = params.orK
        self.router_cfg_.BOTTOM_ROUTING_LAYER_NAME = params.bottomRoutingLayer
        self.router_cfg_.TOP_ROUTING_LAYER_NAME = params.topRoutingLayer
        self.router_cfg_.VERBOSE = params.verbose
        self.router_cfg_.CLEAN_PATCHES = params.cleanPatches
        self.router_cfg_.DO_PA = params.doPa
        self.router_cfg_.SINGLE_STEP_DR = params.singleStepDR
        self.router_cfg_.SAVE_GUIDE_UPDATES = params.saveGuideUpdates
        self.router_cfg_.REPAIR_PDN_LAYER_NAME = params.repairPDNLayerName
        self.router_cfg_.MAX_THREADS = max(1, params.num_threads)
        if params.minAccessPoints >= 0:
            self.router_cfg_.MINNUMACCESSPOINT_MACROCELLPIN = params.minAccessPoints
            self.router_cfg_.MINNUMACCESSPOINT_STDCELLPIN = params.minAccessPoints

    def addUserSelectedVia(self, via_name: str) -> None:
        if self.design_ is None:
            self.design_ = frDesign(self.logger_, self.router_cfg_)
        self.design_.addUserSelectedVia(via_name)

    def setUnidirectionalLayer(self, layer_name: str) -> None:
        if self.design_ is None:
            return
        for layer in self.design_.getTech().getLayers():
            if layer.getName() == layer_name:
                layer.unidirectional = True
                return

    def setDebugDR(self, on: bool = True) -> None:
        self.debug_.debugDR = on

    def setDebugDumpDR(self, on: bool, dumpDir: str) -> None:
        self.debug_.debugDumpDR = on
        self.debug_.dumpDir = dumpDir

    def setDebugSnapshotDir(self, snapshotDir: str) -> None:
        self.debug_.snapshotDir = snapshotDir

    def setDebugMaze(self, on: bool = True) -> None:
        self.debug_.debugMaze = on

    def setDebugPA(self, on: bool = True) -> None:
        self.debug_.debugPA = on

    def setDebugTA(self, on: bool = True) -> None:
        self.debug_.debugTA = on

    def setDebugWriteNetTracks(self, on: bool = True) -> None:
        self.debug_.writeNetTracks = on

    def setDebugNetName(self, name: str) -> None:
        self.debug_.netName = name

    def setDebugPinName(self, name: str) -> None:
        self.debug_.pinName = name

    def setDebugBox(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.debug_.box = (x1, y1, x2, y2)

    def setDebugIter(self, iter_num: int) -> None:
        self.debug_.iter = iter_num

    def setDebugPaMarkers(self, on: bool = True) -> None:
        self.debug_.paMarkers = on

    def setDebugPaEdge(self, on: bool = True) -> None:
        self.debug_.paEdge = on

    def setDebugPaCommit(self, on: bool = True) -> None:
        self.debug_.paCommit = on

    def setDumpLastWorker(self, on: bool = True) -> None:
        self.debug_.dumpLastWorker = on

    def setDebugWorkerParams(
        self,
        mazeEndIter: int,
        drcCost: int,
        markerCost: int,
        fixedShapeCost: int,
        markerDecay: float,
        ripupMode: int,
        followGuide: int,
    ) -> None:
        self.debug_.mazeEndIter = mazeEndIter
        self.debug_.drcCost = drcCost
        self.debug_.markerCost = markerCost
        self.debug_.fixedShapeCost = fixedShapeCost
        self.debug_.markerDecay = markerDecay
        self.debug_.ripupMode = ripupMode
        self.debug_.followGuide = followGuide

    def setDistributed(self, on: bool = True) -> None:
        self.distributed_ = on

    def setWorkerIpPort(self, ip: str, port: int) -> None:
        self.dist_ip_ = ip
        self.dist_port_ = port

    def setSharedVolume(self, volume: str) -> None:
        self.shared_volume_ = volume
        if self.shared_volume_ and not self.shared_volume_.endswith("/"):
            self.shared_volume_ += "/"

    def setCloudSize(self, cloud_sz: int) -> None:
        self.cloud_sz_ = cloud_sz

    def getCloudSize(self) -> int:
        return self.cloud_sz_

    def getNumDRVs(self) -> int:
        if self.num_drvs_ < 0:
            raise RuntimeError("Detailed routing has not been run yet.")
        return self.num_drvs_

    def addWorkerResults(self, results: Sequence[Tuple[int, str]]) -> None:
        self.workers_results_.extend(results)
        self.results_sz_ = len(self.workers_results_)

    def getWorkerResults(self) -> List[Tuple[int, str]]:
        results = list(self.workers_results_)
        self.workers_results_.clear()
        self.results_sz_ = 0
        return results

    def getWorkerResultsSize(self) -> int:
        return self.results_sz_

    def clearDesign(self) -> None:
        self.design_ = None
        self.dr_ = None
        self.pa_ = None
        self.num_drvs_ = -1

    def initGuide(self) -> bool:
        _unsupported("TritonRoute::initGuide")

    def prep(self) -> None:
        _unsupported("TritonRoute::prep")

    def main(self) -> int:
        _unsupported("TritonRoute::main")

    def endFR(self) -> None:
        _unsupported("TritonRoute::endFR")

    def pinAccess(self, target_insts: Optional[Sequence[Any]] = None) -> None:
        _unsupported("TritonRoute::pinAccess")

    def stepDR(
        self,
        size: int,
        offset: int,
        mazeEndIter: int,
        workerDRCCost: int,
        workerMarkerCost: int,
        workerFixedShapeCost: int,
        workerMarkerDecay: float,
        ripupMode: int,
        followGuide: bool,
    ) -> None:
        _unsupported("TritonRoute::stepDR")

    def gr(self) -> None:
        _unsupported("TritonRoute::gr")

    def ta(self) -> None:
        _unsupported("TritonRoute::ta")

    def dr(self) -> None:
        _unsupported("TritonRoute::dr")

    def checkDRC(self, filename: str, x1: int, y1: int, x2: int, y2: int, marker_name: str, num_threads: int) -> None:
        _unsupported("TritonRoute::checkDRC")

    def reportDRC(
        self,
        file_name: str,
        markers: Sequence[frMarker],
        marker_name: str,
        drcBox: Rect = (0, 0, 0, 0),
    ) -> None:
        _unsupported("TritonRoute::reportDRC")

    def reportConstraints(self) -> None:
        _unsupported("TritonRoute::reportConstraints")

    def routeLayerLengths(self, wire: Any) -> List[int]:
        _unsupported("TritonRoute::routeLayerLengths")

    def runDRWorker(self, workerStr: str, viaData: Optional[FlexDRViaData] = None) -> str:
        _unsupported("TritonRoute::runDRWorker")

    def debugSingleWorker(self, dumpDir: str, drcRpt: str) -> None:
        _unsupported("TritonRoute::debugSingleWorker")

    def updateGlobals(self, file_name: str) -> None:
        _unsupported("TritonRoute::updateGlobals")

    def resetDb(self, file_name: str) -> None:
        _unsupported("TritonRoute::resetDb")

    def updateDesign(self, updates_or_path: Any, num_threads: int) -> None:
        _unsupported("TritonRoute::updateDesign")

    def sendDesignDist(self) -> None:
        _unsupported("TritonRoute::sendDesignDist")

    def writeGlobals(self, name: str) -> bool:
        _unsupported("TritonRoute::writeGlobals")

    def sendDesignUpdates(self, router_cfg_path: str, num_threads: int) -> None:
        _unsupported("TritonRoute::sendDesignUpdates")

    def sendGlobalsUpdates(self, router_cfg_path: str, serializedViaData: str) -> None:
        _unsupported("TritonRoute::sendGlobalsUpdates")

    def fixMaxSpacing(self, num_threads: int) -> None:
        _unsupported("TritonRoute::fixMaxSpacing")

    def deleteInstancePAData(self, inst: Any) -> None:
        _unsupported("TritonRoute::deleteInstancePAData")

    def addInstancePAData(self, inst: Any) -> None:
        _unsupported("TritonRoute::addInstancePAData")


def create_triton_route() -> TritonRoute:
    """创建 drt 顶层入口对象，类似 C++ MakeTritonRoute 工厂。"""

    return TritonRoute()


__all__ = [
    "FlexDR",
    "FlexDRSearchRepairArgs",
    "FlexDRViaData",
    "FlexGCWorker",
    "FlexGR",
    "FlexGridGraph",
    "FlexGridGraphNode",
    "FlexMazeIdx",
    "FlexPA",
    "ParamStruct",
    "Point",
    "Rect",
    "RipUpMode",
    "RouterConfiguration",
    "TritonRoute",
    "create_triton_route",
    "dbTechLayerDir",
    "dbTechLayerType",
    "frBlock",
    "frBlockObjectEnum",
    "frCoord",
    "frDebugSettings",
    "frDesign",
    "frDirEnum",
    "frGuide",
    "frLayer",
    "frLayerNum",
    "frMarker",
    "frNet",
    "frNode",
    "frRegionQuery",
    "frShape",
    "frTechObject",
    "frUInt4",
    "frVia",
    "frViaDef",
]
