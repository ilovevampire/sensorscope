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

"""LiDAR analysis of a static capture: per-beam noise, dropouts, static-wall residuals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import warnings

import numpy as np

from ..core.capture import CaptureData
from ..core.timing import analyze_timing, TimingStats

NAN = float('nan')


@dataclass
class LidarAnalysis:
    n_scans: int
    n_beams: int
    duration_s: float
    timing: TimingStats
    angles_deg: np.ndarray
    mean_r: np.ndarray  # per-beam mean of valid returns (NaN if none)
    std_r: np.ndarray  # per-beam std of valid returns
    valid_frac: np.ndarray  # per-beam fraction of valid returns
    valid_pct: float  # overall
    median_beam_std: float  # typical range noise (beams with >50 % valid)
    bad_beams: int  # beams with < 50 % valid returns
    sector_center_deg: float
    sector_width_deg: float
    sector_mask: np.ndarray
    wall_distance: float  # metres from the sensor to the fitted wall line
    wall_noise_std: float  # std of perpendicular distance over all scans (m)
    wall_flatness_rms: float  # rms of the *mean* scan around the line (geometry error)
    wall_line_xy: np.ndarray  # 2x2 end points of the fitted line, for plotting
    mean_xy: np.ndarray  # Nx2 mean scan points (valid beams)
    residuals: np.ndarray  # pooled perpendicular distances (m)
    warnings: List[str] = field(default_factory=list)


def _wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def analyze_lidar(
    cap: CaptureData, sector_center_deg: Optional[float] = None, sector_width_deg: float = 20.0
) -> LidarAnalysis:
    scans = [s for s in cap.extras if s is not None]
    if len(scans) < 3:
        raise ValueError('Capture at least 3 scans (30+ recommended) before analysing.')
    n_beams = scans[0].ranges.size
    scans = [s for s in scans if s.ranges.size == n_beams]
    s0 = scans[0]
    R = np.vstack([s.ranges for s in scans]).astype(float)
    valid = np.isfinite(R) & (R >= s0.range_min) & (R <= s0.range_max)
    Rv = np.where(valid, R, np.nan)

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        mean_r = np.nanmean(Rv, axis=0)
        std_r = np.nanstd(Rv, axis=0)
    valid_frac = valid.mean(axis=0)
    good = valid_frac > 0.5
    angles = s0.angles
    angles_deg = np.degrees(angles)

    if sector_center_deg is None:  # auto: the nearest well-observed beam
        cand = np.where(good, mean_r, np.inf)
        sector_center_deg = (
            float(angles_deg[int(np.argmin(cand))]) if np.isfinite(cand).any() else 0.0
        )
    sector = (np.abs(_wrap_deg(angles_deg - sector_center_deg)) <= sector_width_deg / 2.0) & good
    if sector.sum() < 3:
        raise ValueError('The chosen sector has fewer than 3 good beams. Widen it or move it.')

    # Total-least-squares line through the mean scan inside the sector.
    px, py = mean_r[sector] * np.cos(angles[sector]), mean_r[sector] * np.sin(angles[sector])
    pts = np.column_stack([px, py])
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c)
    direction, normal = vt[0], vt[1]
    flat = float(np.sqrt(np.mean(((pts - c) @ normal) ** 2)))

    # Perpendicular distance of every valid return in the sector, from every scan.
    vs = valid[:, sector]
    Rs = np.where(vs, R[:, sector], 0.0)  # avoid inf * sin() = nan
    X = Rs * np.cos(angles[sector])
    Y = Rs * np.sin(angles[sector])
    d = ((X - c[0]) * normal[0] + (Y - c[1]) * normal[1])[vs]
    half = max(np.ptp(pts @ direction), 1e-3) / 2.0 + 0.1
    line = np.vstack([c - direction * half, c + direction * half])

    all_good = np.isfinite(mean_r)
    mean_xy = np.column_stack(
        [mean_r[all_good] * np.cos(angles[all_good]), mean_r[all_good] * np.sin(angles[all_good])]
    )
    timing = analyze_timing(cap.t, cap.stamp)
    res = LidarAnalysis(
        n_scans=len(scans),
        n_beams=n_beams,
        duration_s=cap.duration_s,
        timing=timing,
        angles_deg=angles_deg,
        mean_r=mean_r,
        std_r=std_r,
        valid_frac=valid_frac,
        valid_pct=float(100.0 * valid.mean()),
        median_beam_std=float(np.median(std_r[good])) if good.any() else NAN,
        bad_beams=int((~good).sum()),
        sector_center_deg=float(sector_center_deg),
        sector_width_deg=float(sector_width_deg),
        sector_mask=sector,
        wall_distance=float(abs(c @ normal)),
        wall_noise_std=float(np.std(d)),
        wall_flatness_rms=flat,
        wall_line_xy=line,
        mean_xy=mean_xy,
        residuals=d,
    )
    res.warnings = _warnings(res)
    return res


def _warnings(r: LidarAnalysis) -> List[str]:
    w: List[str] = []
    if r.n_scans < 30:
        w.append(f'Only {r.n_scans} scans captured; use 30 or more for stable statistics.')
    if r.bad_beams:
        w.append(
            f'{r.bad_beams} of {r.n_beams} beams return mostly invalid data (blocked, '
            'out of range, or dark/absorbing surfaces).'
        )
    if r.valid_pct < 90.0:
        w.append(f'Only {r.valid_pct:.1f} % of all returns are valid.')
    if np.isfinite(r.median_beam_std) and r.wall_noise_std > 3.0 * r.median_beam_std:
        w.append(
            'Wall residuals are much larger than per-beam noise: the surface may not be '
            'flat or the scene is not static. Pick a flatter sector.'
        )
    w.append('Keep the scene completely static: moving objects inflate the noise numbers.')
    return w
