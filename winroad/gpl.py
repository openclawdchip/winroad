"""OpenROAD gpl 全局布局模块的 Python 翻译骨架。

本文件按 OpenROAD `src/gpl` 的源码边界建立 Python 对象：

- `Replace` 是 gpl 顶层入口，对应 `gpl::Replace`。
- `PlacerBase*` 保存 OpenDB 到布局内部对象的映射。
- `InitialPlace`、`NesterovPlace`、`RouteBase`、`TimingBase`
  保留 C++ 入口类与关键函数边界。

这里不做估算 demo，也不发明新架构。尚未翻译的 C++ 数值求解、
RUDY/GR 交互、STA/resize 交互会显式抛出 `NotImplementedError`，
保证后续继续翻译时边界清楚。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .odb import DbDatabase, DbInst, DbNet, PlacementStatus, SigType


Rect = Tuple[int, int, int, int]
Cluster = List[DbInst]
Clusters = List[Cluster]


def _area(rect: Rect) -> int:
    """矩形面积工具，坐标顺序与 OpenDB Rect 一致：lx, ly, ux, uy。"""

    lx, ly, ux, uy = rect
    return max(0, ux - lx) * max(0, uy - ly)


def _center(rect: Rect) -> Tuple[int, int]:
    """返回矩形中心。"""

    lx, ly, ux, uy = rect
    return (lx + ux) // 2, (ly + uy) // 2


def _get_block(db: Optional[DbDatabase]) -> Any:
    """兼容当前 WinRoad ODB 骨架，取得顶层 block。"""

    if db is None or db.chip is None:
        return None
    if hasattr(db.chip, "get_top_block"):
        return db.chip.get_top_block()
    top = getattr(db.chip, "top", None)
    return getattr(db.chip, "blocks", {}).get(top) if top is not None else None


def _iter_block_insts(block: Any) -> List[DbInst]:
    """以 OpenDB `block->getInsts()` 的语义遍历实例。"""

    if block is None:
        return []
    insts = getattr(block, "insts", {})
    if isinstance(insts, dict):
        return list(insts.values())
    return list(insts)


def _iter_block_nets(block: Any) -> List[DbNet]:
    """以 OpenDB `block->getNets()` 的语义遍历线网。"""

    if block is None:
        return []
    nets = getattr(block, "nets", {})
    if isinstance(nets, dict):
        return list(nets.values())
    return list(nets)


def _inst_rect(inst: DbInst) -> Rect:
    """从 DbInst 取得实例矩形；没有 bbox 时退化到原点零面积。"""

    if getattr(inst, "bbox", None) is not None:
        return inst.bbox  # type: ignore[return-value]
    return (inst.x, inst.y, inst.x, inst.y)


def _db_inst_set_origin(inst: DbInst, x: int, y: int) -> None:
    """兼容 DbInst 的 set_origin，同时保持 bbox 平移。"""

    old_x, old_y = inst.x, inst.y
    if getattr(inst, "bbox", None) is not None:
        lx, ly, ux, uy = inst.bbox  # type: ignore[misc]
        inst.bbox = (x, y, x + (ux - lx), y + (uy - ly))
    if hasattr(inst, "set_origin"):
        inst.set_origin(x, y)
    else:
        inst.x = x
        inst.y = y
    if getattr(inst, "bbox", None) is None and (old_x, old_y) != (x, y):
        inst.x = x
        inst.y = y


@dataclass
class FloatPoint:
    """对应 `gpl::FloatPoint`。"""

    x: float = 0.0
    y: float = 0.0


@dataclass
class PlaceOptions:
    """对应 `gpl::PlaceOptions`，保留 C++ 默认值和字段名。"""

    initialPlaceMaxIter: int = 20
    initialPlaceMinDiffLength: int = 1500
    initialPlaceMaxSolverIter: int = 100
    initialPlaceMaxFanout: int = 200
    initialPlaceNetWeightScale: float = 800.0
    skipIoMode: bool = False
    forceCenterInitialPlace: bool = False
    timingDrivenMode: bool = False
    routabilityDrivenMode: bool = False
    uniformTargetDensityMode: bool = False
    timingNetWeightOverflows: List[int] = field(default_factory=lambda: [64, 20])
    timingNetWeightMax: float = 5.0
    overflow: float = 0.1
    nesterovPlaceMaxIter: int = 5000
    keepResizeBelowOverflow: float = 1.0
    routabilityUseRudy: bool = True
    disableRevertIfDiverge: bool = False
    disablePinDensityAdjust: bool = False
    enable_routing_congestion: bool = False
    minPhiCoef: float = 0.95
    maxPhiCoef: float = 1.05
    initDensityPenaltyFactor: float = 0.00008
    initWireLengthCoef: float = 0.25
    referenceHpwl: float = 446000000.0
    binGridCntX: int = 0
    binGridCntY: int = 0
    density: float = 0.7
    routabilityCheckOverflow: float = 0.3
    routabilitySnapshotOverflow: float = 0.6
    routabilityMaxDensity: float = 0.99
    routabilityTargetRcMetric: float = 1.01
    routabilityInflationRatioCoef: float = 2.0
    routabilityMaxInflationRatio: float = 3.0
    routabilityRcK1: float = 1.0
    routabilityRcK2: float = 1.0
    routabilityRcK3: float = 0.0
    routabilityRcK4: float = 0.0
    padLeft: int = 0
    padRight: int = 0

    def skipIo(self) -> None:
        """对应 `PlaceOptions::skipIo()`。"""

        self.skipIoMode = True
        self.initialPlaceMaxIter = 0
        self.timingDrivenMode = False
        self.routabilityDrivenMode = False

    def validate(self, logger: Any = None) -> None:
        """对应 `PlaceOptions::validate()` 的 Python 检查。"""

        if self.initialPlaceMaxIter < 0:
            raise ValueError("initialPlaceMaxIter must be non-negative")
        if self.initialPlaceMaxFanout <= 0:
            raise ValueError("initialPlaceMaxFanout must be positive")
        if not 0.0 <= self.density <= 1.0:
            raise ValueError("Target density must be in [0.0, 1.0]")


@dataclass
class PlacerBaseVars:
    """对应 `gpl::PlacerBaseVars`。"""

    padLeft: int
    padRight: int
    skipIoMode: bool
    disablePinDensityAdjust: bool

    @classmethod
    def from_options(cls, options: PlaceOptions) -> "PlacerBaseVars":
        return cls(
            padLeft=options.padLeft,
            padRight=options.padRight,
            skipIoMode=options.skipIoMode,
            disablePinDensityAdjust=options.disablePinDensityAdjust,
        )


@dataclass
class InitialPlaceVars:
    """对应 `gpl::InitialPlaceVars`。"""

    maxIter: int
    minDiffLength: int
    maxSolverIter: int
    maxFanout: int
    netWeightScale: float
    debug: bool
    forceCenter: bool

    @classmethod
    def from_options(cls, options: PlaceOptions, debug: bool) -> "InitialPlaceVars":
        return cls(
            maxIter=options.initialPlaceMaxIter,
            minDiffLength=options.initialPlaceMinDiffLength,
            maxSolverIter=options.initialPlaceMaxSolverIter,
            maxFanout=options.initialPlaceMaxFanout,
            netWeightScale=options.initialPlaceNetWeightScale,
            debug=debug,
            forceCenter=options.forceCenterInitialPlace,
        )


@dataclass
class NesterovBaseVars:
    """对应 `gpl::NesterovBaseVars`。"""

    isSetBinCnt: bool
    useUniformTargetDensity: bool
    targetDensity: float
    binCntX: int
    binCntY: int
    minPhiCoef: float
    maxPhiCoef: float
    isMaxPhiCoefChanged: bool = False
    minWireLengthForceBar: float = -300.0

    @classmethod
    def from_options(cls, options: PlaceOptions) -> "NesterovBaseVars":
        return cls(
            isSetBinCnt=options.binGridCntX > 0 and options.binGridCntY > 0,
            useUniformTargetDensity=options.uniformTargetDensityMode,
            targetDensity=options.density,
            binCntX=options.binGridCntX,
            binCntY=options.binGridCntY,
            minPhiCoef=options.minPhiCoef,
            maxPhiCoef=options.maxPhiCoef,
        )


@dataclass
class NesterovPlaceVars:
    """对应 `gpl::NesterovPlaceVars`。"""

    maxNesterovIter: int
    initDensityPenalty: float
    initWireLengthCoef: float
    targetOverflow: float
    referenceHpwl: float
    routability_end_overflow: float
    routability_snapshot_overflow: float
    keepResizeBelowOverflow: float
    timingDrivenMode: bool
    routability_driven_mode: bool
    disableRevertIfDiverge: bool
    debug: bool = False
    debug_pause_iterations: int = 10
    debug_update_iterations: int = 10
    debug_draw_bins: bool = True
    debug_inst: Optional[DbInst] = None
    debug_start_iter: int = 0
    debug_rudy_start: int = 5000
    debug_rudy_stride: int = 1
    debug_generate_images: bool = False
    debug_images_path: str = "REPORTS_DIR"
    timingDrivenIterCounter: int = 0
    maxBackTrack: int = 10
    minPreconditioner: float = 1.0
    initialPrevCoordiUpdateCoef: float = 100.0
    maxRecursionWlCoef: int = 10
    maxRecursionInitSLPCoef: int = 10

    @classmethod
    def from_options(cls, options: PlaceOptions) -> "NesterovPlaceVars":
        return cls(
            maxNesterovIter=options.nesterovPlaceMaxIter,
            initDensityPenalty=options.initDensityPenaltyFactor,
            initWireLengthCoef=options.initWireLengthCoef,
            targetOverflow=options.overflow,
            referenceHpwl=options.referenceHpwl,
            routability_end_overflow=options.routabilityCheckOverflow,
            routability_snapshot_overflow=options.routabilitySnapshotOverflow,
            keepResizeBelowOverflow=options.keepResizeBelowOverflow,
            timingDrivenMode=options.timingDrivenMode,
            routability_driven_mode=options.routabilityDrivenMode,
            disableRevertIfDiverge=options.disableRevertIfDiverge,
        )


@dataclass
class RouteBaseVars:
    """对应 `gpl::RouteBaseVars`。"""

    useRudy: bool
    targetRC: float
    inflationRatioCoef: float
    maxInflationRatio: float
    maxDensity: float
    ignoreEdgeRatio: float = 0.0
    minInflationRatio: float = 1.0
    rcK1: float = 1.0
    rcK2: float = 1.0
    rcK3: float = 0.0
    rcK4: float = 0.0

    @classmethod
    def from_options(cls, options: PlaceOptions) -> "RouteBaseVars":
        return cls(
            useRudy=options.routabilityUseRudy,
            targetRC=options.routabilityTargetRcMetric,
            inflationRatioCoef=options.routabilityInflationRatioCoef,
            maxInflationRatio=options.routabilityMaxInflationRatio,
            maxDensity=options.routabilityMaxDensity,
            rcK1=options.routabilityRcK1,
            rcK2=options.routabilityRcK2,
            rcK3=options.routabilityRcK3,
            rcK4=options.routabilityRcK4,
        )


@dataclass
class Die:
    """对应 `gpl::Die`，保存 die/core 矩形及派生尺寸。"""

    dieLx_: int = 0
    dieLy_: int = 0
    dieUx_: int = 0
    dieUy_: int = 0
    coreLx_: int = 0
    coreLy_: int = 0
    coreUx_: int = 0
    coreUy_: int = 0

    @classmethod
    def from_rects(cls, die_rect: Rect, core_rect: Optional[Rect] = None) -> "Die":
        die = cls()
        die.setDieBox(die_rect)
        die.setCoreBox(core_rect if core_rect is not None else die_rect)
        return die

    def setDieBox(self, dieRect: Rect) -> None:
        self.dieLx_, self.dieLy_, self.dieUx_, self.dieUy_ = dieRect

    def setCoreBox(self, coreRect: Rect) -> None:
        self.coreLx_, self.coreLy_, self.coreUx_, self.coreUy_ = coreRect

    def dieLx(self) -> int:
        return self.dieLx_

    def dieLy(self) -> int:
        return self.dieLy_

    def dieUx(self) -> int:
        return self.dieUx_

    def dieUy(self) -> int:
        return self.dieUy_

    def coreLx(self) -> int:
        return self.coreLx_

    def coreLy(self) -> int:
        return self.coreLy_

    def coreUx(self) -> int:
        return self.coreUx_

    def coreUy(self) -> int:
        return self.coreUy_

    def dieCx(self) -> int:
        return (self.dieLx_ + self.dieUx_) // 2

    def dieCy(self) -> int:
        return (self.dieLy_ + self.dieUy_) // 2

    def dieDx(self) -> int:
        return self.dieUx_ - self.dieLx_

    def dieDy(self) -> int:
        return self.dieUy_ - self.dieLy_

    def coreCx(self) -> int:
        return (self.coreLx_ + self.coreUx_) // 2

    def coreCy(self) -> int:
        return (self.coreLy_ + self.coreUy_) // 2

    def coreDx(self) -> int:
        return self.coreUx_ - self.coreLx_

    def coreDy(self) -> int:
        return self.coreUy_ - self.coreLy_

    def dieArea(self) -> int:
        return _area((self.dieLx_, self.dieLy_, self.dieUx_, self.dieUy_))

    def coreArea(self) -> int:
        return _area((self.coreLx_, self.coreLy_, self.coreUx_, self.coreUy_))


@dataclass
class Instance:
    """对应 `gpl::Instance`，包装 OpenDB 实例或 dummy instance。"""

    inst_: Optional[DbInst] = None
    lx_: int = 0
    ly_: int = 0
    ux_: int = 0
    uy_: int = 0
    extId_: int = -(2**31)
    is_macro_: bool = False
    is_locked_: bool = False
    pins_: List["Pin"] = field(default_factory=list)

    @classmethod
    def from_db(cls, inst: DbInst) -> "Instance":
        lx, ly, ux, uy = _inst_rect(inst)
        obj = cls(inst_=inst, lx_=lx, ly_=ly, ux_=ux, uy_=uy)
        obj.is_macro_ = bool((ux - lx) and (uy - ly) and getattr(inst, "physical_only", False))
        return obj

    @classmethod
    def dummy(cls, lx: int, ly: int, ux: int, uy: int) -> "Instance":
        return cls(inst_=None, lx_=lx, ly_=ly, ux_=ux, uy_=uy)

    def dbInst(self) -> Optional[DbInst]:
        return self.inst_

    def isFixed(self) -> bool:
        return bool(self.inst_ and self.inst_.status in {PlacementStatus.FIXED, PlacementStatus.COVER, PlacementStatus.LOCKED})

    def isInstance(self) -> bool:
        return self.inst_ is not None

    def isPlaceInstance(self) -> bool:
        return self.isInstance() and not self.isFixed() and not self.is_locked_

    def isMacro(self) -> bool:
        return self.is_macro_

    def isLocked(self) -> bool:
        return self.is_locked_

    def lock(self) -> None:
        self.is_locked_ = True

    def unlock(self) -> None:
        self.is_locked_ = False

    def isDummy(self) -> bool:
        return self.inst_ is None

    def copyDbLocation(self, pbc: Optional["PlacerBaseCommon"] = None) -> None:
        if self.inst_ is None:
            return
        self.lx_, self.ly_, self.ux_, self.uy_ = _inst_rect(self.inst_)

    def setLocation(self, x: int, y: int) -> None:
        dx, dy = self.dx(), self.dy()
        self.lx_, self.ly_, self.ux_, self.uy_ = x, y, x + dx, y + dy

    def setCenterLocation(self, x: int, y: int) -> None:
        self.setLocation(x - self.dx() // 2, y - self.dy() // 2)

    def dbSetPlaced(self) -> None:
        if self.inst_ is not None:
            self.inst_.status = PlacementStatus.PLACED

    def dbSetPlacementStatus(self, ps: PlacementStatus) -> None:
        if self.inst_ is not None:
            self.inst_.status = ps

    def dbSetLocation(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        if x is not None and y is not None:
            self.setLocation(x, y)
        if self.inst_ is not None:
            _db_inst_set_origin(self.inst_, self.lx_, self.ly_)

    def dbSetCenterLocation(self, x: int, y: int) -> None:
        self.setCenterLocation(x, y)
        self.dbSetLocation()

    def lx(self) -> int:
        return self.lx_

    def ly(self) -> int:
        return self.ly_

    def ux(self) -> int:
        return self.ux_

    def uy(self) -> int:
        return self.uy_

    def cx(self) -> int:
        return (self.lx_ + self.ux_) // 2

    def cy(self) -> int:
        return (self.ly_ + self.uy_) // 2

    def dx(self) -> int:
        return self.ux_ - self.lx_

    def dy(self) -> int:
        return self.uy_ - self.ly_

    def getArea(self) -> int:
        return _area((self.lx_, self.ly_, self.ux_, self.uy_))

    def setExtId(self, extId: int) -> None:
        self.extId_ = extId

    def getExtId(self) -> int:
        return self.extId_

    def addPin(self, pin: "Pin") -> None:
        self.pins_.append(pin)

    def getPins(self) -> List["Pin"]:
        return self.pins_

    def snapOutward(self, origin: Tuple[int, int], step_x: int, step_y: int) -> None:
        """对应 C++ snapOutward，按 site 网格向外扩展到合法坐标。"""

        ox, oy = origin
        if step_x > 0:
            self.lx_ = ox + ((self.lx_ - ox) // step_x) * step_x
            self.ux_ = ox + ((self.ux_ - ox + step_x - 1) // step_x) * step_x
        if step_y > 0:
            self.ly_ = oy + ((self.ly_ - oy) // step_y) * step_y
            self.uy_ = oy + ((self.uy_ - oy + step_y - 1) // step_y) * step_y

    def extendSizeByScale(self, scale: float, logger: Any = None) -> int:
        """按 C++ 语义膨胀实例尺寸，返回面积增量。"""

        old_area = self.getArea()
        cx, cy = self.cx(), self.cy()
        new_dx = int(round(self.dx() * scale))
        new_dy = int(round(self.dy() * scale))
        self.lx_ = cx - new_dx // 2
        self.ly_ = cy - new_dy // 2
        self.ux_ = self.lx_ + new_dx
        self.uy_ = self.ly_ + new_dy
        return self.getArea() - old_area


@dataclass
class Pin:
    """对应 `gpl::Pin`，保存 ITerm/BTerm 的布局中心与实例/线网关系。"""

    term_: Any = None
    inst_: Optional[Instance] = None
    net_: Optional["Net"] = None
    cx_: int = 0
    cy_: int = 0
    offsetCx_: int = 0
    offsetCy_: int = 0
    iTermField_: bool = False
    bTermField_: bool = False
    minPinXField_: bool = False
    minPinYField_: bool = False
    maxPinXField_: bool = False
    maxPinYField_: bool = False

    def getDbITerm(self) -> Any:
        return self.term_ if self.iTermField_ else None

    def getDbBTerm(self) -> Any:
        return self.term_ if self.bTermField_ else None

    def isITerm(self) -> bool:
        return self.iTermField_

    def isBTerm(self) -> bool:
        return self.bTermField_

    def isMinPinX(self) -> bool:
        return self.minPinXField_

    def isMaxPinX(self) -> bool:
        return self.maxPinXField_

    def isMinPinY(self) -> bool:
        return self.minPinYField_

    def isMaxPinY(self) -> bool:
        return self.maxPinYField_

    def setITerm(self) -> None:
        self.iTermField_, self.bTermField_ = True, False

    def setBTerm(self) -> None:
        self.bTermField_, self.iTermField_ = True, False

    def setMinPinX(self) -> None:
        self.minPinXField_ = True

    def setMinPinY(self) -> None:
        self.minPinYField_ = True

    def setMaxPinX(self) -> None:
        self.maxPinXField_ = True

    def setMaxPinY(self) -> None:
        self.maxPinYField_ = True

    def unsetMinPinX(self) -> None:
        self.minPinXField_ = False

    def unsetMinPinY(self) -> None:
        self.minPinYField_ = False

    def unsetMaxPinX(self) -> None:
        self.maxPinXField_ = False

    def unsetMaxPinY(self) -> None:
        self.maxPinYField_ = False

    def cx(self) -> int:
        return self.cx_

    def cy(self) -> int:
        return self.cy_

    def getOffsetCx(self) -> int:
        return self.offsetCx_

    def getOffsetCy(self) -> int:
        return self.offsetCy_

    def updateLocation(self, inst: Optional[Instance] = None) -> None:
        if inst is not None:
            self.inst_ = inst
        if self.inst_ is not None:
            self.cx_ = self.inst_.cx() + self.offsetCx_
            self.cy_ = self.inst_.cy() + self.offsetCy_

    def setInstance(self, inst: Instance) -> None:
        self.inst_ = inst

    def setNet(self, net: "Net") -> None:
        self.net_ = net

    def isPlaceInstConnected(self) -> bool:
        return bool(self.inst_ and self.inst_.isPlaceInstance())

    def getInstance(self) -> Optional[Instance]:
        return self.inst_

    def getNet(self) -> Optional["Net"]:
        return self.net_

    def getName(self) -> str:
        return getattr(self.term_, "name", str(self.term_))

    def updateCoordi(self, term: Any = None) -> None:
        if term is not None:
            self.term_ = term
        self.updateLocation()


@dataclass
class Net:
    """对应 `gpl::Net`，保存布局 pin 集合和 HPWL bbox。"""

    net_: Optional[DbNet] = None
    pins_: List[Pin] = field(default_factory=list)
    lx_: int = 0
    ly_: int = 0
    ux_: int = 0
    uy_: int = 0
    skipIoMode: bool = False

    def lx(self) -> int:
        return self.lx_

    def ly(self) -> int:
        return self.ly_

    def ux(self) -> int:
        return self.ux_

    def uy(self) -> int:
        return self.uy_

    def cx(self) -> int:
        return (self.lx_ + self.ux_) // 2

    def cy(self) -> int:
        return (self.ly_ + self.uy_) // 2

    def getHpwl(self) -> int:
        self.updateBox(self.skipIoMode)
        return max(0, self.ux_ - self.lx_) + max(0, self.uy_ - self.ly_)

    def updateBox(self, skipIoMode: bool = False) -> None:
        pins = [pin for pin in self.pins_ if not (skipIoMode and pin.isBTerm())]
        if not pins:
            self.lx_ = self.ly_ = self.ux_ = self.uy_ = 0
            return
        xs = [pin.cx() for pin in pins]
        ys = [pin.cy() for pin in pins]
        self.lx_, self.ux_ = min(xs), max(xs)
        self.ly_, self.uy_ = min(ys), max(ys)

    def getPins(self) -> List[Pin]:
        return self.pins_

    def getDbNet(self) -> Optional[DbNet]:
        return self.net_

    def getSigType(self) -> SigType:
        return self.net_.sig_type if self.net_ is not None else SigType.OTHER

    def addPin(self, pin: Pin) -> None:
        self.pins_.append(pin)
        pin.setNet(self)


class GCellChange(Enum):
    """对应 `GCell::GCellChange`。"""

    kNone = "none"
    kRoutability = "routability"
    kTimingDriven = "timing_driven"
    kNewInstance = "new_instance"
    kDownsize = "downsize"
    kUpsize = "upsize"
    kResizeNoChange = "resize_no_change"


@dataclass
class GCell:
    """对应 `gpl::GCell`，Nesterov 里的可移动/填充单元。"""

    insts_: List[Instance] = field(default_factory=list)
    gPins_: List["GPin"] = field(default_factory=list)
    lx_: int = 0
    ly_: int = 0
    ux_: int = 0
    uy_: int = 0
    dLx_: int = 0
    dLy_: int = 0
    dUx_: int = 0
    dUy_: int = 0
    densityScale_: float = 0.0
    gradientX_: float = 0.0
    gradientY_: float = 0.0
    change_: GCellChange = GCellChange.kNone

    @classmethod
    def from_instance(cls, inst: Instance) -> "GCell":
        cell = cls(insts_=[inst], lx_=inst.lx(), ly_=inst.ly(), ux_=inst.ux(), uy_=inst.uy())
        cell.setDensityLocation(cell.lx_, cell.ly_)
        cell.setDensitySize(cell.dx(), cell.dy())
        return cell

    @classmethod
    def filler(cls, cx: int, cy: int, dx: int, dy: int) -> "GCell":
        cell = cls(lx_=cx - dx // 2, ly_=cy - dy // 2, ux_=cx - dx // 2 + dx, uy_=cy - dy // 2 + dy)
        cell.setDensityLocation(cell.lx_, cell.ly_)
        cell.setDensitySize(dx, dy)
        return cell

    def insts(self) -> List[Instance]:
        return self.insts_

    def gPins(self) -> List["GPin"]:
        return self.gPins_

    def getName(self) -> str:
        names = [inst.dbInst().name for inst in self.insts_ if inst.dbInst() is not None]
        return ",".join(names) if names else "FILLER"

    def addGPin(self, gPin: "GPin") -> None:
        self.gPins_.append(gPin)
        gPin.setGCell(self)

    def clearGPins(self) -> None:
        self.gPins_.clear()

    def updateLocations(self) -> None:
        for inst in self.insts_:
            inst.setLocation(self.lx_, self.ly_)

    def isLocked(self) -> bool:
        return any(inst.isLocked() for inst in self.insts_)

    def lock(self) -> None:
        for inst in self.insts_:
            inst.lock()

    def lx(self) -> int:
        return self.lx_

    def ly(self) -> int:
        return self.ly_

    def ux(self) -> int:
        return self.ux_

    def uy(self) -> int:
        return self.uy_

    def cx(self) -> int:
        return (self.lx_ + self.ux_) // 2

    def cy(self) -> int:
        return (self.ly_ + self.uy_) // 2

    def dx(self) -> int:
        return self.ux_ - self.lx_

    def dy(self) -> int:
        return self.uy_ - self.ly_

    def dLx(self) -> int:
        return self.dLx_

    def dLy(self) -> int:
        return self.dLy_

    def dUx(self) -> int:
        return self.dUx_

    def dUy(self) -> int:
        return self.dUy_

    def dCx(self) -> int:
        return (self.dLx_ + self.dUx_) // 2

    def dCy(self) -> int:
        return (self.dLy_ + self.dUy_) // 2

    def dDx(self) -> int:
        return self.dUx_ - self.dLx_

    def dDy(self) -> int:
        return self.dUy_ - self.dLy_

    def setCenterLocation(self, cx: int, cy: int) -> None:
        dx, dy = self.dx(), self.dy()
        self.lx_, self.ly_, self.ux_, self.uy_ = cx - dx // 2, cy - dy // 2, cx - dx // 2 + dx, cy - dy // 2 + dy

    def setSize(self, dx: int, dy: int, change: GCellChange = GCellChange.kNone) -> None:
        cx, cy = self.cx(), self.cy()
        self.lx_, self.ly_, self.ux_, self.uy_ = cx - dx // 2, cy - dy // 2, cx - dx // 2 + dx, cy - dy // 2 + dy
        self.change_ = change

    def setAreaChangeType(self, change: GCellChange) -> None:
        self.change_ = change

    def changeType(self) -> GCellChange:
        return self.change_

    def setAllLocations(self, lx: int, ly: int, ux: int, uy: int) -> None:
        self.lx_, self.ly_, self.ux_, self.uy_ = lx, ly, ux, uy

    def setDensityLocation(self, dLx: int, dLy: int) -> None:
        dx, dy = self.dDx() or self.dx(), self.dDy() or self.dy()
        self.dLx_, self.dLy_, self.dUx_, self.dUy_ = dLx, dLy, dLx + dx, dLy + dy

    def setDensityCenterLocation(self, dCx: int, dCy: int) -> None:
        dx, dy = self.dDx(), self.dDy()
        self.dLx_, self.dLy_, self.dUx_, self.dUy_ = dCx - dx // 2, dCy - dy // 2, dCx - dx // 2 + dx, dCy - dy // 2 + dy

    def setDensitySize(self, dDx: int, dDy: int) -> None:
        cx, cy = self.dCx(), self.dCy()
        self.dLx_, self.dLy_, self.dUx_, self.dUy_ = cx - dDx // 2, cy - dDy // 2, cx - dDx // 2 + dDx, cy - dDy // 2 + dDy

    def setDensityScale(self, densityScale: float) -> None:
        self.densityScale_ = densityScale

    def setGradientX(self, gradientX: float) -> None:
        self.gradientX_ = gradientX

    def setGradientY(self, gradientY: float) -> None:
        self.gradientY_ = gradientY

    def getGradientX(self) -> float:
        return self.gradientX_

    def getGradientY(self) -> float:
        return self.gradientY_

    def getDensityScale(self) -> float:
        return self.densityScale_

    def isInstance(self) -> bool:
        return bool(self.insts_)

    def isFiller(self) -> bool:
        return not self.insts_

    def isMacroInstance(self) -> bool:
        return any(inst.isMacro() for inst in self.insts_)

    def isStdInstance(self) -> bool:
        return self.isInstance() and not self.isMacroInstance()

    def contains(self, db_inst: DbInst) -> bool:
        return any(inst.dbInst() is db_inst for inst in self.insts_)


@dataclass
class GPin:
    """对应 `gpl::GPin`。"""

    pins_: List[Pin] = field(default_factory=list)
    gCell_: Optional[GCell] = None
    gNet_: Optional["GNet"] = None
    offsetCx_: int = 0
    offsetCy_: int = 0
    cx_: int = 0
    cy_: int = 0
    maxExpSumX_: float = 0.0
    maxExpSumY_: float = 0.0
    minExpSumX_: float = 0.0
    minExpSumY_: float = 0.0
    hasMaxExpSumX_: bool = False
    hasMaxExpSumY_: bool = False
    hasMinExpSumX_: bool = False
    hasMinExpSumY_: bool = False

    @classmethod
    def from_pin(cls, pin: Pin) -> "GPin":
        return cls(pins_=[pin], cx_=pin.cx(), cy_=pin.cy(), offsetCx_=pin.getOffsetCx(), offsetCy_=pin.getOffsetCy())

    def getPbPin(self) -> Optional[Pin]:
        return self.pins_[0] if self.pins_ else None

    def getPbPins(self) -> List[Pin]:
        return self.pins_

    def getGCell(self) -> Optional[GCell]:
        return self.gCell_

    def getGNet(self) -> Optional["GNet"]:
        return self.gNet_

    def setGCell(self, gCell: GCell) -> None:
        self.gCell_ = gCell

    def setGNet(self, gNet: "GNet") -> None:
        self.gNet_ = gNet

    def cx(self) -> int:
        return self.cx_

    def cy(self) -> int:
        return self.cy_

    def clearWaVars(self) -> None:
        self.maxExpSumX_ = self.maxExpSumY_ = self.minExpSumX_ = self.minExpSumY_ = 0.0
        self.hasMaxExpSumX_ = self.hasMaxExpSumY_ = self.hasMinExpSumX_ = self.hasMinExpSumY_ = False

    def setCenterLocation(self, cx: int, cy: int) -> None:
        self.cx_, self.cy_ = cx, cy

    def updateLocation(self, gCell: Optional[GCell] = None) -> None:
        if gCell is not None:
            self.gCell_ = gCell
        if self.gCell_ is not None:
            self.cx_ = self.gCell_.cx() + self.offsetCx_
            self.cy_ = self.gCell_.cy() + self.offsetCy_

    def updateDensityLocation(self, gCell: Optional[GCell] = None) -> None:
        if gCell is not None:
            self.gCell_ = gCell
        if self.gCell_ is not None:
            self.cx_ = self.gCell_.dCx() + self.offsetCx_
            self.cy_ = self.gCell_.dCy() + self.offsetCy_

    def updateCoordi(self) -> None:
        self.updateLocation()


@dataclass
class GNet:
    """对应 `gpl::GNet`，保存 WA wirelength 所需累计量。"""

    nets_: List[Net] = field(default_factory=list)
    gPins_: List[GPin] = field(default_factory=list)
    lx_: int = 0
    ly_: int = 0
    ux_: int = 0
    uy_: int = 0
    timingWeight_: float = 1.0
    customWeight_: float = 1.0
    waExpMinSumX_: float = 0.0
    waXExpMinSumX_: float = 0.0
    waExpMinSumY_: float = 0.0
    waYExpMinSumY_: float = 0.0
    waExpMaxSumX_: float = 0.0
    waXExpMaxSumX_: float = 0.0
    waExpMaxSumY_: float = 0.0
    waYExpMaxSumY_: float = 0.0
    isDontCare_: bool = False

    @classmethod
    def from_net(cls, net: Net) -> "GNet":
        return cls(nets_=[net])

    def getPbNet(self) -> Optional[Net]:
        return self.nets_[0] if self.nets_ else None

    def getPbNets(self) -> List[Net]:
        return self.nets_

    def getGPins(self) -> List[GPin]:
        return self.gPins_

    def lx(self) -> int:
        return self.lx_

    def ly(self) -> int:
        return self.ly_

    def ux(self) -> int:
        return self.ux_

    def uy(self) -> int:
        return self.uy_

    def setTimingWeight(self, timingWeight: float) -> None:
        self.timingWeight_ = timingWeight

    def setCustomWeight(self, customWeight: float) -> None:
        self.customWeight_ = customWeight

    def getTotalWeight(self) -> float:
        return self.timingWeight_ * self.customWeight_

    def getTimingWeight(self) -> float:
        return self.timingWeight_

    def getCustomWeight(self) -> float:
        return self.customWeight_

    def addGPin(self, gPin: GPin) -> None:
        self.gPins_.append(gPin)
        gPin.setGNet(self)

    def clearGPins(self) -> None:
        self.gPins_.clear()

    def updateBox(self) -> None:
        if not self.gPins_:
            self.lx_ = self.ly_ = self.ux_ = self.uy_ = 0
            return
        xs = [pin.cx() for pin in self.gPins_]
        ys = [pin.cy() for pin in self.gPins_]
        self.lx_, self.ux_ = min(xs), max(xs)
        self.ly_, self.uy_ = min(ys), max(ys)

    def getHpwl(self) -> int:
        self.updateBox()
        return max(0, self.ux_ - self.lx_) + max(0, self.uy_ - self.ly_)

    def setDontCare(self) -> None:
        self.isDontCare_ = True

    def isDontCare(self) -> bool:
        return self.isDontCare_

    def clearWaVars(self) -> None:
        self.waExpMinSumX_ = self.waXExpMinSumX_ = self.waExpMinSumY_ = self.waYExpMinSumY_ = 0.0
        self.waExpMaxSumX_ = self.waXExpMaxSumX_ = self.waExpMaxSumY_ = self.waYExpMaxSumY_ = 0.0

    def addWaExpMinSumX(self, value: float) -> None:
        self.waExpMinSumX_ += value

    def addWaXExpMinSumX(self, value: float) -> None:
        self.waXExpMinSumX_ += value

    def addWaExpMinSumY(self, value: float) -> None:
        self.waExpMinSumY_ += value

    def addWaYExpMinSumY(self, value: float) -> None:
        self.waYExpMinSumY_ += value

    def addWaExpMaxSumX(self, value: float) -> None:
        self.waExpMaxSumX_ += value

    def addWaXExpMaxSumX(self, value: float) -> None:
        self.waXExpMaxSumX_ += value

    def addWaExpMaxSumY(self, value: float) -> None:
        self.waExpMaxSumY_ += value

    def addWaYExpMaxSumY(self, value: float) -> None:
        self.waYExpMaxSumY_ += value


@dataclass
class Bin:
    """对应 `gpl::Bin`。"""

    x_: int = 0
    y_: int = 0
    lx_: int = 0
    ly_: int = 0
    ux_: int = 0
    uy_: int = 0
    nonPlaceArea_: int = 0
    instPlacedArea_: int = 0
    instPlacedAreaUnscaled_: int = 0
    nonPlaceAreaUnscaled_: int = 0
    fillerArea_: int = 0
    density_: float = 0.0
    targetDensity_: float = 0.0
    electroPhi_: float = 0.0
    electroFieldX_: float = 0.0
    electroFieldY_: float = 0.0

    def x(self) -> int:
        return self.x_

    def y(self) -> int:
        return self.y_

    def lx(self) -> int:
        return self.lx_

    def ly(self) -> int:
        return self.ly_

    def ux(self) -> int:
        return self.ux_

    def uy(self) -> int:
        return self.uy_

    def cx(self) -> int:
        return (self.lx_ + self.ux_) // 2

    def cy(self) -> int:
        return (self.ly_ + self.uy_) // 2

    def dx(self) -> int:
        return self.ux_ - self.lx_

    def dy(self) -> int:
        return self.uy_ - self.ly_

    def electroPhi(self) -> float:
        return self.electroPhi_

    def electroFieldX(self) -> float:
        return self.electroFieldX_

    def electroFieldY(self) -> float:
        return self.electroFieldY_

    def getTargetDensity(self) -> float:
        return self.targetDensity_

    def getDensity(self) -> float:
        return self.density_

    def setDensity(self, density: float) -> None:
        self.density_ = density

    def setBinTargetDensity(self, density: float) -> None:
        self.targetDensity_ = density

    def setElectroField(self, electroFieldX: float, electroFieldY: float) -> None:
        self.electroFieldX_, self.electroFieldY_ = electroFieldX, electroFieldY

    def setElectroPhi(self, phi: float) -> None:
        self.electroPhi_ = phi

    def setNonPlaceArea(self, area: int) -> None:
        self.nonPlaceArea_ = area

    def setInstPlacedArea(self, area: int) -> None:
        self.instPlacedArea_ = area

    def setFillerArea(self, area: int) -> None:
        self.fillerArea_ = area

    def setNonPlaceAreaUnscaled(self, area: int) -> None:
        self.nonPlaceAreaUnscaled_ = area

    def setInstPlacedAreaUnscaled(self, area: int) -> None:
        self.instPlacedAreaUnscaled_ = area

    def addNonPlaceArea(self, area: int) -> None:
        self.nonPlaceArea_ += area

    def addInstPlacedArea(self, area: int) -> None:
        self.instPlacedArea_ += area

    def addFillerArea(self, area: int) -> None:
        self.fillerArea_ += area

    def addNonPlaceAreaUnscaled(self, area: int) -> None:
        self.nonPlaceAreaUnscaled_ += area

    def addInstPlacedAreaUnscaled(self, area: int) -> None:
        self.instPlacedAreaUnscaled_ += area

    def getBinArea(self) -> int:
        return _area((self.lx_, self.ly_, self.ux_, self.uy_))

    def getNonPlaceArea(self) -> int:
        return self.nonPlaceArea_

    def instPlacedArea(self) -> int:
        return self.instPlacedArea_

    def getNonPlaceAreaUnscaled(self) -> int:
        return self.nonPlaceAreaUnscaled_

    def getInstPlacedAreaUnscaled(self) -> int:
        return self.instPlacedAreaUnscaled_

    def getFillerArea(self) -> int:
        return self.fillerArea_


@dataclass
class BinGrid:
    """对应 `gpl::BinGrid`。"""

    lx_: int = 0
    ly_: int = 0
    ux_: int = 0
    uy_: int = 0
    bins_: List[Bin] = field(default_factory=list)
    pb_: Optional["PlacerBase"] = None
    log_: Any = None
    binCntX_: int = 0
    binCntY_: int = 0
    binSizeX_: float = 0.0
    binSizeY_: float = 0.0
    targetDensity_: float = 0.0
    sumOverflowArea_: int = 0
    sumOverflowAreaUnscaled_: int = 0
    isSetBinCnt_: bool = False
    num_threads_: int = 1

    def setPlacerBase(self, pb: "PlacerBase") -> None:
        self.pb_ = pb

    def setLogger(self, log: Any) -> None:
        self.log_ = log

    def setRegionPoints(self, lx: int, ly: int, ux: int, uy: int) -> None:
        self.lx_, self.ly_, self.ux_, self.uy_ = lx, ly, ux, uy

    def setBinCnt(self, binCntX: int, binCntY: int) -> None:
        self.binCntX_, self.binCntY_ = binCntX, binCntY
        self.isSetBinCnt_ = True

    def setBinTargetDensity(self, density: float) -> None:
        self.targetDensity_ = density
        for bin_obj in self.bins_:
            bin_obj.setBinTargetDensity(density)

    def setNumThreads(self, num_threads: int) -> None:
        self.num_threads_ = num_threads

    def initBins(self) -> None:
        if self.binCntX_ <= 0:
            self.binCntX_ = 1
        if self.binCntY_ <= 0:
            self.binCntY_ = 1
        self.binSizeX_ = (self.ux_ - self.lx_) / self.binCntX_ if self.binCntX_ else 0.0
        self.binSizeY_ = (self.uy_ - self.ly_) / self.binCntY_ if self.binCntY_ else 0.0
        self.bins_.clear()
        for y in range(self.binCntY_):
            for x in range(self.binCntX_):
                lx = int(round(self.lx_ + x * self.binSizeX_))
                ly = int(round(self.ly_ + y * self.binSizeY_))
                ux = int(round(self.lx_ + (x + 1) * self.binSizeX_))
                uy = int(round(self.ly_ + (y + 1) * self.binSizeY_))
                self.bins_.append(Bin(x, y, lx, ly, ux, uy, targetDensity_=self.targetDensity_))

    def lx(self) -> int:
        return self.lx_

    def ly(self) -> int:
        return self.ly_

    def ux(self) -> int:
        return self.ux_

    def uy(self) -> int:
        return self.uy_

    def cx(self) -> int:
        return (self.lx_ + self.ux_) // 2

    def cy(self) -> int:
        return (self.ly_ + self.uy_) // 2

    def dx(self) -> int:
        return self.ux_ - self.lx_

    def dy(self) -> int:
        return self.uy_ - self.ly_

    def getBinCntX(self) -> int:
        return self.binCntX_

    def getBinCntY(self) -> int:
        return self.binCntY_

    def getBinSizeX(self) -> float:
        return self.binSizeX_

    def getBinSizeY(self) -> float:
        return self.binSizeY_

    def getOverflowArea(self) -> int:
        return self.sumOverflowArea_

    def getOverflowAreaUnscaled(self) -> int:
        return self.sumOverflowAreaUnscaled_

    def getBins(self) -> List[Bin]:
        return self.bins_

    def getBinsConst(self) -> List[Bin]:
        return self.bins_


@dataclass
class Tile:
    """对应 `gpl::Tile`。"""

    x_: int = 0
    y_: int = 0
    lx_: int = 0
    ly_: int = 0
    ux_: int = 0
    uy_: int = 0
    layers_: int = 0
    inflationRatio_: float = 1.0
    inflatedRatio_: float = 0.0

    def area(self) -> int:
        return _area((self.lx_, self.ly_, self.ux_, self.uy_))

    def inflationRatio(self) -> float:
        return self.inflationRatio_

    def inflatedRatio(self) -> float:
        return self.inflatedRatio_

    def setInflationRatio(self, ratio: float) -> None:
        self.inflationRatio_ = ratio

    def setInflatedRatio(self, ratio: float) -> None:
        self.inflatedRatio_ = ratio


@dataclass
class TileGrid:
    """对应 `gpl::TileGrid`。"""

    log_: Any = None
    tileStor_: List[Tile] = field(default_factory=list)
    tiles_: List[Tile] = field(default_factory=list)
    lx_: int = 0
    ly_: int = 0
    tileCntX_: int = 0
    tileCntY_: int = 0
    tileSizeX_: int = 0
    tileSizeY_: int = 0
    numRoutingLayers_: int = 0

    def setLogger(self, log: Any) -> None:
        self.log_ = log

    def setTileCnt(self, tileCntX: int, tileCntY: int) -> None:
        self.tileCntX_, self.tileCntY_ = tileCntX, tileCntY

    def setTileCntX(self, tileCntX: int) -> None:
        self.tileCntX_ = tileCntX

    def setTileCntY(self, tileCntY: int) -> None:
        self.tileCntY_ = tileCntY

    def setTileSize(self, tileSizeX: int, tileSizeY: int) -> None:
        self.tileSizeX_, self.tileSizeY_ = tileSizeX, tileSizeY

    def setTileSizeX(self, tileSizeX: int) -> None:
        self.tileSizeX_ = tileSizeX

    def setTileSizeY(self, tileSizeY: int) -> None:
        self.tileSizeY_ = tileSizeY

    def setNumRoutingLayers(self, num: int) -> None:
        self.numRoutingLayers_ = num

    def setLx(self, lx: int) -> None:
        self.lx_ = lx

    def setLy(self, ly: int) -> None:
        self.ly_ = ly

    def lx(self) -> int:
        return self.lx_

    def ly(self) -> int:
        return self.ly_

    def ux(self) -> int:
        return self.lx_ + self.tileCntX_ * self.tileSizeX_

    def uy(self) -> int:
        return self.ly_ + self.tileCntY_ * self.tileSizeY_

    def tileCntX(self) -> int:
        return self.tileCntX_

    def tileCntY(self) -> int:
        return self.tileCntY_

    def tileSizeX(self) -> int:
        return self.tileSizeX_

    def tileSizeY(self) -> int:
        return self.tileSizeY_

    def numRoutingLayers(self) -> int:
        return self.numRoutingLayers_

    def tiles(self) -> List[Tile]:
        return self.tiles_

    def initTiles(self, use_rudy: bool) -> None:
        self.tileStor_.clear()
        for y in range(max(0, self.tileCntY_)):
            for x in range(max(0, self.tileCntX_)):
                lx = self.lx_ + x * self.tileSizeX_
                ly = self.ly_ + y * self.tileSizeY_
                self.tileStor_.append(Tile(x, y, lx, ly, lx + self.tileSizeX_, ly + self.tileSizeY_, self.numRoutingLayers_))
        self.tiles_ = list(self.tileStor_)


class PlacerBaseCommon:
    """对应 `gpl::PlacerBaseCommon`。

    该类保存与 region 无关的 Instance/Pin/Net 存储和 db 到 pb 的映射。
    当前 WinRoad ODB 还没有完整 ITerm/BTerm 坐标，因此 pin 构造先保留
    容器和映射边界，后续随 ODB 继续补齐。
    """

    def __init__(self, db: DbDatabase, pbVars: PlaceOptions | PlacerBaseVars, log: Any = None):
        self.db_ = db
        self.log_ = log
        self.pbVars_ = pbVars if isinstance(pbVars, PlacerBaseVars) else PlacerBaseVars.from_options(pbVars)
        self.die_ = Die()
        self.instStor_: List[Instance] = []
        self.pinStor_: List[Pin] = []
        self.netStor_: List[Net] = []
        self.insts_: List[Instance] = []
        self.pins_: List[Pin] = []
        self.nets_: List[Net] = []
        self.placeInsts_: List[Instance] = []
        self.instMap_: Dict[int, Instance] = {}
        self.pinMap_: Dict[Any, Pin] = {}
        self.netMap_: Dict[int, Net] = {}
        self.siteSizeX_ = 0
        self.siteSizeY_ = 0
        self.macroInstsArea_ = 0
        self.init()

    def init(self) -> None:
        block = _get_block(self.db_)
        die_rect = getattr(block, "die_area", None) or getattr(block, "bbox", None) or (0, 0, 0, 0)
        self.die_ = Die.from_rects(die_rect)
        for db_inst in _iter_block_insts(block):
            inst = Instance.from_db(db_inst)
            self.instStor_.append(inst)
            self.insts_.append(inst)
            self.instMap_[id(db_inst)] = inst
            if inst.isPlaceInstance():
                self.placeInsts_.append(inst)
            if inst.isMacro():
                self.macroInstsArea_ += inst.getArea()
        for db_net in _iter_block_nets(block):
            net = Net(db_net, skipIoMode=self.pbVars_.skipIoMode)
            self.netStor_.append(net)
            self.nets_.append(net)
            self.netMap_[id(db_net)] = net

    def reset(self) -> None:
        self.__init__(self.db_, self.pbVars_, self.log_)

    def placeInsts(self) -> List[Instance]:
        return self.placeInsts_

    def getInsts(self) -> List[Instance]:
        return self.insts_

    def getPins(self) -> List[Pin]:
        return self.pins_

    def getNets(self) -> List[Net]:
        return self.nets_

    def getDie(self) -> Die:
        return self.die_

    def dbToPb(self, obj: Any) -> Any:
        if isinstance(obj, DbInst):
            return self.instMap_.get(id(obj))
        if isinstance(obj, DbNet):
            return self.netMap_.get(id(obj))
        return self.pinMap_.get(obj)

    def siteSizeX(self) -> int:
        return self.siteSizeX_

    def siteSizeY(self) -> int:
        return self.siteSizeY_

    def getPadLeft(self) -> int:
        return self.pbVars_.padLeft

    def getPadRight(self) -> int:
        return self.pbVars_.padRight

    def isSkipIoMode(self) -> bool:
        return self.pbVars_.skipIoMode

    def getHpwl(self) -> int:
        return sum(net.getHpwl() for net in self.nets_)

    def printInfo(self) -> Dict[str, int]:
        return {
            "insts": len(self.insts_),
            "placeInsts": len(self.placeInsts_),
            "pins": len(self.pins_),
            "nets": len(self.nets_),
        }

    def getMacroInstsArea(self) -> int:
        return self.macroInstsArea_

    def db(self) -> DbDatabase:
        return self.db_

    def unlockAll(self) -> None:
        for inst in self.placeInsts_:
            inst.unlock()


class PlacerBase:
    """对应 `gpl::PlacerBase`，保存某个 region 的布局对象集合。"""

    def __init__(
        self,
        db: Optional[DbDatabase] = None,
        pbCommon: Optional[PlacerBaseCommon] = None,
        log: Any = None,
        check_density: bool = True,
        group: Any = None,
    ):
        self.db_ = db
        self.log_ = log
        self.die_ = pbCommon.getDie() if pbCommon is not None else Die()
        self.region_area_ = self.die_.coreArea()
        self.region_bbox_: Rect = (self.die_.coreLx(), self.die_.coreLy(), self.die_.coreUx(), self.die_.coreUy())
        self.instStor_: List[Instance] = []
        self.pb_insts_: List[Instance] = []
        self.placeInsts_: List[Instance] = []
        self.fixedInsts_: List[Instance] = []
        self.dummyInsts_: List[Instance] = []
        self.nonPlaceInsts_: List[Instance] = []
        self.siteSizeX_ = pbCommon.siteSizeX() if pbCommon else 0
        self.siteSizeY_ = pbCommon.siteSizeY() if pbCommon else 9
        self.placeInstsArea_ = 0
        self.nonPlaceInstsArea_ = 0
        self.macroInstsArea_ = 0
        self.stdInstsArea_ = 0
        self.pbCommon_ = pbCommon
        self.group_ = group
        if pbCommon is not None:
            self.init(check_density)

    def init(self, check_density: bool) -> None:
        for inst in self.pbCommon_.getInsts():  # type: ignore[union-attr]
            self.pb_insts_.append(inst)
            if inst.isPlaceInstance():
                self.placeInsts_.append(inst)
                self.placeInstsArea_ += inst.getArea()
                if inst.isMacro():
                    self.macroInstsArea_ += inst.getArea()
                else:
                    self.stdInstsArea_ += inst.getArea()
            else:
                self.fixedInsts_.append(inst)
                self.nonPlaceInsts_.append(inst)
                self.nonPlaceInstsArea_ += inst.getArea()

    def reset(self) -> None:
        self.pb_insts_.clear()
        self.placeInsts_.clear()
        self.fixedInsts_.clear()
        self.dummyInsts_.clear()
        self.nonPlaceInsts_.clear()

    def getInsts(self) -> List[Instance]:
        return self.pb_insts_

    def placeInsts(self) -> List[Instance]:
        return self.placeInsts_

    def fixedInsts(self) -> List[Instance]:
        return self.fixedInsts_

    def dummyInsts(self) -> List[Instance]:
        return self.dummyInsts_

    def nonPlaceInsts(self) -> List[Instance]:
        return self.nonPlaceInsts_

    def getDie(self) -> Die:
        return self.die_

    def getRegionArea(self) -> int:
        return self.region_area_

    def getRegionBBox(self) -> Rect:
        return self.region_bbox_

    def getSiteSizeX(self) -> int:
        return self.siteSizeX_

    def getSiteSizeY(self) -> int:
        return self.siteSizeY_

    def getHpwl(self) -> int:
        return self.pbCommon_.getHpwl() if self.pbCommon_ is not None else 0

    def printInfo(self, check_density: bool) -> Dict[str, int]:
        return {
            "placeInsts": len(self.placeInsts_),
            "fixedInsts": len(self.fixedInsts_),
            "dummyInsts": len(self.dummyInsts_),
        }

    def placeInstsArea(self) -> int:
        return self.placeInstsArea_

    def nonPlaceInstsArea(self) -> int:
        return self.nonPlaceInstsArea_

    def macroInstsArea(self) -> int:
        return self.macroInstsArea_

    def stdInstsArea(self) -> int:
        return self.stdInstsArea_

    def db(self) -> Optional[DbDatabase]:
        return self.db_

    def getGroup(self) -> Any:
        return self.group_

    def unlockAll(self) -> None:
        for inst in self.placeInsts_:
            inst.unlock()


class NesterovBaseCommon:
    """对应 `gpl::NesterovBaseCommon`。"""

    def __init__(
        self,
        nbVars: NesterovBaseVars,
        pb: PlacerBaseCommon,
        log: Any,
        num_threads: int,
        clusters: Optional[Clusters] = None,
    ):
        self.nbVars_ = nbVars
        self.pbc_ = pb
        self.log_ = log
        self.gCellStor_: List[GCell] = []
        self.gNetStor_: List[GNet] = []
        self.gPinStor_: List[GPin] = []
        self.nbc_gcells_: List[GCell] = []
        self.gNets_: List[GNet] = []
        self.gPins_: List[GPin] = []
        self.gCellMap_: Dict[int, GCell] = {}
        self.gPinMap_: Dict[int, GPin] = {}
        self.gNetMap_: Dict[int, GNet] = {}
        self.num_threads_ = num_threads
        self.delta_area_ = 0
        self.new_gcells_count_ = 0
        self.deleted_gcells_count_ = 0
        self.db_cbk_: Optional[nesterovDbCbk] = None
        self._init_from_pb(clusters or [])

    def _init_from_pb(self, clusters: Clusters) -> None:
        clustered = {id(inst) for cluster in clusters for inst in cluster}
        for inst in self.pbc_.getInsts():
            db_inst = inst.dbInst()
            if db_inst is not None and id(db_inst) in clustered:
                continue
            gcell = GCell.from_instance(inst)
            self.gCellStor_.append(gcell)
            self.nbc_gcells_.append(gcell)
            self.gCellMap_[id(inst)] = gcell
        for net in self.pbc_.getNets():
            gnet = GNet.from_net(net)
            self.gNetStor_.append(gnet)
            self.gNets_.append(gnet)

    def reportInstanceExtensionByPinDensity(self) -> None:
        return None

    def getGCells(self) -> List[GCell]:
        return self.nbc_gcells_

    def getGNets(self) -> List[GNet]:
        return self.gNets_

    def getGPins(self) -> List[GPin]:
        return self.gPins_

    def pbToNb(self, obj: Any) -> Any:
        if isinstance(obj, Instance):
            return self.gCellMap_.get(id(obj))
        if isinstance(obj, Pin):
            return self.gPinMap_.get(id(obj))
        if isinstance(obj, Net):
            return self.gNetMap_.get(id(obj))
        return None

    def dbToNb(self, obj: Any) -> Any:
        pb_obj = self.pbc_.dbToPb(obj)
        return self.pbToNb(pb_obj)

    def updateWireLengthForceWA(self, wlCoeffX: float, wlCoeffY: float) -> None:
        raise NotImplementedError("OpenROAD WA wirelength force update has not been translated yet")

    def getWireLengthGradientPinWA(self, gPin: GPin, wlCoeffX: float, wlCoeffY: float) -> FloatPoint:
        raise NotImplementedError("OpenROAD WA pin gradient has not been translated yet")

    def getWireLengthGradientWA(self, gCell: GCell, wlCoeffX: float, wlCoeffY: float) -> FloatPoint:
        raise NotImplementedError("OpenROAD WA cell gradient has not been translated yet")

    def getWireLengthPreconditioner(self, gCell: GCell) -> FloatPoint:
        raise NotImplementedError("OpenROAD wirelength preconditioner has not been translated yet")

    def getHpwl(self) -> int:
        return sum(gnet.getHpwl() for gnet in self.gNets_)

    def updateDbGCells(self) -> None:
        for gcell in self.nbc_gcells_:
            gcell.updateLocations()
            for inst in gcell.insts():
                inst.dbSetLocation()

    def getNumThreads(self) -> int:
        return self.num_threads_

    def getGCellByIndex(self, i: int) -> GCell:
        return self.nbc_gcells_[i]

    def setCbk(self, cbk: "nesterovDbCbk") -> None:
        self.db_cbk_ = cbk

    def getGCell(self, index: int) -> GCell:
        return self.nbc_gcells_[index]

    def getGCellIndex(self, gCell: GCell) -> int:
        return self.nbc_gcells_.index(gCell)

    def getDeltaArea(self) -> int:
        return self.delta_area_

    def resetDeltaArea(self) -> None:
        self.delta_area_ = 0

    def getNewGcellsCount(self) -> int:
        return self.new_gcells_count_

    def getDeletedGcellsCount(self) -> int:
        return self.deleted_gcells_count_

    def resetNewGcellsCount(self) -> None:
        self.new_gcells_count_ = 0
        self.deleted_gcells_count_ = 0

    def getNbVars(self) -> NesterovBaseVars:
        return self.nbVars_


class NesterovBase:
    """对应 `gpl::NesterovBase`，保存单个 region 的 bin grid 与 filler 状态。"""

    def __init__(self, nbVars: NesterovBaseVars, pb: PlacerBase, nbc: NesterovBaseCommon, log: Any):
        self.nbVars_ = nbVars
        self.pb_ = pb
        self.nbc_ = nbc
        self.log_ = log
        self.bg_ = BinGrid()
        self.fillerStor_: List[GCell] = []
        self.nb_gcells_: List[GCell] = list(nbc.getGCells())
        self.sum_overflow_ = 0.0
        self.sum_overflow_unscaled_ = 0.0
        self.baseWireLengthCoef_ = 0.0
        self.densityPenalty_ = 0.0
        self.wireLengthGradSum_ = 0.0
        self.densityGradSum_ = 0.0
        self.fillerDx_ = 0
        self.fillerDy_ = 0
        self.whiteSpaceArea_ = max(0, pb.getRegionArea() - pb.nonPlaceInstsArea())
        self.movableArea_ = pb.placeInstsArea()
        self.totalFillerArea_ = max(0, self.whiteSpaceArea_ - self.movableArea_)
        self.stdInstsArea_ = pb.stdInstsArea()
        self.macroInstsArea_ = pb.macroInstsArea()
        self.sumPhi_ = 0.0
        self.phiCoef_ = 0.0
        self.targetDensity_ = nbVars.targetDensity
        self.uniformTargetDensity_ = nbVars.targetDensity
        self.stepLength_ = 0.0
        self.coordiDistance_ = 0.0
        self.gradDistance_ = 0.0
        self.isDiverged_ = False
        self.npVars_: Optional[NesterovPlaceVars] = None
        self.iter_ = 0
        self.isConverged_ = False
        self.reprint_iter_header_ = False
        self._init_bin_grid()

    def _init_bin_grid(self) -> None:
        lx, ly, ux, uy = self.pb_.getRegionBBox()
        self.bg_.setRegionPoints(lx, ly, ux, uy)
        self.bg_.setBinCnt(self.nbVars_.binCntX or 1, self.nbVars_.binCntY or 1)
        self.bg_.setBinTargetDensity(self.targetDensity_)
        self.bg_.initBins()

    def getFillerGCell(self, index: int) -> GCell:
        return self.fillerStor_[index]

    def getGCells(self) -> List[GCell]:
        return self.nb_gcells_

    def getSumOverflow(self) -> float:
        return self.sum_overflow_

    def getSumOverflowUnscaled(self) -> float:
        return self.sum_overflow_unscaled_

    def getBaseWireLengthCoef(self) -> float:
        return self.baseWireLengthCoef_

    def getDensityPenalty(self) -> float:
        return self.densityPenalty_

    def getWireLengthGradSum(self) -> float:
        return self.wireLengthGradSum_

    def getDensityGradSum(self) -> float:
        return self.densityGradSum_

    def updateGCellCenterLocation(self, coordis: Sequence[FloatPoint]) -> None:
        for gcell, coord in zip(self.nb_gcells_, coordis):
            gcell.setCenterLocation(int(round(coord.x)), int(round(coord.y)))

    def updateGCellDensityCenterLocation(self, coordis: Sequence[FloatPoint]) -> None:
        for gcell, coord in zip(self.nb_gcells_, coordis):
            gcell.setDensityCenterLocation(int(round(coord.x)), int(round(coord.y)))

    def getBinCntX(self) -> int:
        return self.bg_.getBinCntX()

    def getBinCntY(self) -> int:
        return self.bg_.getBinCntY()

    def getBinSizeX(self) -> float:
        return self.bg_.getBinSizeX()

    def getBinSizeY(self) -> float:
        return self.bg_.getBinSizeY()

    def getOverflowArea(self) -> int:
        return self.bg_.getOverflowArea()

    def getOverflowAreaUnscaled(self) -> int:
        return self.bg_.getOverflowAreaUnscaled()

    def getBins(self) -> List[Bin]:
        return self.bg_.getBins()

    def getBinsConst(self) -> List[Bin]:
        return self.bg_.getBinsConst()

    def getFillerDx(self) -> int:
        return self.fillerDx_

    def getFillerDy(self) -> int:
        return self.fillerDy_

    def getFillerCnt(self) -> int:
        return len(self.fillerStor_)

    def getFillerCellArea(self) -> int:
        return self.fillerDx_ * self.fillerDy_

    def getWhiteSpaceArea(self) -> int:
        return self.whiteSpaceArea_

    def getMovableArea(self) -> int:
        return self.movableArea_

    def getTotalFillerArea(self) -> int:
        return self.totalFillerArea_

    def setMovableArea(self, area: int) -> None:
        self.movableArea_ = area

    def updateAreas(self) -> None:
        self.movableArea_ = sum(cell.dx() * cell.dy() for cell in self.nb_gcells_ if cell.isInstance())
        self.totalFillerArea_ = sum(cell.dx() * cell.dy() for cell in self.fillerStor_)

    def updateDensitySize(self) -> None:
        for gcell in self.nb_gcells_:
            gcell.setDensitySize(gcell.dx(), gcell.dy())

    def getNesterovInstsArea(self) -> int:
        return sum(cell.dx() * cell.dy() for cell in self.nb_gcells_)

    def getStdInstArea(self) -> int:
        return self.stdInstsArea_

    def getMacroInstArea(self) -> int:
        return self.macroInstsArea_

    def getSumPhi(self) -> float:
        return self.sumPhi_

    def getUniformTargetDensity(self) -> float:
        core_area = max(1, self.pb_.getRegionArea())
        return min(1.0, max(0.0, self.pb_.placeInstsArea() / core_area))

    def initTargetDensity(self) -> float:
        return self.nbVars_.targetDensity

    def getTargetDensity(self) -> float:
        return self.targetDensity_

    def setTargetDensity(self, targetDensity: float) -> None:
        self.targetDensity_ = targetDensity
        self.bg_.setBinTargetDensity(targetDensity)

    def checkConsistency(self) -> None:
        if self.targetDensity_ < 0 or self.targetDensity_ > 1:
            raise ValueError("targetDensity must be in [0, 1]")

    def cutFillerCells(self, targetFillerArea: int) -> None:
        while self.fillerStor_ and self.getTotalFillerArea() > targetFillerArea:
            self.fillerStor_.pop()
            self.updateAreas()

    def updateDensityCoordiLayoutInside(self, gcell: GCell) -> None:
        gcell.setDensityCenterLocation(
            int(self.getDensityCoordiLayoutInsideX(gcell, gcell.dCx())),
            int(self.getDensityCoordiLayoutInsideY(gcell, gcell.dCy())),
        )

    def getDensityCoordiLayoutInsideX(self, gCell: GCell, cx: float) -> float:
        half = gCell.dDx() / 2
        return min(max(cx, self.bg_.lx() + half), self.bg_.ux() - half)

    def getDensityCoordiLayoutInsideY(self, gCell: GCell, cy: float) -> float:
        half = gCell.dDy() / 2
        return min(max(cy, self.bg_.ly() + half), self.bg_.uy() - half)

    def getDensityPreconditioner(self, gCell: GCell) -> FloatPoint:
        raise NotImplementedError("OpenROAD density preconditioner has not been translated yet")

    def getDensityGradient(self, gCell: GCell) -> FloatPoint:
        raise NotImplementedError("OpenROAD electrostatic density gradient has not been translated yet")

    def updateDensityFieldBin(self) -> None:
        raise NotImplementedError("OpenROAD FFT density field update has not been translated yet")

    def getBinGrid(self) -> BinGrid:
        return self.bg_

    def initDensity1(self) -> None:
        raise NotImplementedError("OpenROAD Nesterov initDensity1 has not been translated yet")

    def initDensity2(self, wlCoeffX: float, wlCoeffY: float) -> float:
        raise NotImplementedError("OpenROAD Nesterov initDensity2 has not been translated yet")

    def setNpVars(self, npVars: NesterovPlaceVars) -> None:
        self.npVars_ = npVars

    def setIter(self, iter: int) -> None:
        self.iter_ = iter

    def setMaxPhiCoefChanged(self, maxPhiCoefChanged: bool) -> None:
        self.nbVars_.isMaxPhiCoefChanged = maxPhiCoefChanged

    def checkConvergence(self, gpl_iter_count: int, routability_gpl_iter_count: int, rb: Optional["RouteBase"]) -> bool:
        return self.isConverged_

    def resetConverged(self) -> None:
        self.isConverged_ = False

    def checkDivergence(self) -> bool:
        return self.isDiverged_

    def saveSnapshot(self) -> None:
        return None

    def revertToSnapshot(self) -> bool:
        return False

    def resetMinSumOverflow(self) -> None:
        return None

    def isDiverged(self) -> bool:
        return self.isDiverged_

    def getPb(self) -> PlacerBase:
        return self.pb_

    def getGroup(self) -> Any:
        return self.pb_.getGroup()


class InitialPlace:
    """对应 `gpl::InitialPlace`。

    稀疏矩阵创建、BiCGSTAB 求解和坐标回写是后续翻译重点。
    """

    def __init__(
        self,
        ipVars: InitialPlaceVars,
        pbc: PlacerBaseCommon,
        pbVec: List[PlacerBase],
        graphics: Optional["AbstractGraphics"],
        logger: Any,
    ):
        self.ipVars_ = ipVars
        self.pbc_ = pbc
        self.pbVec_ = pbVec
        self.graphics_ = graphics
        self.log_ = logger
        self.gif_key_ = 0
        self.instLocVecX_: List[float] = []
        self.fixedInstForceVecX_: List[float] = []
        self.instLocVecY_: List[float] = []
        self.fixedInstForceVecY_: List[float] = []

    def doBicgstabPlace(self, threads: int) -> None:
        if self.ipVars_.maxIter == 0:
            return
        raise NotImplementedError("OpenROAD InitialPlace BiCGSTAB solver has not been translated yet")

    def placeInstsInitialPositions(self) -> None:
        raise NotImplementedError("OpenROAD InitialPlace placement initialization has not been translated yet")

    def setPlaceInstExtId(self) -> None:
        for index, inst in enumerate(self.pbc_.placeInsts()):
            inst.setExtId(index)

    def updatePinInfo(self) -> None:
        raise NotImplementedError("OpenROAD InitialPlace pin update has not been translated yet")

    def createSparseMatrix(self) -> None:
        raise NotImplementedError("OpenROAD InitialPlace sparse matrix creation has not been translated yet")

    def updateCoordi(self) -> None:
        raise NotImplementedError("OpenROAD InitialPlace coordinate update has not been translated yet")


class RouteBase:
    """对应 `gpl::RouteBase`，保留 RUDY/GR routability 边界。"""

    def __init__(
        self,
        rbVars: RouteBaseVars,
        db: Optional[DbDatabase],
        grouter: Any,
        nbc: Optional[NesterovBaseCommon],
        nbVec: List[NesterovBase],
        log: Any,
    ):
        self.rbVars_ = rbVars
        self.db_ = db
        self.grouter_ = grouter
        self.nbc_ = nbc
        self.nbVec_ = nbVec
        self.log_ = log
        self.tg_ = TileGrid()
        self.inflatedAreaDelta_: List[int] = []
        self.minRcInflatedAreaDelta_: List[int] = []
        self.accumulatedInflatedAreaDelta_: List[int] = []
        self.revert_count_ = 0
        self.final_average_rc_ = 0.0
        self.overflowed_tiles_count_ = 0
        self.total_route_overflow_ = 0.0
        self.is_min_rc_ = False
        self.minRc_ = 1e30
        self.minRcTargetDensity_: List[float] = []
        self.min_RC_violated_cnt_ = 0
        self.max_routability_no_improvement_ = 3
        self.max_routability_revert_ = 50

    def updateGrtRoute(self) -> None:
        raise NotImplementedError("OpenROAD GR route update has not been translated yet")

    def getGrtResult(self) -> None:
        raise NotImplementedError("OpenROAD GR result extraction has not been translated yet")

    def loadGrt(self) -> None:
        raise NotImplementedError("OpenROAD GR heatmap loading has not been translated yet")

    def getGrtRC(self) -> float:
        raise NotImplementedError("OpenROAD GR RC metric has not been translated yet")

    def calculateRudyTiles(self) -> None:
        raise NotImplementedError("OpenROAD RUDY tile calculation has not been translated yet")

    def updateRudyAverage(self, verbose: bool = True) -> None:
        raise NotImplementedError("OpenROAD RUDY average update has not been translated yet")

    def getRudyAverage(self) -> float:
        return self.final_average_rc_

    def getOverflowedTilesCount(self) -> int:
        return self.overflowed_tiles_count_

    def getTotalTilesCount(self) -> int:
        return len(self.tg_.tiles())

    def getTotalRudyOverflow(self) -> float:
        return self.total_route_overflow_

    def isMinRc(self) -> bool:
        return self.is_min_rc_

    def routability(self, routability_driven_revert_count: int) -> Tuple[bool, bool]:
        raise NotImplementedError("OpenROAD routability-driven inflation loop has not been translated yet")

    def inflatedAreaDelta(self) -> List[int]:
        return self.inflatedAreaDelta_

    def getTotalInflation(self) -> int:
        return sum(self.inflatedAreaDelta_)

    def getRevertCount(self) -> int:
        return self.revert_count_


class TimingBase:
    """对应 `gpl::TimingBase`，保留 timing-driven net reweight 边界。"""

    def __init__(
        self,
        nbc: Optional[NesterovBaseCommon] = None,
        grt: Any = None,
        rs: Any = None,
        log: Any = None,
    ):
        self.grt_ = grt
        self.rs_ = rs
        self.log_ = log
        self.nbc_ = nbc
        self.timingNetWeightOverflow_: List[int] = []
        self.timingOverflowChk_: List[int] = []
        self.net_weight_max_ = 5.0

    def isTimingNetWeightOverflow(self, overflow: float) -> bool:
        return int(round(overflow * 100)) in self.timingNetWeightOverflow_

    def addTimingNetWeightOverflow(self, overflow: int) -> None:
        self.timingNetWeightOverflow_.append(overflow)

    def setTimingNetWeightOverflows(self, overflows: Sequence[int]) -> None:
        self.timingNetWeightOverflow_ = list(overflows)
        self.initTimingOverflowChk()

    def deleteTimingNetWeightOverflow(self, overflow: int) -> None:
        self.timingNetWeightOverflow_ = [item for item in self.timingNetWeightOverflow_ if item != overflow]
        self.initTimingOverflowChk()

    def clearTimingNetWeightOverflow(self) -> None:
        self.timingNetWeightOverflow_.clear()
        self.timingOverflowChk_.clear()

    def getTimingNetWeightOverflowSize(self) -> int:
        return len(self.timingNetWeightOverflow_)

    def setTimingNetWeightMax(self, max: float) -> None:
        self.net_weight_max_ = max

    def executeTimingDriven(self, run_journal_restore: bool) -> bool:
        raise NotImplementedError("OpenROAD timing-driven net reweight has not been translated yet")

    def initTimingOverflowChk(self) -> None:
        self.timingOverflowChk_ = sorted(set(self.timingNetWeightOverflow_), reverse=True)


class NesterovPlace:
    """对应 `gpl::NesterovPlace`，Nesterov 主循环入口。"""

    def __init__(
        self,
        npVars: Optional[NesterovPlaceVars] = None,
        pbc: Optional[PlacerBaseCommon] = None,
        nbc: Optional[NesterovBaseCommon] = None,
        pbVec: Optional[List[PlacerBase]] = None,
        nbVec: Optional[List[NesterovBase]] = None,
        rb: Optional[RouteBase] = None,
        tb: Optional[TimingBase] = None,
        graphics: Optional["AbstractGraphics"] = None,
        log: Any = None,
    ):
        self.pbc_ = pbc
        self.nbc_ = nbc
        self.pbVec_ = pbVec or []
        self.nbVec_ = nbVec or []
        self.log_ = log
        self.rb_ = rb
        self.tb_ = tb
        self.npVars_ = npVars
        self.graphics_ = graphics
        self.total_sum_overflow_ = 0.0
        self.total_sum_overflow_unscaled_ = 0.0
        self.average_overflow_ = 0.0
        self.average_overflow_unscaled_ = 0.0
        self.diverge_snapshot_average_overflow_unscaled_ = 0.0
        self.min_hpwl_ = 2**63 - 1
        self.diverge_snapshot_iter_ = 0
        self.is_min_hpwl_ = False
        self.densityPenaltyStor_: List[float] = []
        self.baseWireLengthCoef_ = 0.0
        self.wireLengthCoefX_ = 0.0
        self.wireLengthCoefY_ = 0.0
        self.prevHpwl_ = 0
        self.num_region_diverged_ = 0
        self.is_routability_need_ = True
        self.divergeMsg_ = ""
        self.divergeCode_ = 0
        self.recursionCntWlCoef_ = 0
        self.recursionCntInitSLPCoef_ = 0
        self.placement_gif_key_ = -1
        self.routability_gif_key_ = -1
        self.db_cbk_: Optional[nesterovDbCbk] = None

    def doNesterovPlace(self, start_iter: int = 0) -> int:
        raise NotImplementedError("OpenROAD NesterovPlace main loop has not been translated yet")

    def updateWireLengthCoef(self, overflow: float) -> None:
        raise NotImplementedError("OpenROAD wirelength coefficient update has not been translated yet")

    def updateNextIter(self, iter: int) -> None:
        for nb in self.nbVec_:
            nb.setIter(iter)

    def updateDb(self) -> None:
        if self.nbc_ is not None:
            self.nbc_.updateDbGCells()

    def checkInvalidValues(self, wireLengthGradSum: float, densityGradSum: float) -> None:
        if wireLengthGradSum != wireLengthGradSum or densityGradSum != densityGradSum:
            raise ValueError("Invalid gradient value in NesterovPlace")

    def getWireLengthCoefX(self) -> float:
        return self.wireLengthCoefX_

    def getWireLengthCoefY(self) -> float:
        return self.wireLengthCoefY_

    def getNpVars(self) -> Optional[NesterovPlaceVars]:
        return self.npVars_

    def setTargetOverflow(self, overflow: float) -> None:
        if self.npVars_ is not None:
            self.npVars_.targetOverflow = overflow

    def setMaxIters(self, limit: int) -> None:
        if self.npVars_ is not None:
            self.npVars_.maxNesterovIter = limit

    def resizeGCell(self, inst: DbInst) -> None:
        raise NotImplementedError("OpenROAD resize callback has not been translated yet")

    def moveGCell(self, inst: DbInst) -> None:
        raise NotImplementedError("OpenROAD move callback has not been translated yet")

    def createCbkGCell(self, inst: DbInst) -> None:
        raise NotImplementedError("OpenROAD dbInst create callback has not been translated yet")

    def createGNet(self, net: DbNet) -> None:
        raise NotImplementedError("OpenROAD dbNet create callback has not been translated yet")

    def createCbkITerm(self, iterm: Any) -> None:
        raise NotImplementedError("OpenROAD dbITerm create callback has not been translated yet")

    def destroyCbkGCell(self, inst: DbInst) -> None:
        raise NotImplementedError("OpenROAD dbInst destroy callback has not been translated yet")

    def destroyCbkGNet(self, net: DbNet) -> None:
        raise NotImplementedError("OpenROAD dbNet destroy callback has not been translated yet")

    def destroyCbkITerm(self, iterm: Any) -> None:
        raise NotImplementedError("OpenROAD dbITerm destroy callback has not been translated yet")


class nesterovDbCbk:
    """对应 `gpl::nesterovDbCbk`。"""

    def __init__(self, nesterov_place: NesterovPlace):
        self.nesterov_place_ = nesterov_place

    def inDbInstCreate(self, inst: DbInst) -> None:
        self.nesterov_place_.createCbkGCell(inst)

    def inDbInstDestroy(self, inst: DbInst) -> None:
        self.nesterov_place_.destroyCbkGCell(inst)

    def inDbITermCreate(self, iterm: Any) -> None:
        self.nesterov_place_.createCbkITerm(iterm)

    def inDbITermDestroy(self, iterm: Any) -> None:
        self.nesterov_place_.destroyCbkITerm(iterm)

    def inDbNetCreate(self, net: DbNet) -> None:
        self.nesterov_place_.createGNet(net)

    def inDbNetDestroy(self, net: DbNet) -> None:
        self.nesterov_place_.destroyCbkGNet(net)

    def inDbInstSwapMasterAfter(self, inst: DbInst) -> None:
        self.nesterov_place_.resizeGCell(inst)

    def inDbPostMoveInst(self, inst: DbInst) -> None:
        self.nesterov_place_.moveGCell(inst)


class AbstractGraphics:
    """对应 `gpl::AbstractGraphics` 的 Python 抽象接口。"""

    def MakeNew(self, logger: Any) -> "AbstractGraphics":
        raise NotImplementedError

    def debugForMbff(self) -> None:
        raise NotImplementedError

    def debugForInitialPlace(self, pbc: PlacerBaseCommon, pbVec: List[PlacerBase]) -> None:
        raise NotImplementedError

    def debugForNesterovPlace(
        self,
        np: NesterovPlace,
        pbc: PlacerBaseCommon,
        nbc: NesterovBaseCommon,
        rb: RouteBase,
        pbVec: List[PlacerBase],
        nbVec: List[NesterovBase],
        draw_bins: bool,
        inst: Optional[DbInst],
    ) -> None:
        raise NotImplementedError

    def cellPlot(self, pause: bool = False) -> None:
        self.cellPlotImpl(pause)

    def addIter(self, iter: int, overflow: float) -> None:
        raise NotImplementedError

    def addTimingDrivenIter(self, iter: int) -> None:
        raise NotImplementedError

    def addRoutabilitySnapshot(self, iter: int) -> None:
        raise NotImplementedError

    def addRoutabilityIter(self, iter: int, revert: bool) -> None:
        raise NotImplementedError

    def mbffMapping(self, segs: Sequence[Any]) -> None:
        raise NotImplementedError

    def mbffFlopClusters(self, ffs: Sequence[DbInst]) -> None:
        raise NotImplementedError

    def status(self, message: str) -> None:
        raise NotImplementedError

    def enabled(self) -> bool:
        raise NotImplementedError

    def setDebugOn(self, set_on: bool) -> None:
        raise NotImplementedError

    def cellPlotImpl(self, pause: bool) -> None:
        raise NotImplementedError


class GraphicsNone(AbstractGraphics):
    """对应 OpenROAD `GraphicsNone`，默认无图形后端。"""

    def __init__(self, logger: Any = None):
        self.logger = logger
        self.debug_on = False

    def MakeNew(self, logger: Any) -> "GraphicsNone":
        return GraphicsNone(logger)

    def debugForMbff(self) -> None:
        self.debug_on = True

    def debugForInitialPlace(self, pbc: PlacerBaseCommon, pbVec: List[PlacerBase]) -> None:
        self.debug_on = True

    def debugForNesterovPlace(
        self,
        np: NesterovPlace,
        pbc: PlacerBaseCommon,
        nbc: NesterovBaseCommon,
        rb: RouteBase,
        pbVec: List[PlacerBase],
        nbVec: List[NesterovBase],
        draw_bins: bool,
        inst: Optional[DbInst],
    ) -> None:
        self.debug_on = True

    def addIter(self, iter: int, overflow: float) -> None:
        return None

    def addTimingDrivenIter(self, iter: int) -> None:
        return None

    def addRoutabilitySnapshot(self, iter: int) -> None:
        return None

    def addRoutabilityIter(self, iter: int, revert: bool) -> None:
        return None

    def mbffMapping(self, segs: Sequence[Any]) -> None:
        return None

    def mbffFlopClusters(self, ffs: Sequence[DbInst]) -> None:
        return None

    def status(self, message: str) -> None:
        return None

    def enabled(self) -> bool:
        return False

    def setDebugOn(self, set_on: bool) -> None:
        self.debug_on = set_on

    def cellPlotImpl(self, pause: bool) -> None:
        return None


def isValidSigType(db_type: SigType) -> bool:
    """对应 `isValidSigType`：GPL 只处理 SIGNAL/CLOCK。"""

    return db_type in {SigType.SIGNAL, SigType.CLOCK}


class Replace:
    """对应 `gpl::Replace`，OpenROAD gpl 顶层入口类。"""

    def __init__(
        self,
        odb: Optional[DbDatabase],
        sta: Any = None,
        resizer: Any = None,
        router: Any = None,
        logger: Any = None,
    ):
        self.db_ = odb
        self.sta_ = sta
        self.rs_ = resizer
        self.fr_ = router
        self.log_ = logger
        self.graphics_: AbstractGraphics = GraphicsNone(logger)
        self.pbc_: Optional[PlacerBaseCommon] = None
        self.nbc_: Optional[NesterovBaseCommon] = None
        self.pbVec_: List[PlacerBase] = []
        self.nbVec_: List[NesterovBase] = []
        self.rb_: Optional[RouteBase] = None
        self.tb_: Optional[TimingBase] = None
        self.ip_: Optional[InitialPlace] = None
        self.np_: Optional[NesterovPlace] = None
        self.total_placeable_insts_ = 0
        self.clusters_: Clusters = []
        self.gui_debug_ = False
        self.gui_debug_pause_iterations_ = 10
        self.gui_debug_update_iterations_ = 10
        self.gui_debug_draw_bins_ = False
        self.gui_debug_initial_ = False
        self.gui_debug_inst_: Optional[DbInst] = None
        self.gui_debug_start_iter_ = 0
        self.gui_debug_rudy_start_ = 0
        self.gui_debug_rudy_stride_ = 0
        self.gui_debug_generate_images_ = False
        self.gui_debug_images_path_ = "REPORTS_DIR"

    def setGraphicsInterface(self, graphics: AbstractGraphics) -> None:
        self.graphics_ = graphics.MakeNew(self.log_)

    def reset(self) -> None:
        self.ip_ = None
        self.np_ = None
        self.pbc_ = None
        self.nbc_ = None
        self.pbVec_.clear()
        self.nbVec_.clear()
        self.tb_ = None
        self.rb_ = None

    def addPlacementCluster(self, cluster: Cluster) -> None:
        self.clusters_.append(cluster)

    def checkHasCoreRows(self) -> None:
        block = _get_block(self.db_)
        if block is None:
            raise ValueError("No block defined in design")
        if getattr(block, "die_area", None) is None and getattr(block, "bbox", None) is None:
            raise ValueError("No rows/core area defined in design")

    def doIncrementalPlace(self, threads: int, options: Optional[PlaceOptions] = None) -> None:
        options = options or PlaceOptions()
        self.checkHasCoreRows()
        if self.pbc_ is None:
            self.pbc_ = PlacerBaseCommon(self.db_, options, self.log_)  # type: ignore[arg-type]
            for inst in self.pbc_.placeInsts():
                db_inst = inst.dbInst()
                if db_inst is not None and db_inst.status == PlacementStatus.PLACED:
                    inst.lock()
            self.pbVec_.append(PlacerBase(self.db_, self.pbc_, self.log_, True))
            self.total_placeable_insts_ = sum(len(pb.placeInsts()) for pb in self.pbVec_)
        self.doInitialPlace(threads, options)
        iter_count = self.doNesterovPlace(threads, options)
        for pb in self.pbVec_:
            pb.unlockAll()
        if options.overflow < 0.2:
            final_options = PlaceOptions(**{**options.__dict__})
            final_options.uniformTargetDensityMode = True
            final_options.initDensityPenaltyFactor = 1
            self.doNesterovPlace(threads, final_options, iter_count + 1)

    def doPlace(self, threads: int, options: Optional[PlaceOptions] = None) -> None:
        options = options or PlaceOptions()
        self.doInitialPlace(threads, options)
        self.doNesterovPlace(threads, options)

    def doInitialPlace(self, threads: int, options: Optional[PlaceOptions] = None) -> None:
        options = options or PlaceOptions()
        self.checkHasCoreRows()
        if self.pbc_ is None:
            self.pbc_ = PlacerBaseCommon(self.db_, options, self.log_)  # type: ignore[arg-type]
            self.pbVec_.append(PlacerBase(self.db_, self.pbc_, self.log_, True))
            if self.pbVec_ and not self.pbVec_[0].placeInsts():
                self.pbVec_.pop(0)
            self.total_placeable_insts_ = sum(len(pb.placeInsts()) for pb in self.pbVec_)
        ipVars = InitialPlaceVars.from_options(options, self.gui_debug_initial_)
        self.ip_ = InitialPlace(ipVars, self.pbc_, self.pbVec_, self.graphics_.MakeNew(self.log_), self.log_)  # type: ignore[arg-type]
        self.ip_.doBicgstabPlace(threads)

    def doNesterovPlace(self, threads: int, options: Optional[PlaceOptions] = None, start_iter: int = 0) -> int:
        options = options or PlaceOptions()
        self.checkHasCoreRows()
        if not self.initNesterovPlace(options, threads, True):
            return 0
        if options.timingDrivenMode and self.rs_ is not None and hasattr(self.rs_, "resizeSlackPreamble"):
            self.rs_.resizeSlackPreamble()
        assert self.np_ is not None
        return self.np_.doNesterovPlace(start_iter)

    def runMBFF(self, max_sz: int, alpha: float, beta: float, threads: int, num_paths: int) -> None:
        raise NotImplementedError("OpenROAD MBFF clustering has not been translated yet")

    def initNesterovPlace(self, options: PlaceOptions, threads: int, check_density: bool) -> bool:
        if self.pbc_ is None:
            self.pbc_ = PlacerBaseCommon(self.db_, options, self.log_)  # type: ignore[arg-type]
            self.pbVec_.append(PlacerBase(self.db_, self.pbc_, self.log_, check_density))
            self.total_placeable_insts_ = sum(len(pb.placeInsts()) for pb in self.pbVec_)
        if self.total_placeable_insts_ == 0:
            return False
        if self.nbc_ is None:
            nbVars = NesterovBaseVars.from_options(options)
            self.nbc_ = NesterovBaseCommon(nbVars, self.pbc_, self.log_, threads, self.clusters_)
            for pb in self.pbVec_:
                self.nbVec_.append(NesterovBase(nbVars, pb, self.nbc_, self.log_))
        if self.rb_ is None:
            self.rb_ = RouteBase(RouteBaseVars.from_options(options), self.db_, self.fr_, self.nbc_, self.nbVec_, self.log_)
        if self.tb_ is None:
            self.tb_ = TimingBase(self.nbc_, self.fr_, self.rs_, self.log_)
            self.tb_.setTimingNetWeightOverflows(options.timingNetWeightOverflows)
            self.tb_.setTimingNetWeightMax(options.timingNetWeightMax)
        if self.np_ is None:
            npVars = NesterovPlaceVars.from_options(options)
            npVars.debug = self.gui_debug_
            npVars.debug_pause_iterations = self.gui_debug_pause_iterations_
            npVars.debug_update_iterations = self.gui_debug_update_iterations_
            npVars.debug_draw_bins = self.gui_debug_draw_bins_
            npVars.debug_inst = self.gui_debug_inst_
            npVars.debug_start_iter = self.gui_debug_start_iter_
            npVars.debug_rudy_start = self.gui_debug_rudy_start_
            npVars.debug_rudy_stride = self.gui_debug_rudy_stride_
            npVars.debug_generate_images = self.gui_debug_generate_images_
            npVars.debug_images_path = self.gui_debug_images_path_
            for nb in self.nbVec_:
                nb.setNpVars(npVars)
            self.np_ = NesterovPlace(npVars, self.pbc_, self.nbc_, self.pbVec_, self.nbVec_, self.rb_, self.tb_, self.graphics_.MakeNew(self.log_), self.log_)
        self.np_.setTargetOverflow(options.overflow)
        self.np_.setMaxIters(options.nesterovPlaceMaxIter)
        return True

    def getUniformTargetDensity(self, options: Optional[PlaceOptions] = None, threads: int = 1) -> float:
        options = options or PlaceOptions()
        options_no_io = PlaceOptions(**{**options.__dict__})
        options_no_io.skipIo()
        if self.initNesterovPlace(options_no_io, threads, False) and self.nbVec_:
            return self.nbVec_[0].getUniformTargetDensity()
        return 1.0

    def setDebug(
        self,
        pause_iterations: int,
        update_iterations: int,
        draw_bins: bool,
        initial: bool,
        inst: Optional[DbInst],
        start_iter: int,
        start_rudy: int,
        rudy_stride: int,
        generate_images: bool,
        images_path: str,
    ) -> None:
        self.gui_debug_ = True
        self.gui_debug_pause_iterations_ = pause_iterations
        self.gui_debug_update_iterations_ = update_iterations
        self.gui_debug_draw_bins_ = draw_bins
        self.gui_debug_initial_ = initial
        self.gui_debug_inst_ = inst
        self.gui_debug_start_iter_ = start_iter
        self.gui_debug_rudy_start_ = start_rudy
        self.gui_debug_rudy_stride_ = rudy_stride
        self.gui_debug_generate_images_ = generate_images
        self.gui_debug_images_path_ = images_path


def make_replace(
    odb: Optional[DbDatabase],
    sta: Any = None,
    resizer: Any = None,
    router: Any = None,
    logger: Any = None,
) -> Replace:
    """对应 `makeReplace()` 风格的 Python 工厂。"""

    return Replace(odb, sta, resizer, router, logger)


__all__ = [
    "AbstractGraphics",
    "Bin",
    "BinGrid",
    "Cluster",
    "Clusters",
    "Die",
    "FloatPoint",
    "GCell",
    "GCellChange",
    "GNet",
    "GPin",
    "GraphicsNone",
    "InitialPlace",
    "InitialPlaceVars",
    "Instance",
    "Net",
    "NesterovBase",
    "NesterovBaseCommon",
    "NesterovBaseVars",
    "NesterovPlace",
    "NesterovPlaceVars",
    "Pin",
    "PlaceOptions",
    "PlacerBase",
    "PlacerBaseCommon",
    "PlacerBaseVars",
    "Replace",
    "RouteBase",
    "RouteBaseVars",
    "Tile",
    "TileGrid",
    "TimingBase",
    "isValidSigType",
    "make_replace",
    "nesterovDbCbk",
]
