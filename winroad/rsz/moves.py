"""Setup-repair move state and move class boundaries."""

from __future__ import annotations

from math import inf
from typing import Any, Dict, List, Optional, Set

from .common import MoveStateData, MoveStateType, PinInfo, RiseFallArray, _not_translated, _obj_key


class BaseMove:
    """setup 修复动作基类，对应 ``BaseMove``。

    这里先翻译 move 计数、提交/回滚集合等通用状态；具体动作在 C++ 中由
    BufferMove、SizeUpMove、SwapPinsMove 等派生类实现，后续应按类继续补。
    """

    def __init__(self, resizer: "Resizer") -> None:
        self.resizer_ = resizer
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.logger_ = resizer.logger_
        self.network_ = getattr(resizer.sta_, "network", None)
        self.db_network_ = resizer.db_network_
        self.sta_ = resizer.sta_
        self.db_ = resizer.db_
        self.dbu_ = resizer.dbu_
        self.opendp_ = resizer.opendp_
        self.scene_ = None
        self.all_inst_set_: Set[Any] = set()
        self.accepted_inst_set_: Set[Any] = set()
        self.pending_inst_set_: Set[Any] = set()
        self.all_count_ = 0
        self.pending_count_ = 0
        self.rejected_count_ = 0
        self.accepted_count_ = 0
        self.input_slew_map_: Dict[Any, RiseFallArray] = {}
        self.tgt_slews_: RiseFallArray = (inf, inf)

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        return False

    def name(self) -> str:
        raise NotImplementedError("BaseMove::name must be implemented by subclasses")

    def init(self) -> None:
        """刷新 STA/DB 依赖指针；对应 C++ init 边界。"""

        self.db_network_ = self.resizer_.db_network_
        self.sta_ = self.resizer_.sta_
        self.db_ = self.resizer_.db_
        self.dbu_ = self.resizer_.dbu_
        self.opendp_ = self.resizer_.opendp_

    def countMove(self, inst: Any, count: int = 1) -> None:
        key = _obj_key(inst)
        self.all_inst_set_.add(key)
        self.pending_inst_set_.add(key)
        self.all_count_ += count
        self.pending_count_ += count

    def commitMoves(self) -> None:
        self.accepted_inst_set_.update(self.pending_inst_set_)
        self.accepted_count_ += self.pending_count_
        self.pending_inst_set_.clear()
        self.pending_count_ = 0

    def undoMoves(self) -> None:
        self.rejected_count_ += self.pending_count_
        self.pending_inst_set_.clear()
        self.pending_count_ = 0

    def numPendingMoves(self) -> int:
        return self.pending_count_

    def hasPendingMoves(self, inst: Any) -> int:
        return int(_obj_key(inst) in self.pending_inst_set_)

    def numCommittedMoves(self) -> int:
        return self.accepted_count_

    def numRejectedMoves(self) -> int:
        return self.rejected_count_

    def hasMoves(self, inst: Any) -> int:
        key = _obj_key(inst)
        return int(key in self.all_inst_set_ or key in self.pending_inst_set_)

    def numMoves(self) -> int:
        return self.all_count_

class BufferMove(BaseMove):
    """对应 ``BufferMove``，setup repair 的重缓冲动作边界。"""

    def name(self) -> str:
        return "BufferMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("BufferMove::doMove")

    def rebufferNet(self, drvr_pin: Any) -> None:
        _not_translated("BufferMove::rebufferNet")

    def rebuffer(self, drvr_pin: Any) -> int:
        _not_translated("BufferMove::rebuffer")

    def debugCheckMultipleBuffers(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("BufferMove::debugCheckMultipleBuffers")

    def hasTopLevelOutputPort(self, net: Any) -> bool:
        _not_translated("BufferMove::hasTopLevelOutputPort")

class UnbufferMove(BaseMove):
    """对应 ``UnbufferMove``，buffer removal 动作边界。"""

    buffer_removal_max_fanout_ = 10

    def name(self) -> str:
        return "UnbufferMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("UnbufferMove::doMove")

    def removeBufferIfPossible(self, buffer: Any, honorDontTouchFixed: bool) -> bool:
        _not_translated("UnbufferMove::removeBufferIfPossible")

    def canRemoveBuffer(self, buffer: Any, honorDontTouchFixed: bool) -> bool:
        _not_translated("UnbufferMove::canRemoveBuffer")

    def removeBuffer(self, buffer: Any) -> bool:
        _not_translated("UnbufferMove::removeBuffer")

    def bufferBetweenPorts(self, buffer: Any) -> bool:
        _not_translated("UnbufferMove::bufferBetweenPorts")

    def bufferRemovalCreatesFeedthrough(self, ip_modnet: Any, op_modnet: Any) -> bool:
        _not_translated("UnbufferMove::bufferRemovalCreatesFeedthrough")

class SizeUpMove(BaseMove):
    """对应 ``SizeUpMove``。"""

    def name(self) -> str:
        return "SizeUpMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SizeUpMove::doMove")

class SizeUpMatchMove(BaseMove):
    """对应 ``SizeUpMatchMove``，匹配前级驱动强度的 size-up 动作。"""

    def name(self) -> str:
        return "SizeUpMoveMatch"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SizeUpMatchMove::doMove")

class SizeDownMove(BaseMove):
    """对应 ``SizeDownMove``。"""

    size_down_max_fanout_ = 10

    def name(self) -> str:
        return "SizeDownMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SizeDownMove::doMove")

    def downSizeGate(self, *_args: Any, **_kwargs: Any) -> Any:
        _not_translated("SizeDownMove::downSizeGate")

class SwapPinsMove(BaseMove):
    """对应 ``SwapPinsMove``，等价输入 pin swap 的动作边界。"""

    def __init__(self, resizer: "Resizer") -> None:
        super().__init__(resizer)
        self.equiv_pin_map_: Dict[Any, Set[Any]] = {}

    def name(self) -> str:
        return "SwapPinsMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SwapPinsMove::doMove")

    def reportSwappablePins(self) -> None:
        _not_translated("SwapPinsMove::reportSwappablePins")

    def swapPins(self, inst: Any, port1: Any, port2: Any) -> bool:
        _not_translated("SwapPinsMove::swapPins")

    def equivCellPins(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("SwapPinsMove::equivCellPins")

    def annotateInputSlews(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("SwapPinsMove::annotateInputSlews")

    def findSwapPinCandidate(self, *_args: Any, **_kwargs: Any) -> None:
        _not_translated("SwapPinsMove::findSwapPinCandidate")

    def resetInputSlews(self) -> None:
        _not_translated("SwapPinsMove::resetInputSlews")

class CloneMove(BaseMove):
    """对应 ``CloneMove``，gate cloning 动作边界。"""

    def name(self) -> str:
        return "CloneMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("CloneMove::doMove")

    def computeCloneGateLocation(self, *_args: Any, **_kwargs: Any) -> Point:
        _not_translated("CloneMove::computeCloneGateLocation")

    def cloneDriver(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("CloneMove::cloneDriver")

class SplitLoadMove(BaseMove):
    """对应 ``SplitLoadMove``。"""

    split_load_min_fanout_ = 8

    def name(self) -> str:
        return "SplitLoadMove"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("SplitLoadMove::doMove")

class VTSwapSpeedMove(BaseMove):
    """对应 ``VTSwapSpeedMove``，setup timing 用 VT swap 动作边界。"""

    def name(self) -> str:
        return "VTSwapSpeed"

    def doMove(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("VTSwapSpeedMove::doMove")

    def isSwappable(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("VTSwapSpeedMove::isSwappable")

class MoveTracker:
    """记录 setup repair 尝试、提交、拒绝的 pin/move 状态。"""

    def __init__(self, logger: Any, sta: Any, db_network: Any, block: Any) -> None:
        self.logger_ = logger
        self.sta_ = sta
        self.db_network_ = db_network
        self.block_ = block
        self.current_endpoint_: Any = None
        self.critical_pins_: List[Any] = []
        self.violators_: List[Any] = []
        self.pin_infos_: Dict[Any, PinInfo] = {}
        self.moves_: List[MoveStateData] = []
        self.pending_moves_: List[MoveStateData] = []

    def inDbITermDestroy(self, iterm: Any) -> None:
        """OpenDB callback 边界；当前 Python 版本只保留接口。"""

    def inDbITermCreate(self, iterm: Any) -> None:
        """OpenDB callback 边界；当前 Python 版本只保留接口。"""

    def setCurrentEndpoint(self, endpoint_pin: Any) -> None:
        self.current_endpoint_ = endpoint_pin

    def currentEndpoint(self) -> Any:
        return self.current_endpoint_

    def trackCriticalPins(self, critical_pins: Sequence[Any]) -> None:
        self.critical_pins_.extend(critical_pins)

    def criticalPins(self) -> List[Any]:
        return list(self.critical_pins_)

    def trackViolator(self, pin: Any) -> None:
        self.violators_.append(pin)

    def violators(self) -> List[Any]:
        return list(self.violators_)

    def trackViolatorWithInfo(
        self,
        pin: Any,
        gate_type: str,
        load_delay: float,
        intrinsic_delay: float,
        pin_slack: float,
        endpoint_slack: float,
    ) -> None:
        self.trackViolator(pin)
        self.pin_infos_[_obj_key(pin)] = PinInfo(
            pin, gate_type, load_delay, intrinsic_delay, pin_slack, endpoint_slack
        )

    def pinInfo(self, pin: Any) -> Optional[PinInfo]:
        return self.pin_infos_.get(_obj_key(pin))

    def trackMove(self, pin: Any, move_type: str, state: MoveStateType) -> None:
        data = MoveStateData(pin=pin, order=len(self.moves_), move_type=move_type, state=state)
        self.moves_.append(data)
        if state is MoveStateType.ATTEMPT:
            self.pending_moves_.append(data)

    def moves(self) -> List[MoveStateData]:
        return list(self.moves_)

    def pendingMoves(self) -> List[MoveStateData]:
        return list(self.pending_moves_)

    def commitMoves(self) -> None:
        for data in self.pending_moves_:
            self.moves_.append(
                MoveStateData(data.pin, data.move_type, MoveStateType.ATTEMPT_COMMIT, len(self.moves_))
            )
        self.pending_moves_.clear()

    def rejectMoves(self) -> None:
        for data in self.pending_moves_:
            self.moves_.append(
                MoveStateData(data.pin, data.move_type, MoveStateType.ATTEMPT_REJECT, len(self.moves_))
            )
        self.pending_moves_.clear()

    def moveSummary(self) -> Dict[str, int]:
        summary = {state.name.lower(): 0 for state in MoveStateType}
        for move in self.moves_:
            summary[move.state.name.lower()] += 1
        summary["pending"] = len(self.pending_moves_)
        return summary
