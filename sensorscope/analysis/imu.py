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

"""IMU analysis of a (mostly static) capture: Allan variance, noise, spectrum, sanity checks."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, List

import numpy as np

from .allan import AllanResult, analyze_allan
from .spectrum import histogram_fit, HistogramFit, welch_psd
from ..core.capture import CaptureData
from ..core.timing import analyze_timing, TimingStats

GRAVITY = 9.80665
GYRO_AXES = ('gx', 'gy', 'gz')
ACCEL_AXES = ('ax', 'ay', 'az')
UNITS = {'gx': 'rad/s', 'gy': 'rad/s', 'gz': 'rad/s', 'ax': 'm/s²', 'ay': 'm/s²', 'az': 'm/s²'}


@dataclass
class AxisResult:
    name: str
    unit: str
    mean: float  # static bias (gyro) / gravity component (accel)
    std: float
    allan: AllanResult
    psd_f: np.ndarray
    psd: np.ndarray
    hist: HistogramFit


@dataclass
class ImuAnalysis:
    fs: float
    n: int
    duration_s: float
    axes: Dict[str, AxisResult]
    timing: TimingStats
    gravity_mean: float
    gravity_error_pct: float
    warnings: List[str] = field(default_factory=list)

    def mean_param(self, names, attr: str) -> float:
        vals = [getattr(self.axes[n].allan, attr) for n in names if n in self.axes]
        return float(np.mean(vals)) if vals else float('nan')


def analyze_imu(cap: CaptureData) -> ImuAnalysis:
    if cap.n < 200:
        raise ValueError('Capture at least 200 samples (a few seconds) before analysing.')
    timing = analyze_timing(cap.t, cap.stamp)
    fs = timing.rate_hz if math.isfinite(timing.rate_hz) and timing.rate_hz > 0 else cap.rate_hz

    axes: Dict[str, AxisResult] = {}
    for name in GYRO_AXES + ACCEL_AXES:
        x = cap.channels[name]
        x = x[np.isfinite(x)]
        f, p = welch_psd(x, fs)
        axes[name] = AxisResult(
            name,
            UNITS[name],
            float(x.mean()),
            float(x.std()),
            analyze_allan(x, fs),
            f,
            p,
            histogram_fit(x),
        )

    g_vec = np.array([axes[a].mean for a in ACCEL_AXES])
    g_mean = float(np.linalg.norm(g_vec))
    g_err = 100.0 * (g_mean - GRAVITY) / GRAVITY

    res = ImuAnalysis(
        fs=fs,
        n=cap.n,
        duration_s=cap.duration_s,
        axes=axes,
        timing=timing,
        gravity_mean=g_mean,
        gravity_error_pct=g_err,
    )
    res.warnings = _warnings(res)
    return res


def _warnings(r: ImuAnalysis) -> List[str]:
    w: List[str] = []
    d = r.duration_s
    if d < 120:
        w.append(
            f'Capture is only {d:.0f} s. Allan results are rough; use at least 10 minutes '
            'for noise density.'
        )
    elif d < 3600:
        w.append(
            f'Capture is {d / 60:.0f} min: good for noise density (N). Bias instability (B) '
            'needs 1–3 hours.'
        )
    if any(a.allan.min_at_edge for a in r.axes.values()) and d >= 120:
        w.append(
            'The Allan curve is still falling at the longest averaging time, so bias '
            'instability (B) has not been reached. Capture longer.'
        )
    moving = [n for n in GYRO_AXES if abs(r.axes[n].mean) > 0.05]
    if moving:
        w.append(
            'Gyro mean is above 0.05 rad/s (about 3 °/s) on '
            + ', '.join(moving)
            + '. Was the sensor still? Motion invalidates the Allan analysis.'
        )
    if abs(r.gravity_error_pct) > 3.0:
        w.append(
            f'Mean |acceleration| is {r.gravity_mean:.2f} m/s² ({r.gravity_error_pct:+.1f} % '
            'from 1 g). Check units and scale, or whether the sensor is static.'
        )
    t = r.timing
    if t.n and t.dropped_est > 0.01 * t.n:
        w.append(
            f'About {t.dropped_est} samples were dropped ({100.0 * t.dropped_est / t.n:.1f} %). '
            'Allan variance assumes uniform sampling.'
        )
    return w


def datasheet_lines(r: ImuAnalysis) -> List[str]:
    """Results in the units printed on IMU datasheets."""
    gN, gB = r.mean_param(GYRO_AXES, 'N'), r.mean_param(GYRO_AXES, 'B')
    aN, aB = r.mean_param(ACCEL_AXES, 'N'), r.mean_param(ACCEL_AXES, 'B')
    rad2deg = 180.0 / math.pi
    return [
        f'Gyro angle random walk:  {gN * rad2deg * 60.0:.4g} °/√h   |   bias instability: '
        f'{gB * rad2deg * 3600.0:.4g} °/h',
        f'Accel velocity random walk:  {aN * 60.0:.4g} m/s/√h   |   bias instability: '
        f'{aB / GRAVITY * 1000.0:.4g} mg',
    ]
