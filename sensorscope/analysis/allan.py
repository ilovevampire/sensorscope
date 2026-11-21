# Copyright 2026 Vishal Gaud
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Overlapping Allan deviation and noise-parameter fit (IEEE 952 style).

For rate data ``x`` (gyro in rad/s, accelerometer in m/s^2) sampled at ``fs``:

    sigma^2(tau) = N^2 / tau  +  (0.664 B)^2  +  K^2 tau / 3

N  noise density           [x-unit / sqrt(Hz)]   (angle / velocity random walk)
B  bias instability        [x-unit]              (flat bottom of the curve)
K  rate random walk        [x-unit / s / sqrt(Hz)]
"""

from __future__ import annotations

from dataclasses import dataclass
import itertools
from typing import Tuple

import numpy as np

NAN = float('nan')
BIAS_INSTABILITY_SCALE = 0.664  # sqrt(2 ln2 / pi): flicker floor = 0.664 * B


@dataclass
class AllanResult:
    fs: float
    n_samples: int
    taus: np.ndarray
    adev: np.ndarray
    err: np.ndarray  # approximate relative error of each point
    fit_curve: np.ndarray  # model evaluated at taus
    N: float = NAN  # noise density
    B: float = NAN  # bias instability (curve minimum / 0.664)
    tau_B: float = NAN  # tau at the curve minimum
    K: float = NAN  # rate random walk
    min_at_edge: bool = False  # True if the minimum is the last point (capture too short)


def allan_deviation(x, fs: float, n_taus: int = 60) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Overlapping Allan deviation. Returns ``(taus, adev, relative_error)``."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 16:
        raise ValueError('Need at least 16 samples for an Allan deviation.')
    m_max = max(1, n // 4)  # beyond N/4 the estimate has > 40 % error
    m = np.unique(np.round(np.logspace(0, np.log10(m_max), n_taus)).astype(int))
    c = np.concatenate(([0.0], np.cumsum(x)))
    adev = np.empty(m.size)
    err = np.empty(m.size)
    for i, mi in enumerate(m):
        ym = (c[mi:] - c[:-mi]) / mi  # means of every length-mi window
        d = ym[mi:] - ym[:-mi]  # differences of adjacent windows
        adev[i] = np.sqrt(0.5 * np.mean(d * d))
        err[i] = 1.0 / np.sqrt(2.0 * max(n / mi - 1.0, 0.5))
    return m / fs, adev, err


def _fit_model(taus, adev, err) -> Tuple[float, float, float]:
    """Weighted non-negative least squares for sigma^2 = a/tau + b + c*tau."""
    y = adev**2
    cols = np.stack([1.0 / taus, np.ones_like(taus), taus], axis=1)
    w = 1.0 / np.maximum(2.0 * err * y, 1e-300)  # relative-error weights
    best, best_res = (0.0, 0.0, 0.0), np.inf
    for k in (1, 2, 3):
        for idx in itertools.combinations(range(3), k):
            A = cols[:, idx] * w[:, None]
            theta, *_ = np.linalg.lstsq(A, y * w, rcond=None)
            if np.any(theta < 0):
                continue
            res = float(np.sum((A @ theta - y * w) ** 2))
            if res < best_res:
                full = np.zeros(3)
                full[list(idx)] = theta
                best, best_res = tuple(full), res
    return best


def analyze_allan(x, fs: float, n_taus: int = 60) -> AllanResult:
    taus, adev, err = allan_deviation(x, fs, n_taus)
    a, b, c = _fit_model(taus, adev, err)
    # Look for the minimum only among reliable points (< 25 % estimated error, roughly
    # tau <= capture length / 9): the noisy tail can dip below the true minimum by chance.
    idx = np.nonzero(err <= 0.25)[0]
    if idx.size < 3:
        idx = np.arange(taus.size)
    i_min = int(idx[np.argmin(adev[idx])])
    return AllanResult(
        fs=float(fs),
        n_samples=int(np.isfinite(np.asarray(x, float)).sum()),
        taus=taus,
        adev=adev,
        err=err,
        fit_curve=np.sqrt(a / taus + b + c * taus),
        N=float(np.sqrt(a)),
        B=float(adev[i_min] / BIAS_INSTABILITY_SCALE),
        tau_B=float(taus[i_min]),
        K=float(np.sqrt(3.0 * c)),
        min_at_edge=bool(i_min >= idx[-1] - 1),
    )
