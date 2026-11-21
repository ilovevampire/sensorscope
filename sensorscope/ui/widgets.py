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

"""Small shared widgets for the analysis tabs."""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

import numpy as np
import pyqtgraph as pg
from PySide6 import QtGui, QtWidgets

from .plots import PALETTE


def fmt(x: float, digits: int = 5) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '–'
    return f'{x:.{digits}g}'


class MetricsTable(QtWidgets.QTableWidget):
    """Read-only table. A row with a label but no values is drawn as a bold section header."""

    def __init__(self, headers: Sequence[str], parent=None) -> None:
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(list(headers))
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setDefaultSectionSize(24)

    def set_rows(self, rows: Iterable[Sequence[str]]) -> None:
        rows = [list(r) for r in rows]
        self.setRowCount(len(rows))
        bold = QtGui.QFont(self.font())
        bold.setBold(True)
        for i, row in enumerate(rows):
            header = bool(row) and row[0] != '' and all(c == '' for c in row[1:])
            for j, text in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(text))
                if header:
                    item.setFont(bold)
                self.setItem(i, j, item)


def _plain_axes(plot: pg.PlotWidget) -> None:
    """Show real numbers, not '(x0.001)' style SI-prefix scaling."""
    for name in ('left', 'bottom'):
        plot.getAxis(name).enableAutoSIPrefix(False)


def log_plot(title: str, x_label: str, y_label: str) -> pg.PlotWidget:
    plot = pg.PlotWidget()
    plot.setTitle(title, size='10pt')
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.setLabel('bottom', x_label)
    plot.setLabel('left', y_label)
    plot.setLogMode(x=True, y=True)
    plot.addLegend(offset=(10, 5))
    plot.setMinimumHeight(160)
    _plain_axes(plot)
    return plot


def line_plot(title: str, x_label: str, y_label: str) -> pg.PlotWidget:
    plot = pg.PlotWidget()
    plot.setTitle(title, size='10pt')
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.setLabel('bottom', x_label)
    plot.setLabel('left', y_label)
    plot.addLegend(offset=(10, 5))
    plot.setMinimumHeight(140)
    _plain_axes(plot)
    return plot


def positive(a) -> np.ndarray:
    """Clamp to a tiny positive number so log axes never see zero."""
    return np.maximum(np.asarray(a, dtype=float), 1e-30)


def draw_histogram(
    plot: pg.PlotWidget, centers, density, gauss=None, color: str = PALETTE[0]
) -> None:
    plot.clear()
    if len(centers) > 1:
        width = float(centers[1] - centers[0]) * 0.9
        plot.addItem(pg.BarGraphItem(x=centers, height=density, width=width, brush=color))
    if gauss is not None:
        plot.plot(centers, gauss, pen=pg.mkPen('#ffd54f', width=2), name='Gaussian fit')


def circle_xy(cx: float, cy: float, r: float, n: int = 120) -> Tuple[np.ndarray, np.ndarray]:
    a = np.linspace(0, 2 * math.pi, n)
    return cx + r * np.cos(a), cy + r * np.sin(a)


def timing_rows(t) -> List[Tuple[str, str]]:
    rows = [
        ('Timing', ''),
        ('Message rate (Hz)', fmt(t.rate_hz)),
        ('Receive jitter (ms)', fmt(t.recv_jitter_ms, 3)),
    ]
    if t.has_stamps:
        rows += [
            ('Header-stamp jitter (ms)', fmt(t.stamp_jitter_ms, 3)),
            (
                'Latency mean / max (ms)',
                f'{fmt(t.latency_mean_ms, 3)} / {fmt(t.latency_max_ms, 3)}',
            ),
        ]
    else:
        rows.append(('Header stamps', 'missing'))
    rows += [('Dropped (estimate)', str(t.dropped_est)), ('Out of order', str(t.out_of_order))]
    return rows
