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

"""Welch PSD, histogram with Gaussian fit, and autocorrelation time (numpy only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

NAN = float('nan')


def welch_psd(x, fs: float, nperseg: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
    """One-sided power spectral density in ``unit^2 / Hz`` (Hann window, 50 % overlap)."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 32:
        raise ValueError('Need at least 32 samples for a spectrum.')
    if nperseg is None:
        nperseg = int(2 ** np.floor(np.log2(max(32, min(8192, n // 8)))))
    nperseg = min(nperseg, n)
    win = np.hanning(nperseg)
    scale = 1.0 / (fs * np.sum(win**2))
    step = max(1, nperseg // 2)
    acc, count = None, 0
    for start in range(0, n - nperseg + 1, step):
        seg = x[start:start + nperseg]
        p = scale * np.abs(np.fft.rfft((seg - seg.mean()) * win)) ** 2
        acc = p if acc is None else acc + p
        count += 1
    psd = acc / count
    psd[1:-1] *= 2.0  # fold negative frequencies (not DC / Nyquist)
    return np.fft.rfftfreq(nperseg, 1.0 / fs), psd


@dataclass
class HistogramFit:
    centers: np.ndarray
    density: np.ndarray
    gauss: np.ndarray  # Gaussian pdf with the same mean/std, at ``centers``
    mean: float
    std: float
    skew: float
    excess_kurtosis: float  # 0 for a Gaussian


def histogram_fit(x, bins: int = 60) -> HistogramFit:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 8:
        raise ValueError('Need at least 8 samples for a histogram.')
    mean, std = float(x.mean()), float(x.std())
    density, edges = np.histogram(x, bins=bins, density=True)
    centers = 0.5 * (edges[:-1] + edges[1:])
    if std > 0:
        z = (x - mean) / std
        skew, kurt = float(np.mean(z**3)), float(np.mean(z**4) - 3.0)
        gauss = np.exp(-0.5 * ((centers - mean) / std) ** 2) / (std * np.sqrt(2 * np.pi))
    else:
        skew = kurt = 0.0
        gauss = np.zeros_like(centers)
    return HistogramFit(centers, density, gauss, mean, std, skew, kurt)


def autocorr_time(x, dt: float) -> float:
    """Time (s) for the autocorrelation to fall below 1/e; NaN if it never does."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 16:
        return NAN
    x = x - x.mean()
    f = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    if ac[0] <= 0:
        return NAN
    ac = ac / ac[0]
    below = np.nonzero(ac < 1.0 / np.e)[0]
    return float(below[0] * dt) if below.size else NAN
