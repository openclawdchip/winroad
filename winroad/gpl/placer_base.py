"""PlacerBase object layer for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..odb import DbDatabase, DbInst, DbNet, PlacementStatus, SigType
from .common import Rect, _area, _center, _db_inst_set_origin, _get_block, _inst_rect, _iter_block_insts, _iter_block_nets
from .options import PlaceOptions

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


