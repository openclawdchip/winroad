"""Nesterov placement object layer for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..odb import DbInst, DbNet
from .common import Cluster, Clusters, _area
from .options import PlaceOptions
from .placer_base import Instance, Net, Pin, PlacerBase, PlacerBaseCommon

@dataclass
class FloatPoint:
    """对应 `gpl::FloatPoint`。"""

    x: float = 0.0
    y: float = 0.0


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

    def setMaxExpSumX(self, maxExpSumX: float) -> None:
        self.maxExpSumX_ = maxExpSumX
        self.hasMaxExpSumX_ = True

    def setMaxExpSumY(self, maxExpSumY: float) -> None:
        self.maxExpSumY_ = maxExpSumY
        self.hasMaxExpSumY_ = True

    def setMinExpSumX(self, minExpSumX: float) -> None:
        self.minExpSumX_ = minExpSumX
        self.hasMinExpSumX_ = True

    def setMinExpSumY(self, minExpSumY: float) -> None:
        self.minExpSumY_ = minExpSumY
        self.hasMinExpSumY_ = True

    def maxExpSumX(self) -> float:
        return self.maxExpSumX_

    def maxExpSumY(self) -> float:
        return self.maxExpSumY_

    def minExpSumX(self) -> float:
        return self.minExpSumX_

    def minExpSumY(self) -> float:
        return self.minExpSumY_

    def hasMaxExpSumX(self) -> bool:
        return self.hasMaxExpSumX_

    def hasMaxExpSumY(self) -> bool:
        return self.hasMaxExpSumY_

    def hasMinExpSumX(self) -> bool:
        return self.hasMinExpSumX_

    def hasMinExpSumY(self) -> bool:
        return self.hasMinExpSumY_

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

    def waExpMinSumX(self) -> float:
        return self.waExpMinSumX_

    def waXExpMinSumX(self) -> float:
        return self.waXExpMinSumX_

    def waExpMinSumY(self) -> float:
        return self.waExpMinSumY_

    def waYExpMinSumY(self) -> float:
        return self.waYExpMinSumY_

    def waExpMaxSumX(self) -> float:
        return self.waExpMaxSumX_

    def waXExpMaxSumX(self) -> float:
        return self.waXExpMaxSumX_

    def waExpMaxSumY(self) -> float:
        return self.waExpMaxSumY_

    def waYExpMaxSumY(self) -> float:
        return self.waYExpMaxSumY_


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

    def electroForceX(self) -> float:
        """C++ 旧命名兼容：当前源码中等价于 electroFieldX。"""

        return self.electroFieldX_

    def electroForceY(self) -> float:
        """C++ 旧命名兼容：当前源码中等价于 electroFieldY。"""

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

    def setElectroForce(self, electroForceX: float, electroForceY: float) -> None:
        """C++ 旧命名兼容：当前源码中等价于 setElectroField。"""

        self.setElectroField(electroForceX, electroForceY)

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

    def updateBinsGCellDensityArea(self, cells: Sequence[GCell]) -> None:
        for bin_obj in self.bins_:
            bin_obj.setInstPlacedArea(0)
            bin_obj.setInstPlacedAreaUnscaled(0)
            bin_obj.setFillerArea(0)
            bin_obj.setDensity(0.0)
        for gcell in cells:
            min_x, max_x = self.getDensityMinMaxIdxX(gcell)
            min_y, max_y = self.getDensityMinMaxIdxY(gcell)
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    bin_obj = self.bins_[y * self.binCntX_ + x]
                    overlap = self._overlap_area(
                        (gcell.dLx(), gcell.dLy(), gcell.dUx(), gcell.dUy()),
                        (bin_obj.lx(), bin_obj.ly(), bin_obj.ux(), bin_obj.uy()),
                    )
                    if overlap <= 0:
                        continue
                    if gcell.isFiller():
                        bin_obj.addFillerArea(overlap)
                    else:
                        bin_obj.addInstPlacedArea(overlap)
                        bin_obj.addInstPlacedAreaUnscaled(overlap)
        self.sumOverflowArea_ = 0
        self.sumOverflowAreaUnscaled_ = 0
        for bin_obj in self.bins_:
            bin_area = max(1, bin_obj.getBinArea())
            place_area = bin_obj.instPlacedArea() + bin_obj.getFillerArea()
            density = place_area / bin_area
            bin_obj.setDensity(density)
            allowed = int(round(bin_area * bin_obj.getTargetDensity()))
            overflow = max(0, place_area + bin_obj.getNonPlaceArea() - allowed)
            overflow_unscaled = max(0, bin_obj.getInstPlacedAreaUnscaled() + bin_obj.getNonPlaceAreaUnscaled() - allowed)
            self.sumOverflowArea_ += overflow
            self.sumOverflowAreaUnscaled_ += overflow_unscaled

    def _overlap_area(self, lhs: Tuple[int, int, int, int], rhs: Tuple[int, int, int, int]) -> int:
        lx = max(lhs[0], rhs[0])
        ly = max(lhs[1], rhs[1])
        ux = min(lhs[2], rhs[2])
        uy = min(lhs[3], rhs[3])
        return _area((lx, ly, ux, uy))

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

    def getDensityMinMaxIdxX(self, gcell: GCell) -> Tuple[int, int]:
        return self._range_to_bin_idx(gcell.dLx(), gcell.dUx(), self.lx_, self.binSizeX_, self.binCntX_)

    def getDensityMinMaxIdxY(self, gcell: GCell) -> Tuple[int, int]:
        return self._range_to_bin_idx(gcell.dLy(), gcell.dUy(), self.ly_, self.binSizeY_, self.binCntY_)

    def getMinMaxIdxX(self, inst: Instance) -> Tuple[int, int]:
        return self._range_to_bin_idx(inst.lx(), inst.ux(), self.lx_, self.binSizeX_, self.binCntX_)

    def getMinMaxIdxY(self, inst: Instance) -> Tuple[int, int]:
        return self._range_to_bin_idx(inst.ly(), inst.uy(), self.ly_, self.binSizeY_, self.binCntY_)

    def _range_to_bin_idx(self, low: int, high: int, origin: int, size: float, count: int) -> Tuple[int, int]:
        if count <= 0 or size <= 0:
            return (0, 0)
        min_idx = int((low - origin) // size)
        max_idx = int(((high - origin) - 1) // size) if high > low else min_idx
        min_idx = min(max(min_idx, 0), count - 1)
        max_idx = min(max(max_idx, 0), count - 1)
        return (min_idx, max_idx)

    def getBins(self) -> List[Bin]:
        return self.bins_

    def getBinsConst(self) -> List[Bin]:
        return self.bins_

    def updateBinsNonPlaceArea(self) -> None:
        for bin_obj in self.bins_:
            bin_obj.setNonPlaceArea(0)
            bin_obj.setNonPlaceAreaUnscaled(0)
        if self.pb_ is None:
            return
        for inst in self.pb_.nonPlaceInsts():
            min_x, max_x = self.getMinMaxIdxX(inst)
            min_y, max_y = self.getMinMaxIdxY(inst)
            inst_rect = (inst.lx(), inst.ly(), inst.ux(), inst.uy())
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    bin_obj = self.bins_[y * self.binCntX_ + x]
                    overlap = self._overlap_area(inst_rect, (bin_obj.lx(), bin_obj.ly(), bin_obj.ux(), bin_obj.uy()))
                    bin_obj.addNonPlaceArea(overlap)
                    bin_obj.addNonPlaceAreaUnscaled(overlap)


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
        self.changed_gcells_: List[GCell] = []
        self.timing_driven_net_reweight_overflow_: List[int] = []
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
            self.gNetMap_[id(net)] = gnet
        self.rebuildPinRelationships()

    def rebuildPinRelationships(self) -> None:
        self.gPinStor_.clear()
        self.gPins_.clear()
        self.gPinMap_.clear()
        for gcell in self.nbc_gcells_:
            gcell.clearGPins()
        for gnet in self.gNets_:
            gnet.clearGPins()
        for pin in self.pbc_.getPins():
            gpin = GPin.from_pin(pin)
            inst = pin.getInstance()
            net = pin.getNet()
            gcell = self.pbToNb(inst) if inst is not None else None
            gnet = self.pbToNb(net) if net is not None else None
            if gcell is not None:
                gcell.addGPin(gpin)
            if gnet is not None:
                gnet.addGPin(gpin)
            self.gPinStor_.append(gpin)
            self.gPins_.append(gpin)
            self.gPinMap_[id(pin)] = gpin

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

    def updateWireLengthForceWAInit(self, wlCoeffX: float, wlCoeffY: float) -> None:
        raise NotImplementedError("OpenROAD WA wirelength force init has not been translated yet")

    def getWireLengthGradientPinWA(self, gPin: GPin, wlCoeffX: float, wlCoeffY: float) -> FloatPoint:
        raise NotImplementedError("OpenROAD WA pin gradient has not been translated yet")

    def getWireLengthGradientWA(self, gCell: GCell, wlCoeffX: float, wlCoeffY: float) -> FloatPoint:
        raise NotImplementedError("OpenROAD WA cell gradient has not been translated yet")

    def getWireLengthPreconditioner(self, gCell: GCell) -> FloatPoint:
        raise NotImplementedError("OpenROAD wirelength preconditioner has not been translated yet")

    def updatePinLocation(self) -> None:
        for gpin in self.gPins_:
            gpin.updateLocation()

    def updateDensityPinLocation(self) -> None:
        for gpin in self.gPins_:
            gpin.updateDensityLocation()

    def updateGNetBox(self) -> None:
        for gnet in self.gNets_:
            gnet.updateBox()

    def setTimingNetWeight(self, net: Net, weight: float) -> None:
        gnet = self.pbToNb(net)
        if gnet is not None:
            gnet.setTimingWeight(weight)

    def resetTimingNetWeights(self) -> None:
        for gnet in self.gNets_:
            gnet.setTimingWeight(1.0)

    def addChangedGCell(self, gcell: GCell) -> None:
        if gcell not in self.changed_gcells_:
            self.changed_gcells_.append(gcell)

    def clearChangedGCells(self) -> None:
        self.changed_gcells_.clear()

    def changedGCells(self) -> List[GCell]:
        return self.changed_gcells_

    def getHpwl(self) -> int:
        return sum(gnet.getHpwl() for gnet in self.gNets_)

    def updateDbGCells(self) -> None:
        for gcell in self.nbc_gcells_:
            gcell.updateLocations()
            for inst in gcell.insts():
                inst.dbSetLocation()

    def addGCellForInstance(self, inst: Instance) -> GCell:
        existing = self.gCellMap_.get(id(inst))
        if existing is not None:
            return existing
        gcell = GCell.from_instance(inst)
        self.gCellStor_.append(gcell)
        self.nbc_gcells_.append(gcell)
        self.gCellMap_[id(inst)] = gcell
        self.new_gcells_count_ += 1
        self.delta_area_ += gcell.dx() * gcell.dy()
        self.addChangedGCell(gcell)
        return gcell

    def removeGCellForInstance(self, inst: Instance) -> Optional[GCell]:
        gcell = self.gCellMap_.pop(id(inst), None)
        if gcell is None:
            return None
        for gcells in (self.nbc_gcells_, self.gCellStor_):
            if gcell in gcells:
                gcells.remove(gcell)
        self.deleted_gcells_count_ += 1
        self.delta_area_ -= gcell.dx() * gcell.dy()
        return gcell

    def addGNetForNet(self, net: Net) -> GNet:
        existing = self.gNetMap_.get(id(net))
        if existing is not None:
            return existing
        gnet = GNet.from_net(net)
        self.gNetStor_.append(gnet)
        self.gNets_.append(gnet)
        self.gNetMap_[id(net)] = gnet
        return gnet

    def removeGNetForNet(self, net: Net) -> Optional[GNet]:
        gnet = self.gNetMap_.pop(id(net), None)
        if gnet is None:
            return None
        for gnets in (self.gNets_, self.gNetStor_):
            if gnet in gnets:
                gnets.remove(gnet)
        return gnet

    def reportStatus(self) -> Dict[str, Any]:
        return {
            "gcells": len(self.nbc_gcells_),
            "gnets": len(self.gNets_),
            "gpins": len(self.gPins_),
            "changed_gcells": len(self.changed_gcells_),
            "delta_area": self.delta_area_,
            "new_gcells": self.new_gcells_count_,
            "deleted_gcells": self.deleted_gcells_count_,
            "hpwl": self.getHpwl(),
        }

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
        self.snapshot_gcell_coordis_: List[FloatPoint] = []
        self.snapshot_density_coordis_: List[FloatPoint] = []
        self.prevSLPCoordi_: List[FloatPoint] = []
        self.curSLPCoordi_: List[FloatPoint] = []
        self.nextSLPCoordi_: List[FloatPoint] = []
        self.prevSLPGradient_: List[FloatPoint] = []
        self.curSLPGradient_: List[FloatPoint] = []
        self.nextSLPGradient_: List[FloatPoint] = []
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
        self.whiteSpaceArea_ = max(0, self.pb_.getRegionArea() - self.pb_.nonPlaceInstsArea())

    def initFillerGCells(self) -> None:
        raise NotImplementedError("OpenROAD filler creation and placement has not been translated yet")

    def resetFillerGCells(self) -> None:
        self.fillerStor_.clear()
        self.nb_gcells_ = [cell for cell in self.nb_gcells_ if not cell.isFiller()]
        self.updateAreas()

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

    def updateWireLengthForceWA(self, wlCoeffX: float, wlCoeffY: float) -> None:
        self.nbc_.updateWireLengthForceWA(wlCoeffX, wlCoeffY)

    def updateWireLengthForceWAInit(self, wlCoeffX: float, wlCoeffY: float) -> None:
        self.nbc_.updateWireLengthForceWAInit(wlCoeffX, wlCoeffY)

    def updateGCellDensityCenterLocation(self) -> None:
        for gcell in self.nb_gcells_:
            gcell.setDensityCenterLocation(gcell.cx(), gcell.cy())
            self.updateDensityCoordiLayoutInside(gcell)

    def updateInitialPrevSLPCoordi(self) -> None:
        self.prevSLPCoordi_ = [FloatPoint(cell.cx(), cell.cy()) for cell in self.nb_gcells_]

    def updateCurSLPCoordi(self) -> None:
        self.curSLPCoordi_ = [FloatPoint(cell.cx(), cell.cy()) for cell in self.nb_gcells_]

    def updateNextSLPCoordi(self) -> None:
        self.nextSLPCoordi_ = [FloatPoint(cell.cx(), cell.cy()) for cell in self.nb_gcells_]

    def updatePrevGradient(self) -> None:
        self.prevSLPGradient_ = list(self.curSLPGradient_)

    def updateCurGradient(self) -> None:
        raise NotImplementedError("OpenROAD current SLP gradient update has not been translated yet")

    def updateNextGradient(self) -> None:
        raise NotImplementedError("OpenROAD next SLP gradient update has not been translated yet")

    def updatePrevSLPCoordi(self) -> None:
        self.prevSLPCoordi_ = list(self.curSLPCoordi_)

    def updateDensityCenterCoordiLayoutInside(self) -> None:
        for gcell in self.nb_gcells_:
            self.updateDensityCoordiLayoutInside(gcell)

    def refreshDensityMetrics(self) -> None:
        self.bg_.updateBinsNonPlaceArea()
        self.bg_.updateBinsGCellDensityArea(self.nb_gcells_)
        area = max(1, self.pb_.getRegionArea())
        self.sum_overflow_ = self.bg_.getOverflowArea() / area
        self.sum_overflow_unscaled_ = self.bg_.getOverflowAreaUnscaled() / area

    def getBinGrid(self) -> BinGrid:
        return self.bg_

    def initDensity1(self) -> None:
        raise NotImplementedError("OpenROAD Nesterov initDensity1 has not been translated yet")

    def initDensity2(self, wlCoeffX: float, wlCoeffY: float) -> float:
        raise NotImplementedError("OpenROAD Nesterov initDensity2 has not been translated yet")

    def initBaseWireLengthCoef(self) -> None:
        raise NotImplementedError("OpenROAD base wirelength coefficient initialization has not been translated yet")

    def initDensityPenalty(self, init_density_penalty: float) -> None:
        self.densityPenalty_ = init_density_penalty

    def updateDensityPenalty(self, overflow: float) -> None:
        raise NotImplementedError("OpenROAD density penalty update has not been translated yet")

    def updatePhiCoef(self, overflow: float) -> None:
        raise NotImplementedError("OpenROAD phi coefficient update has not been translated yet")

    def updateGradSum(self) -> None:
        raise NotImplementedError("OpenROAD gradient sum update has not been translated yet")

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
        self.snapshot_gcell_coordis_ = [FloatPoint(cell.cx(), cell.cy()) for cell in self.nb_gcells_]
        self.snapshot_density_coordis_ = [FloatPoint(cell.dCx(), cell.dCy()) for cell in self.nb_gcells_]

    def revertToSnapshot(self) -> bool:
        if not self.snapshot_gcell_coordis_:
            return False
        self.updateGCellCenterLocation(self.snapshot_gcell_coordis_)
        for gcell, coord in zip(self.nb_gcells_, self.snapshot_density_coordis_):
            gcell.setDensityCenterLocation(int(round(coord.x)), int(round(coord.y)))
        self.nbc_.updatePinLocation()
        self.nbc_.updateGNetBox()
        return True

    def resetMinSumOverflow(self) -> None:
        return None

    def isDiverged(self) -> bool:
        return self.isDiverged_

    def getPb(self) -> PlacerBase:
        return self.pb_

    def getGroup(self) -> Any:
        return self.pb_.getGroup()


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
        self.last_iter_ = 0
        self.timing_driven_iter_ = 0
        self.routability_iter_ = 0
        self.snapshot_saved_ = False
        self.last_report_: Dict[str, Any] = {}
        self.db_cbk_: Optional[nesterovDbCbk] = None

    def doNesterovPlace(self, start_iter: int = 0) -> int:
        self.last_iter_ = start_iter
        if self.graphics_ is not None and self.npVars_ is not None and self.npVars_.debug:
            self.graphics_.debugForNesterovPlace(
                self,
                self.pbc_,  # type: ignore[arg-type]
                self.nbc_,  # type: ignore[arg-type]
                self.rb_,  # type: ignore[arg-type]
                self.pbVec_,
                self.nbVec_,
                self.npVars_.debug_draw_bins,
                self.npVars_.debug_inst,
            )
        raise NotImplementedError("OpenROAD NesterovPlace main loop has not been translated yet")

    def init(self) -> None:
        raise NotImplementedError("OpenROAD NesterovPlace initialization sequence has not been translated yet")

    def initWireLengthCoef(self) -> None:
        raise NotImplementedError("OpenROAD initial wirelength coefficient calculation has not been translated yet")

    def updateWireLengthCoef(self, overflow: float) -> None:
        raise NotImplementedError("OpenROAD wirelength coefficient update has not been translated yet")

    def updateInitialPrevSLPCoordi(self) -> None:
        for nb in self.nbVec_:
            nb.updateInitialPrevSLPCoordi()

    def updateCurSLPCoordi(self) -> None:
        for nb in self.nbVec_:
            nb.updateCurSLPCoordi()

    def updateNextSLPCoordi(self) -> None:
        for nb in self.nbVec_:
            nb.updateNextSLPCoordi()

    def updatePrevGradient(self) -> None:
        for nb in self.nbVec_:
            nb.updatePrevGradient()

    def updateCurGradient(self) -> None:
        for nb in self.nbVec_:
            nb.updateCurGradient()

    def updateNextGradient(self) -> None:
        for nb in self.nbVec_:
            nb.updateNextGradient()

    def updatePrevSLPCoordi(self) -> None:
        for nb in self.nbVec_:
            nb.updatePrevSLPCoordi()

    def updateNextIter(self, iter: int) -> None:
        for nb in self.nbVec_:
            nb.setIter(iter)

    def updateDb(self) -> None:
        if self.nbc_ is not None:
            self.nbc_.updateDbGCells()

    def updateGCellDensityCenterLocation(self) -> None:
        for nb in self.nbVec_:
            nb.updateGCellDensityCenterLocation()

    def updateDensityCenterCoordiLayoutInside(self) -> None:
        for nb in self.nbVec_:
            nb.updateDensityCenterCoordiLayoutInside()

    def saveSnapshot(self) -> None:
        for nb in self.nbVec_:
            nb.saveSnapshot()
        self.diverge_snapshot_average_overflow_unscaled_ = self.average_overflow_unscaled_
        self.diverge_snapshot_iter_ = self.last_iter_
        self.snapshot_saved_ = True
        if self.graphics_ is not None:
            self.graphics_.addRoutabilitySnapshot(self.last_iter_)

    def revertToSnapshot(self) -> bool:
        reverted = all(nb.revertToSnapshot() for nb in self.nbVec_)
        if reverted:
            self.updateDb()
        return reverted

    def checkConvergence(self, iter: int, routability_iter: int) -> bool:
        return all(nb.checkConvergence(iter, routability_iter, self.rb_) for nb in self.nbVec_)

    def checkDivergence(self) -> bool:
        self.num_region_diverged_ = sum(1 for nb in self.nbVec_ if nb.checkDivergence())
        return self.num_region_diverged_ > 0

    def updateOverflow(self) -> None:
        for nb in self.nbVec_:
            nb.refreshDensityMetrics()
        self.total_sum_overflow_ = sum(nb.getSumOverflow() for nb in self.nbVec_)
        self.total_sum_overflow_unscaled_ = sum(nb.getSumOverflowUnscaled() for nb in self.nbVec_)
        count = max(1, len(self.nbVec_))
        self.average_overflow_ = self.total_sum_overflow_ / count
        self.average_overflow_unscaled_ = self.total_sum_overflow_unscaled_ / count

    def checkInvalidValues(self, wireLengthGradSum: float, densityGradSum: float) -> None:
        if wireLengthGradSum != wireLengthGradSum or densityGradSum != densityGradSum:
            raise ValueError("Invalid gradient value in NesterovPlace")

    def updateTiming(self, overflow: float) -> bool:
        if self.tb_ is None or self.npVars_ is None or not self.npVars_.timingDrivenMode:
            return False
        if self.tb_.isTimingNetWeightOverflow(overflow):
            self.timing_driven_iter_ += 1
            self.npVars_.timingDrivenIterCounter += 1
            if self.graphics_ is not None:
                self.graphics_.addTimingDrivenIter(self.last_iter_)
            return self.tb_.executeTimingDriven(False)
        return False

    def updateRoutability(self, routability_driven_revert_count: int) -> Tuple[bool, bool]:
        if self.rb_ is None or self.npVars_ is None or not self.npVars_.routability_driven_mode:
            return (False, False)
        self.routability_iter_ += 1
        result = self.rb_.routability(routability_driven_revert_count)
        if self.graphics_ is not None:
            self.graphics_.addRoutabilityIter(self.last_iter_, result[1])
        return result

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

    def reportStatus(self) -> Dict[str, Any]:
        self.last_report_ = {
            "iter": self.last_iter_,
            "average_overflow": self.average_overflow_,
            "average_overflow_unscaled": self.average_overflow_unscaled_,
            "total_sum_overflow": self.total_sum_overflow_,
            "hpwl": self.nbc_.getHpwl() if self.nbc_ is not None else 0,
            "min_hpwl": self.min_hpwl_,
            "num_region_diverged": self.num_region_diverged_,
            "timing_driven_iter": self.timing_driven_iter_,
            "routability_iter": self.routability_iter_,
            "snapshot_saved": self.snapshot_saved_,
            "diverge_snapshot_iter": self.diverge_snapshot_iter_,
            "diverge_code": self.divergeCode_,
            "diverge_message": self.divergeMsg_,
            "base_common": self.nbc_.reportStatus() if self.nbc_ is not None else {},
        }
        return self.last_report_

    def getLastReport(self) -> Dict[str, Any]:
        return self.last_report_

    def resizeGCell(self, inst: DbInst) -> None:
        if self.pbc_ is None or self.nbc_ is None:
            return
        pb_inst = self.pbc_.dbToPb(inst)
        gcell = self.nbc_.pbToNb(pb_inst)
        if pb_inst is None or gcell is None:
            return
        old_area = gcell.dx() * gcell.dy()
        pb_inst.copyDbLocation(self.pbc_)
        gcell.setAllLocations(pb_inst.lx(), pb_inst.ly(), pb_inst.ux(), pb_inst.uy())
        gcell.setDensitySize(gcell.dx(), gcell.dy())
        self.nbc_.delta_area_ += gcell.dx() * gcell.dy() - old_area
        self.nbc_.addChangedGCell(gcell)
        for nb in self.nbVec_:
            nb.updateAreas()

    def moveGCell(self, inst: DbInst) -> None:
        if self.pbc_ is None or self.nbc_ is None:
            return
        pb_inst = self.pbc_.dbToPb(inst)
        gcell = self.nbc_.pbToNb(pb_inst)
        if pb_inst is None or gcell is None:
            return
        pb_inst.copyDbLocation(self.pbc_)
        gcell.setAllLocations(pb_inst.lx(), pb_inst.ly(), pb_inst.ux(), pb_inst.uy())
        gcell.setDensityCenterLocation(gcell.cx(), gcell.cy())
        self.nbc_.addChangedGCell(gcell)
        self.nbc_.updatePinLocation()
        self.nbc_.updateGNetBox()

    def createCbkGCell(self, inst: DbInst) -> None:
        if self.pbc_ is None or self.nbc_ is None:
            return
        pb_inst = self.pbc_.addDbInst(inst)
        gcell = self.nbc_.addGCellForInstance(pb_inst)
        for nb in self.nbVec_:
            if gcell not in nb.nb_gcells_:
                nb.nb_gcells_.append(gcell)
                nb.updateAreas()

    def createGNet(self, net: DbNet) -> None:
        if self.pbc_ is None or self.nbc_ is None:
            return
        pb_net = self.pbc_.addDbNet(net)
        self.nbc_.addGNetForNet(pb_net)

    def createCbkITerm(self, iterm: Any) -> None:
        if self.nbc_ is not None:
            self.nbc_.rebuildPinRelationships()

    def destroyCbkGCell(self, inst: DbInst) -> None:
        if self.pbc_ is None or self.nbc_ is None:
            return
        pb_inst = self.pbc_.removeDbInst(inst)
        if pb_inst is None:
            return
        gcell = self.nbc_.removeGCellForInstance(pb_inst)
        if gcell is None:
            return
        for nb in self.nbVec_:
            if gcell in nb.nb_gcells_:
                nb.nb_gcells_.remove(gcell)
                nb.updateAreas()

    def destroyCbkGNet(self, net: DbNet) -> None:
        if self.pbc_ is None or self.nbc_ is None:
            return
        pb_net = self.pbc_.removeDbNet(net)
        if pb_net is not None:
            self.nbc_.removeGNetForNet(pb_net)

    def destroyCbkITerm(self, iterm: Any) -> None:
        if self.nbc_ is not None:
            self.nbc_.rebuildPinRelationships()


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


