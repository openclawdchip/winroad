"""Initial placement boundary for WinRoad gpl."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
        self.matrix_is_b2b_stamped_ = False
        self.last_solver_report_: Dict[str, Any] = {}

    def doBicgstabPlace(self, threads: int) -> None:
        self.last_threads_ = threads
        self.solver_failed_ = False
        self.last_solver_report_ = {}
        if self.ipVars_.maxIter == 0:
            return
        self.setPlaceInstExtId()
        self.placeInstsInitialPositions()
        self.updatePinInfo()
        self.createSparseMatrix()
        if not self.matrix_is_b2b_stamped_:
            self.solver_failed_ = True
            self.last_solver_report_ = {
                "status": "not_stamped",
                "message": (
                    "OpenROAD InitialPlace B2B net stamping has not been translated; "
                    "the base sparse matrix is only a safe identity placeholder."
                ),
                "matrix": self.reportMatrix(sample_limit=3),
            }
            raise NotImplementedError(self.last_solver_report_["message"])
        self.solveLinearSystem()
        self.instLocVecX_ = list(self.solutionVecX_)
        self.instLocVecY_ = list(self.solutionVecY_)
        self.updateCoordi()

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
        self.matrix_is_b2b_stamped_ = False

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
        self.matrix_is_b2b_stamped_ = False

    def markSparseMatrixStamped(self, stamped: bool = True) -> None:
        """标记 sparse matrix 已由调用方完成真实 B2B stamping。

        基类还没有翻译 OpenROAD 的 B2B stamping；测试或后续翻译线程可先填好
        ``sparseMatrix_``/RHS/solution 容器，再用这个标记启用真实数值求解。
        """

        self.matrix_is_b2b_stamped_ = stamped
        self.matrix_nonzero_count_ = sum(len(row) for row in self.sparseMatrix_)

    def validateLinearSystem(self) -> Dict[str, Any]:
        """检查当前 sparse matrix/RHS/solution 容器是否可求解。"""

        n = len(self.sparseMatrix_)
        issues: List[Dict[str, Any]] = []
        if n == 0:
            issues.append({"type": "empty_matrix", "message": "sparse matrix 为空"})
        for name, vec in (("rhs_x", self.rhsVecX_), ("rhs_y", self.rhsVecY_)):
            if len(vec) != n:
                issues.append({"type": "vector_size_mismatch", "vector": name, "size": len(vec), "rows": n})
        for name, vec in (("solution_x", self.solutionVecX_), ("solution_y", self.solutionVecY_)):
            if len(vec) != n:
                issues.append({"type": "solution_size_mismatch", "vector": name, "size": len(vec), "rows": n})
        for row_index, row in enumerate(self.sparseMatrix_):
            if not row:
                issues.append({"type": "empty_row", "row": row_index})
                continue
            diag = 0.0
            for col, value in row:
                if col < 0 or col >= n:
                    issues.append({"type": "column_out_of_range", "row": row_index, "column": col})
                if not math.isfinite(float(value)):
                    issues.append({"type": "non_finite_matrix_value", "row": row_index, "column": col})
                if col == row_index:
                    diag += float(value)
            if diag == 0.0:
                issues.append({"type": "missing_diagonal", "row": row_index})
        return {
            "format": "winroad-gpl-initial-place-linear-system-validation",
            "version": 1,
            "valid": not issues,
            "issue_count": len(issues),
            "rows": n,
            "nonzeros": sum(len(row) for row in self.sparseMatrix_),
            "issues": issues,
        }

    @staticmethod
    def _dot(lhs: Sequence[float], rhs: Sequence[float]) -> float:
        return sum(float(a) * float(b) for a, b in zip(lhs, rhs))

    @staticmethod
    def _norm(vec: Sequence[float]) -> float:
        return math.sqrt(sum(float(value) * float(value) for value in vec))

    def _matvec(self, vector: Sequence[float]) -> List[float]:
        result = []
        for row in self.sparseMatrix_:
            total = 0.0
            for col, value in row:
                total += float(value) * float(vector[col])
            result.append(total)
        return result

    def _residual_norm(self, rhs: Sequence[float], solution: Sequence[float]) -> float:
        ax = self._matvec(solution)
        return self._norm([float(b) - float(a) for a, b in zip(ax, rhs)])

    def _solve_dense(self, rhs: Sequence[float]) -> List[float]:
        """小规模 Gaussian elimination fallback，用于 BiCGSTAB 遇到 breakdown。"""

        n = len(self.sparseMatrix_)
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        for row_index, row in enumerate(self.sparseMatrix_):
            for col, value in row:
                matrix[row_index][col] += float(value)
        b = [float(value) for value in rhs]
        for pivot in range(n):
            best = max(range(pivot, n), key=lambda row: abs(matrix[row][pivot]))
            if abs(matrix[best][pivot]) <= 1e-15:
                raise ValueError("InitialPlace linear system is singular")
            if best != pivot:
                matrix[pivot], matrix[best] = matrix[best], matrix[pivot]
                b[pivot], b[best] = b[best], b[pivot]
            pivot_value = matrix[pivot][pivot]
            for col in range(pivot, n):
                matrix[pivot][col] /= pivot_value
            b[pivot] /= pivot_value
            for row in range(pivot + 1, n):
                factor = matrix[row][pivot]
                if factor == 0.0:
                    continue
                for col in range(pivot, n):
                    matrix[row][col] -= factor * matrix[pivot][col]
                b[row] -= factor * b[pivot]
        x = [0.0 for _ in range(n)]
        for row in range(n - 1, -1, -1):
            x[row] = b[row] - sum(matrix[row][col] * x[col] for col in range(row + 1, n))
        return x

    def _solve_bicgstab(self, rhs: Sequence[float], initial: Sequence[float]) -> Tuple[List[float], Dict[str, Any]]:
        """纯 Python BiCGSTAB，小规模/已 stamp 系统使用。"""

        n = len(self.sparseMatrix_)
        max_iter = max(1, self.ipVars_.maxSolverIter)
        tolerance = 1e-9
        x = [float(value) for value in initial]
        ax = self._matvec(x)
        r = [float(b) - float(a) for b, a in zip(rhs, ax)]
        r_hat = list(r)
        rhs_norm = max(self._norm(rhs), 1.0)
        residual = self._norm(r)
        if residual <= tolerance * rhs_norm:
            return x, {"method": "bicgstab", "converged": True, "iterations": 0, "residual": residual}

        rho_old = alpha = omega = 1.0
        v = [0.0 for _ in range(n)]
        p = [0.0 for _ in range(n)]
        for iteration in range(1, max_iter + 1):
            rho_new = self._dot(r_hat, r)
            if abs(rho_new) <= 1e-30:
                raise ValueError("InitialPlace BiCGSTAB breakdown: rho is zero")
            if iteration == 1:
                p = list(r)
            else:
                beta = (rho_new / rho_old) * (alpha / omega)
                p = [ri + beta * (pi - omega * vi) for ri, pi, vi in zip(r, p, v)]
            v = self._matvec(p)
            denom = self._dot(r_hat, v)
            if abs(denom) <= 1e-30:
                raise ValueError("InitialPlace BiCGSTAB breakdown: alpha denominator is zero")
            alpha = rho_new / denom
            s = [ri - alpha * vi for ri, vi in zip(r, v)]
            s_norm = self._norm(s)
            if s_norm <= tolerance * rhs_norm:
                x = [xi + alpha * pi for xi, pi in zip(x, p)]
                return x, {"method": "bicgstab", "converged": True, "iterations": iteration, "residual": s_norm}
            t = self._matvec(s)
            tt = self._dot(t, t)
            if abs(tt) <= 1e-30:
                raise ValueError("InitialPlace BiCGSTAB breakdown: omega denominator is zero")
            omega = self._dot(t, s) / tt
            if abs(omega) <= 1e-30:
                raise ValueError("InitialPlace BiCGSTAB breakdown: omega is zero")
            x = [xi + alpha * pi + omega * si for xi, pi, si in zip(x, p, s)]
            r = [si - omega * ti for si, ti in zip(s, t)]
            residual = self._norm(r)
            if residual <= tolerance * rhs_norm:
                return x, {"method": "bicgstab", "converged": True, "iterations": iteration, "residual": residual}
            rho_old = rho_new
        return x, {"method": "bicgstab", "converged": False, "iterations": max_iter, "residual": residual}

    def _solve_vector(self, rhs: Sequence[float], initial: Sequence[float], axis: str) -> Tuple[List[float], Dict[str, Any]]:
        n = len(self.sparseMatrix_)
        try:
            solution, report = self._solve_bicgstab(rhs, initial)
        except ValueError as exc:
            if n > 256:
                raise
            solution = self._solve_dense(rhs)
            report = {
                "method": "dense_gaussian",
                "converged": True,
                "iterations": n,
                "residual": self._residual_norm(rhs, solution),
                "fallback_reason": str(exc),
            }
        if not report.get("converged"):
            if n > 256:
                raise RuntimeError(f"InitialPlace {axis} solver did not converge: {report}")
            solution = self._solve_dense(rhs)
            report = {
                "method": "dense_gaussian",
                "converged": True,
                "iterations": n,
                "residual": self._residual_norm(rhs, solution),
                "fallback_reason": "bicgstab_not_converged",
            }
        report["axis"] = axis
        return solution, report

    def solveLinearSystem(self) -> Dict[str, Any]:
        """求解当前 sparse matrix 对应的 X/Y 线性系统。

        该函数只使用已经存在的矩阵/RHS，不生成 OpenROAD B2B stamping；大型系统
        依赖未翻译 stamping 和高性能 solver，失败时会给出明确错误。
        """

        validation = self.validateLinearSystem()
        if not validation["valid"]:
            self.solver_failed_ = True
            self.last_solver_report_ = {"status": "invalid_system", "validation": validation}
            raise ValueError(f"InitialPlace linear system is invalid: {validation['issues']}")
        n = len(self.sparseMatrix_)
        if n > 4096:
            self.solver_failed_ = True
            self.last_solver_report_ = {
                "status": "too_large",
                "rows": n,
                "message": "pure Python InitialPlace solver is limited to 4096 rows",
            }
            raise NotImplementedError(self.last_solver_report_["message"])

        self.solutionVecX_, x_report = self._solve_vector(self.rhsVecX_, self.solutionVecX_, "x")
        self.solutionVecY_, y_report = self._solve_vector(self.rhsVecY_, self.solutionVecY_, "y")
        self.solver_failed_ = False
        self.last_solver_report_ = {
            "status": "solved",
            "rows": n,
            "nonzeros": validation["nonzeros"],
            "x": x_report,
            "y": y_report,
        }
        return dict(self.last_solver_report_)

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
            "b2b_stamped": self.matrix_is_b2b_stamped_,
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
            "solver": dict(self.last_solver_report_),
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


