"""Sparse linear solver helpers for WinRoad GPL initial placement."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

SparseRows = List[List[Tuple[int, float]]]


@dataclass
class ResidualError:
    """Corresponds to ``gpl::ResidualError``."""

    x: float = math.nan
    y: float = math.nan


def _dot(lhs: Sequence[float], rhs: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(lhs, rhs))


def _norm(vec: Sequence[float]) -> float:
    return math.sqrt(sum(float(value) * float(value) for value in vec))


def _matvec(matrix: SparseRows, vector: Sequence[float]) -> List[float]:
    result: List[float] = []
    for row in matrix:
        total = 0.0
        for col, value in row:
            total += float(value) * float(vector[col])
        result.append(total)
    return result


def _residual_error(matrix: SparseRows, rhs: Sequence[float], solution: Sequence[float]) -> float:
    ax = _matvec(matrix, solution)
    residual = _norm([float(b) - float(a) for b, a in zip(rhs, ax)])
    return residual / max(_norm(rhs), 1.0)


def _solve_dense(matrix_rows: SparseRows, rhs: Sequence[float]) -> List[float]:
    n = len(matrix_rows)
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    for row_index, row in enumerate(matrix_rows):
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


def _solve_bicgstab(
    matrix: SparseRows,
    rhs: Sequence[float],
    initial: Sequence[float],
    max_iterations: int,
    tolerance: float = 1e-9,
) -> Tuple[List[float], Dict[str, Any]]:
    n = len(matrix)
    x = [float(value) for value in initial]
    r = [float(b) - float(a) for b, a in zip(rhs, _matvec(matrix, x))]
    r_hat = list(r)
    rhs_norm = max(_norm(rhs), 1.0)
    residual = _norm(r)
    if residual <= tolerance * rhs_norm:
        return x, {"method": "bicgstab", "converged": True, "iterations": 0, "error": residual / rhs_norm}

    rho_old = alpha = omega = 1.0
    v = [0.0 for _ in range(n)]
    p = [0.0 for _ in range(n)]
    for iteration in range(1, max(1, max_iterations) + 1):
        rho_new = _dot(r_hat, r)
        if abs(rho_new) <= 1e-30:
            raise ValueError("BiCGSTAB breakdown: rho is zero")
        if iteration == 1:
            p = list(r)
        else:
            beta = (rho_new / rho_old) * (alpha / omega)
            p = [ri + beta * (pi - omega * vi) for ri, pi, vi in zip(r, p, v)]

        v = _matvec(matrix, p)
        denom = _dot(r_hat, v)
        if abs(denom) <= 1e-30:
            raise ValueError("BiCGSTAB breakdown: alpha denominator is zero")
        alpha = rho_new / denom
        s = [ri - alpha * vi for ri, vi in zip(r, v)]
        s_norm = _norm(s)
        if s_norm <= tolerance * rhs_norm:
            x = [xi + alpha * pi for xi, pi in zip(x, p)]
            return x, {
                "method": "bicgstab",
                "converged": True,
                "iterations": iteration,
                "error": s_norm / rhs_norm,
            }

        t = _matvec(matrix, s)
        tt = _dot(t, t)
        if abs(tt) <= 1e-30:
            raise ValueError("BiCGSTAB breakdown: omega denominator is zero")
        omega = _dot(t, s) / tt
        if abs(omega) <= 1e-30:
            raise ValueError("BiCGSTAB breakdown: omega is zero")

        x = [xi + alpha * pi + omega * si for xi, pi, si in zip(x, p, s)]
        r = [si - omega * ti for si, ti in zip(s, t)]
        residual = _norm(r)
        if residual <= tolerance * rhs_norm:
            return x, {
                "method": "bicgstab",
                "converged": True,
                "iterations": iteration,
                "error": residual / rhs_norm,
            }
        rho_old = rho_new

    return x, {
        "method": "bicgstab",
        "converged": False,
        "iterations": max(1, max_iterations),
        "error": residual / rhs_norm,
    }


def _solve_with_guess(
    matrix: SparseRows,
    rhs: Sequence[float],
    initial: Sequence[float],
    max_iterations: int,
    axis: str,
) -> Tuple[List[float], Dict[str, Any]]:
    try:
        solution, report = _solve_bicgstab(matrix, rhs, initial, max_iterations)
    except ValueError as exc:
        if len(matrix) > 256:
            raise
        solution = _solve_dense(matrix, rhs)
        report = {
            "method": "dense_gaussian",
            "converged": True,
            "iterations": len(matrix),
            "error": _residual_error(matrix, rhs, solution),
            "fallback_reason": str(exc),
        }

    if not report.get("converged"):
        if len(matrix) > 256:
            raise RuntimeError(f"InitialPlace {axis} solver did not converge: {report}")
        solution = _solve_dense(matrix, rhs)
        report = {
            "method": "dense_gaussian",
            "converged": True,
            "iterations": len(matrix),
            "error": _residual_error(matrix, rhs, solution),
            "fallback_reason": "bicgstab_not_converged",
        }
    report["axis"] = axis
    return solution, report


def cpuSparseSolve(
    maxSolverIter: int,
    iter: int,
    placeInstForceMatrixX: SparseRows,
    fixedInstForceVecX: Sequence[float],
    instLocVecX: List[float],
    placeInstForceMatrixY: SparseRows,
    fixedInstForceVecY: Sequence[float],
    instLocVecY: List[float],
    logger: Any = None,
    threads: int = 1,
) -> Tuple[ResidualError, Dict[str, Any]]:
    """Corresponds to ``gpl::cpuSparseSolve``.

    Eigen's implementation reports the relative residual after ``solveWithGuess``.
    This pure-Python translation follows the same call shape and mutates the
    solution vectors supplied by ``InitialPlace``.
    """

    x_solution, x_report = _solve_with_guess(
        placeInstForceMatrixX, fixedInstForceVecX, instLocVecX, maxSolverIter, "x"
    )
    y_solution, y_report = _solve_with_guess(
        placeInstForceMatrixY, fixedInstForceVecY, instLocVecY, maxSolverIter, "y"
    )

    instLocVecX[:] = x_solution
    instLocVecY[:] = y_solution
    return ResidualError(float(x_report["error"]), float(y_report["error"])), {
        "status": "solved",
        "iteration": iter,
        "threads": threads,
        "x": x_report,
        "y": y_report,
    }
