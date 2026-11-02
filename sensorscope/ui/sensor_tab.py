"""SensorTab: everything shown for one topic (plots, stats, controls)."""

from __future__ import annotations

import math

from PySide6 import QtCore, QtWidgets

from ..core.stats import STAT_KEYS, summarize
from .plots import ScanView, TimeSeriesPlot, TrackView


def _fmt(x: float) -> str:
    return "–" if not math.isfinite(x) else f"{x:.5g}"


class StatsTable(QtWidgets.QTableWidget):
    """Numeric summary (over the visible window) of every channel."""

    def __init__(self, channels, parent=None) -> None:
        cols = ("Channel",) + tuple(k.capitalize() if k != "rms" else "RMS" for k in STAT_KEYS)
        super().__init__(len(channels), len(cols), parent)
        self._channels = list(channels)
        self.setHorizontalHeaderLabels(cols)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        align = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        for row, name in enumerate(self._channels):
            self.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            for col in range(1, len(cols)):
                item = QtWidgets.QTableWidgetItem("–")
                item.setTextAlignment(align)
                self.setItem(row, col, item)

    def update_stats(self, snap) -> None:
        for row, name in enumerate(self._channels):
            stats = summarize(snap[name][1]) if name in snap else {}
            for col, key in enumerate(STAT_KEYS, start=1):
                self.item(row, col).setText(_fmt(stats.get(key, float("nan"))))


class SensorTab(QtWidgets.QWidget):
    def __init__(self, stream, parent=None) -> None:
        super().__init__(parent)
        self.stream = stream
        self.paused = False
        spec = stream.spec

        # --- header + controls ---
        self.header = QtWidgets.QLabel()
        self.window_spin = QtWidgets.QSpinBox()
        self.window_spin.setRange(1, 120)
        self.window_spin.setValue(10)
        self.window_spin.setSuffix(" s")
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._on_pause)
        clear_btn = QtWidgets.QPushButton("Clear")
        clear_btn.clicked.connect(self.stream.clear)
        export_btn = QtWidgets.QPushButton("Export CSV…")
        export_btn.clicked.connect(self._export_csv)

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(self.header, 1)
        controls.addWidget(QtWidgets.QLabel("Window"))
        controls.addWidget(self.window_spin)
        controls.addWidget(self.pause_btn)
        controls.addWidget(clear_btn)
        controls.addWidget(export_btn)

        # --- left: scrolling time-series plots ---
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.plots = []
        for title, chans in spec.groups.items():
            plot = TimeSeriesPlot(title, chans)
            self.plots.append(plot)
            left_layout.addWidget(plot, 1)

        # --- right: optional special view + stats table ---
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.view = None
        if spec.view == "scan":
            self.view = ScanView()
        elif spec.view == "track":
            self.view = TrackView(f"{spec.label} track (m)")
        if self.view is not None:
            right_layout.addWidget(self.view, 3)
        self.stats = StatsTable(spec.channels)
        right_layout.addWidget(self.stats, 2)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        right.setMinimumWidth(480)  # keep the stats table readable on every tab
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([740, 520])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(splitter, 1)

    # -- slots ---------------------------------------------------------------
    def _on_pause(self, checked: bool) -> None:
        self.paused = checked
        self.pause_btn.setText("Resume" if checked else "Pause")

    def _export_csv(self) -> None:
        default = self.stream.topic.strip("/").replace("/", "_") + ".csv"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export CSV", default, "CSV (*.csv)")
        if path:
            rows = self.stream.to_csv(path, self.window_spin.value())
            QtWidgets.QMessageBox.information(self, "Export CSV", f"Saved {rows} rows to\n{path}")

    # -- called ~30x/s by the main window while this tab is visible ------------
    def refresh(self, update_stats: bool) -> None:
        self._update_header()
        if self.paused:
            return
        window = float(self.window_spin.value())
        snap = self.stream.snapshot(window)
        times = [t[-1] for t, _ in snap.values() if len(t)]
        t_ref = max(times) if times else 0.0
        for plot in self.plots:
            plot.update_data(snap, t_ref, window)
        if self.view is not None:
            self.view.update_view(self.stream, snap, t_ref)
        if update_stats:
            self.stats.update_stats(snap)

    def _update_header(self) -> None:
        r = self.stream.rate
        text = (f"{self.stream.topic}    {r.rate_hz:.1f} Hz    "
                f"jitter {r.jitter_ms:.2f} ms    {r.count} msgs")
        age = self.stream.seconds_since_last()
        stale = age is not None and age > 2.0
        if stale:
            text += f"    NO DATA for {age:.0f} s"
        self.header.setText(text)
        self.header.setStyleSheet("color: #ff8a65;" if stale else "")
