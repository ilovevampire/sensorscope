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

"""LiDAR Analysis tab: per-beam noise, dropout map, static-wall fit."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from .analysis_tab import AnalysisTab
from .plots import PALETTE
from .widgets import draw_histogram, fmt, line_plot, MetricsTable, timing_rows
from ..analysis.lidar import analyze_lidar


class LidarAnalysisTab(AnalysisTab):
    guidance = (
        'Point the LiDAR at a static scene with at least one flat wall and keep people and '
        'objects out of view. Capture 30 or more scans (3 s at 10 Hz), 1–2 minutes is better. '
        'The wall sector is picked automatically (nearest wall) or set by hand.'
    )
    min_samples = 3

    def build_controls(self, row: QtWidgets.QHBoxLayout) -> None:
        self.auto_chk = QtWidgets.QCheckBox('Auto wall sector')
        self.auto_chk.setChecked(True)
        self.center_spin = QtWidgets.QDoubleSpinBox()
        self.center_spin.setRange(-180.0, 180.0)
        self.center_spin.setSuffix(' ° center')
        self.center_spin.setEnabled(False)
        self.width_spin = QtWidgets.QDoubleSpinBox()
        self.width_spin.setRange(4.0, 120.0)
        self.width_spin.setValue(20.0)
        self.width_spin.setSuffix(' ° wide')
        self.auto_chk.toggled.connect(lambda on: self.center_spin.setEnabled(not on))
        for w in (self.auto_chk, self.center_spin, self.width_spin):
            row.addWidget(w)

    def build_results(self, layout: QtWidgets.QVBoxLayout) -> None:
        self.noise_plot = line_plot('Range noise per beam', 'beam angle (°)', 'std (m)')
        self.drop_plot = line_plot('Valid returns per beam', 'beam angle (°)', 'valid (%)')
        left = QtWidgets.QWidget()
        lv = QtWidgets.QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(self.noise_plot)
        lv.addWidget(self.drop_plot)

        self.map_plot = pg.PlotWidget()
        self.map_plot.setTitle('Mean scan and wall fit (m)', size='10pt')
        self.map_plot.setAspectLocked(True)
        self.map_plot.showGrid(x=True, y=True, alpha=0.3)
        self.map_plot.addLegend(offset=(10, 5))
        self.table = MetricsTable(['Metric', 'Value'])
        self.hist_plot = line_plot('Wall residuals', 'perpendicular error (m)', 'density')
        right = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(self.map_plot, 2)
        rv.addWidget(self.table, 5)
        rv.addWidget(self.hist_plot, 2)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([600, 640])
        layout.addWidget(splitter)

    def make_job(self, cap):
        center = None if self.auto_chk.isChecked() else self.center_spin.value()
        width = self.width_spin.value()
        return lambda: analyze_lidar(cap, center, width)

    def show_result(self, r) -> None:
        ang = r.angles_deg
        order = np.argsort(ang)
        self.noise_plot.clear()
        self.noise_plot.plot(
            ang[order], np.nan_to_num(r.std_r[order]), pen=pg.mkPen(PALETTE[0], width=1.5)
        )
        self.drop_plot.clear()
        self.drop_plot.plot(
            ang[order], 100.0 * r.valid_frac[order], pen=pg.mkPen(PALETTE[2], width=1.5)
        )
        self.drop_plot.setYRange(0, 105)
        self.map_plot.clear()
        self.map_plot.plot(
            r.mean_xy[:, 0],
            r.mean_xy[:, 1],
            pen=None,
            symbol='o',
            symbolSize=3,
            symbolBrush=PALETTE[0],
            symbolPen=None,
            name='mean scan',
        )
        self.map_plot.plot(
            r.wall_line_xy[:, 0],
            r.wall_line_xy[:, 1],
            pen=pg.mkPen('#ffd54f', width=3),
            name='fitted wall',
        )
        self.map_plot.plot(
            [0],
            [0],
            pen=None,
            symbol='o',
            symbolSize=9,
            symbolBrush='#ff5555',
            symbolPen=None,
            name='sensor',
        )
        draw_histogram(self.hist_plot, *self._hist(r.residuals))
        self.table.set_rows(
            [
                ('Scans / beams', f'{r.n_scans} / {r.n_beams}'),
                ('Valid returns (%)', fmt(r.valid_pct, 4)),
                ('Beams mostly invalid', str(r.bad_beams)),
                ('Typical range noise, std (m)', fmt(r.median_beam_std)),
                ('Wall sector', f'{r.sector_center_deg:.0f}° ± {r.sector_width_deg / 2:.0f}°'),
                ('Wall distance (m)', fmt(r.wall_distance)),
                ('Wall noise, perpendicular std (m)', fmt(r.wall_noise_std)),
                ('Wall flatness, rms of mean scan (m)', fmt(r.wall_flatness_rms)),
            ]
            + timing_rows(r.timing)
        )

    @staticmethod
    def _hist(x):
        from ..analysis.spectrum import histogram_fit

        h = histogram_fit(x, bins=50)
        return h.centers, h.density, h.gauss
