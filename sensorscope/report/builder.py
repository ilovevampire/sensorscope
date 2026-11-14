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

"""Build a self-contained HTML report (embedded PNG figures) from CaptureData."""

from __future__ import annotations

import base64
import datetime
import html
import io
import math
from typing import List, Sequence

import numpy as np

from ..analysis.export import gazebo_imu_sdf, kalibr_yaml
from ..analysis.gps import analyze_gps
from ..analysis.imu import ACCEL_AXES, analyze_imu, datasheet_lines, GYRO_AXES
from ..analysis.lidar import analyze_lidar
from ..core.capture import CaptureData
from ..core.stats import STAT_KEYS, summarize
from ..core.timing import analyze_timing

CSS = """
body{font-family:system-ui,Segoe UI,Roboto,sans-serif;
max-width:1050px;margin:2rem auto;padding:0 1rem;color:#1c2128}
h1{margin-bottom:.2rem} h2{margin-top:2.4rem;border-bottom:2px solid #d0d7de;padding-bottom:.3rem}
h3{margin-top:1.4rem} .meta{color:#57606a} img{max-width:100%;margin:.5rem 0}
table{border-collapse:collapse;margin:.6rem 0;font-size:.92rem}
th,td{border:1px solid #d0d7de;padding:.3rem .6rem;text-align:right}
th:first-child,td:first-child{text-align:left} th{background:#f6f8fa}
.warn{background:#fff8c5;border-left:4px solid #d4a72c;padding:.4rem .8rem;margin:.4rem 0}
.note{background:#eaf2ff;border-left:4px solid #3d8bfd;padding:.4rem .8rem;margin:.4rem 0}
pre{background:#f6f8fa;padding:.8rem;overflow:auto;border-radius:6px}
"""


def _g(x, d: int = 5) -> str:
    return '–' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{x:.{d}g}'


def _fig_html(fig, alt: str) -> str:
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=105, bbox_inches='tight')
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f'<img alt="{html.escape(alt)}" src="data:image/png;base64,{b64}">'


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    head = ''.join(f'<th>{html.escape(h)}</th>' for h in headers)
    body = ''.join(
        '<tr>' + ''.join(f'<td>{html.escape(str(c))}</td>' for c in r) + '</tr>' for r in rows
    )
    return f'<table><tr>{head}</tr>{body}</table>'


def _notes(items, css: str = 'warn') -> str:
    return ''.join(f'<div class="{css}">{html.escape(w)}</div>' for w in items)


def _plt():
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    return plt


# -- common sections ---------------------------------------------------------------
def _timing_table(cap: CaptureData) -> str:
    t = analyze_timing(cap.t, cap.stamp)
    rows = [
        ['Messages', str(t.n)],
        ['Rate (Hz)', _g(t.rate_hz)],
        ['Receive/log-time jitter (ms)', _g(t.recv_jitter_ms, 3)],
    ]
    if t.has_stamps:
        rows += [
            ['Header-stamp jitter (ms)', _g(t.stamp_jitter_ms, 3)],
            ['Latency mean / max (ms)', f'{_g(t.latency_mean_ms, 3)} / {_g(t.latency_max_ms, 3)}'],
        ]
    else:
        rows.append(['Header stamps', 'missing'])
    rows += [['Dropped (estimate)', str(t.dropped_est)], ['Out of order', str(t.out_of_order)]]
    return '<h3>Timing</h3>' + _table(['Metric', 'Value'], rows)


def _stats_table(cap: CaptureData) -> str:
    rows = []
    for name, v in cap.channels.items():
        s = summarize(v)
        rows.append([name] + [_g(s[k]) for k in STAT_KEYS])
    return '<h3>Channel statistics (whole recording)</h3>' + _table(
        ['Channel'] + [k.capitalize() for k in STAT_KEYS], rows
    )


# -- per-sensor sections -----------------------------------------------------------
def _imu_section(cap: CaptureData) -> str:
    plt = _plt()
    r = analyze_imu(cap)
    out = [_notes(r.warnings)]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4))
    for ax, names, title, unit in (
        (axs[0], GYRO_AXES, 'Gyroscope', 'rad/s'),
        (axs[1], ACCEL_AXES, 'Accelerometer', 'm/s²'),
    ):
        for i, n in enumerate(names):
            a = r.axes[n].allan
            ax.loglog(a.taus, a.adev, 'o-', ms=3, color=f'C{i}', label=n)
            ax.loglog(a.taus, a.fit_curve, '--', lw=1, color=f'C{i}')
        ax.set(title=f'{title} Allan deviation', xlabel='τ (s)', ylabel=f'σ ({unit})')
        ax.grid(True, which='both', alpha=0.3)
        ax.legend()
    out.append(_fig_html(fig, 'Allan deviation'))
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.6))
    for ax, names, title in (
        (axs[0], GYRO_AXES, 'Gyroscope'),
        (axs[1], ACCEL_AXES, 'Accelerometer'),
    ):
        for i, n in enumerate(names):
            ax.loglog(r.axes[n].psd_f[1:], r.axes[n].psd[1:], lw=0.8, color=f'C{i}', label=n)
        ax.set(title=f'{title} PSD', xlabel='frequency (Hz)', ylabel='unit²/Hz')
        ax.grid(True, which='both', alpha=0.3)
        ax.legend()
    out.append(_fig_html(fig, 'Power spectral density'))
    rows = [
        [f'{n} [{a.unit}]', _g(a.mean), _g(a.std), _g(a.allan.N), _g(a.allan.B), _g(a.allan.K)]
        for n, a in r.axes.items()
    ]
    out.append(
        _table(['Axis', 'Mean (bias)', 'Std', 'N (/√Hz)', 'B bias instab.', 'K rate rw'], rows)
    )
    out.append(
        f"<p class='meta'>{r.fs:.1f} Hz, {r.duration_s / 60:.1f} min, {r.n:,} samples. "
        f'Mean |a| = {r.gravity_mean:.4f} m/s² ({r.gravity_error_pct:+.2f} % from 1 g).</p>'
    )
    out.append(
        "<div class='note'>" + '<br>'.join(html.escape(x) for x in datasheet_lines(r)) + '</div>'
    )
    out.append('<h3>Kalibr YAML</h3><pre>' + html.escape(kalibr_yaml(r, cap.topic)) + '</pre>')
    out.append('<h3>Gazebo noise</h3><pre>' + html.escape(gazebo_imu_sdf(r)) + '</pre>')
    return ''.join(out)


def _lidar_section(cap: CaptureData) -> str:
    plt = _plt()
    r = analyze_lidar(cap)
    out = [_notes(r.warnings)]
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8))
    order = np.argsort(r.angles_deg)
    axs[0].plot(r.angles_deg[order], np.nan_to_num(r.std_r[order]), lw=0.8)
    axs[0].set(title='Range noise per beam', xlabel='beam angle (°)', ylabel='std (m)')
    axs[1].plot(r.angles_deg[order], 100 * r.valid_frac[order], lw=0.8, color='C2')
    axs[1].set(
        title='Valid returns per beam', xlabel='beam angle (°)', ylabel='valid (%)', ylim=(0, 105)
    )
    axs[2].plot(r.mean_xy[:, 0], r.mean_xy[:, 1], '.', ms=2)
    axs[2].plot(
        r.wall_line_xy[:, 0], r.wall_line_xy[:, 1], '-', color='gold', lw=3, label='fitted wall'
    )
    axs[2].plot([0], [0], 'ro')
    axs[2].set(title='Mean scan and wall fit (m)', aspect='equal')
    axs[2].legend(loc='upper right', fontsize=8)
    for ax in axs:
        ax.grid(True, alpha=0.3)
    out.append(_fig_html(fig, 'LiDAR noise and wall fit'))
    rows = [
        ['Scans / beams', f'{r.n_scans} / {r.n_beams}'],
        ['Valid returns (%)', _g(r.valid_pct, 4)],
        ['Beams mostly invalid', str(r.bad_beams)],
        ['Typical range noise, std (m)', _g(r.median_beam_std)],
        ['Wall sector', f'{r.sector_center_deg:.0f}° ± {r.sector_width_deg / 2:.0f}°'],
        ['Wall distance (m)', _g(r.wall_distance)],
        ['Wall noise, perpendicular std (m)', _g(r.wall_noise_std)],
        ['Wall flatness, rms of mean scan (m)', _g(r.wall_flatness_rms)],
    ]
    out.append(_table(['Metric', 'Value'], rows))
    return ''.join(out)


def _gps_section(cap: CaptureData) -> str:
    plt = _plt()
    r = analyze_gps(cap)
    out = [_notes(r.warnings)]
    de, dn = r.east - r.mean_east, r.north - r.mean_north
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={'width_ratios': [1, 1.4]})
    axs[0].plot(de, dn, '.', ms=2, alpha=0.6)
    th = np.linspace(0, 2 * np.pi, 200)
    axs[0].plot(
        r.cep50 * np.cos(th), r.cep50 * np.sin(th), color='gold', label=f'CEP50 {r.cep50:.2f} m'
    )
    axs[0].plot(
        r.cep95 * np.cos(th), r.cep95 * np.sin(th), color='C1', label=f'CEP95 {r.cep95:.2f} m'
    )
    axs[0].plot([0], [0], 'r+', ms=12)
    axs[0].set(title='Position scatter about the mean (m)', aspect='equal')
    axs[0].legend()
    axs[1].plot(r.t_fix, de, lw=0.8, label='east')
    axs[1].plot(r.t_fix, dn, lw=0.8, label='north')
    axs[1].set(title='Offset from mean over time', xlabel='time (s)', ylabel='m')
    axs[1].legend()
    for ax in axs:
        ax.grid(True, alpha=0.3)
    out.append(_fig_html(fig, 'GPS scatter'))
    rows = [
        ['Samples / with fix', f'{r.n} / {r.n_fix}'],
        ['Fix availability (%)', _g(r.availability_pct, 4)],
        ['Duration (s)', _g(r.duration_s)],
        ['Std east / north (m)', f'{_g(r.std_east)} / {_g(r.std_north)}'],
        ['RMS horizontal (m)', _g(r.rms_h)],
        ['CEP50 (m)', _g(r.cep50)],
        ['CEP95 (m)', _g(r.cep95)],
        ['2DRMS (m)', _g(r.drms2)],
        [
            'Drift east / north (m/min)',
            f'{_g(r.drift_east_m_per_min)} / {_g(r.drift_north_m_per_min)}',
        ],
        ['Reported horizontal std (m)', _g(r.reported_h_std)],
        ['Measured horizontal std (m)', _g(r.measured_h_std)],
        ['Measured / reported', _g(r.covariance_ratio, 3)],
        ['Error correlation time (s)', _g(r.autocorr_s, 3)],
    ]
    out.append(_table(['Metric', 'Value'], rows))
    return ''.join(out)


def _odom_section(cap: CaptureData) -> str:
    plt = _plt()
    x, y = cap.channels['x'], cap.channels['y']
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(x, y, lw=1)
    ax.plot(x[:1], y[:1], 'go', label='start')
    ax.plot(x[-1:], y[-1:], 'ro', label='end')
    ax.set(title='Odometry track (m)', aspect='equal')
    ax.grid(True, alpha=0.3)
    ax.legend()
    return _fig_html(fig, 'Odometry track')


_SECTIONS = {'imu': _imu_section, 'lidar': _lidar_section, 'gps': _gps_section}


def build_report(
    captures: List[CaptureData], title: str = 'SensorScope report', source: str = ''
) -> str:
    """Return a complete HTML document."""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    summary = _table(
        ['Topic', 'Type', 'Messages', 'Duration (s)', 'Rate (Hz)'],
        [
            [c.topic, c.spec.msg_type, f'{c.n:,}', _g(c.duration_s, 5), _g(c.rate_hz, 4)]
            for c in captures
        ],
    )
    parts = [
        f'<h1>{html.escape(title)}</h1>',
        f"<p class='meta'>Generated {now}"
        + (f' from <code>{html.escape(source)}</code>' if source else '')
        + '</p>',
        '<h2>Overview</h2>',
        summary,
    ]
    for cap in captures:
        parts.append(
            f'<h2>{html.escape(cap.spec.label)}: <code>{html.escape(cap.topic)}</code></h2>'
        )
        if cap.truncated:
            parts.append(
                _notes(
                    [
                        'The capture buffer filled up; only the first part of this topic was '
                        'analysed.'
                    ]
                )
            )
        kind = cap.spec.analysis
        try:
            if kind in _SECTIONS:
                parts.append(_SECTIONS[kind](cap))
            elif cap.spec.view == 'track':
                parts.append(_odom_section(cap))
        except ValueError as exc:
            parts.append(_notes([f'Analysis skipped: {exc}']))
        parts.append(_timing_table(cap))
        parts.append(_stats_table(cap))
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body>'
        + ''.join(parts)
        + '</body></html>'
    )
