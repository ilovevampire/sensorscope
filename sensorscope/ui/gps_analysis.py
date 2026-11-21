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

"""GPS Analysis tab: scatter with CEP circles, drift, covariance check."""

from __future__ import annotations

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from .analysis_tab import AnalysisTab
from .plots import PALETTE
from .widgets import circle_xy, draw_histogram, fmt, line_plot, MetricsTable, timing_rows
from ..analysis.gps import analyze_gps
from ..analysis.spectrum import histogram_fit


class GpsAnalysisTab(AnalysisTab):
    guidance = (
        'Fix the antenna in place with a clear view of the sky and capture at least 10 minutes '
        '(longer is better). The result shows real position noise (CEP, RMS), slow drift, and '
        'whether the covariance your driver reports can be trusted by an EKF.'
    )
    min_samples = 20

    def build_results(self, layout: QtWidgets.QVBoxLayout) -> None:
        self.scatter = pg.PlotWidget()
        self.scatter.setTitle('Position scatter about the mean (m)', size='10pt')
        self.scatter.setAspectLocked(True)
        self.scatter.showGrid(x=True, y=True, alpha=0.3)
        self.scatter.addLegend(offset=(10, 5))
        self.time_plot = line_plot('Offset from mean over time', 'time (s)', 'metres')
        left = QtWidgets.QWidget()
        lv = QtWidgets.QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(self.scatter, 3)
        lv.addWidget(self.time_plot, 2)

        self.table = MetricsTable(['Metric', 'Value'])
        self.hist_plot = line_plot(
            'Radial error distribution', 'distance from mean (m)', 'density'
        )
        right = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(self.table, 6)
        rv.addWidget(self.hist_plot, 2)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([620, 620])
        layout.addWidget(splitter)

    def analyze(self, cap):
        return analyze_gps(cap)

    def show_result(self, r) -> None:
        de, dn = r.east - r.mean_east, r.north - r.mean_north
        self.scatter.clear()
        self.scatter.plot(
            de,
            dn,
            pen=None,
            symbol='o',
            symbolSize=3,
            symbolBrush=PALETTE[0],
            symbolPen=None,
            name='fixes',
        )
        for radius, color, name in (
            (r.cep50, '#ffd54f', f'CEP50 {r.cep50:.2f} m'),
            (r.cep95, '#ff8a65', f'CEP95 {r.cep95:.2f} m'),
        ):
            x, y = circle_xy(0.0, 0.0, radius)
            self.scatter.plot(x, y, pen=pg.mkPen(color, width=2), name=name)
        self.scatter.plot(
            [0], [0], pen=None, symbol='+', symbolSize=14, symbolBrush='#ff5555', name='mean'
        )
        self.time_plot.clear()
        self.time_plot.plot(r.t_fix, de, pen=pg.mkPen(PALETTE[0], width=1), name='east')
        self.time_plot.plot(r.t_fix, dn, pen=pg.mkPen(PALETTE[1], width=1), name='north')
        h = histogram_fit(r.radial, bins=40)
        draw_histogram(self.hist_plot, h.centers, h.density)
        self.table.set_rows(
            [
                ('Samples / with fix', f'{r.n} / {r.n_fix}'),
                ('Fix availability (%)', fmt(r.availability_pct, 4)),
                ('Duration (s)', fmt(r.duration_s, 5)),
                ('Accuracy', ''),
                ('Std east / north (m)', f'{fmt(r.std_east)} / {fmt(r.std_north)}'),
                ('RMS horizontal (m)', fmt(r.rms_h)),
                ('CEP50 (m)', fmt(r.cep50)),
                ('CEP95 (m)', fmt(r.cep95)),
                ('2DRMS (m)', fmt(r.drms2)),
                (
                    'Drift east / north (m/min)',
                    f'{fmt(r.drift_east_m_per_min)} / {fmt(r.drift_north_m_per_min)}',
                ),
                ('Altitude mean / std (m)', f'{fmt(r.alt_mean)} / {fmt(r.alt_std)}'),
                ('Is the reported covariance honest?', ''),
                ('Reported horizontal std (m)', fmt(r.reported_h_std)),
                ('Measured horizontal std (m)', fmt(r.measured_h_std)),
                ('Measured / reported', fmt(r.covariance_ratio, 3)),
                ('Error correlation time (s)', fmt(r.autocorr_s, 3)),
            ]
            + timing_rows(r.timing)
        )
