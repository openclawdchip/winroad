"""Setup timing repair flow boundary for :mod:`winroad.rsz`."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Set

from .common import (
    EndpointRepairState,
    MoveType,
    OptoParams,
    RepairFlowPhase,
    RepairFlowState,
    RepairPhaseEvent,
    RepairSetupConfig,
    _json_value,
    _not_translated,
    _obj_key,
)
from .moves import (
    BaseMove,
    BufferMove,
    CloneMove,
    MoveTracker,
    SizeDownMove,
    SizeUpMatchMove,
    SizeUpMove,
    SplitLoadMove,
    SwapPinsMove,
    UnbufferMove,
    VTSwapSpeedMove,
)


class RepairSetup:
    """setup timing repair 主流程边界。"""

    initial_decreasing_slack_max_passes_ = 6
    pass_limit_increment_ = 5
    print_interval_ = 10
    opto_small_interval_ = 100
    opto_large_interval_ = 1000
    inc_fix_rate_threshold_ = 0.0001
    max_last_gasp_passes_ = 10

    def __init__(self, resizer: Resizer) -> None:
        self.resizer_ = resizer
        self.logger_ = resizer.logger_
        self.db_network_ = resizer.db_network_
        self.estimate_parasitics_ = resizer.estimate_parasitics_
        self.violator_collector_ = None
        self.move_tracker_: Optional[MoveTracker] = None
        self.fallback_ = False
        self.min_viol_ = 0.0
        self.max_viol_ = 0.0
        self.max_repairs_per_pass_ = 1
        self.removed_buffer_count_ = 0
        self.initial_design_area_ = 0.0
        self.move_sequence_: List[BaseMove] = []
        self.move_sequence_types_: List[MoveType] = []
        self.buffer_move_ = BufferMove(resizer)
        self.unbuffer_move_ = UnbufferMove(resizer)
        self.swap_pins_move_ = SwapPinsMove(resizer)
        self.sizeup_move_ = SizeUpMove(resizer)
        self.sizeup_match_move_ = SizeUpMatchMove(resizer)
        self.sizedown_move_ = SizeDownMove(resizer)
        self.clone_move_ = CloneMove(resizer)
        self.split_load_move_ = SplitLoadMove(resizer)
        self.vt_swap_move_ = VTSwapSpeedMove(resizer)
        self.endpoint_pass_counts_phase1_: Dict[Any, int] = {}
        self.wns_no_progress_count_ = 0
        self.rejected_pin_moves_current_endpoint_: Dict[Any, Set[BaseMove]] = {}
        self.overall_no_progress_count_ = 0
        self.max_end_repairs_ = -1
        self.equiv_pin_map_: Dict[Any, Set[Any]] = {}
        self.config_ = RepairSetupConfig()
        self.phase_ = RepairFlowPhase.IDLE
        self.phase_history_: List[RepairPhaseEvent] = []
        self.endpoint_states_: Dict[Any, EndpointRepairState] = {}

    def init(self) -> None:
        self.db_network_ = self.resizer_.db_network_
        for move in self.allMoves():
            move.init()

    def allMoves(self) -> List[BaseMove]:
        return [
            self.buffer_move_,
            self.unbuffer_move_,
            self.swap_pins_move_,
            self.sizeup_move_,
            self.sizeup_match_move_,
            self.sizedown_move_,
            self.clone_move_,
            self.split_load_move_,
            self.vt_swap_move_,
        ]

    def setupMoveSequence(
        self,
        sequence: Sequence[MoveType],
        skip_pin_swap: bool,
        skip_gate_cloning: bool,
        skip_size_down: bool,
        skip_buffering: bool,
        skip_buffer_removal: bool,
        skip_vt_swap: bool,
    ) -> None:
        """保存 move sequence 边界。

        C++ 会创建具体 BaseMove 派生类；这些派生动作尚未翻译，所以这里先只
        保留筛选后的枚举序列，供文档/测试确认入口参数。
        """

        skipped = set()
        if skip_pin_swap:
            skipped.add(MoveType.SWAP)
        if skip_gate_cloning:
            skipped.add(MoveType.CLONE)
        if skip_size_down:
            skipped.add(MoveType.SIZEDOWN)
        if skip_buffering:
            skipped.update({MoveType.BUFFER, MoveType.SPLIT})
        if skip_buffer_removal:
            skipped.add(MoveType.UNBUFFER)
        if skip_vt_swap:
            skipped.add(MoveType.VTSWAP_SPEED)
        move_map: Dict[MoveType, BaseMove] = {
            MoveType.BUFFER: self.buffer_move_,
            MoveType.UNBUFFER: self.unbuffer_move_,
            MoveType.SWAP: self.swap_pins_move_,
            MoveType.SIZE: self.sizeup_move_,
            MoveType.SIZEUP: self.sizeup_move_,
            MoveType.SIZEUP_MATCH: self.sizeup_match_move_,
            MoveType.SIZEDOWN: self.sizedown_move_,
            MoveType.CLONE: self.clone_move_,
            MoveType.SPLIT: self.split_load_move_,
            MoveType.VTSWAP_SPEED: self.vt_swap_move_,
        }
        self.move_sequence_types_ = [move for move in sequence if move not in skipped]
        self.move_sequence_ = [move_map[move] for move in self.move_sequence_types_]
        self.config_.move_sequence = list(self.move_sequence_types_)
        self.config_.skip_pin_swap = skip_pin_swap
        self.config_.skip_gate_cloning = skip_gate_cloning
        self.config_.skip_size_down = skip_size_down
        self.config_.skip_buffering = skip_buffering
        self.config_.skip_buffer_removal = skip_buffer_removal
        self.config_.skip_vt_swap = skip_vt_swap

    def configure(
        self,
        setup_slack_margin: Optional[float] = None,
        verbose: Optional[bool] = None,
        skip_pin_swap: Optional[bool] = None,
        skip_gate_cloning: Optional[bool] = None,
        skip_size_down: Optional[bool] = None,
        skip_buffering: Optional[bool] = None,
        skip_buffer_removal: Optional[bool] = None,
        skip_vt_swap: Optional[bool] = None,
        max_repairs_per_pass: Optional[int] = None,
        max_end_repairs: Optional[int] = None,
        move_sequence: Optional[Sequence[MoveType]] = None,
    ) -> RepairSetupConfig:
        prev = self.config_
        setup_slack_margin = prev.setup_slack_margin if setup_slack_margin is None else setup_slack_margin
        verbose = prev.verbose if verbose is None else verbose
        skip_pin_swap = prev.skip_pin_swap if skip_pin_swap is None else skip_pin_swap
        skip_gate_cloning = prev.skip_gate_cloning if skip_gate_cloning is None else skip_gate_cloning
        skip_size_down = prev.skip_size_down if skip_size_down is None else skip_size_down
        skip_buffering = prev.skip_buffering if skip_buffering is None else skip_buffering
        skip_buffer_removal = prev.skip_buffer_removal if skip_buffer_removal is None else skip_buffer_removal
        skip_vt_swap = prev.skip_vt_swap if skip_vt_swap is None else skip_vt_swap
        if max_repairs_per_pass is not None:
            self.max_repairs_per_pass_ = int(max_repairs_per_pass)
        if max_end_repairs is not None:
            self.max_end_repairs_ = int(max_end_repairs)
        selected_sequence = list(move_sequence) if move_sequence is not None else list(prev.move_sequence or self.move_sequence_types_)
        self.config_ = RepairSetupConfig(
            setup_slack_margin=setup_slack_margin,
            verbose=verbose,
            skip_pin_swap=skip_pin_swap,
            skip_gate_cloning=skip_gate_cloning,
            skip_size_down=skip_size_down,
            skip_buffering=skip_buffering,
            skip_buffer_removal=skip_buffer_removal,
            skip_vt_swap=skip_vt_swap,
            max_repairs_per_pass=self.max_repairs_per_pass_,
            max_end_repairs=self.max_end_repairs_,
            move_sequence=selected_sequence,
        )
        if move_sequence is not None:
            self.setupMoveSequence(
                move_sequence,
                skip_pin_swap,
                skip_gate_cloning,
                skip_size_down,
                skip_buffering,
                skip_buffer_removal,
                skip_vt_swap,
            )
        self.setPhase(RepairFlowPhase.CONFIGURED, "configure")
        return self.config_

    def resetConfig(self) -> None:
        self.max_repairs_per_pass_ = 1
        self.max_end_repairs_ = -1
        self.move_sequence_.clear()
        self.move_sequence_types_.clear()
        self.config_ = RepairSetupConfig()
        self.setPhase(RepairFlowPhase.IDLE, "reset_config")

    def config(self) -> RepairSetupConfig:
        return self.config_

    def importConfig(self, data: Dict[str, Any]) -> RepairSetupConfig:
        """导入 setup repair 配置，不触发 STA 查询或 move 执行。"""

        config = RepairSetupConfig.from_dict(data)
        return self.configure(
            setup_slack_margin=config.setup_slack_margin,
            verbose=config.verbose,
            skip_pin_swap=config.skip_pin_swap,
            skip_gate_cloning=config.skip_gate_cloning,
            skip_size_down=config.skip_size_down,
            skip_buffering=config.skip_buffering,
            skip_buffer_removal=config.skip_buffer_removal,
            skip_vt_swap=config.skip_vt_swap,
            max_repairs_per_pass=config.max_repairs_per_pass,
            max_end_repairs=config.max_end_repairs,
            move_sequence=config.move_sequence,
        )

    def exportConfig(self) -> Dict[str, Any]:
        """导出 JSON-safe 配置快照。"""

        return self.reportConfig()

    def reportConfig(self) -> Dict[str, Any]:
        return self.config_.as_dict()

    def moveSequenceTypes(self) -> List[MoveType]:
        return list(self.move_sequence_types_)

    def setMoveTracker(self, tracker: Optional[MoveTracker]) -> None:
        self.move_tracker_ = tracker

    def makeMoveTracker(self) -> MoveTracker:
        self.move_tracker_ = MoveTracker(
            self.logger_,
            self.resizer_.sta_,
            self.db_network_,
            self.resizer_.block_,
        )
        return self.move_tracker_

    def moveTracker(self) -> Optional[MoveTracker]:
        return self.move_tracker_

    def beginEndpointRepair(self, endpoint_pin: Any) -> int:
        """记录当前 endpoint 的一次 repair 尝试，供上层调度/报告使用。"""

        key = _obj_key(endpoint_pin)
        count = self.endpoint_pass_counts_phase1_.get(key, 0) + 1
        self.endpoint_pass_counts_phase1_[key] = count
        state = self.endpoint_states_.setdefault(key, EndpointRepairState(endpoint_pin))
        state.begin()
        self.rejected_pin_moves_current_endpoint_.clear()
        if self.move_tracker_ is not None:
            self.move_tracker_.setCurrentEndpoint(endpoint_pin)
        self.setPhase(RepairFlowPhase.REPAIRING, f"endpoint={_json_value(endpoint_pin)}")
        return count

    def finishEndpointRepair(self, endpoint_pin: Any, committed: bool, reason: str = "") -> None:
        """结束一个 endpoint repair 尝试，只更新状态机和统计。"""

        key = _obj_key(endpoint_pin)
        state = self.endpoint_states_.setdefault(key, EndpointRepairState(endpoint_pin))
        state.finish(committed, reason)
        phase = RepairFlowPhase.COMMITTED if committed else RepairFlowPhase.ROLLED_BACK
        self.setPhase(phase, reason or f"endpoint={_json_value(endpoint_pin)}")

    def endpointRepairCount(self, endpoint_pin: Any) -> int:
        return self.endpoint_pass_counts_phase1_.get(_obj_key(endpoint_pin), 0)

    def recordRejectedMove(self, pin: Any, move: BaseMove) -> None:
        key = _obj_key(pin)
        self.rejected_pin_moves_current_endpoint_.setdefault(key, set()).add(move)

    def rejectedMovesForPin(self, pin: Any) -> Set[BaseMove]:
        return set(self.rejected_pin_moves_current_endpoint_.get(_obj_key(pin), set()))

    def removedBufferCount(self) -> int:
        return self.removed_buffer_count_

    def recordRemovedBuffer(self, count: int = 1) -> None:
        if count < 0:
            raise ValueError("removed buffer count must be non-negative")
        self.removed_buffer_count_ += count

    def resetCounters(self) -> None:
        self.removed_buffer_count_ = 0
        self.endpoint_pass_counts_phase1_.clear()
        self.endpoint_states_.clear()
        self.wns_no_progress_count_ = 0
        self.overall_no_progress_count_ = 0
        self.rejected_pin_moves_current_endpoint_.clear()
        for move in self.allMoves():
            move.all_inst_set_.clear()
            move.accepted_inst_set_.clear()
            move.pending_inst_set_.clear()
            move.all_count_ = 0
            move.pending_count_ = 0
            move.rejected_count_ = 0
            move.accepted_count_ = 0
        self.setPhase(RepairFlowPhase.IDLE, "reset_counters")

    def reportCounters(self) -> Dict[str, Any]:
        return {
            "removed_buffers": self.removed_buffer_count_,
            "endpoint_repairs": _json_value(self.endpoint_pass_counts_phase1_),
            "wns_no_progress": self.wns_no_progress_count_,
            "overall_no_progress": self.overall_no_progress_count_,
            "move_counts": {move.name(): move.moveCounters() for move in self.allMoves()},
            "endpoint_states": self.reportEndpointStates(),
        }

    def reportMoveSummary(self) -> Dict[str, Any]:
        move_counts = {move.name(): move.numMoves() for move in self.allMoves()}
        return {
            "move_sequence": [move.value for move in self.move_sequence_types_],
            "removed_buffers": self.removed_buffer_count_,
            "endpoint_repairs": _json_value(self.endpoint_pass_counts_phase1_),
            "move_counts": move_counts,
            "tracker": self.move_tracker_.report() if self.move_tracker_ is not None else None,
            "config": self.reportConfig(),
            "phase": self.phase_.value,
        }

    def setPhase(self, phase: RepairFlowPhase, reason: str = "") -> None:
        """记录 setup repair 状态机阶段。"""

        self.phase_ = phase
        self.phase_history_.append(RepairPhaseEvent(phase=phase, reason=reason, order=len(self.phase_history_)))

    def phase(self) -> RepairFlowPhase:
        return self.phase_

    def phaseHistory(self) -> List[RepairPhaseEvent]:
        return list(self.phase_history_)

    def reportEndpointStates(self) -> List[Dict[str, Any]]:
        return [state.as_dict() for state in self.endpoint_states_.values()]

    def validateBatch(self, batch: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """校验一组 setup 配置，供批处理入口先行 fail-fast。

        这里只检查 Python 接口层能保证的边界：数值非负、move 名称可解析、skip 后
        至少保留一个动作。真实 violator 收集和 STA slack 查询仍由未翻译入口负责。
        """

        errors: List[str] = []
        normalized: List[Dict[str, Any]] = []
        for index, item in enumerate(batch):
            try:
                config = RepairSetupConfig.from_dict(item)
                if config.max_repairs_per_pass < 0:
                    raise ValueError("max_repairs_per_pass must be non-negative")
                if config.max_end_repairs < -1:
                    raise ValueError("max_end_repairs must be -1 or non-negative")
                if config.setup_slack_margin < 0.0:
                    raise ValueError("setup_slack_margin must be non-negative")
                probe = RepairSetupConfig.from_dict(config.as_dict())
                self._validateMoveSequenceNotEmpty(probe)
                normalized.append(config.as_dict())
            except Exception as exc:  # noqa: BLE001 - 批处理需要收集所有配置错误。
                errors.append(f"batch[{index}]: {exc}")
        return {"valid": not errors, "errors": errors, "items": normalized}

    def _validateMoveSequenceNotEmpty(self, config: RepairSetupConfig) -> None:
        skipped = set()
        if config.skip_pin_swap:
            skipped.add(MoveType.SWAP)
        if config.skip_gate_cloning:
            skipped.add(MoveType.CLONE)
        if config.skip_size_down:
            skipped.add(MoveType.SIZEDOWN)
        if config.skip_buffering:
            skipped.update({MoveType.BUFFER, MoveType.SPLIT})
        if config.skip_buffer_removal:
            skipped.add(MoveType.UNBUFFER)
        if config.skip_vt_swap:
            skipped.add(MoveType.VTSWAP_SPEED)
        if config.move_sequence and not [move for move in config.move_sequence if move not in skipped]:
            raise ValueError("move_sequence is empty after applying skip flags")

    def reportState(self) -> Dict[str, Any]:
        """返回 setup flow 的配置、计数器和 tracker 快照。"""

        return RepairFlowState(
            name="RepairSetup",
            config=self.reportConfig(),
            counters=self.reportCounters(),
            details=self.reportMoveSummary(),
            phase=self.phase_,
            history=self.phase_history_,
        ).as_dict()

    def statistics(self) -> Dict[str, Any]:
        return self.reportState()

    def to_json(self, **json_kwargs: Any) -> str:
        kwargs = {"sort_keys": True}
        kwargs.update(json_kwargs)
        return json.dumps(self.statistics(), **kwargs)

    def repairSetup(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RepairSetup::repairSetup")

    def repairEndpoint(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RepairSetup::repairEndpoint")

    def repairPins(self, *_args: Any, **_kwargs: Any) -> bool:
        _not_translated("RepairSetup::repairPins")

    def fanout(self, vertex: Any) -> int:
        fanout = getattr(vertex, "fanout", 0)
        return int(fanout() if callable(fanout) else fanout)

    def hasTopLevelOutputPort(self, net: Any) -> bool:
        _not_translated("RepairSetup::hasTopLevelOutputPort")

    def reportSwappablePins(self) -> None:
        self.swap_pins_move_.reportSwappablePins()
