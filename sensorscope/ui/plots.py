"""Plot widgets: scrolling time series, LiDAR scan view, and XY track view."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

PALETTE = ["#4fc3f7", "#ff8a65", "#81c784", "#ba68c8", "#ffd54f", "#4db6ac"]
_EMPTY = (np.empty(0), np.empty(0))


class TimeSeriesPlot(pg.PlotWidget):
    """One plot with several channels; x axis is seconds relative to 'now'."""

    def __init__(self, title: str, channels, parent=None) -> None:
        super().__init__(parent=parent)
        self.setMinimumHeight(120)
        self.setTitle(title, size="10pt")
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel("bottom", "time (s)")
        self.addLegend(offset=(10, 5))
        self.setClipToView(True)
        self.setDownsampling(auto=True, mode="peak")
        self._curves = {}
        for i, name in enumerate(channels):
            pen = pg.mkPen(PALETTE[i % len(PALETTE)], width=1.5)
            self._curves[name] = self.plot(pen=pen, name=name, connect="finite")

    def update_data(self, snap, t_ref: float, window_s: float) -> None:
        for name, curve in self._curves.items():
            t, v = snap.get(name, _EMPTY)
            curve.setData(t - t_ref, v)
        self.setXRange(-window_s, 0.0, padding=0.02)


class ScanView(pg.PlotWidget):
    """Top-down view of the latest LiDAR scan."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setTitle("Latest scan, sensor frame (m)", size="10pt")
        self.setAspectLocked(True)
        self.showGrid(x=True, y=True, alpha=0.25)
        self._scatter = pg.ScatterPlotItem(size=3, pen=pg.mkPen(None), brush=pg.mkBrush("#4fc3f7"))
        self.addItem(self._scatter)
        self.addItem(pg.ScatterPlotItem([0], [0], size=10, pen=pg.mkPen(None), brush=pg.mkBrush("#ff5555")))
        self._fitted = False

    def update_view(self, stream, snap, t_ref: float) -> None:
        if stream.extra is None:
            return
        xs, ys = stream.extra
        self._scatter.setData(x=xs, y=ys)
        if not self._fitted and len(xs):
            self.autoRange()  # fit once; after that the user may zoom freely
            self._fitted = True


class TrackView(pg.PlotWidget):
    """XY path of two channels (GPS local ENU, or odometry x/y)."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent=parent)
        self.setTitle(title, size="10pt")
        self.setAspectLocked(True)
        self.showGrid(x=True, y=True, alpha=0.25)
        self._path = self.plot(pen=pg.mkPen("#81c784", width=1.5), symbol="o", symbolSize=3,
                               symbolBrush="#81c784", symbolPen=None, connect="finite")
        self._head = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush("#ff5555"))
        self.addItem(self._head)

    def update_view(self, stream, snap, t_ref: float) -> None:
        xch, ych = stream.spec.view_channels
        x, y = snap[xch][1], snap[ych][1]
        self._path.setData(x, y)
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.any():
            self._head.setData(x=[x[ok][-1]], y=[y[ok][-1]])
