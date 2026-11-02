"""Headless GUI smoke test: builds the window from synthetic streams (no ROS)."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

import numpy as np  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

from sensorscope.core.stream import SensorStream  # noqa: E402
from sensorscope.sensors import REGISTRY  # noqa: E402
from sensorscope.ui.main_window import MainWindow  # noqa: E402
from sensorscope.ui.theme import apply_dark_theme  # noqa: E402


class FakeSource:
    def __init__(self, streams):
        self._streams = streams

    def get_streams(self):
        return self._streams


def _filled_streams():
    streams = {}
    imu = SensorStream("/imu/data", REGISTRY["sensor_msgs/msg/Imu"])
    for i in range(500):
        t = i * 0.01
        imu.push(t, {"ax": 0.03 + 0.05 * math.sin(40 * t), "ay": 0.0, "az": 9.81,
                     "accel_norm": 9.81, "gx": 0.0, "gy": 0.0, "gz": 0.2,
                     "roll": 0.0, "pitch": 0.0, "yaw": t})
    streams["/imu/data"] = imu
    scan = SensorStream("/scan", REGISTRY["sensor_msgs/msg/LaserScan"])
    ang = np.linspace(-math.pi, math.pi, 360)
    for i in range(50):
        scan.push(i * 0.1, {"valid_pct": 98.0, "r_min": 3.0, "r_mean": 4.0, "r_max": 5.0},
                  (4 * np.cos(ang), 3 * np.sin(ang)))
    streams["/scan"] = scan
    gps = SensorStream("/gps/fix", REGISTRY["sensor_msgs/msg/NavSatFix"])
    for i in range(100):
        t = i * 0.2
        gps.push(t, {"east": 20 * math.sin(0.05 * t), "north": 20 * (1 - math.cos(0.05 * t)),
                     "alt": 430.0, "h_std": 1.5, "status": 0.0})
    streams["/gps/fix"] = gps
    return streams


@pytest.fixture(scope="module")
def app():
    a = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    apply_dark_theme(a)
    return a


def test_window_builds_tabs_and_refreshes(app):
    win = MainWindow(FakeSource(_filled_streams()))
    assert win.tab_widget.count() == 3
    for i in range(win.tab_widget.count()):
        win.tab_widget.setCurrentIndex(i)
        for _ in range(8):  # enough frames to trigger a stats refresh
            win._on_frame()
        tab = win.tab_widget.currentWidget()
        assert tab.stats.item(0, 2).text() != "–"  # 'Mean' column was filled in
    win.close()


def test_empty_state_and_pause(app):
    win = MainWindow(FakeSource({}))
    assert win.tab_widget.count() == 0 and not win.placeholder.isHidden()
    win._on_frame()  # must not crash with no tabs
    win.close()
    win2 = MainWindow(FakeSource(_filled_streams()))
    tab = win2.tab_widget.currentWidget()
    tab.pause_btn.setChecked(True)
    assert tab.paused and tab.pause_btn.text() == "Resume"
    tab.refresh(update_stats=True)  # paused refresh is a no-op, not an error
    win2.close()
