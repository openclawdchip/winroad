"""Top-level Resizer API for :mod:`winroad.rsz`."""

from __future__ import annotations

from math import inf
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .buffered_net import BufferedNet, FixedDelay
from .common import (
    BufferUse,
    LibraryAnalysisData,
    MoveType,
    RiseFallArray,
    VTCategory,
    _name_of,
    _not_translated,
    _obj_key,
)


class Resizer:
    """rsz 顶层入口类，对应 ``class Resizer``。

    该类连接 OpenDB、OpenSTA、Steiner tree、global router、OpenDP 和 parasitics
    估算器。Python 版本先保存依赖、配置、统计和 public API 边界；所有需要
    STA graph/parasitics/placement 的真实修复流程委托给对应 Repair* 类或抛出
    未翻译错误。
    """

    kDefaultBufBaseName = "input"
    kDefaultNetBaseName = "net"

    def __init__(
        self,
        logger: Any = None,
        db: Any = None,
        sta: Any = None,
        stt_builder: Any = None,
        global_router: Any = None,
        opendp: Any = None,
        estimate_parasitics: Any = None,
    ) -> None:
        self.logger_ = logger
        self.db_ = db
        self.sta_ = sta
        self.stt_builder_ = stt_builder
        self.global_router_ = global_router
        self.opendp_ = opendp
        self.estimate_parasitics_ = estimate_parasitics
        self.db_network_ = getattr(sta, "db_network", None)
        self.block_ = None
        self.dbu_ = 0
        self.design_area_ = 0.0
        self.max_utilization_ = 1.0
        self.dont_use_: Set[Any] = set()
        self.dont_touch_insts_: Set[Any] = set()
        self.dont_touch_nets_: Set[Any] = set()
        self.debug_pin_ = None
        self.worst_slack_nets_percent_ = 0.0
        self.buffer_list_: List[Any] = []
        self.fast_buffer_sizes_: List[Any] = []
        self.clk_buffers_: List[Any] = []
        self.clock_buffer_string_ = ""
        self.clock_buffer_footprint_ = ""
        self.resize_slacks_: Dict[Any, float] = {}
        self.graphics_: Optional[ResizerObserver] = None
        self.lib_data_ = LibraryAnalysisData()
        self.parse_to_openroad_ = None
        self.resizer_ = None
        self.opcode_mapper_ = None
        self.swap_arith_modules_ = None
        self.tielib_port_ = None
        self.tiehi_cell_ = None
        self.tiehi_port_ = None
        self.tielo_cell_ = None
        self.tielo_port_ = None
        self.target_load_map_: Dict[Any, float] = {}
        self.input_slew_map_: Dict[Any, RiseFallArray] = {}
        self.tgt_slews_: RiseFallArray = (inf, inf)
        self.dont_use_changed_ = False
        self.dont_touch_changed_ = False
        from .repair_design import RepairDesign
        from .repair_hold import RepairHold
        from .repair_setup import RepairSetup
        from .recover_power import RecoverPower

        self.repair_design_ = RepairDesign(self)
        self.repair_setup_ = RepairSetup(self)
        self.repair_hold_ = RepairHold(self)
        self.recover_power_ = RecoverPower(self)
        self.initBlock()

    def coreArea(self) -> float:
        """返回 core/die 面积；单位沿用 C++ 注释里的平方米。"""

        block = self.block_
        die = getattr(block, "die_area", None)
        if die is None:
            return 0.0
        lx, ly, ux, uy = die
        return self.dbuToMeters(max(0, ux - lx)) * self.dbuToMeters(max(0, uy - ly))

    def utilization(self) -> float:
        area = self.coreArea()
        return self.designArea() / area if area > 0.0 else 0.0

    def maxArea(self) -> float:
        return self.coreArea() * self.max_utilization_

    def orderedLoadPinVertices(self) -> List[Any]:
        _not_translated("Resizer::orderedLoadPinVertices")

    def setDontUse(self, cell: Any, dont_use: bool) -> None:
        key = _obj_key(cell)
        if dont_use:
            self.dont_use_.add(key)
        else:
            self.dont_use_.discard(key)
        self.dont_use_changed_ = True

    def resetDontUse(self) -> None:
        self.dont_use_.clear()
        self.dont_use_changed_ = True

    def dontUse(self, cell: Any) -> bool:
        return _obj_key(cell) in self.dont_use_

    def reportDontUse(self) -> List[str]:
        return sorted(_name_of(cell) for cell in self.dont_use_)

    def setDontTouch(self, obj: Any, dont_touch: bool) -> None:
        target = self.dont_touch_nets_ if getattr(obj, "is_net", False) else self.dont_touch_insts_
        key = _obj_key(obj)
        if dont_touch:
            target.add(key)
        else:
            target.discard(key)
        self.dont_touch_changed_ = True

    def dontTouch(self, obj: Any) -> bool:
        key = _obj_key(obj)
        return key in self.dont_touch_insts_ or key in self.dont_touch_nets_

    def insertBufferAfterDriver(self, *_args: Any, **_kwargs: Any) -> Any:
        _not_translated("Resizer::insertBufferAfterDriver")

    def insertBufferBeforeLoad(self, *_args: Any, **_kwargs: Any) -> Any:
        _not_translated("Resizer::insertBufferBeforeLoad")

    def insertBufferBeforeLoads(self, *_args: Any, **_kwargs: Any) -> Any:
        _not_translated("Resizer::insertBufferBeforeLoads")

    def reportDontTouch(self) -> Dict[str, List[str]]:
        return {
            "insts": sorted(_name_of(inst) for inst in self.dont_touch_insts_),
            "nets": sorted(_name_of(net) for net in self.dont_touch_nets_),
        }

    def reportFastBufferSizes(self) -> List[Any]:
        return list(self.fast_buffer_sizes_)

    def setMaxUtilization(self, max_utilization: float) -> None:
        self.max_utilization_ = max_utilization

    def removeBuffers(self, insts: Sequence[Any]) -> None:
        _not_translated("Resizer::removeBuffers")

    def unbufferNet(self, net: Any) -> None:
        _not_translated("Resizer::unbufferNet")

    def bufferInputs(self, buffer_cell: Any = None, verbose: bool = False) -> None:
        _not_translated("Resizer::bufferInputs")

    def bufferOutputs(self, buffer_cell: Any = None, verbose: bool = False) -> None:
        _not_translated("Resizer::bufferOutputs")

    def postReadLiberty(self) -> None:
        """STA dbNetworkObserver 回调；C++ 中会刷新 dont_use/buffer 列表。"""

        self.copyDontUseFromLiberty()
        self.findBuffers()

    def balanceRowUsage(self) -> None:
        _not_translated("Resizer::balanceRowUsage")

    def resizeDrvrToTargetSlew(self, drvr_pin: Any) -> None:
        _not_translated("Resizer::resizeDrvrToTargetSlew")

    def targetSlew(self, rf: Any) -> float:
        _not_translated("Resizer::targetSlew")

    def targetLoadCap(self, cell: Any) -> float:
        key = _obj_key(cell)
        if key in self.target_load_map_:
            return self.target_load_map_[key]
        _not_translated("Resizer::targetLoadCap")

    def repairSetup(self, *args: Any, **kwargs: Any) -> bool:
        return self.repair_setup_.repairSetup(*args, **kwargs)

    def reportSwappablePins(self) -> None:
        self.repair_setup_.reportSwappablePins()

    def reportSetupMoves(self) -> Dict[str, Any]:
        return self.repair_setup_.reportMoveSummary()

    def configureRepairSetup(self, *args: Any, **kwargs: Any) -> Any:
        return self.repair_setup_.configure(*args, **kwargs)

    def reportRepairSetupConfig(self) -> Dict[str, Any]:
        return self.repair_setup_.reportConfig()

    def reportRepairSetupCounters(self) -> Dict[str, Any]:
        return self.repair_setup_.reportCounters()

    def rebufferNet(self, drvr_pin: Any) -> None:
        _not_translated("Resizer::rebufferNet")

    def repairHold(self, *args: Any, **kwargs: Any) -> bool:
        return self.repair_hold_.repairHold(*args, **kwargs)

    def holdBufferCount(self) -> int:
        return self.repair_hold_.holdBufferCount()

    def reportHoldCounters(self) -> Dict[str, Any]:
        return self.repair_hold_.reportCounters()

    def configureRepairHold(self, *args: Any, **kwargs: Any) -> Any:
        return self.repair_hold_.configure(*args, **kwargs)

    def reportRepairHoldConfig(self) -> Dict[str, Any]:
        return self.repair_hold_.reportConfig()

    def recoverPower(self, recover_power_percent: float, match_cell_footprint: bool = False, verbose: bool = False) -> bool:
        return self.recover_power_.recoverPower(recover_power_percent, match_cell_footprint, verbose)

    def reportRecoverPowerCounters(self) -> Dict[str, Any]:
        return self.recover_power_.reportCounters()

    def configureRecoverPower(self, *args: Any, **kwargs: Any) -> Any:
        return self.recover_power_.configure(*args, **kwargs)

    def reportRecoverPowerConfig(self) -> Dict[str, Any]:
        return self.recover_power_.reportConfig()

    def swapArithModules(self, path_count: int, target: str, slack_margin: float) -> None:
        _not_translated("Resizer::swapArithModules")

    def designArea(self) -> float:
        return self.design_area_

    def designAreaIncr(self, delta: float) -> None:
        self.design_area_ += delta

    def findFloatingNets(self) -> List[Any]:
        _not_translated("Resizer::findFloatingNets")

    def findFloatingPins(self) -> Set[Any]:
        _not_translated("Resizer::findFloatingPins")

    def findOverdrivenNets(self, include_parallel_driven: bool) -> List[Any]:
        _not_translated("Resizer::findOverdrivenNets")

    def repairTieFanout(self, tie_port: Any, separation: float, verbose: bool) -> None:
        _not_translated("Resizer::repairTieFanout")

    def bufferWireDelay(self, buffer_cell: Any, wire_length: float) -> Tuple[float, float]:
        _not_translated("Resizer::bufferWireDelay")

    def setDebugPin(self, pin: Any) -> None:
        self.debug_pin_ = pin

    def setWorstSlackNetsPercent(self, percent: float) -> None:
        self.worst_slack_nets_percent_ = percent

    def annotateInputSlews(self, inst: Any, scene: Any, min_max: Any) -> None:
        _not_translated("Resizer::annotateInputSlews")

    def resetInputSlews(self) -> None:
        _not_translated("Resizer::resetInputSlews")

    def repairDesign(self, *args: Any, **kwargs: Any) -> None:
        self.repair_design_.repairDesign(*args, **kwargs)

    def repairDesignBufferCount(self) -> int:
        return self.repair_design_.insertedBufferCount()

    def repairDesignViolationCounters(self) -> Dict[str, int]:
        return self.repair_design_.reportViolationCounters()

    def configureRepairDesign(self, *args: Any, **kwargs: Any) -> Any:
        return self.repair_design_.configureLimits(*args, **kwargs)

    def reportRepairDesignLimits(self) -> Dict[str, Any]:
        return self.repair_design_.reportLimits()

    def repairNet(self, *args: Any, **kwargs: Any) -> None:
        self.repair_design_.repairNet(*args, **kwargs)

    def repairClkNets(self, max_wire_length: float) -> None:
        self.repair_design_.repairClkNets(max_wire_length)

    def setClockBuffersList(self, clk_buffers: Sequence[Any]) -> None:
        self.clk_buffers_ = list(clk_buffers)

    def inferClockBufferList(self, lib_name: str, buffers: List[str]) -> None:
        _not_translated("Resizer::inferClockBufferList")

    def isClockCellCandidate(self, cell: Any) -> bool:
        name = _name_of(cell)
        return bool(self.clock_buffer_string_ and self.clock_buffer_string_ in name)

    def setClockBufferString(self, clk_str: str) -> None:
        self.clock_buffer_string_ = clk_str

    def setClockBufferFootprint(self, footprint: str) -> None:
        self.clock_buffer_footprint_ = footprint

    def resetClockBufferPattern(self) -> None:
        self.clock_buffer_string_ = ""
        self.clock_buffer_footprint_ = ""

    def hasClockBufferString(self) -> bool:
        return bool(self.clock_buffer_string_)

    def hasClockBufferFootprint(self) -> bool:
        return bool(self.clock_buffer_footprint_)

    def getClockBufferString(self) -> str:
        return self.clock_buffer_string_

    def getClockBufferFootprint(self) -> str:
        return self.clock_buffer_footprint_

    def getBufferUse(self, buffer: Any) -> BufferUse:
        return BufferUse.CLOCK if buffer in self.clk_buffers_ else BufferUse.DATA

    def repairClkInverters(self) -> None:
        self.repair_design_.repairClkInverters()

    def reportLongWires(self, count: int, digits: int) -> None:
        _not_translated("Resizer::reportLongWires")

    def findMaxWireLength(self, *args: Any, **kwargs: Any) -> float:
        _not_translated("Resizer::findMaxWireLength")

    def maxLoadManhattenDistance(self, net: Any) -> float:
        _not_translated("Resizer::maxLoadManhattenDistance")

    def resizeSlackPreamble(self) -> None:
        self.resize_slacks_.clear()

    def findResizeSlacks(self, run_journal_restore: bool) -> None:
        _not_translated("Resizer::findResizeSlacks")

    def resizeWorstSlackNets(self) -> List[Any]:
        return sorted(self.resize_slacks_, key=self.resize_slacks_.get)

    def resizeNetSlack(self, net: Any) -> Optional[float]:
        return self.resize_slacks_.get(_obj_key(net))

    def findFaninFanouts(self, end_pins: Set[Any]) -> Set[Any]:
        _not_translated("Resizer::findFaninFanouts")

    def findFanins(self, end_pins: Set[Any]) -> Set[Any]:
        _not_translated("Resizer::findFanins")

    def getDbNetwork(self) -> Any:
        return self.db_network_

    def getDbBlock(self) -> Any:
        return self.block_

    def dbuToMeters(self, dist: int) -> float:
        dbu = self.dbu_ or getattr(self.block_, "dbu_per_micron", 0)
        return dist / dbu * 1.0e-6 if dbu else 0.0

    def metersToDbu(self, dist: float) -> int:
        dbu = self.dbu_ or getattr(self.block_, "dbu_per_micron", 0)
        return int(round(dist * 1.0e6 * dbu)) if dbu else 0

    def makeEquivCells(self) -> None:
        _not_translated("Resizer::makeEquivCells")

    def cellVTType(self, master: Any) -> VTCategory:
        vt_index = int(getattr(master, "vt_index", 0))
        vt_name = str(getattr(master, "vt_name", ""))
        return VTCategory(vt_index, vt_name)

    def initBlock(self) -> None:
        chip = getattr(self.db_, "chip", None)
        self.block_ = getattr(chip, "block", None) or getattr(chip, "top_block", None)
        if self.block_ is None and hasattr(chip, "get_top_block"):
            self.block_ = chip.get_top_block()
        if self.block_ is None and hasattr(self.db_, "get_top_block"):
            self.block_ = self.db_.get_top_block()
        self.dbu_ = int(getattr(self.block_, "dbu_per_micron", 0) or 0)

    def journalBeginTest(self) -> None:
        _not_translated("Resizer::journalBeginTest")

    def journalRestoreTest(self) -> None:
        _not_translated("Resizer::journalRestoreTest")

    def logger(self) -> Any:
        return self.logger_

    def eliminateDeadLogic(self, clean_nets: bool) -> None:
        _not_translated("Resizer::eliminateDeadLogic")

    def cellLeakage(self, cell: Any) -> Optional[float]:
        return getattr(cell, "leakage", None)

    def reportEquivalentCells(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("Resizer::reportEquivalentCells")

    def reportBuffers(self, filtered: bool) -> List[Any]:
        if not filtered:
            return list(self.buffer_list_)
        return [cell for cell in self.buffer_list_ if not self.dontUse(cell)]

    def getBufferList(self, buffer_list: List[Any]) -> None:
        buffer_list.extend(self.buffer_list_)

    def setDebugGraphics(self, graphics: ResizerObserver) -> None:
        self.graphics_ = graphics
        self.repair_design_.setDebugGraphics(graphics)

    @staticmethod
    def parseMove(s: str) -> MoveType:
        normalized = s.strip().lower().replace("-", "_")
        aliases = {
            "buffer": MoveType.BUFFER,
            "unbuffer": MoveType.UNBUFFER,
            "swap": MoveType.SWAP,
            "size": MoveType.SIZE,
            "sizeup": MoveType.SIZEUP,
            "size_up": MoveType.SIZEUP,
            "sizedown": MoveType.SIZEDOWN,
            "size_down": MoveType.SIZEDOWN,
            "clone": MoveType.CLONE,
            "split": MoveType.SPLIT,
            "vtswap_speed": MoveType.VTSWAP_SPEED,
            "vt_swap_speed": MoveType.VTSWAP_SPEED,
            "sizeup_match": MoveType.SIZEUP_MATCH,
            "size_up_match": MoveType.SIZEUP_MATCH,
        }
        if normalized not in aliases:
            raise ValueError(f"unknown rsz move: {s}")
        return aliases[normalized]

    @staticmethod
    def parseMoveSequence(sequence: str) -> List[MoveType]:
        if not sequence.strip():
            return []
        tokens = [token for token in sequence.replace(",", " ").split() if token]
        return [Resizer.parseMove(token) for token in tokens]

    def fullyRebuffer(self, pin: Any) -> None:
        _not_translated("Resizer::fullyRebuffer")

    def hasFanout(self, drvr: Any) -> bool:
        fanout = getattr(drvr, "fanout", None)
        if callable(fanout):
            fanout = fanout()
        return bool(fanout)

    def getEstimateParasitics(self) -> Any:
        return self.estimate_parasitics_

    def getSlewRCFactor(self) -> float:
        return self.repair_design_.getSlewRCFactor()

    def findDriverSlewForLoad(self, *_args: Any, **_kwargs: Any) -> float:
        _not_translated("Resizer::findDriverSlewForLoad")

    def computeNewDelaysSlews(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("Resizer::computeNewDelaysSlews")

    def estimateSlewsAfterBufferRemoval(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("Resizer::estimateSlewsAfterBufferRemoval")

    def estimateSlewsInTree(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("Resizer::estimateSlewsInTree")

    def init(self) -> None:
        self.initBlock()

    def computeDesignArea(self) -> float:
        block = self.block_
        insts = getattr(block, "insts", {})
        area = 0.0
        for inst in getattr(insts, "values", lambda: [])():
            bbox = getattr(inst, "bbox", None)
            if bbox is not None:
                lx, ly, ux, uy = bbox
                area += self.dbuToMeters(max(0, ux - lx)) * self.dbuToMeters(max(0, uy - ly))
        return area

    def initDesignArea(self) -> None:
        self.design_area_ = self.computeDesignArea()

    def copyDontUseFromLiberty(self) -> None:
        """占位边界：后续从 Liberty cell dont_use 属性同步。"""

    def findBuffers(self) -> None:
        """占位边界：后续从 Liberty/LEF 识别 buffer/inverter。"""

class SwapArithModules:
    """算术模块替换抽象接口，对应 ``SwapArithModules``。"""

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.db_network_ = None
        self.logger_ = None

    def replaceArithModules(self, path_count: int, target: str, slack_threshold: float) -> bool:
        raise NotImplementedError

    def collectArithInstsOnPath(self, path: Any, arithInsts: Set[Any]) -> None:
        raise NotImplementedError

    def isArithInstance(self, inst: Any) -> Tuple[bool, Any]:
        raise NotImplementedError

    def hasArithOperatorProperty(self, mod_inst: Any) -> bool:
        raise NotImplementedError

    def findCriticalInstances(self, path_count: int, target: str, slack_threshold: float, insts: Set[Any]) -> None:
        raise NotImplementedError

    def doSwapInstances(self, insts: Set[Any], target: str) -> bool:
        raise NotImplementedError

def initResizer(tcl_interp: Any = None) -> Resizer:
    """对应 ``MakeResizer.hh`` 的入口函数。

    C++ 版本向 Tcl 注册命令；Python 版本返回一个顶层 ``Resizer``，调用方可再
    注入 db/sta/router 等依赖。
    """

    return Resizer()
