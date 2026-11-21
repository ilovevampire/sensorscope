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

"""IMU Analysis tab: Allan deviation, noise fit table, spectrum, histogram, export."""

from __future__ import annotations

import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from .analysis_tab import AnalysisTab
from .plots import PALETTE
from .widgets import draw_histogram, fmt, line_plot, log_plot, MetricsTable, positive
from ..analysis.export import gazebo_imu_sdf, kalibr_yaml
from ..analysis.imu import ACCEL_AXES, analyze_imu, datasheet_lines, GYRO_AXES


class ImuAnalysisTab(AnalysisTab):
    guidance = (
        'Put the IMU on a solid, still surface away from motors, fans and foot traffic. '
        'Press Start capture and leave it untouched: 10 minutes gives noise density (N), '
        '1–3 hours gives bias instability (B). Press Stop to analyse, or Analyze now for a '
        'preview.'
    )
    min_samples = 500

    def build_results(self, layout: QtWidgets.QVBoxLayout) -> None:
        self.gyro_plot = log_plot('Gyroscope Allan deviation', 'τ (s)', 'σ (rad/s)')
        self.accel_plot = log_plot('Accelerometer Allan deviation', 'τ (s)', 'σ (m/s²)')
        left = QtWidgets.QWidget()
        lv = QtWidgets.QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(self.gyro_plot)
        lv.addWidget(self.accel_plot)

        self.table = MetricsTable(
            ['Axis', 'Mean (bias)', 'Std', 'N  (/√Hz)', 'B  bias instab.', 'K  rate rw']
        )
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(GYRO_AXES + ACCEL_AXES)
        self.combo.currentTextChanged.connect(self._draw_channel)
        self.psd_plot = log_plot('Power spectral density', 'frequency (Hz)', 'PSD (unit²/Hz)')
        self.hist_plot = line_plot('Noise histogram', 'value', 'density')
        self.info = QtWidgets.QPlainTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(125)
        copy_k = QtWidgets.QPushButton('Copy Kalibr YAML')
        copy_k.clicked.connect(lambda: self._copy(kalibr_yaml, 'Kalibr YAML'))
        copy_g = QtWidgets.QPushButton('Copy Gazebo noise')
        copy_g.clicked.connect(lambda: self._copy(gazebo_imu_sdf, 'Gazebo noise'))

        right = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.table.setMinimumHeight(205)
        rv.addWidget(self.table, 3)
        rv.addWidget(self.info)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(copy_k)
        buttons.addWidget(copy_g)
        rv.addLayout(buttons)
        sel = QtWidgets.QHBoxLayout()
        sel.addWidget(QtWidgets.QLabel('Channel'))
        sel.addWidget(self.combo)
        sel.addStretch(1)
        rv.addLayout(sel)
        rv.addWidget(self.psd_plot, 2)
        rv.addWidget(self.hist_plot, 2)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([620, 620])
        layout.addWidget(splitter)

    def analyze(self, cap):
        return analyze_imu(cap)

    def show_result(self, r) -> None:
        for plot, names in ((self.gyro_plot, GYRO_AXES), (self.accel_plot, ACCEL_AXES)):
            plot.clear()
            for i, name in enumerate(names):
                a = r.axes[name].allan
                color = PALETTE[i % len(PALETTE)]
                plot.plot(
                    a.taus,
                    positive(a.adev),
                    pen=pg.mkPen(color, width=2),
                    name=name,
                    symbol='o',
                    symbolSize=4,
                    symbolBrush=color,
                )
                plot.plot(
                    a.taus,
                    positive(a.fit_curve),
                    pen=pg.mkPen(color, width=1, style=QtCore.Qt.PenStyle.DashLine),
                )
        rows = []
        for name in GYRO_AXES + ACCEL_AXES:
            ax = r.axes[name]
            rows.append(
                [
                    f'{name} [{ax.unit}]',
                    fmt(ax.mean),
                    fmt(ax.std),
                    fmt(ax.allan.N),
                    fmt(ax.allan.B),
                    fmt(ax.allan.K),
                ]
            )
        self.table.set_rows(rows)
        t = r.timing
        timing = (
            f'Timing: stamp jitter {fmt(t.stamp_jitter_ms, 3)} ms, receive jitter '
            f'{fmt(t.recv_jitter_ms, 3)} ms, latency {fmt(t.latency_mean_ms, 3)} ms, '
            f'~{t.dropped_est} dropped'
            if t.has_stamps
            else f'Timing: no header stamps, receive jitter {fmt(t.recv_jitter_ms, 3)} ms, '
            f'~{t.dropped_est} dropped'
        )
        self.info.setPlainText(
            '\n'.join(
                [
                    f'Sampling: {r.fs:.1f} Hz over {r.duration_s / 60:.1f} min ({r.n:,} samples)',
                    f'Mean |a| = {r.gravity_mean:.4f} m/s² ({r.gravity_error_pct:+.2f} % '
                    f'from 1 g)',
                ]
                + datasheet_lines(r)
                + [timing]
            )
        )
        self._draw_channel(self.combo.currentText())

    def _draw_channel(self, name: str) -> None:
        r = self.result
        if r is None or name not in r.axes:
            return
        ax = r.axes[name]
        self.psd_plot.clear()
        self.psd_plot.plot(
            ax.psd_f[1:], positive(ax.psd[1:]), pen=pg.mkPen(PALETTE[0], width=1.5), name=name
        )
        draw_histogram(self.hist_plot, ax.hist.centers, ax.hist.density, ax.hist.gauss)

    def _copy(self, builder, label: str) -> None:
        if self.result is None:
            self.status.setText('Run an analysis first.')
            return
        text = (
            builder(self.result, self.stream.topic)
            if builder is kalibr_yaml
            else builder(self.result)
        )
        QtWidgets.QApplication.clipboard().setText(text)
        self.status.setText(f'{label} copied to the clipboard.')
