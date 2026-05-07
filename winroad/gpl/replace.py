"""Top-level Replace entry point for WinRoad gpl."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..odb import DbDatabase, DbInst, PlacementStatus, SigType
from .common import Cluster, Clusters, _get_block
from .graphics import AbstractGraphics, GraphicsNone
from .initial_place import InitialPlace, InitialPlaceVars
from .nesterov import NesterovBase, NesterovBaseCommon, NesterovBaseVars, NesterovPlace, NesterovPlaceVars
from .options import PlaceOptions
from .placer_base import PlacerBase, PlacerBaseCommon
from .route_base import RouteBase, RouteBaseVars
from .timing_base import TimingBase

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
        self.total_placeable_insts_ = 0

    def addPlacementCluster(self, cluster: Cluster) -> None:
        self.clusters_.append(list(cluster))

    def clearPlacementClusters(self) -> None:
        self.clusters_.clear()

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

    def doIncrementalPlace(self, threads: int, options: Optional[PlaceOptions] = None) -> None:
        options = options or PlaceOptions()
        options.validate(self.log_)
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
        options.validate(self.log_)
        self.doInitialPlace(threads, options)
        self.doNesterovPlace(threads, options)

    def doInitialPlace(self, threads: int, options: Optional[PlaceOptions] = None) -> None:
        options = options or PlaceOptions()
        options.validate(self.log_)
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
        options.validate(self.log_)
        self.checkHasCoreRows()
        if not self.initNesterovPlace(options, threads, True):
            return 0
        if options.timingDrivenMode and self.rs_ is not None and hasattr(self.rs_, "resizeSlackPreamble"):
            self.rs_.resizeSlackPreamble()
        assert self.np_ is not None
        return self.np_.doNesterovPlace(start_iter)

    def runMBFF(self, max_sz: int, alpha: float, beta: float, threads: int, num_paths: int) -> None:
        raise NotImplementedError("OpenROAD MBFF clustering has not been translated yet")

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
            "base_common": self.pbc_.printInfo() if self.pbc_ is not None else {},
            "nesterov_base_common": self.nbc_.reportStatus() if self.nbc_ is not None else {},
        }

    def setInitialPlaceMaxIter(self, options: PlaceOptions, max_iter: int) -> None:
        options.initialPlaceMaxIter = max_iter
        options.validate(self.log_)

    def setNesterovPlaceMaxIter(self, options: PlaceOptions, max_iter: int) -> None:
        options.nesterovPlaceMaxIter = max_iter
        options.validate(self.log_)

    def setTargetDensity(self, options: PlaceOptions, density: float) -> None:
        options.density = density
        options.validate(self.log_)

    def setTargetOverflow(self, options: PlaceOptions, overflow: float) -> None:
        options.overflow = overflow
        options.validate(self.log_)

    def initNesterovPlace(self, options: PlaceOptions, threads: int, check_density: bool) -> bool:
        options.validate(self.log_)
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


