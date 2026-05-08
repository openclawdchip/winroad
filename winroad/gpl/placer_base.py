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
        if pin not in self.pins_:
            self.pins_.append(pin)
            pin.setInstance(self)

    def removePin(self, pin: "Pin") -> None:
        """断开 Instance -> Pin 的反向关系，供 DB callback 生命周期使用。"""

        if pin in self.pins_:
            self.pins_.remove(pin)
        if pin.getInstance() is self:
            pin.inst_ = None

    def getPins(self) -> List["Pin"]:
        return self.pins_

    def report(self) -> Dict[str, Any]:
        """导出实例状态，便于上层报告对象关系而不直接暴露内部字段。"""

        db_inst = self.dbInst()
        return {
            "name": getattr(db_inst, "name", "DUMMY") if db_inst is not None else "DUMMY",
            "is_instance": self.isInstance(),
            "is_place_instance": self.isPlaceInstance(),
            "is_fixed": self.isFixed(),
            "is_macro": self.isMacro(),
            "is_locked": self.isLocked(),
            "location": (self.lx_, self.ly_, self.ux_, self.uy_),
            "center": (self.cx(), self.cy()),
            "area": self.getArea(),
            "ext_id": self.extId_,
            "pins": len(self.pins_),
        }

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

    def clearInstance(self) -> None:
        self.inst_ = None

    def clearNet(self) -> None:
        self.net_ = None

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

    def report(self) -> Dict[str, Any]:
        """导出 pin 与 Instance/Net 的轻量关系。"""

        inst = self.getInstance()
        net = self.getNet()
        db_inst = inst.dbInst() if inst is not None else None
        db_net = net.getDbNet() if net is not None else None
        return {
            "name": self.getName(),
            "is_iterm": self.isITerm(),
            "is_bterm": self.isBTerm(),
            "inst": getattr(db_inst, "name", None),
            "net": getattr(db_net, "name", None),
            "center": (self.cx_, self.cy_),
            "offset": (self.offsetCx_, self.offsetCy_),
        }


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
        if pin not in self.pins_:
            self.pins_.append(pin)
            pin.setNet(self)

    def removePin(self, pin: Pin) -> None:
        """断开 Net -> Pin 的反向关系，保持 Python 对象图可恢复。"""

        if pin in self.pins_:
            self.pins_.remove(pin)
        if pin.getNet() is self:
            pin.net_ = None

    def report(self) -> Dict[str, Any]:
        """导出线网状态；HPWL 只使用已存在 pin 坐标，不做算法估算。"""

        db_net = self.getDbNet()
        self.updateBox(self.skipIoMode)
        return {
            "name": getattr(db_net, "name", None),
            "sig_type": self.getSigType().value if hasattr(self.getSigType(), "value") else str(self.getSigType()),
            "pins": len(self.pins_),
            "bbox": (self.lx_, self.ly_, self.ux_, self.uy_),
            "hpwl": max(0, self.ux_ - self.lx_) + max(0, self.uy_ - self.ly_),
            "skip_io": self.skipIoMode,
        }


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
        self._init_pins(block)

    def _resolve_inst(self, name_or_inst: Any) -> Optional[Instance]:
        if isinstance(name_or_inst, DbInst):
            return self.instMap_.get(id(name_or_inst))
        for inst in self.insts_:
            db_inst = inst.dbInst()
            if db_inst is not None and db_inst.name == name_or_inst:
                return inst
        return None

    def _resolve_net(self, name_or_net: Any) -> Optional[Net]:
        if isinstance(name_or_net, DbNet):
            return self.netMap_.get(id(name_or_net))
        for net in self.nets_:
            db_net = net.getDbNet()
            if db_net is not None and db_net.name == name_or_net:
                return net
        return None

    def _add_pin(self, term: Any, inst: Optional[Instance], net: Optional[Net], is_bterm: bool = False) -> Pin:
        if term is None:
            raise ValueError("Cannot create GPL Pin for a missing DB term")
        pin = self.pinMap_.get(id(term))
        if pin is None:
            pin = Pin(term_=term, inst_=inst, net_=net)
            if is_bterm:
                pin.setBTerm()
            else:
                pin.setITerm()
            self.pinStor_.append(pin)
            self.pins_.append(pin)
            self.pinMap_[id(term)] = pin
        if inst is not None:
            inst.addPin(pin)
            pin.updateLocation(inst)
        if net is not None:
            net.addPin(pin)
        return pin

    def addDbITerm(self, term_name: Any, term: Any) -> Pin:
        """按当前 ODB 骨架新增/同步一个 ITerm pin。"""

        inst = self._resolve_inst(getattr(term, "inst", None))
        net = self._resolve_net(getattr(term, "net", None))
        pin = self._add_pin(term, inst, net, False)
        self.pinMap_[term_name] = pin
        return pin

    def addDbBTerm(self, term_name: Any, term: Any) -> Pin:
        """按当前 ODB 骨架新增/同步一个 BTerm pin。"""

        block = _get_block(self.db_)
        bpins = getattr(block, "bpins", {}) if block is not None else {}
        net = self._resolve_net(getattr(term, "net", None))
        pin = self._add_pin(term, None, net, True)
        pin.cx_, pin.cy_ = self._bterm_center(block, term, bpins)
        self.pinMap_[term_name] = pin
        return pin

    def removeDbTerm(self, term_or_name: Any) -> Optional[Pin]:
        """删除 ITerm/BTerm 对应 Pin，并同步 Instance/Net 两端反向关系。"""

        try:
            pin = self.pinMap_.pop(term_or_name, None)
        except TypeError:
            pin = None
        if pin is None:
            pin = self.pinMap_.pop(id(term_or_name), None)
        if pin is None:
            return None
        for key, value in list(self.pinMap_.items()):
            if value is pin:
                self.pinMap_.pop(key, None)
        inst = pin.getInstance()
        net = pin.getNet()
        if inst is not None:
            inst.removePin(pin)
        if net is not None:
            net.removePin(pin)
        for pins in (self.pins_, self.pinStor_):
            if pin in pins:
                pins.remove(pin)
        pin.clearInstance()
        pin.clearNet()
        return pin

    def _init_pins(self, block: Any) -> None:
        db = self.db_
        iterms = getattr(db, "iterms", {}) if db is not None else {}
        for term_name, term in getattr(iterms, "items", lambda: [])():
            inst = self._resolve_inst(getattr(term, "inst", None))
            net = self._resolve_net(getattr(term, "net", None))
            if inst is not None or net is not None:
                self._add_pin(term, inst, net, False)
                self.pinMap_[term_name] = self.pinMap_[id(term)]
        if block is None:
            return
        bterms = getattr(block, "bterms", {})
        bpins = getattr(block, "bpins", {})
        for bterm_name, bterm in getattr(bterms, "items", lambda: [])():
            net = self._resolve_net(getattr(bterm, "net", None))
            pin = self._add_pin(bterm, None, net, True)
            pin.cx_, pin.cy_ = self._bterm_center(block, bterm, bpins)
            self.pinMap_[bterm_name] = pin

    def rebuildPinRelationships(self) -> None:
        """重新扫描当前 ODB 骨架里的 ITerm/BTerm，并同步反向关系。

        C++ 里 DB callback 会在 term 变化后维护 GPL pin 关系；这里保留
        同名层面的状态重建入口，不尝试推导缺失的真实 pin shape。
        """

        self.pinStor_.clear()
        self.pins_.clear()
        self.pinMap_.clear()
        for inst in self.insts_:
            inst.pins_.clear()
        for net in self.nets_:
            net.pins_.clear()
        self._init_pins(_get_block(self.db_))

    def _bterm_center(self, block: Any, bterm: Any, bpins: Any) -> Tuple[int, int]:
        for bpin_name in getattr(bterm, "bpins", []):
            bpin = bpins.get(bpin_name) if isinstance(bpins, dict) else None
            for box in getattr(bpin, "boxes", []) if bpin is not None else []:
                rect = getattr(box, "rect", None)
                if rect is not None:
                    return _center(rect)
        region = getattr(bterm, "constraint_region", None)
        if region is not None:
            return _center(region)
        return self.die_.coreCx(), self.die_.coreCy()

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
        try:
            pin = self.pinMap_.get(obj)
        except TypeError:
            pin = None
        return pin or self.pinMap_.get(id(obj))

    def addDbInst(self, db_inst: DbInst) -> Instance:
        existing = self.instMap_.get(id(db_inst))
        if existing is not None:
            return existing
        inst = Instance.from_db(db_inst)
        self.instStor_.append(inst)
        self.insts_.append(inst)
        self.instMap_[id(db_inst)] = inst
        if inst.isPlaceInstance():
            self.placeInsts_.append(inst)
        if inst.isMacro():
            self.macroInstsArea_ += inst.getArea()
        return inst

    def removeDbInst(self, db_inst: DbInst) -> Optional[Instance]:
        inst = self.instMap_.pop(id(db_inst), None)
        if inst is None:
            return None
        # DB 删除实例时，先断开 pin 的实例端；net 端是否还存在由后续 ITerm
        # callback/rebuild 决定，避免留下指向已删除 Instance 的反向关系。
        for pin in list(inst.getPins()):
            inst.removePin(pin)
        for insts in (self.insts_, self.placeInsts_, self.instStor_):
            if inst in insts:
                insts.remove(inst)
        if inst.isMacro():
            self.macroInstsArea_ = max(0, self.macroInstsArea_ - inst.getArea())
        return inst

    def addDbNet(self, db_net: DbNet) -> Net:
        existing = self.netMap_.get(id(db_net))
        if existing is not None:
            return existing
        net = Net(db_net, skipIoMode=self.pbVars_.skipIoMode)
        self.netStor_.append(net)
        self.nets_.append(net)
        self.netMap_[id(db_net)] = net
        return net

    def removeDbNet(self, db_net: DbNet) -> Optional[Net]:
        net = self.netMap_.pop(id(db_net), None)
        if net is None:
            return None
        # 删除 net 时同步 pin 的 net 端，保持 Python 对象图没有悬挂 net。
        for pin in list(net.getPins()):
            net.removePin(pin)
        for nets in (self.nets_, self.netStor_):
            if net in nets:
                nets.remove(net)
        return net

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

    def reportConnectivity(self, sample_limit: int = 0) -> Dict[str, Any]:
        """汇总 Instance/Pin/Net 关系，sample_limit>0 时附带少量对象样本。"""

        dangling_inst_pins = sum(1 for pin in self.pins_ if pin.isITerm() and pin.getInstance() is None)
        dangling_net_pins = sum(1 for pin in self.pins_ if pin.getNet() is None)
        report: Dict[str, Any] = {
            "insts": len(self.insts_),
            "place_insts": len(self.placeInsts_),
            "pins": len(self.pins_),
            "nets": len(self.nets_),
            "dangling_inst_pins": dangling_inst_pins,
            "dangling_net_pins": dangling_net_pins,
            "hpwl": self.getHpwl(),
            "macro_area": self.macroInstsArea_,
        }
        if sample_limit > 0:
            report["sample_insts"] = [inst.report() for inst in self.insts_[:sample_limit]]
            report["sample_nets"] = [net.report() for net in self.nets_[:sample_limit]]
            report["sample_pins"] = [pin.report() for pin in self.pins_[:sample_limit]]
        return report

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
        self.placeInstsArea_ = 0
        self.nonPlaceInstsArea_ = 0
        self.macroInstsArea_ = 0
        self.stdInstsArea_ = 0
        if self.pbCommon_ is not None:
            self.init(True)

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

    def reportStatus(self) -> Dict[str, Any]:
        """导出 region 级 PlacerBase 状态。"""

        return {
            "insts": len(self.pb_insts_),
            "place_insts": len(self.placeInsts_),
            "fixed_insts": len(self.fixedInsts_),
            "dummy_insts": len(self.dummyInsts_),
            "non_place_insts": len(self.nonPlaceInsts_),
            "region_area": self.region_area_,
            "region_bbox": self.region_bbox_,
            "place_area": self.placeInstsArea_,
            "non_place_area": self.nonPlaceInstsArea_,
            "macro_area": self.macroInstsArea_,
            "std_area": self.stdInstsArea_,
            "hpwl": self.getHpwl(),
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


