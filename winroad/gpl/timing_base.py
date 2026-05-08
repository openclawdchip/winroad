"""Timing-driven placement boundary for WinRoad gpl."""

from __future__ import annotations

import inspect
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .nesterov import GNet, NesterovBaseCommon

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
        self.timing_driven_nets_: List[GNet] = []
        self.prev_timing_weights_: Dict[int, float] = {}
        self.prev_timing_weights_by_id_: Dict[int, float] = {}
        self.restore_count_ = 0
        self.last_restored_weights_ = 0
        self.run_journal_restore_ = False
        self.timing_driven_iter_ = 0
        self.last_overflow_ = 0.0
        self.last_resizer_result_ = False
        self.last_weight_updates_: List[Dict[str, Any]] = []
        self.last_update_count_ = 0
        self.last_update_changed_count_ = 0
        self.last_update_max_weight_ = 1.0
        self.last_execute_result_ = False
        self.last_resizer_hook_: Dict[str, Any] = {}
        self.last_filler_reset_: Dict[str, Any] = {}

    def isTimingNetWeightOverflow(self, overflow: float) -> bool:
        checkpoint = int(round(overflow * 100))
        self.last_overflow_ = overflow
        if checkpoint not in self.timingOverflowChk_:
            return False
        self.timingOverflowChk_.remove(checkpoint)
        return True

    def addTimingNetWeightOverflow(self, overflow: int) -> None:
        self.timingNetWeightOverflow_.append(overflow)
        self.initTimingOverflowChk()

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
        if max < 1.0:
            raise ValueError("timing net weight max 必须大于等于 1.0")
        self.net_weight_max_ = max

    def executeTimingDriven(self, run_journal_restore: bool) -> bool:
        """执行纯数据版 timing-driven reweight。

        OpenROAD 原始流程会先从 STA 读取关键路径 slack，再调用 resizer hook；
        这些真实依赖仍保留在对应未实现入口。这里仅对已经登记在
        `timing_driven_nets_` 的 GNet 做确定性权重更新，便于 Python 层保存、
        恢复和报告 timing-driven 状态。
        """

        self.run_journal_restore_ = run_journal_restore
        self.timing_driven_iter_ += 1
        self.snapshotTimingWeights()
        self.updateGNetWeights()
        self.last_execute_result_ = self.last_update_count_ > 0
        return self.last_execute_result_

    def resetTimingDrivenNets(self) -> None:
        self.timing_driven_nets_.clear()
        if self.nbc_ is not None:
            self.nbc_.resetTimingNetWeights()

    def addTimingDrivenNet(self, gnet: GNet) -> None:
        """记录 timing-driven net，真实 STA slack 筛选仍在未翻译入口中。"""

        if gnet not in self.timing_driven_nets_:
            self.timing_driven_nets_.append(gnet)

    def clearTimingDrivenNets(self) -> None:
        self.timing_driven_nets_.clear()

    def updateGNetWeights(self) -> None:
        """按已登记 timing net 的顺序确定性更新权重。

        这里不读取 STA slack，也不推断关键度。调用者必须先通过
        `addTimingDrivenNet` 或 `setTimingDrivenNets` 提供真实 timing-driven net
        容器。权重从 1.0 单调插值到 `net_weight_max_`，并按当前顺序分配：
        越靠前的 net 权重越高，方便上游用真实 STA 结果排序后复用该入口。
        """

        nets = self._uniqueTimingDrivenNets()
        self.last_weight_updates_ = []
        self.last_update_count_ = 0
        self.last_update_changed_count_ = 0
        self.last_update_max_weight_ = 1.0
        if not nets:
            return

        count = len(nets)
        denominator = max(1, count - 1)
        for rank, gnet in enumerate(nets):
            old_weight = float(gnet.getTimingWeight())
            if count == 1:
                new_weight = float(self.net_weight_max_)
            else:
                criticality = 1.0 - (rank / denominator)
                new_weight = 1.0 + (float(self.net_weight_max_) - 1.0) * criticality
            new_weight = self._clampWeight(new_weight)
            gnet.setTimingWeight(new_weight)
            changed = abs(old_weight - new_weight) > 1.0e-12
            self.last_update_count_ += 1
            self.last_update_changed_count_ += 1 if changed else 0
            self.last_update_max_weight_ = max(self.last_update_max_weight_, new_weight)
            self.last_weight_updates_.append(
                {
                    "index": rank,
                    "name": self._gnetName(gnet),
                    "old_weight": old_weight,
                    "new_weight": new_weight,
                    "changed": changed,
                }
            )

    def setTimingDrivenNets(self, gnets: Iterable[GNet]) -> None:
        self.timing_driven_nets_ = []
        for gnet in gnets:
            self.addTimingDrivenNet(gnet)

    def importTimingDrivenNetsByIndex(self, indexes: Iterable[int]) -> None:
        """从 nesterov common 的 GNet 下标导入 timing-driven net 列表。"""

        if self.nbc_ is None:
            raise ValueError("缺少 NesterovBaseCommon，无法按下标导入 GNet")
        all_nets = self.nbc_.getGNets()
        self.timing_driven_nets_ = []
        for index in indexes:
            idx = int(index)
            if idx < 0 or idx >= len(all_nets):
                raise IndexError(f"GNet index 越界: {idx}")
            self.addTimingDrivenNet(all_nets[idx])

    def runResizerForTiming(self, run_journal_restore: bool) -> bool:
        self.run_journal_restore_ = run_journal_restore
        report = self._invokeAdapterHook(
            hook_names=(
                "runResizerForTiming",
                "repairTiming",
                "repairTimingDriven",
                "runTimingRepair",
                "runTimingDrivenRepair",
                "timingRepair",
            ),
            args=(run_journal_restore,),
            sources=self._hookSources(),
            label="resizer_timing_repair",
        )
        self.last_resizer_hook_ = report
        self.last_resizer_result_ = report.get("status") == "ok"
        return self.last_resizer_result_

    def resetFillerCells(self) -> bool:
        report = self._invokeAdapterHook(
            hook_names=(
                "resetFillerCells",
                "resetFillerGCells",
                "resetFillers",
                "resetTimingDrivenFillerCells",
            ),
            args=(),
            sources=self._hookSources(),
            label="filler_reset",
        )
        self.last_filler_reset_ = report
        return report.get("status") == "ok"

    def initTimingOverflowChk(self) -> None:
        self.timingOverflowChk_ = sorted(set(self.timingNetWeightOverflow_), reverse=True)

    def timingOverflowChk(self) -> List[int]:
        return self.timingOverflowChk_

    def timingDrivenNets(self) -> List[GNet]:
        return self.timing_driven_nets_

    def restorePrevTimingWeights(self) -> None:
        if self.nbc_ is None:
            return
        restored = 0
        for index, gnet in enumerate(self.nbc_.getGNets()):
            weight = self.prev_timing_weights_by_id_.get(id(gnet), self.prev_timing_weights_.get(index))
            if weight is not None:
                gnet.setTimingWeight(weight)
                restored += 1
        self.restore_count_ += 1
        self.last_restored_weights_ = restored
        self.last_weight_updates_ = []
        self.last_update_count_ = 0
        self.last_update_changed_count_ = 0
        self.last_update_max_weight_ = max(
            [gnet.getTimingWeight() for gnet in self.nbc_.getGNets()] or [1.0]
        )

    def snapshotTimingWeights(self) -> None:
        self.prev_timing_weights_ = {}
        self.prev_timing_weights_by_id_ = {}
        if self.nbc_ is None:
            return
        for index, gnet in enumerate(self.nbc_.getGNets()):
            weight = gnet.getTimingWeight()
            self.prev_timing_weights_[index] = weight
            self.prev_timing_weights_by_id_[id(gnet)] = weight

    def clearTimingWeightSnapshot(self) -> None:
        self.prev_timing_weights_.clear()
        self.prev_timing_weights_by_id_.clear()

    def reportTimingDriven(self) -> Dict[str, Any]:
        return {
            "checkpoints": list(self.timingNetWeightOverflow_),
            "remaining_checkpoints": list(self.timingOverflowChk_),
            "max_weight": self.net_weight_max_,
            "timing_driven_iter": self.timing_driven_iter_,
            "timing_driven_nets": len(self.timing_driven_nets_),
            "last_overflow": self.last_overflow_,
            "run_journal_restore": self.run_journal_restore_,
            "snapshot_weights": len(self.prev_timing_weights_),
            "restore_count": self.restore_count_,
            "last_restored_weights": self.last_restored_weights_,
            "last_resizer_result": self.last_resizer_result_,
            "last_resizer_hook": dict(self.last_resizer_hook_),
            "last_filler_reset": dict(self.last_filler_reset_),
            "last_execute_result": self.last_execute_result_,
            "last_update_count": self.last_update_count_,
            "last_update_changed_count": self.last_update_changed_count_,
            "last_update_max_weight": self.last_update_max_weight_,
        }

    def reportTimingNets(self, sample_limit: int = 0) -> Dict[str, Any]:
        """导出 timing-driven net 样本和权重快照状态。"""

        all_weights = self._allTimingWeights()
        report: Dict[str, Any] = {
            "timing_driven_nets": len(self.timing_driven_nets_),
            "unique_timing_driven_nets": len(self._uniqueTimingDrivenNets()),
            "snapshot_weights": len(self.prev_timing_weights_),
            "snapshot_weights_by_id": len(self.prev_timing_weights_by_id_),
            "weighted_nets": sum(1 for _, weight in all_weights if weight != 1.0),
            "max_observed_weight": max([weight for _, weight in all_weights] or [1.0]),
            "last_weight_updates": self.last_weight_updates_[:sample_limit] if sample_limit > 0 else [],
        }
        if sample_limit > 0:
            report["sample_nets"] = [gnet.report() for gnet in self.timing_driven_nets_[:sample_limit]]
        return report

    def exportTimingWeightSnapshot(self) -> Dict[str, Any]:
        """导出当前和上一次 snapshot 的纯权重状态。"""

        current = [
            {"index": index, "name": self._gnetName(gnet), "weight": gnet.getTimingWeight()}
            for index, gnet in self._indexedGNets()
        ]
        return {
            "current_weights": current,
            "previous_weights": dict(self.prev_timing_weights_),
            "timing_driven_indexes": self._timingDrivenIndexes(),
            "report": self.reportTimingDriven(),
        }

    def importTimingWeightSnapshot(self, snapshot: Dict[str, Any], restore_current: bool = True) -> None:
        """导入 `exportTimingWeightSnapshot` 的权重快照。

        只恢复 Python GNet timing weight 和登记列表，不访问真实 STA/resizer。
        """

        if self.nbc_ is None:
            raise ValueError("缺少 NesterovBaseCommon，无法导入 timing weight snapshot")
        self.prev_timing_weights_ = {
            int(index): float(weight)
            for index, weight in dict(snapshot.get("previous_weights", {})).items()
        }
        self.prev_timing_weights_by_id_ = {}
        for index, gnet in self._indexedGNets():
            if index in self.prev_timing_weights_:
                self.prev_timing_weights_by_id_[id(gnet)] = self.prev_timing_weights_[index]
        if restore_current:
            all_nets = self.nbc_.getGNets()
            for item in snapshot.get("current_weights", []):
                index = int(item.get("index", -1))
                if 0 <= index < len(all_nets):
                    all_nets[index].setTimingWeight(self._clampWeight(float(item.get("weight", 1.0))))
        if "timing_driven_indexes" in snapshot:
            self.importTimingDrivenNetsByIndex(snapshot["timing_driven_indexes"])

    def validateTimingState(self) -> List[str]:
        errors: List[str] = []
        if self.net_weight_max_ < 1.0:
            errors.append("net_weight_max_ 必须大于等于 1.0")
        if any(item < 0 for item in self.timingNetWeightOverflow_):
            errors.append("timingNetWeightOverflow_ 不能包含负 checkpoint")
        if self.nbc_ is not None:
            all_ids = {id(gnet) for gnet in self.nbc_.getGNets()}
            for gnet in self.timing_driven_nets_:
                if id(gnet) not in all_ids:
                    errors.append(f"timing-driven net {self._gnetName(gnet)} 不在 NesterovBaseCommon 中")
            for index, weight in self.prev_timing_weights_.items():
                if index < 0 or index >= len(self.nbc_.getGNets()):
                    errors.append(f"snapshot index 越界: {index}")
                if weight < 1.0 or weight > self.net_weight_max_:
                    errors.append(f"snapshot weight 越界: {index}={weight}")
            for gnet in self.nbc_.getGNets():
                weight = gnet.getTimingWeight()
                if weight < 1.0 or weight > self.net_weight_max_:
                    errors.append(f"GNet {self._gnetName(gnet)} timing weight 越界: {weight}")
        return errors

    def _uniqueTimingDrivenNets(self) -> List[GNet]:
        seen = set()
        unique: List[GNet] = []
        for gnet in self.timing_driven_nets_:
            marker = id(gnet)
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(gnet)
        self.timing_driven_nets_ = unique
        return unique

    def _indexedGNets(self) -> List[Tuple[int, GNet]]:
        if self.nbc_ is None:
            return []
        return list(enumerate(self.nbc_.getGNets()))

    def _allTimingWeights(self) -> List[Tuple[GNet, float]]:
        return [(gnet, float(gnet.getTimingWeight())) for _, gnet in self._indexedGNets()]

    def _timingDrivenIndexes(self) -> List[int]:
        if self.nbc_ is None:
            return []
        index_by_id = {id(gnet): index for index, gnet in self._indexedGNets()}
        return [index_by_id[id(gnet)] for gnet in self._uniqueTimingDrivenNets() if id(gnet) in index_by_id]

    def _clampWeight(self, weight: float) -> float:
        return min(float(self.net_weight_max_), max(1.0, float(weight)))

    def _gnetName(self, gnet: GNet) -> str:
        getter = getattr(gnet, "getName", None)
        if callable(getter):
            return str(getter())
        return str(gnet)

    def _hookSources(self) -> List[Tuple[str, Any]]:
        sources: List[Tuple[str, Any]] = []
        seen = set()
        for name, obj in (("resizer", self.rs_), ("router", self.grt_), ("nesterov_common", self.nbc_)):
            if obj is None:
                continue
            if obj is self:
                continue
            marker = id(obj)
            if marker in seen:
                continue
            seen.add(marker)
            sources.append((name, obj))
            for nested_name, nested_obj in self._nestedHookSources(name, obj):
                if nested_obj is self:
                    continue
                nested_marker = id(nested_obj)
                if nested_marker in seen:
                    continue
                seen.add(nested_marker)
                sources.append((nested_name, nested_obj))
        return sources

    def _nestedHookSources(self, prefix: str, obj: Any) -> List[Tuple[str, Any]]:
        sources: List[Tuple[str, Any]] = []
        for attr in ("nbVec_", "pbVec_", "tb_", "np_", "ip_"):
            nested = getattr(obj, attr, None)
            if isinstance(nested, (list, tuple)):
                for index, item in enumerate(nested):
                    if item is not None and item is not self:
                        sources.append((f"{prefix}.{attr}[{index}]", item))
            elif nested is not None and nested is not self and attr in {"tb_", "np_", "ip_"}:
                sources.append((f"{prefix}.{attr}", nested))
        return sources

    def _invokeAdapterHook(
        self,
        hook_names: Sequence[str],
        args: Tuple[Any, ...],
        sources: Sequence[Tuple[str, Any]],
        label: str,
    ) -> Dict[str, Any]:
        attempts: List[Dict[str, Any]] = []
        for source_name, source in sources:
            for hook_name in hook_names:
                hook = getattr(source, hook_name, None)
                if not callable(hook):
                    attempts.append(
                        {
                            "source": source_name,
                            "hook": hook_name,
                            "status": "missing",
                        }
                    )
                    continue
                call_args: Optional[Tuple[Any, ...]] = None
                signature_notes: List[str] = []
                for candidate_args in self._hookArgVariants(args):
                    compatible, signature_note = self._hookAcceptsArgs(hook, candidate_args)
                    if compatible:
                        call_args = candidate_args
                        break
                    signature_notes.append(f"{len(candidate_args)} args: {signature_note}")
                if call_args is None:
                    attempts.append(
                        {
                            "source": source_name,
                            "hook": hook_name,
                            "status": "incompatible",
                            "detail": "; ".join(signature_notes),
                        }
                    )
                    continue
                try:
                    result = hook(*call_args)
                except Exception as exc:
                    report = {
                        "label": label,
                        "status": "error",
                        "source": source_name,
                        "hook": hook_name,
                        "args": len(call_args),
                        "detail": {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                        "attempts": attempts + [
                            {
                                "source": source_name,
                                "hook": hook_name,
                                "status": "error",
                                "args": len(call_args),
                                "detail": {
                                    "type": type(exc).__name__,
                                    "message": str(exc),
                                },
                            }
                        ],
                    }
                    return report
                return {
                    "label": label,
                    "status": "ok",
                    "source": source_name,
                    "hook": hook_name,
                    "args": len(call_args),
                    "result": self._summarizeHookResult(result),
                    "result_type": type(result).__name__,
                    "attempts": attempts
                    + [
                        {
                            "source": source_name,
                            "hook": hook_name,
                            "status": "called",
                            "args": len(call_args),
                            "result_type": type(result).__name__,
                        }
                    ],
                }
        return {
            "label": label,
            "status": "missing_hook",
            "detail": "no compatible adapter method was found",
            "attempts": attempts,
        }

    def _hookArgVariants(self, args: Tuple[Any, ...]) -> List[Tuple[Any, ...]]:
        if not args:
            return [()]
        return [args, ()]

    def _hookAcceptsArgs(self, hook: Any, args: Tuple[Any, ...]) -> Tuple[bool, str]:
        try:
            sig = inspect.signature(hook)
        except (TypeError, ValueError):
            return True, "signature_unavailable"
        positional = 0
        required = 0
        has_varargs = False
        for param in sig.parameters.values():
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                positional += 1
                if param.default is inspect.Signature.empty:
                    required += 1
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                has_varargs = True
        if len(args) < required:
            return False, f"requires_at_least_{required}_args"
        if not has_varargs and len(args) > positional:
            return False, f"accepts_at_most_{positional}_args"
        return True, "ok"

    def _summarizeHookResult(self, result: Any) -> Any:
        if isinstance(result, (type(None), bool, int, float, str)):
            return result
        if isinstance(result, dict):
            return {str(key): self._summarizeHookResult(value) for key, value in result.items()}
        if isinstance(result, (list, tuple)):
            return [self._summarizeHookResult(item) for item in result]
        return repr(result)


