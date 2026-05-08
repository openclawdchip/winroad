"""Top-level Replace entry point for WinRoad gpl."""

from __future__ import annotations

from time import monotonic
from typing import Any, Callable, Dict, List, Optional, TypeVar

from ..odb import DbDatabase, DbInst, PlacementStatus, SigType
from .common import Cluster, Clusters, _get_block
from .graphics import AbstractGraphics, GraphicsNone
from .initial_place import InitialPlace, InitialPlaceVars
from .nesterov import NesterovBase, NesterovBaseCommon, NesterovBaseVars, NesterovPlace, NesterovPlaceVars
from .options import MBFFOptions, PlaceOptions
from .placer_base import PlacerBase, PlacerBaseCommon
from .route_base import RouteBase, RouteBaseVars
from .timing_base import TimingBase

def isValidSigType(db_type: SigType) -> bool:
    """对应 `isValidSigType`：GPL 只处理 SIGNAL/CLOCK。"""

    return db_type in {SigType.SIGNAL, SigType.CLOCK}


T = TypeVar("T")


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
        self.flow_reports_: List[Dict[str, Any]] = []
        self.last_error_: Optional[Dict[str, Any]] = None
        self.mbff_options_: Optional[MBFFOptions] = None
        self.mbff_report_: Dict[str, Any] = {}
        self.default_options_ = PlaceOptions()

    def init(
        self,
        odb: Optional[DbDatabase],
        sta: Any = None,
        resizer: Any = None,
        router: Any = None,
        logger: Any = None,
    ) -> None:
        self.db_ = odb
        self.sta_ = sta
        self.rs_ = resizer
        self.fr_ = router
        self.log_ = logger

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
        self.total_placeable_insts_ = 0
        self.flow_reports_.clear()
        self.last_error_ = None
        self.mbff_options_ = None
        self.mbff_report_ = {}
        self.default_options_ = PlaceOptions()

    def _target_options(self, options: Optional[PlaceOptions]) -> PlaceOptions:
        return options if options is not None else self.default_options_

    def _split_option_arg(self, first: Any, rest: tuple[Any, ...], expected: int) -> tuple[PlaceOptions, tuple[Any, ...]]:
        if isinstance(first, PlaceOptions):
            args = rest
            options = first
        else:
            args = (first,) + rest
            options = self.default_options_
        if len(args) != expected:
            raise TypeError(f"expected {expected} value argument(s), got {len(args)}")
        return options, args

    def addPlacementCluster(self, cluster: Cluster) -> None:
        self.clusters_.append(list(cluster))

    def clearPlacementClusters(self) -> None:
        self.clusters_.clear()

    def getPlacementClusters(self) -> Clusters:
        """返回 cluster 拷贝，避免调用方直接改内部容器。"""

        return [list(cluster) for cluster in self.clusters_]

    def getTotalPlaceableInsts(self) -> int:
        return self.total_placeable_insts_

    def getInitialPlace(self) -> Optional[InitialPlace]:
        return self.ip_

    def getNesterovPlace(self) -> Optional[NesterovPlace]:
        return self.np_

    def getRouteBase(self) -> Optional[RouteBase]:
        return self.rb_

    def getTimingBase(self) -> Optional[TimingBase]:
        return self.tb_

    def checkHasCoreRows(self) -> None:
        block = _get_block(self.db_)
        if block is None:
            raise ValueError("No block defined in design")
        if getattr(block, "die_area", None) is None and getattr(block, "bbox", None) is None:
            raise ValueError("No rows/core area defined in design")

    def _validate_threads(self, threads: int) -> None:
        if not isinstance(threads, int) or threads <= 0:
            raise ValueError("threads must be a positive integer")

    def _options_report(self, options: Optional[PlaceOptions]) -> Dict[str, Any]:
        return options.report() if options is not None else {}

    def _base_counts(self) -> Dict[str, Any]:
        return {
            "placeable_insts": self.total_placeable_insts_,
            "clusters": len(self.clusters_),
            "placer_bases": len(self.pbVec_),
            "nesterov_bases": len(self.nbVec_),
            "has_pbc": self.pbc_ is not None,
            "has_nbc": self.nbc_ is not None,
            "has_initial_place": self.ip_ is not None,
            "has_nesterov_place": self.np_ is not None,
            "has_route_base": self.rb_ is not None,
            "has_timing_base": self.tb_ is not None,
        }

    def _run_stage(self, name: str, action: Callable[[], T], options: Optional[PlaceOptions] = None, extra: Optional[Dict[str, Any]] = None) -> T:
        started = monotonic()
        report: Dict[str, Any] = {
            "stage": name,
            "status": "running",
            "options": self._options_report(options),
            "before": self._base_counts(),
        }
        if extra:
            report.update(extra)
        self.flow_reports_.append(report)
        try:
            result = action()
        except Exception as exc:
            report["status"] = "error"
            report["error"] = {"type": type(exc).__name__, "message": str(exc)}
            report["after"] = self._base_counts()
            report["elapsed_sec"] = monotonic() - started
            self.last_error_ = dict(report["error"])
            raise
        report["status"] = "ok"
        report["after"] = self._base_counts()
        report["elapsed_sec"] = monotonic() - started
        return result

    def doIncrementalPlace(self, threads: int, options: Optional[PlaceOptions] = None) -> None:
        options = options or self.default_options_
        options.validate(self.log_)
        self._validate_threads(threads)
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
        options = options or self.default_options_
        options.validate(self.log_)
        self._validate_threads(threads)
        def action() -> None:
            self.doInitialPlace(threads, options)
            self.doNesterovPlace(threads, options)

        self._run_stage("doPlace", action, options, {"threads": threads})

    def doInitialPlace(self, threads: int, options: Optional[PlaceOptions] = None) -> None:
        options = options or self.default_options_
        options.validate(self.log_)
        self._validate_threads(threads)
        self.checkHasCoreRows()
        def action() -> None:
            if self.pbc_ is None:
                self.pbc_ = PlacerBaseCommon(self.db_, options, self.log_)  # type: ignore[arg-type]
                self.pbVec_.append(PlacerBase(self.db_, self.pbc_, self.log_, True))
                if self.pbVec_ and not self.pbVec_[0].placeInsts():
                    self.pbVec_.pop(0)
                self.total_placeable_insts_ = sum(len(pb.placeInsts()) for pb in self.pbVec_)
            ipVars = InitialPlaceVars.from_options(options, self.gui_debug_initial_)
            self.ip_ = InitialPlace(ipVars, self.pbc_, self.pbVec_, self.graphics_.MakeNew(self.log_), self.log_)  # type: ignore[arg-type]
            self.ip_.doBicgstabPlace(threads)

        self._run_stage("doInitialPlace", action, options, {"threads": threads})

    def doNesterovPlace(self, threads: int, options: Optional[PlaceOptions] = None, start_iter: int = 0) -> int:
        options = options or self.default_options_
        options.validate(self.log_)
        self._validate_threads(threads)
        if start_iter < 0:
            raise ValueError("start_iter must be non-negative")
        self.checkHasCoreRows()
        def action() -> int:
            if not self.initNesterovPlace(options, threads, True):
                return 0
            if options.timingDrivenMode and self.rs_ is not None and hasattr(self.rs_, "resizeSlackPreamble"):
                self.rs_.resizeSlackPreamble()
            assert self.np_ is not None
            return self.np_.doNesterovPlace(start_iter)

        return self._run_stage("doNesterovPlace", action, options, {"threads": threads, "start_iter": start_iter})

    def runMBFF(self, max_sz: int, alpha: float, beta: float, threads: int, num_paths: int) -> Dict[str, Any]:
        options = MBFFOptions(max_sz=max_sz, alpha=alpha, beta=beta, threads=threads, num_paths=num_paths)
        options.validate(self.log_)
        self._validate_threads(threads)
        self.mbff_options_ = options
        block = _get_block(self.db_)
        insts = list(getattr(block, "insts", {}).values()) if isinstance(getattr(block, "insts", None), dict) else list(getattr(block, "insts", []) or [])
        movable = [
            inst
            for inst in insts
            if getattr(inst, "status", PlacementStatus.UNPLACED) not in {PlacementStatus.FIXED, PlacementStatus.COVER, PlacementStatus.LOCKED}
        ]
        self.mbff_report_ = {
            "status": "not_run",
            "implemented": False,
            "reason": "OpenROAD MBFF clustering requires Liberty/STA/Resizer/OpenDB mutation; this Python pass only records the translated boundary.",
            "config": options.report(),
            "design": {
                "has_block": block is not None,
                "inst_count": len(insts),
                "movable_inst_count": len(movable),
                "placeable_insts": self.total_placeable_insts_,
            },
            "translated_cpp_boundary": {
                "class": "gpl::MBFF",
                "constructor_multistart": 20,
                "entry": "MBFF::Run(max_sz, alpha, beta)",
                "major_helpers": [
                    "ReadFFs",
                    "ReadPaths",
                    "ReadLibs",
                    "SetTrayNames",
                    "SeparateFlops",
                    "SetVars",
                    "SetRatios",
                    "RunClustering",
                    "ModifyPinConnections",
                ],
            },
            "clusters_before": len(self.clusters_),
            "clusters_after": len(self.clusters_),
            "clusters_created": 0,
        }
        self.flow_reports_.append({"stage": "runMBFF", "status": "boundary", "mbff": dict(self.mbff_report_), "after": self._base_counts()})
        return dict(self.mbff_report_)

    def resetRoutabilityResources(self) -> None:
        self.rb_ = None
        if self.np_ is not None:
            self.np_.rb_ = None

    def resetTimingResources(self) -> None:
        self.tb_ = None
        if self.np_ is not None:
            self.np_.tb_ = None

    def reportInitialPlace(self) -> Dict[str, Any]:
        if self.ip_ is None:
            return {}
        return self.ip_.reportStatus()

    def reportNesterovPlace(self) -> Dict[str, Any]:
        if self.np_ is None:
            return {}
        return self.np_.reportStatus()

    def reportRoutability(self) -> Dict[str, Any]:
        if self.rb_ is None:
            return {}
        return self.rb_.reportCongestion()

    def reportTimingDriven(self) -> Dict[str, Any]:
        if self.tb_ is None:
            return {}
        return self.tb_.reportTimingDriven()

    def reportDebug(self) -> Dict[str, Any]:
        """导出 GUI/debug 配置状态，和 C++ debug setter 字段一一对应。"""

        return {
            "enabled": self.gui_debug_,
            "pause_iterations": self.gui_debug_pause_iterations_,
            "update_iterations": self.gui_debug_update_iterations_,
            "draw_bins": self.gui_debug_draw_bins_,
            "initial": self.gui_debug_initial_,
            "inst": getattr(self.gui_debug_inst_, "name", None),
            "start_iter": self.gui_debug_start_iter_,
            "rudy_start": self.gui_debug_rudy_start_,
            "rudy_stride": self.gui_debug_rudy_stride_,
            "generate_images": self.gui_debug_generate_images_,
            "images_path": self.gui_debug_images_path_,
        }

    def reportClusters(self) -> Dict[str, Any]:
        """导出 placement cluster 关系摘要。"""

        return {
            "clusters": len(self.clusters_),
            "cluster_sizes": [len(cluster) for cluster in self.clusters_],
        }

    def reportFlow(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self.flow_reports_]

    def reportMBFF(self) -> Dict[str, Any]:
        return dict(self.mbff_report_)

    def reportStatus(self) -> Dict[str, Any]:
        return {
            "placeable_insts": self.total_placeable_insts_,
            "clusters": len(self.clusters_),
            "has_initial_place": self.ip_ is not None,
            "has_nesterov_place": self.np_ is not None,
            "has_route_base": self.rb_ is not None,
            "has_timing_base": self.tb_ is not None,
            "initial_place": self.reportInitialPlace(),
            "nesterov_place": self.reportNesterovPlace(),
            "routability": self.reportRoutability(),
            "timing": self.reportTimingDriven(),
            "debug": self.reportDebug(),
            "cluster_report": self.reportClusters(),
            "flow": self.reportFlow(),
            "last_error": self.last_error_,
            "mbff": self.reportMBFF(),
            "base_common": self.pbc_.reportConnectivity() if self.pbc_ is not None else {},
            "placer_bases": [pb.reportStatus() for pb in self.pbVec_],
            "nesterov_base_common": self.nbc_.reportStatus() if self.nbc_ is not None else {},
        }

    def setInitialPlaceMaxIter(self, options: Optional[PlaceOptions] | int, max_iter: Optional[int] = None) -> None:
        options, args = self._split_option_arg(options, () if max_iter is None else (max_iter,), 1)
        max_iter = args[0]
        options.initialPlaceMaxIter = max_iter
        options.validate(self.log_)

    def setInitialPlaceMinDiffLength(self, options: Optional[PlaceOptions] | int, length: Optional[int] = None) -> None:
        options, args = self._split_option_arg(options, () if length is None else (length,), 1)
        length = args[0]
        options.initialPlaceMinDiffLength = length
        options.validate(self.log_)

    def setInitialPlaceMaxSolverIter(self, options: Optional[PlaceOptions] | int, max_iter: Optional[int] = None) -> None:
        options, args = self._split_option_arg(options, () if max_iter is None else (max_iter,), 1)
        max_iter = args[0]
        options.initialPlaceMaxSolverIter = max_iter
        options.validate(self.log_)

    def setInitialPlaceMaxFanout(self, options: Optional[PlaceOptions] | int, fanout: Optional[int] = None) -> None:
        options, args = self._split_option_arg(options, () if fanout is None else (fanout,), 1)
        fanout = args[0]
        options.initialPlaceMaxFanout = fanout
        options.validate(self.log_)

    def setInitialPlaceNetWeightScale(self, options: Optional[PlaceOptions] | float, scale: Optional[float] = None) -> None:
        options, args = self._split_option_arg(options, () if scale is None else (scale,), 1)
        scale = args[0]
        options.initialPlaceNetWeightScale = scale
        options.validate(self.log_)

    def setNesterovPlaceMaxIter(self, options: Optional[PlaceOptions] | int, max_iter: Optional[int] = None) -> None:
        options, args = self._split_option_arg(options, () if max_iter is None else (max_iter,), 1)
        max_iter = args[0]
        options.nesterovPlaceMaxIter = max_iter
        options.validate(self.log_)
        if self.np_ is not None:
            self.np_.setMaxIters(max_iter)

    def setTargetDensity(self, options: Optional[PlaceOptions] | float, density: Optional[float] = None) -> None:
        options, args = self._split_option_arg(options, () if density is None else (density,), 1)
        density = args[0]
        options.density = density
        options.validate(self.log_)

    def setUniformTargetDensityMode(self, options: Optional[PlaceOptions] | bool, mode: Optional[bool] = None) -> None:
        options, args = self._split_option_arg(options, () if mode is None else (mode,), 1)
        mode = args[0]
        options.uniformTargetDensityMode = bool(mode)
        options.validate(self.log_)

    def setTargetOverflow(self, options: Optional[PlaceOptions] | float, overflow: Optional[float] = None) -> None:
        options, args = self._split_option_arg(options, () if overflow is None else (overflow,), 1)
        overflow = args[0]
        options.overflow = overflow
        options.validate(self.log_)
        if self.np_ is not None:
            self.np_.setTargetOverflow(overflow)

    def setInitDensityPenalityFactor(self, options: Optional[PlaceOptions], penalty_factor: float) -> None:
        options = self._target_options(options)
        options.initDensityPenaltyFactor = penalty_factor
        options.validate(self.log_)

    def setInitDensityPenaltyFactor(self, options: Optional[PlaceOptions], penalty_factor: float) -> None:
        self.setInitDensityPenalityFactor(options, penalty_factor)

    def setInitWireLengthCoef(self, options: Optional[PlaceOptions], coef: float) -> None:
        options = self._target_options(options)
        options.initWireLengthCoef = coef
        options.validate(self.log_)

    def setMinPhiCoef(self, options: Optional[PlaceOptions], min_phi_coef: float) -> None:
        options = self._target_options(options)
        options.minPhiCoef = min_phi_coef
        options.validate(self.log_)

    def setMaxPhiCoef(self, options: Optional[PlaceOptions], max_phi_coef: float) -> None:
        options = self._target_options(options)
        options.maxPhiCoef = max_phi_coef
        options.validate(self.log_)

    def setReferenceHpwl(self, options: Optional[PlaceOptions], ref_hpwl: float) -> None:
        options = self._target_options(options)
        options.referenceHpwl = ref_hpwl
        options.validate(self.log_)

    def setTimingDrivenMode(self, options: Optional[PlaceOptions], enabled: bool) -> None:
        options = self._target_options(options)
        options.timingDrivenMode = enabled
        options.validate(self.log_)

    def setSkipIoMode(self, options: Optional[PlaceOptions], mode: bool) -> None:
        options = self._target_options(options)
        options.skipIoMode = bool(mode)
        options.validate(self.log_)

    def setDisableRevertIfDiverge(self, options: Optional[PlaceOptions], mode: bool) -> None:
        options = self._target_options(options)
        options.disableRevertIfDiverge = bool(mode)
        options.validate(self.log_)

    def setRoutabilityDrivenMode(self, options: Optional[PlaceOptions], enabled: bool) -> None:
        options = self._target_options(options)
        options.routabilityDrivenMode = enabled
        options.validate(self.log_)

    def setRoutabilityUseGrt(self, options: Optional[PlaceOptions], mode: bool) -> None:
        options = self._target_options(options)
        options.routabilityUseRudy = not bool(mode)
        options.validate(self.log_)

    def setRoutabilityCheckOverflow(self, options: Optional[PlaceOptions], overflow: float) -> None:
        options = self._target_options(options)
        options.routabilityCheckOverflow = overflow
        options.validate(self.log_)

    def setRoutabilityMaxDensity(self, options: Optional[PlaceOptions], density: float) -> None:
        options = self._target_options(options)
        options.routabilityMaxDensity = density
        options.validate(self.log_)

    def setRoutabilityMaxInflationIter(self, options: Optional[PlaceOptions], max_iter: int) -> None:
        options = self._target_options(options)
        options.routabilityMaxInflationIter = max_iter
        options.validate(self.log_)

    def setRoutabilityTargetRcMetric(self, options: Optional[PlaceOptions], rc: float) -> None:
        options = self._target_options(options)
        options.routabilityTargetRcMetric = rc
        options.validate(self.log_)

    def setRoutabilityInflationRatioCoef(self, options: Optional[PlaceOptions], coef: float) -> None:
        options = self._target_options(options)
        options.routabilityInflationRatioCoef = coef
        options.validate(self.log_)

    def setRoutabilityMaxInflationRatio(self, options: Optional[PlaceOptions], ratio: float) -> None:
        options = self._target_options(options)
        options.routabilityMaxInflationRatio = ratio
        options.validate(self.log_)

    def setRoutabilityRcCoefficients(self, options: Optional[PlaceOptions], k1: float, k2: float, k3: float, k4: float) -> None:
        options = self._target_options(options)
        options.routabilityRcK1 = k1
        options.routabilityRcK2 = k2
        options.routabilityRcK3 = k3
        options.routabilityRcK4 = k4
        options.validate(self.log_)

    def setEnableRoutingCongestion(self, options: Optional[PlaceOptions], mode: bool) -> None:
        options = self._target_options(options)
        options.enable_routing_congestion = bool(mode)
        options.validate(self.log_)

    def setBinGridCnt(self, options: Optional[PlaceOptions], bin_cnt_x: int, bin_cnt_y: int) -> None:
        options = self._target_options(options)
        options.binGridCntX = bin_cnt_x
        options.binGridCntY = bin_cnt_y
        options.validate(self.log_)

    def setPad(self, options: Optional[PlaceOptions], pad_left: int, pad_right: int) -> None:
        options = self._target_options(options)
        options.padLeft = pad_left
        options.padRight = pad_right
        options.validate(self.log_)

    def setPadLeft(self, options: Optional[PlaceOptions], padding: int) -> None:
        options = self._target_options(options)
        options.padLeft = padding
        options.validate(self.log_)

    def setPadRight(self, options: Optional[PlaceOptions], padding: int) -> None:
        options = self._target_options(options)
        options.padRight = padding
        options.validate(self.log_)

    def setTimingNetWeightOverflows(self, options: Optional[PlaceOptions], overflows: List[int]) -> None:
        options = self._target_options(options)
        options.timingNetWeightOverflows = list(overflows)
        options.validate(self.log_)
        if self.tb_ is not None:
            self.tb_.setTimingNetWeightOverflows(options.timingNetWeightOverflows)

    def addTimingNetWeightOverflow(self, options: Optional[PlaceOptions], overflow: int) -> None:
        options = self._target_options(options)
        options.timingNetWeightOverflows.append(overflow)
        options.validate(self.log_)
        if self.tb_ is not None:
            self.tb_.setTimingNetWeightOverflows(options.timingNetWeightOverflows)

    def setTimingNetWeightMax(self, options: Optional[PlaceOptions], max_weight: float) -> None:
        options = self._target_options(options)
        options.timingNetWeightMax = max_weight
        options.validate(self.log_)
        if self.tb_ is not None:
            self.tb_.setTimingNetWeightMax(max_weight)

    def setKeepResizeBelowOverflow(self, options: Optional[PlaceOptions], overflow: float) -> None:
        options = self._target_options(options)
        options.keepResizeBelowOverflow = overflow
        options.validate(self.log_)

    def initNesterovPlace(self, options: PlaceOptions, threads: int, check_density: bool) -> bool:
        options.validate(self.log_)
        self._validate_threads(threads)
        def action() -> bool:
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
                self.rb_.initRouteBase()
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

        return self._run_stage("initNesterovPlace", action, options, {"threads": threads, "check_density": check_density})

    def getUniformTargetDensity(self, options: Optional[PlaceOptions] = None, threads: int = 1) -> float:
        options = options or self.default_options_
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


