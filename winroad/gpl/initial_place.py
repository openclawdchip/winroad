"""Initial placement boundary for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .options import PlaceOptions
from .placer_base import PlacerBase, PlacerBaseCommon

@dataclass
class InitialPlaceVars:
    """对应 `gpl::InitialPlaceVars`。"""

    maxIter: int
    minDiffLength: int
    maxSolverIter: int
    maxFanout: int
    netWeightScale: float
    debug: bool
    forceCenter: bool

    @classmethod
    def from_options(cls, options: PlaceOptions, debug: bool) -> "InitialPlaceVars":
        return cls(
            maxIter=options.initialPlaceMaxIter,
            minDiffLength=options.initialPlaceMinDiffLength,
            maxSolverIter=options.initialPlaceMaxSolverIter,
            maxFanout=options.initialPlaceMaxFanout,
            netWeightScale=options.initialPlaceNetWeightScale,
            debug=debug,
            forceCenter=options.forceCenterInitialPlace,
        )


class InitialPlace:
    """对应 `gpl::InitialPlace`。

    稀疏矩阵创建、BiCGSTAB 求解和坐标回写是后续翻译重点。
    """

    def __init__(
        self,
        ipVars: InitialPlaceVars,
        pbc: PlacerBaseCommon,
        pbVec: List[PlacerBase],
        graphics: Optional["AbstractGraphics"],
        logger: Any,
    ):
        self.ipVars_ = ipVars
        self.pbc_ = pbc
        self.pbVec_ = pbVec
        self.graphics_ = graphics
        self.log_ = logger
        self.gif_key_ = 0
        self.instLocVecX_: List[float] = []
        self.fixedInstForceVecX_: List[float] = []
        self.instLocVecY_: List[float] = []
        self.fixedInstForceVecY_: List[float] = []
        self.solver_failed_ = False
        self.last_threads_ = 0
        self.is_initialized_ = False

    def doBicgstabPlace(self, threads: int) -> None:
        self.last_threads_ = threads
        if self.ipVars_.maxIter == 0:
            return
        self.setPlaceInstExtId()
        self.placeInstsInitialPositions()
        self.updatePinInfo()
        self.createSparseMatrix()
        raise NotImplementedError("OpenROAD InitialPlace BiCGSTAB solver has not been translated yet")

    def placeInstsInitialPositions(self) -> None:
        die = self.pbc_.getDie()
        center_x, center_y = die.coreCx(), die.coreCy()
        self.instLocVecX_ = []
        self.instLocVecY_ = []
        for inst in self.pbc_.placeInsts():
            if self.ipVars_.forceCenter:
                inst.setCenterLocation(center_x, center_y)
            self.instLocVecX_.append(float(inst.cx()))
            self.instLocVecY_.append(float(inst.cy()))
        self.fixedInstForceVecX_ = [0.0 for _ in self.instLocVecX_]
        self.fixedInstForceVecY_ = [0.0 for _ in self.instLocVecY_]
        self.is_initialized_ = True
        if self.ipVars_.debug and self.graphics_ is not None:
            self.graphics_.debugForInitialPlace(self.pbc_, self.pbVec_)

    def setPlaceInstExtId(self) -> None:
        for index, inst in enumerate(self.pbc_.placeInsts()):
            inst.setExtId(index)

    def updatePinInfo(self) -> None:
        for pin in self.pbc_.getPins():
            pin.updateCoordi()

    def createSparseMatrix(self) -> None:
        raise NotImplementedError("OpenROAD InitialPlace sparse matrix creation has not been translated yet")

    def updateCoordi(self) -> None:
        if len(self.instLocVecX_) != len(self.instLocVecY_):
            raise ValueError("InitialPlace coordinate vectors have different lengths")
        for inst, x, y in zip(self.pbc_.placeInsts(), self.instLocVecX_, self.instLocVecY_):
            inst.setCenterLocation(int(round(x)), int(round(y)))
            inst.dbSetLocation()
        self.updatePinInfo()

    def reportStatus(self) -> Dict[str, Any]:
        return {
            "max_iter": self.ipVars_.maxIter,
            "max_solver_iter": self.ipVars_.maxSolverIter,
            "place_insts": len(self.pbc_.placeInsts()),
            "initialized": self.is_initialized_,
            "solver_failed": self.solver_failed_,
            "last_threads": self.last_threads_,
        }

    def getInstLocVecX(self) -> List[float]:
        return self.instLocVecX_

    def getInstLocVecY(self) -> List[float]:
        return self.instLocVecY_


