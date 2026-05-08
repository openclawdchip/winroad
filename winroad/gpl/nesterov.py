"""Nesterov placement object layer for WinRoad gpl."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..odb import DbInst, DbNet
from .common import Cluster, Clusters, _area
from .options import PlaceOptions
from .placer_base import Instance, Net, Pin, PlacerBase, PlacerBaseCommon

_EXP_CLAMP = 60.0
REPLACE_SQRT2 = math.sqrt(2.0)
REPLACE_FFT_PI = math.pi


def _safe_exp(value: float) -> float:
    """限制指数范围，避免纯 Python WA 计算在大坐标设计上溢出。"""

    return math.exp(max(-_EXP_CLAMP, min(_EXP_CLAMP, value)))


def _safe_div(numer: float, denom: float) -> float:
    return numer / denom if abs(denom) > 1e-30 else 0.0


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
        if gPin not in self.gPins_:
            self.gPins_.append(gPin)
            gPin.setGCell(self)

    def clearGPins(self) -> None:
        for gpin in self.gPins_:
            if gpin.getGCell() is self:
                gpin.clearGCell()
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

    def area(self) -> int:
        return _area((self.lx_, self.ly_, self.ux_, self.uy_))

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

    def densityArea(self) -> int:
        return _area((self.dLx_, self.dLy_, self.dUx_, self.dUy_))

    def setLocation(self, lx: int, ly: int) -> None:
        dx, dy = self.dx(), self.dy()
        self.lx_, self.ly_, self.ux_, self.uy_ = lx, ly, lx + dx, ly + dy

    def setCenterLocation(self, cx: int, cy: int) -> None:
        dx, dy = self.dx(), self.dy()
        self.lx_, self.ly_, self.ux_, self.uy_ = cx - dx // 2, cy - dy // 2, cx - dx // 2 + dx, cy - dy // 2 + dy

    def setSize(self, dx: int, dy: int, change: GCellChange = GCellChange.kNone) -> None:
        cx, cy = self.cx(), self.cy()
        self.lx_, self.ly_, self.ux_, self.uy_ = cx - dx // 2, cy - dy // 2, cx - dx // 2 + dx, cy - dy // 2 + dy
        self.setDensitySize(dx, dy)
        self.change_ = change

    def setAreaChangeType(self, change: GCellChange) -> None:
        self.change_ = change

    def changeType(self) -> GCellChange:
        return self.change_

    def setAllLocations(self, lx: int, ly: int, ux: int, uy: int) -> None:
        self.lx_, self.ly_, self.ux_, self.uy_ = lx, ly, ux, uy

    def setDensityBox(self, dLx: int, dLy: int, dUx: int, dUy: int) -> None:
        self.dLx_, self.dLy_, self.dUx_, self.dUy_ = dLx, dLy, dUx, dUy

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

    def report(self) -> Dict[str, Any]:
        """导出 gcell 纯状态；不包含电势/梯度求解结果。"""

        return {
            "name": self.getName(),
            "is_instance": self.isInstance(),
            "is_filler": self.isFiller(),
            "is_macro": self.isMacroInstance(),
            "location": (self.lx_, self.ly_, self.ux_, self.uy_),
            "density_box": (self.dLx_, self.dLy_, self.dUx_, self.dUy_),
            "area": self.area(),
            "density_area": self.densityArea(),
            "density_scale": self.densityScale_,
            "gradient": (self.gradientX_, self.gradientY_),
            "change": self.change_.value,
            "gpins": len(self.gPins_),
            "insts": len(self.insts_),
        }


@dataclass
class GCellSnapshot:
    """保存 Nesterov snapshot 中单个 GCell 的可恢复状态。"""

    location: Tuple[int, int, int, int]
    density_box: Tuple[int, int, int, int]
    density_scale: float
    gradient: Tuple[float, float]
    change: GCellChange

    @classmethod
    def from_gcell(cls, gcell: GCell) -> "GCellSnapshot":
        return cls(
            location=(gcell.lx(), gcell.ly(), gcell.ux(), gcell.uy()),
            density_box=(gcell.dLx(), gcell.dLy(), gcell.dUx(), gcell.dUy()),
            density_scale=gcell.getDensityScale(),
            gradient=(gcell.getGradientX(), gcell.getGradientY()),
            change=gcell.changeType(),
        )

    def restore(self, gcell: GCell) -> None:
        lx, ly, ux, uy = self.location
        d_lx, d_ly, d_ux, d_uy = self.density_box
        grad_x, grad_y = self.gradient
        gcell.setAllLocations(lx, ly, ux, uy)
        gcell.setDensityBox(d_lx, d_ly, d_ux, d_uy)
        gcell.setDensityScale(self.density_scale)
        gcell.setGradientX(grad_x)
        gcell.setGradientY(grad_y)
        gcell.setAreaChangeType(self.change)


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

    def clearGCell(self) -> None:
        self.gCell_ = None

    def clearGNet(self) -> None:
        self.gNet_ = None

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

    def report(self) -> Dict[str, Any]:
        """导出 gpin 的对象关系和 WA 累计状态。"""

        pb_pin = self.getPbPin()
        return {
            "pin": pb_pin.getName() if pb_pin is not None else None,
            "gcell": self.gCell_.getName() if self.gCell_ is not None else None,
            "gnet": self.gNet_.getName() if self.gNet_ is not None else None,
            "center": (self.cx_, self.cy_),
            "offset": (self.offsetCx_, self.offsetCy_),
            "wa_has_max": (self.hasMaxExpSumX_, self.hasMaxExpSumY_),
            "wa_has_min": (self.hasMinExpSumX_, self.hasMinExpSumY_),
        }


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

    def getName(self) -> str:
        names = [getattr(net.getDbNet(), "name", None) for net in self.nets_]
        names = [name for name in names if name is not None]
        return ",".join(names) if names else "NET"

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
        if gPin not in self.gPins_:
            self.gPins_.append(gPin)
            gPin.setGNet(self)

    def clearGPins(self) -> None:
        for gpin in self.gPins_:
            if gpin.getGNet() is self:
                gpin.clearGNet()
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

    def report(self) -> Dict[str, Any]:
        """导出 gnet 状态，供 timing/routability 报告复用。"""

        self.updateBox()
        return {
            "name": self.getName(),
            "pins": len(self.gPins_),
            "bbox": (self.lx_, self.ly_, self.ux_, self.uy_),
            "hpwl": max(0, self.ux_ - self.lx_) + max(0, self.uy_ - self.ly_),
            "timing_weight": self.timingWeight_,
            "custom_weight": self.customWeight_,
            "total_weight": self.getTotalWeight(),
            "dont_care": self.isDontCare_,
            "wa_exp_min": (self.waExpMinSumX_, self.waExpMinSumY_),
            "wa_exp_max": (self.waExpMaxSumX_, self.waExpMaxSumY_),
        }


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
    electroForceX_: float = 0.0
    electroForceY_: float = 0.0

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
        return self.electroForceX_

    def electroFieldY(self) -> float:
        return self.electroForceY_

    def electroForceX(self) -> float:
        return self.electroForceX_

    def electroForceY(self) -> float:
        return self.electroForceY_

    def getTargetDensity(self) -> float:
        return self.targetDensity_

    def getDensity(self) -> float:
        return self.density_

    def setDensity(self, density: float) -> None:
        self.density_ = density

    def setBinTargetDensity(self, density: float) -> None:
        self.targetDensity_ = density

    def setTargetDensity(self, density: float) -> None:
        self.targetDensity_ = density

    def setElectroField(self, electroFieldX: float, electroFieldY: float) -> None:
        # Compatibility wrapper; canonical fields follow C++
        # Bin::setElectroForce translated from nesterovBase.cpp.
        self.setElectroForce(electroFieldX, electroFieldY)

    def setElectroForce(self, electroForceX: float, electroForceY: float) -> None:
        self.electroForceX_, self.electroForceY_ = electroForceX, electroForceY

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

    def getPlaceArea(self) -> int:
        return self.instPlacedArea_ + self.fillerArea_

    def getAvailableArea(self) -> int:
        return max(0, self.getBinArea() - self.nonPlaceArea_)

    def getOverflowArea(self) -> int:
        allowed = int(round(self.getBinArea() * self.targetDensity_))
        return max(0, self.getPlaceArea() + self.nonPlaceArea_ - allowed)

    def getUtilization(self) -> float:
        return self.getPlaceArea() / max(1, self.getBinArea())

    def getOverflowDensity(self) -> float:
        """返回 bin 超过 target density 的比例；不代表 FFT 电势解。"""

        return max(0.0, self.getDensity() + self.nonPlaceArea_ / max(1, self.getBinArea()) - self.targetDensity_)

    def resetAreas(self) -> None:
        self.nonPlaceArea_ = 0
        self.instPlacedArea_ = 0
        self.instPlacedAreaUnscaled_ = 0
        self.nonPlaceAreaUnscaled_ = 0
        self.fillerArea_ = 0
        self.density_ = 0.0

    def resetElectro(self) -> None:
        self.electroPhi_ = 0.0
        self.electroForceX_ = 0.0
        self.electroForceY_ = 0.0

    def report(self) -> Dict[str, Any]:
        return {
            "index": (self.x_, self.y_),
            "box": (self.lx_, self.ly_, self.ux_, self.uy_),
            "density": self.density_,
            "target_density": self.targetDensity_,
            "overflow_density": self.getOverflowDensity(),
            "electro_phi": self.electroPhi_,
            "electro_force": (self.electroForceX_, self.electroForceY_),
        }


class _TranslatedFFT:
    """Pure-Python translation of `gpl::FFT`'s public density/force contract.

    OpenROAD uses Ooura DCT/DST kernels.  This backend keeps the same method
    sequence used by NesterovBase::updateDensityForceBin: updateDensity(),
    doFFT(), getElectroForce(), getElectroPhi().  The direct cosine/sine series
    is intentionally small and deterministic for Python smoke flows.
    """

    def __init__(self, binCntX: int, binCntY: int, binSizeX: float, binSizeY: float):
        self.binCntX_ = max(1, binCntX)
        self.binCntY_ = max(1, binCntY)
        self.binSizeX_ = float(binSizeX)
        self.binSizeY_ = float(binSizeY)
        self.binDensity_ = [[0.0 for _ in range(self.binCntY_)] for _ in range(self.binCntX_)]
        self.electroPhi_ = [[0.0 for _ in range(self.binCntY_)] for _ in range(self.binCntX_)]
        self.electroForceX_ = [[0.0 for _ in range(self.binCntY_)] for _ in range(self.binCntX_)]
        self.electroForceY_ = [[0.0 for _ in range(self.binCntY_)] for _ in range(self.binCntX_)]
        self.wx_ = [REPLACE_FFT_PI * i / self.binCntX_ for i in range(self.binCntX_)]
        y_scale = self.binSizeY_ / self.binSizeX_ if abs(self.binSizeX_) > 1e-30 else 1.0
        self.wy_ = [REPLACE_FFT_PI * j / self.binCntY_ * y_scale for j in range(self.binCntY_)]

    def updateDensity(self, x: int, y: int, density: float) -> None:
        self.binDensity_[x][y] = density

    def getElectroForce(self, x: int, y: int) -> Tuple[float, float]:
        return (self.electroForceX_[x][y], self.electroForceY_[x][y])

    def getElectroPhi(self, x: int, y: int) -> float:
        return self.electroPhi_[x][y]

    def doFFT(self) -> None:
        nx, ny = self.binCntX_, self.binCntY_
        rho_hat = [[0.0 for _ in range(ny)] for _ in range(nx)]
        for k in range(nx):
            for l in range(ny):
                total = 0.0
                for x in range(nx):
                    cx = math.cos(REPLACE_FFT_PI * k * (x + 0.5) / nx)
                    for y in range(ny):
                        cy = math.cos(REPLACE_FFT_PI * l * (y + 0.5) / ny)
                        total += self.binDensity_[x][y] * cx * cy
                norm = 4.0 / nx / ny
                if k == 0:
                    norm *= 0.5
                if l == 0:
                    norm *= 0.5
                rho_hat[k][l] = total * norm

        phi_hat = [[0.0 for _ in range(ny)] for _ in range(nx)]
        ex_hat = [[0.0 for _ in range(ny)] for _ in range(nx)]
        ey_hat = [[0.0 for _ in range(ny)] for _ in range(nx)]
        for k in range(nx):
            wx = self.wx_[k]
            for l in range(ny):
                wy = self.wy_[l]
                if k == 0 and l == 0:
                    continue
                phi = rho_hat[k][l] / (wx * wx + wy * wy)
                phi_hat[k][l] = phi
                ex_hat[k][l] = phi * wx
                ey_hat[k][l] = phi * wy

        for x in range(nx):
            for y in range(ny):
                phi = 0.0
                force_x = 0.0
                force_y = 0.0
                for k in range(nx):
                    cos_x = math.cos(REPLACE_FFT_PI * k * (x + 0.5) / nx)
                    sin_x = math.sin(REPLACE_FFT_PI * k * (x + 0.5) / nx)
                    for l in range(ny):
                        cos_y = math.cos(REPLACE_FFT_PI * l * (y + 0.5) / ny)
                        sin_y = math.sin(REPLACE_FFT_PI * l * (y + 0.5) / ny)
                        phi += phi_hat[k][l] * cos_x * cos_y
                        force_x += ex_hat[k][l] * sin_x * cos_y
                        force_y += ey_hat[k][l] * cos_x * sin_y
                self.electroPhi_[x][y] = phi
                self.electroForceX_[x][y] = force_x
                self.electroForceY_[x][y] = force_y


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
            bin_obj.setTargetDensity(density)

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
            bin_obj.setInstPlacedAreaUnscaled(0)
            bin_obj.setFillerArea(0)
        for gcell in cells:
            min_x, max_x = self.getDensityMinMaxIdxX(gcell)
            min_y, max_y = self.getDensityMinMaxIdxY(gcell)
            for y in range(min_y, max_y):
                for x in range(min_x, max_x):
                    bin_obj = self.bins_[y * self.binCntX_ + x]
                    overlap = self.getOverlapDensityArea(bin_obj, gcell) * gcell.getDensityScale()
                    if overlap <= 0:
                        continue
                    if gcell.isFiller():
                        bin_obj.addFillerArea(overlap)
                    elif gcell.isMacroInstance():
                        bin_obj.addInstPlacedAreaUnscaled(overlap * bin_obj.getTargetDensity())
                    else:
                        bin_obj.addInstPlacedAreaUnscaled(overlap)
        self.sumOverflowArea_ = 0
        self.sumOverflowAreaUnscaled_ = 0
        for bin_obj in self.bins_:
            bin_obj.setInstPlacedArea(bin_obj.getInstPlacedAreaUnscaled())
            scaled_bin_area = float(bin_obj.getBinArea()) * bin_obj.getTargetDensity()
            if abs(scaled_bin_area) <= 1e-30:
                bin_obj.setDensity(0.0)
                continue
            bin_obj.setDensity(
                (float(bin_obj.instPlacedArea()) + float(bin_obj.getFillerArea()) + float(bin_obj.getNonPlaceArea()))
                / scaled_bin_area
            )
            overflow = max(0.0, float(bin_obj.instPlacedArea()) + float(bin_obj.getNonPlaceArea()) - scaled_bin_area)
            overflow_unscaled = max(
                0.0,
                float(bin_obj.getInstPlacedAreaUnscaled()) + float(bin_obj.getNonPlaceAreaUnscaled()) - scaled_bin_area,
            )
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
        return self._range_to_bin_idx_exclusive(gcell.dLx(), gcell.dUx(), self.lx_, self.binSizeX_, self.binCntX_)

    def getDensityMinMaxIdxY(self, gcell: GCell) -> Tuple[int, int]:
        return self._range_to_bin_idx_exclusive(gcell.dLy(), gcell.dUy(), self.ly_, self.binSizeY_, self.binCntY_)

    def getBinByIdx(self, x: int, y: int) -> Bin:
        return self.bins_[y * self.binCntX_ + x]

    def getBinAtPoint(self, x: float, y: float) -> Optional[Bin]:
        if not self.bins_ or self.binCntX_ <= 0 or self.binCntY_ <= 0:
            return None
        idx_x = int((x - self.lx_) // self.binSizeX_) if self.binSizeX_ > 0 else 0
        idx_y = int((y - self.ly_) // self.binSizeY_) if self.binSizeY_ > 0 else 0
        idx_x = min(max(idx_x, 0), self.binCntX_ - 1)
        idx_y = min(max(idx_y, 0), self.binCntY_ - 1)
        return self.getBinByIdx(idx_x, idx_y)

    def getMinMaxIdxX(self, inst: Instance) -> Tuple[int, int]:
        return self._range_to_bin_idx_exclusive(inst.lx(), inst.ux(), self.lx_, self.binSizeX_, self.binCntX_)

    def getMinMaxIdxY(self, inst: Instance) -> Tuple[int, int]:
        return self._range_to_bin_idx_exclusive(inst.ly(), inst.uy(), self.ly_, self.binSizeY_, self.binCntY_)

    def _range_to_bin_idx(self, low: int, high: int, origin: int, size: float, count: int) -> Tuple[int, int]:
        lower, upper = self._range_to_bin_idx_exclusive(low, high, origin, size, count)
        return (lower, max(lower, upper - 1))

    def _range_to_bin_idx_exclusive(self, low: int, high: int, origin: int, size: float, count: int) -> Tuple[int, int]:
        if count <= 0 or size <= 0:
            return (0, 0)
        min_idx = int((low - origin) // size)
        max_idx = int(math.ceil((high - origin) / size))
        min_idx = min(max(min_idx, 0), count - 1)
        max_idx = min(max(max_idx, 0), count)
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
            for y in range(min_y, max_y):
                for x in range(min_x, max_x):
                    bin_obj = self.bins_[y * self.binCntX_ + x]
                    overlap = self._overlap_area(inst_rect, (bin_obj.lx(), bin_obj.ly(), bin_obj.ux(), bin_obj.uy()))
                    scaled = overlap * bin_obj.getTargetDensity()
                    bin_obj.addNonPlaceArea(scaled)
                    bin_obj.addNonPlaceAreaUnscaled(scaled)

    def resetBinAreas(self) -> None:
        for bin_obj in self.bins_:
            bin_obj.resetAreas()
        self.sumOverflowArea_ = 0
        self.sumOverflowAreaUnscaled_ = 0

    def resetElectro(self) -> None:
        for bin_obj in self.bins_:
            bin_obj.resetElectro()

    def getOverlapDensityArea(self, bin_obj: Bin, cell: GCell) -> float:
        return float(
            self._overlap_area(
                (bin_obj.lx(), bin_obj.ly(), bin_obj.ux(), bin_obj.uy()),
                (cell.dLx(), cell.dLy(), cell.dUx(), cell.dUy()),
            )
        )

    def getInterpolatedElectroField(self, x: float, y: float) -> FloatPoint:
        """Compatibility wrapper for older callers; translated path uses forces."""

        bin_obj = self.getBinAtPoint(x, y)
        if bin_obj is None:
            return FloatPoint()
        return FloatPoint(bin_obj.electroForceX(), bin_obj.electroForceY())

    def getAverageDensity(self) -> float:
        if not self.bins_:
            return 0.0
        return sum(bin_obj.getDensity() for bin_obj in self.bins_) / len(self.bins_)

    def getMaxDensity(self) -> float:
        return max((bin_obj.getDensity() for bin_obj in self.bins_), default=0.0)

    def getTotalPlaceArea(self) -> int:
        return sum(bin_obj.getPlaceArea() for bin_obj in self.bins_)

    def getTotalNonPlaceArea(self) -> int:
        return sum(bin_obj.getNonPlaceArea() for bin_obj in self.bins_)

    def reportStatus(self) -> Dict[str, Any]:
        return {
            "bin_count": len(self.bins_),
            "bin_count_x": self.binCntX_,
            "bin_count_y": self.binCntY_,
            "bin_size_x": self.binSizeX_,
            "bin_size_y": self.binSizeY_,
            "target_density": self.targetDensity_,
            "average_density": self.getAverageDensity(),
            "max_density": self.getMaxDensity(),
            "overflow_area": self.sumOverflowArea_,
            "overflow_area_unscaled": self.sumOverflowAreaUnscaled_,
            "place_area": self.getTotalPlaceArea(),
            "non_place_area": self.getTotalNonPlaceArea(),
        }

    def reportBins(self, sample_limit: int = 0) -> Dict[str, Any]:
        """导出 bin grid 摘要；sample_limit>0 时返回前若干 bin。"""

        report = self.reportStatus()
        if sample_limit > 0:
            report["sample_bins"] = [
                {
                    "index": (bin_obj.x(), bin_obj.y()),
                    "box": (bin_obj.lx(), bin_obj.ly(), bin_obj.ux(), bin_obj.uy()),
                    "density": bin_obj.getDensity(),
                    "target_density": bin_obj.getTargetDensity(),
                    "place_area": bin_obj.getPlaceArea(),
                    "non_place_area": bin_obj.getNonPlaceArea(),
                    "overflow_area": bin_obj.getOverflowArea(),
                    "utilization": bin_obj.getUtilization(),
                }
                for bin_obj in self.bins_[:sample_limit]
            ]
        return report


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
        """更新 WA wirelength 的 net/pin 累计量。

        这是 OpenROAD weighted-average wirelength 的纯 Python 版本：按 pin 坐标
        累积 exp(+/-coord/gamma) 与 coord*exp(+/-coord/gamma)。它不依赖 FFT/ODB。
        """

        self.updatePinLocation()
        for gnet in self.gNets_:
            gnet.clearWaVars()
            pins = gnet.getGPins()
            if gnet.isDontCare() or len(pins) <= 1:
                continue
            for gpin in pins:
                gpin.clearWaVars()
                exp_max_x = _safe_exp(gpin.cx() / max(wlCoeffX, 1e-9))
                exp_min_x = _safe_exp(-gpin.cx() / max(wlCoeffX, 1e-9))
                exp_max_y = _safe_exp(gpin.cy() / max(wlCoeffY, 1e-9))
                exp_min_y = _safe_exp(-gpin.cy() / max(wlCoeffY, 1e-9))
                gpin.setMaxExpSumX(exp_max_x)
                gpin.setMinExpSumX(exp_min_x)
                gpin.setMaxExpSumY(exp_max_y)
                gpin.setMinExpSumY(exp_min_y)
                gnet.addWaExpMaxSumX(exp_max_x)
                gnet.addWaXExpMaxSumX(gpin.cx() * exp_max_x)
                gnet.addWaExpMinSumX(exp_min_x)
                gnet.addWaXExpMinSumX(gpin.cx() * exp_min_x)
                gnet.addWaExpMaxSumY(exp_max_y)
                gnet.addWaYExpMaxSumY(gpin.cy() * exp_max_y)
                gnet.addWaExpMinSumY(exp_min_y)
                gnet.addWaYExpMinSumY(gpin.cy() * exp_min_y)

    def updateWireLengthForceWAInit(self, wlCoeffX: float, wlCoeffY: float) -> None:
        self.updateWireLengthForceWA(wlCoeffX, wlCoeffY)

    def getWireLengthGradientPinWA(self, gPin: GPin, wlCoeffX: float, wlCoeffY: float) -> FloatPoint:
        gnet = gPin.getGNet()
        if gnet is None or gnet.isDontCare() or len(gnet.getGPins()) <= 1:
            return FloatPoint()
        gamma_x = max(wlCoeffX, 1e-9)
        gamma_y = max(wlCoeffY, 1e-9)
        exp_max_x = gPin.maxExpSumX() if gPin.hasMaxExpSumX() else _safe_exp(gPin.cx() / gamma_x)
        exp_min_x = gPin.minExpSumX() if gPin.hasMinExpSumX() else _safe_exp(-gPin.cx() / gamma_x)
        exp_max_y = gPin.maxExpSumY() if gPin.hasMaxExpSumY() else _safe_exp(gPin.cy() / gamma_y)
        exp_min_y = gPin.minExpSumY() if gPin.hasMinExpSumY() else _safe_exp(-gPin.cy() / gamma_y)

        # WA 目标：sum(x*e^(x/g))/sum(e^(x/g)) - sum(x*e^(-x/g))/sum(e^(-x/g))
        # 对单 pin 求导，得到 max/min 两项的解析梯度。
        max_x_mean = _safe_div(gnet.waXExpMaxSumX(), gnet.waExpMaxSumX())
        min_x_mean = _safe_div(gnet.waXExpMinSumX(), gnet.waExpMinSumX())
        max_y_mean = _safe_div(gnet.waYExpMaxSumY(), gnet.waExpMaxSumY())
        min_y_mean = _safe_div(gnet.waYExpMinSumY(), gnet.waExpMinSumY())
        grad_x = _safe_div(exp_max_x * (1.0 + (gPin.cx() - max_x_mean) / gamma_x), gnet.waExpMaxSumX())
        grad_x -= _safe_div(exp_min_x * (1.0 - (gPin.cx() - min_x_mean) / gamma_x), gnet.waExpMinSumX())
        grad_y = _safe_div(exp_max_y * (1.0 + (gPin.cy() - max_y_mean) / gamma_y), gnet.waExpMaxSumY())
        grad_y -= _safe_div(exp_min_y * (1.0 - (gPin.cy() - min_y_mean) / gamma_y), gnet.waExpMinSumY())
        weight = gnet.getTotalWeight()
        return FloatPoint(grad_x * weight, grad_y * weight)

    def getWireLengthGradientWA(self, gCell: GCell, wlCoeffX: float, wlCoeffY: float) -> FloatPoint:
        grad = FloatPoint()
        for gpin in gCell.gPins():
            pin_grad = self.getWireLengthGradientPinWA(gpin, wlCoeffX, wlCoeffY)
            grad.x += pin_grad.x
            grad.y += pin_grad.y
        return grad

    def getWireLengthPreconditioner(self, gCell: GCell) -> FloatPoint:
        weight_sum = 0.0
        for gpin in gCell.gPins():
            gnet = gpin.getGNet()
            if gnet is not None and not gnet.isDontCare():
                weight_sum += max(0.0, gnet.getTotalWeight())
        precond = max(1.0, weight_sum)
        return FloatPoint(precond, precond)

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

    def setCustomNetWeight(self, net: Net, weight: float) -> None:
        gnet = self.pbToNb(net)
        if gnet is not None:
            gnet.setCustomWeight(weight)

    def resetTimingNetWeights(self) -> None:
        for gnet in self.gNets_:
            gnet.setTimingWeight(1.0)

    def resetCustomNetWeights(self) -> None:
        for gnet in self.gNets_:
            gnet.setCustomWeight(1.0)

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
        gcell.clearGPins()
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
        gnet.clearGPins()
        for gnets in (self.gNets_, self.gNetStor_):
            if gnet in gnets:
                gnets.remove(gnet)
        return gnet

    def reportChangedGCells(self, sample_limit: int = 0) -> Dict[str, Any]:
        """导出 DB callback 造成的 changed-gcell 队列。"""

        report: Dict[str, Any] = {"changed_gcells": len(self.changed_gcells_)}
        if sample_limit > 0:
            report["sample_gcells"] = [gcell.report() for gcell in self.changed_gcells_[:sample_limit]]
        return report

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
            "timing_weighted_nets": sum(1 for gnet in self.gNets_ if gnet.getTimingWeight() != 1.0),
            "custom_weighted_nets": sum(1 for gnet in self.gNets_ if gnet.getCustomWeight() != 1.0),
            "db_callback_attached": self.db_cbk_ is not None,
        }

    def reportObjects(self, sample_limit: int = 0) -> Dict[str, Any]:
        """导出 Nesterov common 对象关系摘要。"""

        report = self.reportStatus()
        if sample_limit > 0:
            report["sample_gcells"] = [gcell.report() for gcell in self.nbc_gcells_[:sample_limit]]
            report["sample_gnets"] = [gnet.report() for gnet in self.gNets_[:sample_limit]]
            report["sample_gpins"] = [gpin.report() for gpin in self.gPins_[:sample_limit]]
        return report

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

    def resetLifecycleCounters(self) -> None:
        """清理 callback 生命周期计数和 changed 队列。"""

        self.delta_area_ = 0
        self.new_gcells_count_ = 0
        self.deleted_gcells_count_ = 0
        self.clearChangedGCells()

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
        self.snapshot_gcell_states_: List[GCellSnapshot] = []
        self.snapshot_overflow_: float = 0.0
        self.snapshot_overflow_unscaled_: float = 0.0
        self.snapshot_target_density_: float = self.targetDensity_
        self.prevSLPCoordi_: List[FloatPoint] = []
        self.curSLPCoordi_: List[FloatPoint] = []
        self.nextSLPCoordi_: List[FloatPoint] = []
        self.prevSLPGradient_: List[FloatPoint] = []
        self.curSLPGradient_: List[FloatPoint] = []
        self.nextSLPGradient_: List[FloatPoint] = []
        self.prevSLPSumGrads_: List[FloatPoint] = []
        self.curSLPSumGrads_: List[FloatPoint] = []
        self.nextSLPSumGrads_: List[FloatPoint] = []
        self.curCoordi_: List[FloatPoint] = []
        self.nextCoordi_: List[FloatPoint] = []
        self.fft_: Optional[_TranslatedFFT] = None
        self._init_bin_grid()

    def _init_bin_grid(self) -> None:
        lx, ly, ux, uy = self.pb_.getRegionBBox()
        self.bg_.setRegionPoints(lx, ly, ux, uy)
        self.bg_.setBinCnt(self.nbVars_.binCntX or 1, self.nbVars_.binCntY or 1)
        self.bg_.setBinTargetDensity(self.targetDensity_)
        self.bg_.initBins()
        self.fft_ = _TranslatedFFT(self.bg_.getBinCntX(), self.bg_.getBinCntY(), self.bg_.getBinSizeX(), self.bg_.getBinSizeY())

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

    def binCntX(self) -> int:
        return self.bg_.getBinCntX()

    def binCntY(self) -> int:
        return self.bg_.getBinCntY()

    def bins(self) -> List[Bin]:
        return self.bg_.getBins()

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
        self.movableArea_ = sum(cell.area() for cell in self.nb_gcells_ if cell.isInstance())
        self.totalFillerArea_ = sum(cell.area() for cell in self.fillerStor_)
        self.whiteSpaceArea_ = max(0, self.pb_.getRegionArea() - self.pb_.nonPlaceInstsArea())

    def _fillerInitFailure(self, reason: str, **details: Any) -> RuntimeError:
        report = {
            "reason": reason,
            "target_density": self.targetDensity_,
            "white_space_area": self.whiteSpaceArea_,
            "movable_area": self.movableArea_,
            "bin_count": (self.bg_.getBinCntX(), self.bg_.getBinCntY()),
            **details,
        }
        error = RuntimeError(f"Cannot initialize filler GCells: {reason}")
        setattr(error, "report", report)
        return error

    def _deriveFillerCellSize(self) -> Tuple[int, int]:
        candidates = [
            (inst.dx(), inst.dy())
            for inst in self.pb_.placeInsts()
            if not inst.isMacro() and inst.dx() > 0 and inst.dy() > 0
        ]
        if not candidates:
            raise self._fillerInitFailure(
                "missing filler cell dimensions",
                place_insts=len(self.pb_.placeInsts()),
                std_place_insts=0,
            )
        candidates.sort(key=lambda size: (size[1], size[0]))
        dx, dy = candidates[0]
        if dx <= 0 or dy <= 0:
            raise self._fillerInitFailure("invalid filler cell dimensions", filler_dx=dx, filler_dy=dy)
        return dx, dy

    def _appendFillerGCell(self, cx: int, cy: int, dx: int, dy: int, max_area: int) -> int:
        if max_area <= 0:
            return 0
        fill_dx = min(dx, max_area // dy)
        if fill_dx <= 0:
            return 0
        fill_dx = max(1, fill_dx)
        filler = GCell.filler(cx, cy, fill_dx, dy)
        self.updateDensityCoordiLayoutInside(filler)
        self.fillerStor_.append(filler)
        self.nb_gcells_.append(filler)
        return filler.area()

    def _createFillerGCellsInBin(self, bin_obj: Bin, target_area: int) -> int:
        if target_area <= 0:
            return 0
        dx, dy = self.fillerDx_, self.fillerDy_
        if dx <= 0 or dy <= 0:
            raise self._fillerInitFailure("missing filler cell dimensions", filler_dx=dx, filler_dy=dy)

        placed_area = 0
        min_cx = bin_obj.lx() + dx // 2
        max_cx = bin_obj.ux() - (dx - dx // 2)
        min_cy = bin_obj.ly() + dy // 2
        max_cy = bin_obj.uy() - (dy - dy // 2)
        if min_cx > max_cx or min_cy > max_cy:
            return self._appendFillerGCell(bin_obj.cx(), bin_obj.cy(), dx, dy, target_area)

        y = min_cy
        while y <= max_cy and placed_area < target_area:
            x = min_cx
            while x <= max_cx and placed_area < target_area:
                placed_area += self._appendFillerGCell(x, y, dx, dy, target_area - placed_area)
                x += dx
            y += dy
        return placed_area

    def initFillerGCells(self) -> None:
        self.resetFillerGCells()
        self.fillerDx_, self.fillerDy_ = self._deriveFillerCellSize()
        self.bg_.updateBinsNonPlaceArea()
        self.bg_.updateBinsGCellDensityArea(self.nb_gcells_)

        created_area = 0
        for bin_obj in self.bg_.getBins():
            allowed_area = int(round(bin_obj.getBinArea() * self.targetDensity_))
            target_area = max(0, allowed_area - bin_obj.getNonPlaceArea() - bin_obj.instPlacedArea())
            created_area += self._createFillerGCellsInBin(bin_obj, target_area)

        self.updateAreas()
        self.totalFillerArea_ = created_area
        self.bg_.updateBinsGCellDensityArea(self.nb_gcells_)

    def resetFillerGCells(self) -> None:
        self.fillerStor_.clear()
        self.nb_gcells_ = [cell for cell in self.nb_gcells_ if not cell.isFiller()]
        self.updateAreas()

    def updateDensitySize(self) -> None:
        for gcell in self.nb_gcells_:
            if gcell.dx() < REPLACE_SQRT2 * self.bg_.getBinSizeX():
                scale_x = float(gcell.dx()) / float(REPLACE_SQRT2 * self.bg_.getBinSizeX())
                density_size_x = REPLACE_SQRT2 * self.bg_.getBinSizeX()
            else:
                scale_x = 1.0
                density_size_x = float(gcell.dx())
            if gcell.dy() < REPLACE_SQRT2 * self.bg_.getBinSizeY():
                scale_y = float(gcell.dy()) / float(REPLACE_SQRT2 * self.bg_.getBinSizeY())
                density_size_y = REPLACE_SQRT2 * self.bg_.getBinSizeY()
            else:
                scale_y = 1.0
                density_size_y = float(gcell.dy())
            gcell.setDensitySize(int(round(density_size_x)), int(round(density_size_y)))
            gcell.setDensityScale(scale_x * scale_y)

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
        target_lx = float(gcell.dLx())
        target_ly = float(gcell.dLy())
        if target_lx < self.bg_.lx():
            target_lx = float(self.bg_.lx())
        if target_ly < self.bg_.ly():
            target_ly = float(self.bg_.ly())
        if target_lx + gcell.dDx() > self.bg_.ux():
            target_lx = float(self.bg_.ux() - gcell.dDx())
        if target_ly + gcell.dDy() > self.bg_.uy():
            target_ly = float(self.bg_.uy() - gcell.dDy())
        gcell.setDensityLocation(int(round(target_lx)), int(round(target_ly)))

    def getDensityCoordiLayoutInsideX(self, gCell: GCell, cx: float) -> float:
        half = gCell.dDx() / 2
        return min(max(cx, self.bg_.lx() + half), self.bg_.ux() - half)

    def getDensityCoordiLayoutInsideY(self, gCell: GCell, cy: float) -> float:
        half = gCell.dDy() / 2
        return min(max(cy, self.bg_.ly() + half), self.bg_.uy() - half)

    def getDensityPreconditioner(self, gCell: GCell) -> FloatPoint:
        area_val = float(gCell.dx()) * float(gCell.dy())
        return FloatPoint(area_val, area_val)

    def getDensityGradient(self, gCell: GCell) -> FloatPoint:
        pair_x = self.bg_.getDensityMinMaxIdxX(gCell)
        pair_y = self.bg_.getDensityMinMaxIdxY(gCell)
        electro_force = FloatPoint()
        for i in range(pair_x[0], pair_x[1]):
            for j in range(pair_y[0], pair_y[1]):
                bin_obj = self.bg_.getBinsConst()[j * self.binCntX() + i]
                overlap_area = self.bg_.getOverlapDensityArea(bin_obj, gCell) * gCell.getDensityScale()
                electro_force.x += overlap_area * bin_obj.electroForceX()
                electro_force.y += overlap_area * bin_obj.electroForceY()
        return electro_force

    def updateDensityForceBin(self) -> None:
        """Translated from OpenROAD NesterovBase::updateDensityForceBin."""

        self.refreshDensityMetrics()
        if self.fft_ is None:
            self.fft_ = _TranslatedFFT(
                self.bg_.getBinCntX(),
                self.bg_.getBinCntY(),
                self.bg_.getBinSizeX(),
                self.bg_.getBinSizeY(),
            )
        for bin_obj in self.bins():
            self.fft_.updateDensity(bin_obj.x(), bin_obj.y(), bin_obj.getDensity())
        self.fft_.doFFT()
        self.sumPhi_ = 0.0
        for bin_obj in self.bins():
            force_x, force_y = self.fft_.getElectroForce(bin_obj.x(), bin_obj.y())
            bin_obj.setElectroForce(force_x, force_y)
            electro_phi = self.fft_.getElectroPhi(bin_obj.x(), bin_obj.y())
            bin_obj.setElectroPhi(electro_phi)
            self.sumPhi_ += electro_phi * float(bin_obj.getNonPlaceArea() + bin_obj.instPlacedArea() + bin_obj.getFillerArea())

    def updateDensityFieldBin(self) -> None:
        """Compatibility wrapper; main logic is the C++ updateDensityForceBin translation."""

        self.updateDensityForceBin()

    def updateWireLengthForceWA(self, wlCoeffX: float, wlCoeffY: float) -> None:
        self.nbc_.updateWireLengthForceWA(wlCoeffX, wlCoeffY)

    def updateWireLengthForceWAInit(self, wlCoeffX: float, wlCoeffY: float) -> None:
        self.nbc_.updateWireLengthForceWAInit(wlCoeffX, wlCoeffY)

    def updateGCellDensityCenterLocation(self) -> None:
        for gcell in self.nb_gcells_:
            gcell.setDensityCenterLocation(gcell.cx(), gcell.cy())
            self.updateDensityCoordiLayoutInside(gcell)

    def updateInitialPrevSLPCoordi(self) -> None:
        self.curCoordi_ = [FloatPoint(cell.cx(), cell.cy()) for cell in self.nb_gcells_]
        if not self.curSLPGradient_:
            self.updateCurGradient()
        prev_update_coef = self.npVars_.initialPrevCoordiUpdateCoef if self.npVars_ is not None else 100.0
        self.prevSLPCoordi_ = []
        for gcell, cur, grad in zip(self.nb_gcells_, self.curCoordi_, self.curSLPGradient_):
            prev_x = self.getDensityCoordiLayoutInsideX(gcell, cur.x - prev_update_coef * grad.x)
            prev_y = self.getDensityCoordiLayoutInsideY(gcell, cur.y - prev_update_coef * grad.y)
            self.prevSLPCoordi_.append(FloatPoint(prev_x, prev_y))
        self.updateDensityCenterPrevSLP()

    def updateCurSLPCoordi(self) -> None:
        self.curCoordi_ = [FloatPoint(cell.cx(), cell.cy()) for cell in self.nb_gcells_]
        self.curSLPCoordi_ = [FloatPoint(cell.dCx(), cell.dCy()) for cell in self.nb_gcells_]

    def updateNextSLPCoordi(self) -> None:
        self.nextSLPCoordi_ = [FloatPoint(cell.dCx(), cell.dCy()) for cell in self.nb_gcells_]

    def updatePrevGradient(self) -> None:
        self.prevSLPGradient_ = [FloatPoint(g.x, g.y) for g in self.curSLPGradient_]
        self.prevSLPSumGrads_ = [FloatPoint(g.x, g.y) for g in self.curSLPGradient_]

    def updateCurGradient(self) -> None:
        self.curCoordi_ = [FloatPoint(cell.cx(), cell.cy()) for cell in self.nb_gcells_]
        self.curSLPCoordi_ = [FloatPoint(cell.dCx(), cell.dCy()) for cell in self.nb_gcells_]
        self.curSLPGradient_ = [self._getCombinedGradient(gcell) for gcell in self.nb_gcells_]
        self.curSLPSumGrads_ = [FloatPoint(g.x, g.y) for g in self.curSLPGradient_]

    def updateNextGradient(self) -> None:
        self.nextSLPGradient_ = [self._getCombinedGradient(gcell) for gcell in self.nb_gcells_]
        self.nextSLPSumGrads_ = [FloatPoint(g.x, g.y) for g in self.nextSLPGradient_]

    def updateDensityCenterPrevSLP(self) -> None:
        self.updateGCellDensityCenterLocation(self.prevSLPCoordi_)

    def updateDensityCenterNextSLP(self) -> None:
        self.updateGCellDensityCenterLocation(self.nextSLPCoordi_)

    def nesterovUpdateCoordinates(self, coeff: float) -> None:
        if self.isConverged_:
            return
        if not self.curSLPCoordi_:
            self.updateCurGradient()
            self.updateCurSLPCoordi()
        if not self.curSLPSumGrads_:
            self.curSLPSumGrads_ = [FloatPoint(g.x, g.y) for g in self.curSLPGradient_]
        self.nextCoordi_ = []
        self.nextSLPCoordi_ = []
        for gcell, cur_coord, cur_slp, grad in zip(self.nb_gcells_, self.curCoordi_, self.curSLPCoordi_, self.curSLPSumGrads_):
            next_x = cur_slp.x + self.stepLength_ * grad.x
            next_y = cur_slp.y + self.stepLength_ * grad.y
            next_sx = next_x + coeff * (next_x - cur_coord.x)
            next_sy = next_y + coeff * (next_y - cur_coord.y)
            self.nextCoordi_.append(
                FloatPoint(
                    self.getDensityCoordiLayoutInsideX(gcell, next_x),
                    self.getDensityCoordiLayoutInsideY(gcell, next_y),
                )
            )
            self.nextSLPCoordi_.append(
                FloatPoint(
                    self.getDensityCoordiLayoutInsideX(gcell, next_sx),
                    self.getDensityCoordiLayoutInsideY(gcell, next_sy),
                )
            )
        self.updateDensityCenterNextSLP()
        self.updateDensityForceBin()

    def nesterovUpdateStepLength(self) -> bool:
        if self.isConverged_:
            return True
        if not self.curSLPCoordi_ or not self.nextSLPCoordi_:
            return True
        delta_sum = 0.0
        grad_sum = 0.0
        for cur, nxt, grad in zip(self.curSLPCoordi_, self.nextSLPCoordi_, self.curSLPSumGrads_ or self.curSLPGradient_):
            delta_sum += abs(nxt.x - cur.x) + abs(nxt.y - cur.y)
            grad_sum += abs(grad.x) + abs(grad.y)
        if grad_sum <= 1e-30:
            self.isDiverged_ = True
            return False
        new_step = delta_sum / grad_sum
        if not math.isfinite(new_step):
            self.isDiverged_ = True
            return False
        if new_step > self.stepLength_ * 0.95:
            self.stepLength_ = new_step
            return False
        if new_step < 0.01:
            self.stepLength_ = 0.01
            return False
        self.stepLength_ = new_step
        return True

    def nesterovAdjustPhi(self) -> None:
        if self.isConverged_:
            return
        if self.npVars_ is None:
            return
        if not getattr(self.nbVars_, "isMaxPhiCoefChanged", False) and self.sum_overflow_unscaled_ < 0.35:
            self.nbVars_.isMaxPhiCoefChanged = True
            self.nbVars_.maxPhiCoef *= 0.99

    def _getCombinedGradient(self, gcell: GCell) -> FloatPoint:
        wl_grad = self.nbc_.getWireLengthGradientWA(gcell, self.baseWireLengthCoef_ or 1.0, self.baseWireLengthCoef_ or 1.0)
        density_grad = self.getDensityGradient(gcell)
        pre_wl = self.nbc_.getWireLengthPreconditioner(gcell)
        pre_den = self.getDensityPreconditioner(gcell)
        pre_x = max(self._minPreconditioner(), pre_wl.x + self.densityPenalty_ * pre_den.x)
        pre_y = max(self._minPreconditioner(), pre_wl.y + self.densityPenalty_ * pre_den.y)
        return FloatPoint(
            (wl_grad.x + self.densityPenalty_ * density_grad.x) / pre_x,
            (wl_grad.y + self.densityPenalty_ * density_grad.y) / pre_y,
        )

    def _minPreconditioner(self) -> float:
        return self.npVars_.minPreconditioner if self.npVars_ is not None else 1.0

    def updatePrevSLPCoordi(self) -> None:
        self.prevSLPCoordi_ = list(self.curSLPCoordi_)

    def updateNextIter(self, iter: int) -> None:
        if self.isConverged_:
            return
        self.iter_ = iter
        if self.nextSLPCoordi_:
            self.prevSLPCoordi_, self.curSLPCoordi_ = self.curSLPCoordi_, self.nextSLPCoordi_
        if self.nextSLPGradient_:
            self.prevSLPGradient_, self.curSLPGradient_ = self.curSLPGradient_, self.nextSLPGradient_
            self.prevSLPSumGrads_, self.curSLPSumGrads_ = self.curSLPSumGrads_, self.nextSLPSumGrads_
        if self.nextCoordi_:
            self.curCoordi_ = self.nextCoordi_
        for index, gcell in enumerate(self.nb_gcells_):
            if gcell.isInstance() and gcell.isLocked():
                if index < len(self.prevSLPCoordi_) and index < len(self.curSLPCoordi_):
                    self.curSLPCoordi_[index] = self.prevSLPCoordi_[index]
                if index < len(self.prevSLPGradient_) and index < len(self.curSLPGradient_):
                    self.curSLPGradient_[index] = self.prevSLPGradient_[index]
                if index < len(self.curCoordi_):
                    self.curCoordi_[index] = FloatPoint(gcell.cx(), gcell.cy())
        self.updateGCellCenterLocation(self.curCoordi_)
        self.updateGCellDensityCenterLocation(self.curSLPCoordi_)
        self.refreshDensityMetrics()

    def updateDensityCenterCoordiLayoutInside(self) -> None:
        for gcell in self.nb_gcells_:
            self.updateDensityCoordiLayoutInside(gcell)

    def refreshDensityMetrics(self) -> None:
        self.bg_.updateBinsNonPlaceArea()
        self.bg_.updateBinsGCellDensityArea(self.nb_gcells_)
        area = max(1, self.pb_.getRegionArea())
        self.sum_overflow_ = self.bg_.getOverflowArea() / area
        self.sum_overflow_unscaled_ = self.bg_.getOverflowAreaUnscaled() / area

    def refreshState(self) -> None:
        self.updateAreas()
        self.updateDensitySize()
        self.updateGCellDensityCenterLocation()
        self.refreshDensityMetrics()

    def getBinGrid(self) -> BinGrid:
        return self.bg_

    def initDensity1(self) -> None:
        """初始化 density 侧状态。

        真实 OpenROAD 会联动 filler、FFT、电势求解和多轮线搜索。这里仅刷新 bin
        密度、构造局部 density field，并保存初始 SLP 坐标，供纯 Python 外层验证。
        """

        self.refreshState()
        self.updatePhiCoef(self.sum_overflow_)
        self.updateDensityFieldBin()
        self.updateInitialPrevSLPCoordi()
        self.updateCurSLPCoordi()

    def initDensity2(self, wlCoeffX: float, wlCoeffY: float) -> float:
        self.updateWireLengthForceWAInit(wlCoeffX, wlCoeffY)
        self.updateGradSum()
        if self.densityPenalty_ <= 0.0:
            self.initDensityPenalty(self.npVars_.initDensityPenalty if self.npVars_ is not None else 1.0)
        return self.densityPenalty_

    def initBaseWireLengthCoef(self) -> None:
        hpwl = self.nbc_.getHpwl() if self.nbc_ is not None else 0
        region_extent = max(1.0, float(self.pb_.getRegionArea()) ** 0.5)
        self.baseWireLengthCoef_ = max(1.0, hpwl / max(1.0, len(self.nbc_.getGNets())) if hpwl else region_extent / 10.0)

    def initDensityPenalty(self, init_density_penalty: float) -> None:
        self.densityPenalty_ = init_density_penalty

    def updateDensityPenalty(self, overflow: float) -> None:
        """按 overflow 平滑更新 density penalty。

        这是可验证的单调近似：overflow 高于目标时增强 density force，低于目标时缓慢降低。
        OpenROAD 完整数值调参仍未在 Python 中复刻。
        """

        target = self.npVars_.targetOverflow if self.npVars_ is not None else self.nbVars_.targetDensity
        target = max(1e-6, target)
        ratio = max(0.25, min(4.0, overflow / target))
        self.densityPenalty_ = max(1e-12, self.densityPenalty_ * (0.95 + 0.10 * ratio))

    def updatePhiCoef(self, overflow: float) -> None:
        min_phi = self.nbVars_.minPhiCoef
        max_phi = self.nbVars_.maxPhiCoef
        target = self.npVars_.targetOverflow if self.npVars_ is not None else self.nbVars_.targetDensity
        if max_phi < min_phi:
            max_phi = min_phi
        if target <= 0:
            t = 1.0
        else:
            t = max(0.0, min(1.0, overflow / target))
        self.phiCoef_ = min_phi + (max_phi - min_phi) * t
        self.nbVars_.isMaxPhiCoefChanged = self.phiCoef_ >= max_phi

    def updateGradSum(self) -> None:
        wl_sum = 0.0
        density_sum = 0.0
        for gcell in self.nb_gcells_:
            wl_grad = self.nbc_.getWireLengthGradientWA(gcell, self.baseWireLengthCoef_ or 1.0, self.baseWireLengthCoef_ or 1.0)
            den_grad = self.getDensityGradient(gcell)
            wl_sum += abs(wl_grad.x) + abs(wl_grad.y)
            density_sum += abs(den_grad.x) + abs(den_grad.y)
        self.wireLengthGradSum_ = wl_sum
        self.densityGradSum_ = density_sum

    def setNpVars(self, npVars: NesterovPlaceVars) -> None:
        self.npVars_ = npVars

    def setIter(self, iter: int) -> None:
        self.iter_ = iter

    def setMaxPhiCoefChanged(self, maxPhiCoefChanged: bool) -> None:
        self.nbVars_.isMaxPhiCoefChanged = maxPhiCoefChanged

    def checkConvergence(self, gpl_iter_count: int, routability_gpl_iter_count: int, rb: Optional["RouteBase"]) -> bool:
        if self.isConverged_:
            return True
        target = self.npVars_.targetOverflow if self.npVars_ is not None else self.targetDensity_
        if self.sum_overflow_unscaled_ <= target:
            self.isConverged_ = True
            return True
        return False

    def resetConverged(self) -> None:
        self.isConverged_ = False

    def checkDivergence(self) -> bool:
        return self.isDiverged_

    def saveSnapshot(self) -> None:
        self.snapshot_gcell_coordis_ = [FloatPoint(cell.cx(), cell.cy()) for cell in self.nb_gcells_]
        self.snapshot_density_coordis_ = [FloatPoint(cell.dCx(), cell.dCy()) for cell in self.nb_gcells_]
        self.snapshot_gcell_states_ = [GCellSnapshot.from_gcell(cell) for cell in self.nb_gcells_]
        self.snapshot_overflow_ = self.sum_overflow_
        self.snapshot_overflow_unscaled_ = self.sum_overflow_unscaled_
        self.snapshot_target_density_ = self.targetDensity_

    def revertToSnapshot(self) -> bool:
        if not self.snapshot_gcell_states_:
            return False
        if len(self.snapshot_gcell_states_) != len(self.nb_gcells_):
            raise RuntimeError("NesterovBase snapshot no longer matches current gcell count")
        for gcell, state in zip(self.nb_gcells_, self.snapshot_gcell_states_):
            state.restore(gcell)
        self.sum_overflow_ = self.snapshot_overflow_
        self.sum_overflow_unscaled_ = self.snapshot_overflow_unscaled_
        self.setTargetDensity(self.snapshot_target_density_)
        self.nbc_.updatePinLocation()
        self.nbc_.updateGNetBox()
        return True

    def clearSnapshot(self) -> None:
        self.snapshot_gcell_coordis_.clear()
        self.snapshot_density_coordis_.clear()
        self.snapshot_gcell_states_.clear()

    def reportSnapshot(self) -> Dict[str, Any]:
        """导出 snapshot 边界状态，不执行任何优化判断。"""

        return {
            "saved": bool(self.snapshot_gcell_states_),
            "gcells": len(self.snapshot_gcell_states_),
            "overflow": self.snapshot_overflow_,
            "overflow_unscaled": self.snapshot_overflow_unscaled_,
            "target_density": self.snapshot_target_density_,
        }

    def resetMinSumOverflow(self) -> None:
        return None

    def isDiverged(self) -> bool:
        return self.isDiverged_

    def getPb(self) -> PlacerBase:
        return self.pb_

    def getGroup(self) -> Any:
        return self.pb_.getGroup()

    def reportStatus(self) -> Dict[str, Any]:
        return {
            "gcells": len(self.nb_gcells_),
            "fillers": len(self.fillerStor_),
            "target_density": self.targetDensity_,
            "uniform_target_density": self.uniformTargetDensity_,
            "sum_overflow": self.sum_overflow_,
            "sum_overflow_unscaled": self.sum_overflow_unscaled_,
            "movable_area": self.movableArea_,
            "filler_area": self.totalFillerArea_,
            "white_space_area": self.whiteSpaceArea_,
            "density_penalty": self.densityPenalty_,
            "base_wire_length_coef": self.baseWireLengthCoef_,
            "wire_length_grad_sum": self.wireLengthGradSum_,
            "density_grad_sum": self.densityGradSum_,
            "phi_coef": self.phiCoef_,
            "step_length": self.stepLength_,
            "coordi_distance": self.coordiDistance_,
            "grad_distance": self.gradDistance_,
            "iter": self.iter_,
            "converged": self.isConverged_,
            "diverged": self.isDiverged_,
            "snapshot_gcells": len(self.snapshot_gcell_coordis_),
            "snapshot_state": self.reportSnapshot(),
            "prev_slp_coordis": len(self.prevSLPCoordi_),
            "cur_slp_coordis": len(self.curSLPCoordi_),
            "next_slp_coordis": len(self.nextSLPCoordi_),
            "prev_gradients": len(self.prevSLPGradient_),
            "cur_gradients": len(self.curSLPGradient_),
            "next_gradients": len(self.nextSLPGradient_),
            "bin_grid": self.bg_.reportStatus(),
        }


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
        if self.npVars_ is None:
            raise RuntimeError("NesterovPlaceVars is required before doNesterovPlace")
        if not self.nbVec_:
            self.updateOverflow()
            self.reportStatus()
            return self.last_iter_
        self.init()
        curA = 1.0
        for iter_num in range(start_iter, self.npVars_.maxNesterovIter):
            self.last_iter_ = iter_num
            prevA = curA
            curA = (1.0 + math.sqrt(4.0 * prevA * prevA + 1.0)) * 0.5
            coeff = (prevA - 1.0) / curA
            self.doBackTracking(coeff)
            for nb in self.nbVec_:
                nb.nesterovAdjustPhi()
            if self.num_region_diverged_ > 0:
                break
            self.updateNextIter(iter_num)
            for nb in self.nbVec_:
                nb.updateCurGradient()
            self.updateOverflow()
            self.updateDb()
            hpwl = self.nbc_.getHpwl() if self.nbc_ is not None else 0
            if hpwl < self.min_hpwl_:
                self.min_hpwl_ = hpwl
                self.is_min_hpwl_ = True
            else:
                self.is_min_hpwl_ = False
            self.reportStatus()
            if self.checkConvergence(iter_num, self.routability_iter_):
                for nb in self.nbVec_:
                    nb.isConverged_ = True
                break
            if self.checkDivergence() and not self.npVars_.disableRevertIfDiverge:
                self.divergeMsg_ = "pure Python Nesterov state diverged"
                self.divergeCode_ = 1
                self.revertToSnapshot()
                break
        return self.last_iter_

    def init(self) -> None:
        if self.npVars_ is None:
            raise RuntimeError("NesterovPlaceVars is required before init")
        for nb in self.nbVec_:
            nb.setNpVars(self.npVars_)
            nb.initBaseWireLengthCoef()
            nb.initDensity1()
        self.updateOverflow()
        self.initWireLengthCoef()
        self.updateWireLengthCoef(self.average_overflow_)
        if self.nbc_ is not None:
            self.nbc_.updateWireLengthForceWA(self.wireLengthCoefX_, self.wireLengthCoefY_)
        for nb in self.nbVec_:
            nb.updateCurGradient()
            nb.updateInitialPrevSLPCoordi()
            nb.updateDensityCenterPrevSLP()
            nb.updateDensityForceBin()
            nb.updatePrevGradient()
            nb.initDensityPenalty(max(1e-12, self.npVars_.initDensityPenalty))
            nb.initDensity2(self.wireLengthCoefX_, self.wireLengthCoefY_)
        self.updateOverflow()
        if not self.snapshot_saved_:
            self.saveSnapshot()

    def initWireLengthCoef(self) -> None:
        if self.nbVec_:
            self.baseWireLengthCoef_ = sum(nb.getBaseWireLengthCoef() for nb in self.nbVec_) / len(self.nbVec_)
        if self.baseWireLengthCoef_ <= 0.0:
            reference = self.npVars_.referenceHpwl if self.npVars_ is not None else 0.0
            self.baseWireLengthCoef_ = max(1.0, reference / 1000.0 if reference > 0 else 1.0)
        init_coef = self.npVars_.initWireLengthCoef if self.npVars_ is not None else 1.0
        self.wireLengthCoefX_ = max(1e-9, self.baseWireLengthCoef_ * init_coef)
        self.wireLengthCoefY_ = max(1e-9, self.baseWireLengthCoef_ * init_coef)

    def updateWireLengthCoef(self, overflow: float) -> None:
        if overflow > 1.0:
            self.wireLengthCoefX_ = self.wireLengthCoefY_ = 0.1
        elif overflow < 0.1:
            self.wireLengthCoefX_ = self.wireLengthCoefY_ = 10.0
        else:
            self.wireLengthCoefX_ = self.wireLengthCoefY_ = 1.0 / pow(10.0, (overflow - 0.1) * 20 / 9.0 - 1.0)
        self.wireLengthCoefX_ *= self.baseWireLengthCoef_
        self.wireLengthCoefY_ *= self.baseWireLengthCoef_
        if self.log_ is not None and hasattr(self.log_, "debug"):
            try:
                self.log_.debug("NewWireLengthCoef: %g", self.wireLengthCoefX_)
            except Exception:
                pass

    def doBackTracking(self, coeff: float) -> None:
        num_backtrak = 0
        for num_backtrak in range(self.npVars_.maxBackTrack if self.npVars_ is not None else 0):
            for nb in self.nbVec_:
                nb.nesterovUpdateCoordinates(coeff)
            if self.nbc_ is not None:
                self.nbc_.updateWireLengthForceWA(self.wireLengthCoefX_, self.wireLengthCoefY_)
            self.num_region_diverged_ = 0
            for nb in self.nbVec_:
                nb.updateNextGradient()
                self.num_region_diverged_ += 1 if nb.checkDivergence() else 0
            if self.num_region_diverged_ > 0:
                self.divergeMsg_ = "RePlAce diverged at wire/density gradient Sum."
                self.divergeCode_ = 306
                break
            step_length_limit_ok = 0
            self.num_region_diverged_ = 0
            for nb in self.nbVec_:
                if nb.nesterovUpdateStepLength():
                    step_length_limit_ok += 1
                self.num_region_diverged_ += 1 if nb.checkDivergence() else 0
            if self.num_region_diverged_ > 0:
                self.divergeMsg_ = "RePlAce diverged during gradient descent calculation, resulting in an invalid step length (Inf or NaN)."
                self.divergeCode_ = 305
                break
            if step_length_limit_ok != len(self.nbVec_):
                break
        if num_backtrak + 1 > 0 and self.log_ is not None and hasattr(self.log_, "debug"):
            try:
                self.log_.debug("NumBackTrak: %d", num_backtrak + 1)
            except Exception:
                pass

    def _takePurePythonStep(self, nb: NesterovBase) -> None:
        """执行一小步可验证的 SLP 更新；真实 backtracking/动量仍未复刻。"""

        if not nb.curSLPGradient_:
            return
        step = 1.0 / max(1.0, nb.densityPenalty_ + nb.getWireLengthGradSum() + nb.getDensityGradSum())
        nb.stepLength_ = step
        coord_dist = 0.0
        grad_dist = 0.0
        next_coords: List[FloatPoint] = []
        for gcell, grad in zip(nb.getGCells(), nb.curSLPGradient_):
            old_x = float(gcell.cx())
            old_y = float(gcell.cy())
            new_x = nb.getDensityCoordiLayoutInsideX(gcell, old_x - step * grad.x)
            new_y = nb.getDensityCoordiLayoutInsideY(gcell, old_y - step * grad.y)
            coord_dist += abs(new_x - old_x) + abs(new_y - old_y)
            grad_dist += abs(grad.x) + abs(grad.y)
            gcell.setCenterLocation(int(round(new_x)), int(round(new_y)))
            gcell.setDensityCenterLocation(int(round(new_x)), int(round(new_y)))
            next_coords.append(FloatPoint(new_x, new_y))
        nb.nextSLPCoordi_ = next_coords
        nb.coordiDistance_ = coord_dist
        nb.gradDistance_ = grad_dist
        nb.refreshDensityMetrics()
        nb.updateNextGradient()

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
        self.total_sum_overflow_ = 0.0
        self.total_sum_overflow_unscaled_ = 0.0
        for nb in self.nbVec_:
            nb.updateNextIter(iter)
            self.total_sum_overflow_ += nb.getSumOverflow()
            self.total_sum_overflow_unscaled_ += nb.getSumOverflowUnscaled()
        count = max(1, len(self.nbVec_))
        self.average_overflow_ = self.total_sum_overflow_ / count
        self.average_overflow_unscaled_ = self.total_sum_overflow_unscaled_ / count
        self.updateWireLengthCoef(self.average_overflow_)
        if self.npVars_ is not None and not self.npVars_.disableRevertIfDiverge and self.nbc_ is not None:
            hpwl = self.nbc_.getHpwl()
            if hpwl < self.min_hpwl_ and self.average_overflow_unscaled_ <= 0.25:
                self.min_hpwl_ = hpwl
                self.diverge_snapshot_average_overflow_unscaled_ = self.average_overflow_unscaled_
                self.diverge_snapshot_iter_ = iter + 1
                self.is_min_hpwl_ = True
            else:
                self.is_min_hpwl_ = False

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
        if not self.nbVec_ or not self.snapshot_saved_:
            return False
        reverted = all(nb.revertToSnapshot() for nb in self.nbVec_)
        if reverted:
            self.updateDb()
            self.updateOverflow()
        return reverted

    def clearSnapshot(self) -> None:
        for nb in self.nbVec_:
            nb.clearSnapshot()
        self.snapshot_saved_ = False
        self.diverge_snapshot_average_overflow_unscaled_ = 0.0
        self.diverge_snapshot_iter_ = 0

    def reportSnapshot(self) -> Dict[str, Any]:
        """导出 placer 级 snapshot/restore 状态。"""

        return {
            "saved": self.snapshot_saved_,
            "diverge_snapshot_iter": self.diverge_snapshot_iter_,
            "diverge_snapshot_average_overflow_unscaled": self.diverge_snapshot_average_overflow_unscaled_,
            "bases": [nb.reportSnapshot() for nb in self.nbVec_],
        }

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
            "snapshot": self.reportSnapshot(),
            "diverge_code": self.divergeCode_,
            "diverge_message": self.divergeMsg_,
            "base_common": self.nbc_.reportStatus() if self.nbc_ is not None else {},
            "bases": [nb.reportStatus() for nb in self.nbVec_],
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
        self.nbc_.rebuildPinRelationships()

    def createGNet(self, net: DbNet) -> None:
        if self.pbc_ is None or self.nbc_ is None:
            return
        pb_net = self.pbc_.addDbNet(net)
        self.nbc_.addGNetForNet(pb_net)
        self.nbc_.rebuildPinRelationships()

    def createCbkITerm(self, iterm: Any) -> None:
        if self.pbc_ is not None:
            name = getattr(iterm, "name", None)
            if name is None and self.pbc_.db_ is not None:
                for term_name, db_iterm in getattr(self.pbc_.db_, "iterms", {}).items():
                    if db_iterm is iterm:
                        name = term_name
                        break
            if name is not None:
                self.pbc_.addDbITerm(name, iterm)
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
        self.nbc_.rebuildPinRelationships()

    def destroyCbkGNet(self, net: DbNet) -> None:
        if self.pbc_ is None or self.nbc_ is None:
            return
        pb_net = self.pbc_.removeDbNet(net)
        if pb_net is not None:
            self.nbc_.removeGNetForNet(pb_net)
            self.nbc_.rebuildPinRelationships()

    def destroyCbkITerm(self, iterm: Any) -> None:
        if self.pbc_ is not None:
            self.pbc_.removeDbTerm(iterm)
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


