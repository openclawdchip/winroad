"""Shared lightweight types and configuration for the drt package."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum, IntEnum
from typing import Any, Optional, Tuple

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

    def update(self, **values: Any) -> None:
        """Update known configuration fields in place."""

        for name, value in values.items():
            if not hasattr(self, name):
                raise AttributeError(f"Unknown RouterConfiguration field: {name}")
            setattr(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable snapshot of the current router configuration."""

        return asdict(self)

    def copy(self) -> "RouterConfiguration":
        """Return an independent configuration object with the same values."""

        return RouterConfiguration(**self.to_dict())


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

__all__ = [
    "ParamStruct",
    "Point",
    "Rect",
    "RipUpMode",
    "RouterConfiguration",
    "dbTechLayerDir",
    "dbTechLayerType",
    "frBlockObjectEnum",
    "frCoord",
    "frDebugSettings",
    "frDirEnum",
    "frLayerNum",
    "frMIdx",
    "frUInt4",
]
