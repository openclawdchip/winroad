"""Initial placement boundary for WinRoad gpl."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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
        self.sparseMatrix_: List[List[Tuple[int, float]]] = []
        self.rhsVecX_: List[float] = []
        self.rhsVecY_: List[float] = []
        self.solutionVecX_: List[float] = []
        self.solutionVecY_: List[float] = []
        self.matrix_nonzero_count_ = 0
        self.matrix_reuse_count_ = 0
        self.last_matrix_place_inst_count_ = 0
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

    def resizeReusableState(self, place_inst_count: int) -> None:
        """Resize reusable matrix/vector storage without translating the solver."""

        if self.last_matrix_place_inst_count_ == place_inst_count and self.sparseMatrix_:
            self.matrix_reuse_count_ += 1
            for row in self.sparseMatrix_:
                row.clear()
        else:
            self.sparseMatrix_ = [[] for _ in range(place_inst_count)]
            self.matrix_reuse_count_ = 0
        self.rhsVecX_ = [0.0 for _ in range(place_inst_count)]
        self.rhsVecY_ = [0.0 for _ in range(place_inst_count)]
        self.solutionVecX_ = [0.0 for _ in range(place_inst_count)]
        self.solutionVecY_ = [0.0 for _ in range(place_inst_count)]
        self.fixedInstForceVecX_ = [0.0 for _ in range(place_inst_count)]
        self.fixedInstForceVecY_ = [0.0 for _ in range(place_inst_count)]
        self.last_matrix_place_inst_count_ = place_inst_count
        self.matrix_nonzero_count_ = 0

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
        self.resizeReusableState(len(self.instLocVecX_))
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
        place_insts = self.pbc_.placeInsts()
        if len(self.sparseMatrix_) != len(place_insts):
            self.resizeReusableState(len(place_insts))
        else:
            for row in self.sparseMatrix_:
                row.clear()
            self.matrix_nonzero_count_ = 0
        for index, inst in enumerate(place_insts):
            self.sparseMatrix_[index].append((index, 1.0))
            self.rhsVecX_[index] = float(inst.cx())
            self.rhsVecY_[index] = float(inst.cy())
            self.solutionVecX_[index] = float(inst.cx())
            self.solutionVecY_[index] = float(inst.cy())
        self.matrix_nonzero_count_ = sum(len(row) for row in self.sparseMatrix_)

    def reportMatrix(self, sample_limit: int = 0) -> Dict[str, Any]:
        """导出 sparse matrix 占位形状；真实 B2B stamping 仍未翻译。"""

        report: Dict[str, Any] = {
            "rows": len(self.sparseMatrix_),
            "nonzeros": self.matrix_nonzero_count_,
            "rhs_x": len(self.rhsVecX_),
            "rhs_y": len(self.rhsVecY_),
            "solution_x": len(self.solutionVecX_),
            "solution_y": len(self.solutionVecY_),
            "reuse_count": self.matrix_reuse_count_,
        }
        if sample_limit > 0:
            report["sample_rows"] = [list(row) for row in self.sparseMatrix_[:sample_limit]]
        return report

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
            "matrix_rows": len(self.sparseMatrix_),
            "matrix_nonzeros": self.matrix_nonzero_count_,
            "matrix_reuse_count": self.matrix_reuse_count_,
            "rhs_vector_size": len(self.rhsVecX_),
            "solution_vector_size": len(self.solutionVecX_),
            "matrix": self.reportMatrix(),
        }

    def getInstLocVecX(self) -> List[float]:
        return self.instLocVecX_

    def getInstLocVecY(self) -> List[float]:
        return self.instLocVecY_

    def getSparseMatrix(self) -> List[List[Tuple[int, float]]]:
        return self.sparseMatrix_

    def getRhsVecX(self) -> List[float]:
        return self.rhsVecX_

    def getRhsVecY(self) -> List[float]:
        return self.rhsVecY_

    def getSolutionVecX(self) -> List[float]:
        return self.solutionVecX_

    def getSolutionVecY(self) -> List[float]:
        return self.solutionVecY_


