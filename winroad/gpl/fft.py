"""Pure Python translation of OpenROAD GPL FFT/Poisson helpers.

The original implementation uses Ooura's in-place FFT routines.  This module
keeps the same public helper names used by ``fft.cpp`` while evaluating the
cosine/sine transforms directly with Python lists.  It is intentionally simple
and slow, but preserves the array layout and ``FFT.doFFT`` flow.
"""

from __future__ import annotations

from math import cos, pi, sin, sqrt
from typing import Iterable

REPLACE_FFT_PI = 3.141592653589793238462


def _check_power_of_two_length(n: int) -> None:
    if n <= 0 or n & (n - 1):
        raise ValueError("OpenROAD FFT helpers expect positive power-of-two lengths")


def _dct_forward(values: Iterable[float]) -> list[float]:
    a = [float(value) for value in values]
    n = len(a)
    _check_power_of_two_length(n)
    return [
        sum(a[x] * cos(pi * k * (x + 0.5) / n) for x in range(n))
        for k in range(n)
    ]


def _dct_inverse(coeffs: Iterable[float]) -> list[float]:
    c = [float(value) for value in coeffs]
    n = len(c)
    _check_power_of_two_length(n)
    return [
        sum(c[k] * cos(pi * k * (x + 0.5) / n) for k in range(n))
        for x in range(n)
    ]


def _dst_forward(values: Iterable[float]) -> list[float]:
    a = [float(value) for value in values]
    n = len(a)
    _check_power_of_two_length(n)
    return [
        sum(a[x] * sin(pi * k * (x + 0.5) / n) for x in range(n))
        for k in range(n)
    ]


def _dst_inverse(coeffs: Iterable[float]) -> list[float]:
    c = [float(value) for value in coeffs]
    n = len(c)
    _check_power_of_two_length(n)
    return [
        sum(c[k] * sin(pi * k * (x + 0.5) / n) for k in range(n))
        for x in range(n)
    ]


def _replace_row(row: list[float], values: list[float]) -> None:
    for i, value in enumerate(values):
        row[i] = float(value)


def _column(a: list[list[float]], col: int, n1: int) -> list[float]:
    return [a[row][col] for row in range(n1)]


def _replace_column(a: list[list[float]], col: int, values: list[float]) -> None:
    for row, value in enumerate(values):
        a[row][col] = float(value)


def ddct(n: int, isgn: int, a: list[float], ip: list[int] | None = None, w: list[float] | None = None) -> None:
    """In-place 1D DCT helper corresponding to OpenROAD ``ddct``.

    ``ip`` and ``w`` are accepted for signature compatibility with Ooura's
    implementation.  The direct implementation does not need either work area.
    """

    if n != len(a):
        raise ValueError("n must match the input array length")
    _replace_row(a, _dct_forward(a) if isgn < 0 else _dct_inverse(a))


def ddst(n: int, isgn: int, a: list[float], ip: list[int] | None = None, w: list[float] | None = None) -> None:
    """In-place 1D DST helper corresponding to OpenROAD ``ddst``."""

    if n != len(a):
        raise ValueError("n must match the input array length")
    _replace_row(a, _dst_forward(a) if isgn < 0 else _dst_inverse(a))


def ddct2d(
    n1: int,
    n2: int,
    isgn: int,
    a: list[list[float]],
    t: list[float] | None = None,
    ip: list[int] | None = None,
    w: list[float] | None = None,
) -> None:
    """In-place 2D DCT helper corresponding to OpenROAD ``ddct2d``."""

    for i in range(n1):
        row = a[i]
        ddct(n2, isgn, row, ip, w)
    for j in range(n2):
        values = _column(a, j, n1)
        ddct(n1, isgn, values, ip, w)
        _replace_column(a, j, values)


def ddst2d(
    n1: int,
    n2: int,
    isgn: int,
    a: list[list[float]],
    t: list[float] | None = None,
    ip: list[int] | None = None,
    w: list[float] | None = None,
) -> None:
    """In-place 2D DST helper corresponding to OpenROAD ``ddst2d``."""

    for i in range(n1):
        row = a[i]
        ddst(n2, isgn, row, ip, w)
    for j in range(n2):
        values = _column(a, j, n1)
        ddst(n1, isgn, values, ip, w)
        _replace_column(a, j, values)


def ddsct2d(
    n1: int,
    n2: int,
    isgn: int,
    a: list[list[float]],
    t: list[float] | None = None,
    ip: list[int] | None = None,
    w: list[float] | None = None,
) -> None:
    """In-place 2D DST-in-x/DCT-in-y helper corresponding to ``ddsct2d``."""

    for i in range(n1):
        row = a[i]
        ddct(n2, isgn, row, ip, w)
    for j in range(n2):
        values = _column(a, j, n1)
        ddst(n1, isgn, values, ip, w)
        _replace_column(a, j, values)


def ddcst2d(
    n1: int,
    n2: int,
    isgn: int,
    a: list[list[float]],
    t: list[float] | None = None,
    ip: list[int] | None = None,
    w: list[float] | None = None,
) -> None:
    """In-place 2D DCT-in-x/DST-in-y helper corresponding to ``ddcst2d``."""

    for i in range(n1):
        row = a[i]
        ddst(n2, isgn, row, ip, w)
    for j in range(n2):
        values = _column(a, j, n1)
        ddct(n1, isgn, values, ip, w)
        _replace_column(a, j, values)


class FFT:
    """Direct Python translation of OpenROAD ``gpl::FFT``."""

    def __init__(self, binCntX: int, binCntY: int, binSizeX: float, binSizeY: float) -> None:
        self.binCntX_ = int(binCntX)
        self.binCntY_ = int(binCntY)
        self.binSizeX_ = float(binSizeX)
        self.binSizeY_ = float(binSizeY)

        _check_power_of_two_length(self.binCntX_)
        _check_power_of_two_length(self.binCntY_)

        self.binDensity_ = self._new_grid()
        self.electroPhi_ = self._new_grid()
        self.electroForceX_ = self._new_grid()
        self.electroForceY_ = self._new_grid()

        self.csTable_ = [0.0] * (max(self.binCntX_, self.binCntY_) * 3 // 2)
        self.wx_ = [0.0] * self.binCntX_
        self.wxSquare_ = [0.0] * self.binCntX_
        self.wy_ = [0.0] * self.binCntY_
        self.wySquare_ = [0.0] * self.binCntY_
        self.workArea_ = [0] * (round(sqrt(max(self.binCntX_, self.binCntY_))) + 2)

        for i in range(self.binCntX_):
            self.wx_[i] = REPLACE_FFT_PI * float(i) / float(self.binCntX_)
            self.wxSquare_[i] = self.wx_[i] * self.wx_[i]

        for i in range(self.binCntY_):
            self.wy_[i] = (
                REPLACE_FFT_PI
                * float(i)
                / float(self.binCntY_)
                * float(self.binSizeY_)
                / float(self.binSizeX_)
            )
            self.wySquare_[i] = self.wy_[i] * self.wy_[i]

    def _new_grid(self) -> list[list[float]]:
        return [[0.0 for _ in range(self.binCntY_)] for _ in range(self.binCntX_)]

    def updateDensity(self, x: int, y: int, density: float) -> None:
        self.binDensity_[x][y] = float(density)

    def getElectroForce(self, x: int, y: int) -> tuple[float, float]:
        return (self.electroForceX_[x][y], self.electroForceY_[x][y])

    def getElectroPhi(self, x: int, y: int) -> float:
        return self.electroPhi_[x][y]

    def doFFT(self) -> None:
        ddct2d(
            self.binCntX_,
            self.binCntY_,
            -1,
            self.binDensity_,
            None,
            self.workArea_,
            self.csTable_,
        )

        for i in range(self.binCntX_):
            self.binDensity_[i][0] *= 0.5

        for i in range(self.binCntY_):
            self.binDensity_[0][i] *= 0.5

        for i in range(self.binCntX_):
            for j in range(self.binCntY_):
                self.binDensity_[i][j] *= 4.0 / self.binCntX_ / self.binCntY_

        for i in range(self.binCntX_):
            wx = self.wx_[i]
            wx2 = self.wxSquare_[i]

            for j in range(self.binCntY_):
                wy = self.wy_[j]
                wy2 = self.wySquare_[j]

                density = self.binDensity_[i][j]

                if i == 0 and j == 0:
                    phi = electroX = electroY = 0.0
                else:
                    phi = density / (wx2 + wy2)
                    electroX = phi * wx
                    electroY = phi * wy

                self.electroPhi_[i][j] = phi
                self.electroForceX_[i][j] = electroX
                self.electroForceY_[i][j] = electroY

        ddct2d(
            self.binCntX_,
            self.binCntY_,
            1,
            self.electroPhi_,
            None,
            self.workArea_,
            self.csTable_,
        )
        ddsct2d(
            self.binCntX_,
            self.binCntY_,
            1,
            self.electroForceX_,
            None,
            self.workArea_,
            self.csTable_,
        )
        ddcst2d(
            self.binCntX_,
            self.binCntY_,
            1,
            self.electroForceY_,
            None,
            self.workArea_,
            self.csTable_,
        )

