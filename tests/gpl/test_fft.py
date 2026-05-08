from __future__ import annotations

import math
import unittest

from winroad.gpl import FFT


X_MAX = 4
Y_MAX = 4

INPUT_DATA = [
    0.0,
    1.0,
    2.0,
    3.0,
    512.0,
    513.0,
    514.0,
    515.0,
    1024.0,
    1025.0,
    1026.0,
    1027.0,
    1536.0,
    1537.0,
    1538.0,
    1539.0,
]

EXPECTED_FORCE_X = [
    -0.8124174475669861,
    -1.8370411396026611,
    -1.8370411396026611,
    -0.8124174475669861,
    -0.8124174475669861,
    -1.8370411396026611,
    -1.8370411396026611,
    -0.8124174475669861,
    -0.8124174475669861,
    -1.8370411396026611,
    -1.8370411396026611,
    -0.8124174475669861,
    -0.8124174475669861,
    -1.8370411396026611,
    -1.8370411396026611,
    -0.8124174475669861,
]

EXPECTED_FORCE_Y = [
    -415.9577331542969,
    -415.9577331542969,
    -415.9577331542969,
    -415.9577331542969,
    -940.5650634765625,
    -940.5650634765625,
    -940.5650634765625,
    -940.5650634765625,
    -940.5650634765625,
    -940.5650634765625,
    -940.5650634765625,
    -940.5650634765625,
    -415.9577331542969,
    -415.9577331542969,
    -415.9577331542969,
    -415.9577331542969,
]

EXPECTED_PHI = [
    -1215.7578125,
    -1214.3477783203125,
    -1212.4281005859375,
    -1211.01806640625,
    -493.7829284667969,
    -492.372802734375,
    -490.4532470703125,
    -489.0431213378906,
    489.0431213378906,
    490.4532470703125,
    492.372802734375,
    493.7829284667969,
    1211.01806640625,
    1212.4281005859375,
    1214.3477783203125,
    1215.7578125,
]


class FFTTest(unittest.TestCase):
    def test_basic(self) -> None:
        fft = FFT(X_MAX, Y_MAX, X_MAX, Y_MAX)
        for y in range(Y_MAX):
            for x in range(X_MAX):
                fft.updateDensity(x, y, INPUT_DATA[x + y * Y_MAX])

        fft.doFFT()

        for y in range(Y_MAX):
            for x in range(X_MAX):
                force_x, force_y = fft.getElectroForce(x, y)
                phi = fft.getElectroPhi(x, y)
                idx = x + y * Y_MAX
                self.assertTrue(
                    math.isclose(force_x, EXPECTED_FORCE_X[idx], rel_tol=1e-6, abs_tol=1e-6),
                    msg=f"force_x mismatch at ({x},{y})",
                )
                self.assertTrue(
                    math.isclose(force_y, EXPECTED_FORCE_Y[idx], rel_tol=1e-6, abs_tol=1e-6),
                    msg=f"force_y mismatch at ({x},{y})",
                )
                self.assertTrue(
                    math.isclose(phi, EXPECTED_PHI[idx], rel_tol=1e-6, abs_tol=1e-6),
                    msg=f"phi mismatch at ({x},{y})",
                )


if __name__ == "__main__":
    unittest.main()
