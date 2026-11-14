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

"""GPS analysis of a static capture: CEP, RMS, drift, availability, error correlation."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import List

import numpy as np

from .spectrum import autocorr_time
from ..core.capture import CaptureData
from ..core.timing import analyze_timing, TimingStats

NAN = float('nan')


@dataclass
class GpsAnalysis:
    n: int
    n_fix: int
    duration_s: float
    availability_pct: float
    timing: TimingStats
    east: np.ndarray
    north: np.ndarray
    t_fix: np.ndarray  # seconds since first fix sample
    mean_east: float
    mean_north: float
    std_east: float
    std_north: float
    rms_h: float  # sqrt(mean(r^2)) about the mean position
    cep50: float
    cep95: float
    drms2: float  # 2 * rms_h
    radial: np.ndarray
    drift_east_m_per_min: float
    drift_north_m_per_min: float
    alt_mean: float
    alt_std: float
    reported_h_std: float  # mean of the driver's covariance
    measured_h_std: float  # sqrt((var_e + var_n) / 2)
    covariance_ratio: float  # measured / reported
    autocorr_s: float  # error decorrelation time (NaN = never within capture)
    warnings: List[str] = field(default_factory=list)


def analyze_gps(cap: CaptureData) -> GpsAnalysis:
    e, n = cap.channels['east'], cap.channels['north']
    status = cap.channels['status']
    fix = (status >= 0) & np.isfinite(e) & np.isfinite(n)
    if fix.sum() < 20:
        raise ValueError('Need at least 20 fixes. Capture longer, or check the GPS has a fix.')
    t = cap.t[fix] - cap.t[fix][0]
    e, n = e[fix], n[fix]
    me, mn = float(e.mean()), float(n.mean())
    de, dn = e - me, n - mn
    r = np.hypot(de, dn)
    se, sn = float(e.std()), float(n.std())
    rms = float(np.sqrt(np.mean(r**2)))

    slope_e = float(np.polyfit(t, e, 1)[0]) * 60.0
    slope_n = float(np.polyfit(t, n, 1)[0]) * 60.0

    alt = cap.channels['alt'][fix]
    reported = (
        float(np.nanmean(cap.channels['h_std'][fix]))
        if np.isfinite(cap.channels['h_std'][fix]).any()
        else NAN
    )
    measured = math.sqrt((se**2 + sn**2) / 2.0)
    ratio = measured / reported if reported and reported > 0 else NAN
    dt = float(np.median(np.diff(t))) if t.size > 1 else NAN
    tau = max(
        (autocorr_time(de, dt), autocorr_time(dn, dt)), key=lambda v: -1 if np.isnan(v) else v
    )

    res = GpsAnalysis(
        n=cap.n,
        n_fix=int(fix.sum()),
        duration_s=cap.duration_s,
        availability_pct=float(100.0 * fix.mean()),
        timing=analyze_timing(cap.t, cap.stamp),
        east=e,
        north=n,
        t_fix=t,
        mean_east=me,
        mean_north=mn,
        std_east=se,
        std_north=sn,
        rms_h=rms,
        cep50=float(np.median(r)),
        cep95=float(np.percentile(r, 95)),
        drms2=2.0 * rms,
        radial=r,
        drift_east_m_per_min=slope_e,
        drift_north_m_per_min=slope_n,
        alt_mean=float(np.nanmean(alt)),
        alt_std=float(np.nanstd(alt)),
        reported_h_std=reported,
        measured_h_std=measured,
        covariance_ratio=ratio,
        autocorr_s=tau,
    )
    res.warnings = _warnings(res)
    return res


def _warnings(r: GpsAnalysis) -> List[str]:
    w: List[str] = []
    if r.duration_s < 300:
        w.append(
            f'Capture is {r.duration_s:.0f} s. Use 10 minutes or more for a trustworthy CEP, '
            'with the antenna fixed and a clear sky view.'
        )
    if r.availability_pct < 99.0:
        w.append(f'A fix was available for only {r.availability_pct:.1f} % of messages.')
    if np.isfinite(r.covariance_ratio):
        if r.covariance_ratio > 1.5:
            w.append(
                f'Optimistic covariance: measured horizontal std is {r.measured_h_std:.2f} m but '
                f'the driver reports {r.reported_h_std:.2f} m (x{r.covariance_ratio:.1f}). '
                f'Use the '
                "measured values (or larger) in your EKF's GPS measurement noise."
            )
        elif r.covariance_ratio < 0.5:
            w.append(
                f'Pessimistic covariance: measured std {r.measured_h_std:.2f} m is well below the '
                f'reported {r.reported_h_std:.2f} m. The EKF may be under-trusting this GPS.'
            )
    if np.isfinite(r.autocorr_s) and r.autocorr_s > 2.0:
        w.append(
            f'Errors are time-correlated (about {r.autocorr_s:.1f} s). An EKF that treats '
            f'each fix '
            'as independent will be overconfident: inflate R, or use at most one fix every '
            f'{r.autocorr_s:.0f} s.'
        )
    elif not np.isfinite(r.autocorr_s):
        w.append(
            'Errors did not decorrelate within the capture (slow drift). Capture longer to '
            'estimate the correlation time.'
        )
    return w
