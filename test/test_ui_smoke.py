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

"""Headless GUI smoke test: builds the window from synthetic streams (no ROS)."""

import math
import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
pytest.importorskip('PySide6')
pytest.importorskip('pyqtgraph')

import numpy as np  # noqa: E402,I100
from PySide6 import QtWidgets  # noqa: E402,I100

from helpers import feed, gps_capture, imu_capture, lidar_capture  # noqa: E402,I100

from sensorscope.core.stream import SensorStream  # noqa: E402
from sensorscope.sensors import REGISTRY  # noqa: E402
from sensorscope.sensors.lidar import ScanData  # noqa: E402
from sensorscope.ui.main_window import MainWindow  # noqa: E402
from sensorscope.ui.theme import apply_dark_theme  # noqa: E402


class FakeSource:
    """Minimal stand-in for RosRunner: only get_streams() is needed."""

    def __init__(self, streams):
        self._streams = streams

    def get_streams(self):
        return self._streams


def _filled_streams():
    streams = {}
    imu = SensorStream('/imu/data', REGISTRY['sensor_msgs/msg/Imu'])
    for i in range(500):
        t = i * 0.01
        imu.push(
            t,
            {
                'ax': 0.03 + 0.05 * math.sin(40 * t),
                'ay': 0.0,
                'az': 9.81,
                'accel_norm': 9.81,
                'gx': 0.0,
                'gy': 0.0,
                'gz': 0.2,
                'roll': 0.0,
                'pitch': 0.0,
                'yaw': t,
            },
            stamp=t - 0.001,
        )
    streams['/imu/data'] = imu
    scan = SensorStream('/scan', REGISTRY['sensor_msgs/msg/LaserScan'])
    ang = np.linspace(-math.pi, math.pi, 360, endpoint=False)
    ranges = np.minimum(
        4 / np.maximum(abs(np.cos(ang)), 1e-6), 3 / np.maximum(abs(np.sin(ang)), 1e-6)
    )
    for i in range(50):
        scan.push(
            i * 0.1,
            {'valid_pct': 98.0, 'r_min': 3.0, 'r_mean': 4.0, 'r_max': 5.0},
            ScanData(ranges.astype(np.float32), -math.pi, 2 * math.pi / 360, 0.1, 12.0),
        )
    streams['/scan'] = scan
    gps = SensorStream('/gps/fix', REGISTRY['sensor_msgs/msg/NavSatFix'])
    for i in range(100):
        t = i * 0.2
        gps.push(
            t,
            {
                'east': 20 * math.sin(0.05 * t),
                'north': 20 * (1 - math.cos(0.05 * t)),
                'alt': 430.0,
                'h_std': 1.5,
                'status': 0.0,
            },
        )
    streams['/gps/fix'] = gps
    odom = SensorStream('/odom', REGISTRY['nav_msgs/msg/Odometry'])
    for i in range(50):
        odom.push(i * 0.03, {'x': i * 0.03, 'y': 0.0, 'yaw_deg': 0.0, 'vx': 1.0, 'wz': 0.0})
    streams['/odom'] = odom
    return streams


@pytest.fixture(scope='module')
def app():
    a = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    apply_dark_theme(a)
    return a


def test_window_builds_tabs_and_refreshes(app):
    win = MainWindow(FakeSource(_filled_streams()))
    assert win.tab_widget.count() == 4
    for i in range(win.tab_widget.count()):
        win.tab_widget.setCurrentIndex(i)
        for _ in range(8):  # enough frames to trigger a stats refresh
            win._on_frame()
        tab = win.tab_widget.currentWidget()
        assert tab.stats.item(0, 2).text() != '–'  # 'Mean' column was filled in
    win.close()


def test_analysis_switch_only_for_sensors_with_analysis(app):
    win = MainWindow(FakeSource(_filled_streams()))
    by_label = {
        win.tab_widget.tabText(i): win.tab_widget.widget(i) for i in range(win.tab_widget.count())
    }
    assert by_label['IMU  /imu/data'].modes is not None
    assert by_label['LiDAR  /scan'].modes is not None
    assert by_label['GPS  /gps/fix'].modes is not None
    assert by_label['Odometry  /odom'].modes is None
    win.close()


def test_empty_state_and_pause(app):
    win = MainWindow(FakeSource({}))
    assert win.tab_widget.count() == 0 and not win.placeholder.isHidden()
    win._on_frame()  # must not crash with no tabs
    win.close()
    win2 = MainWindow(FakeSource(_filled_streams()))
    tab = win2.tab_widget.currentWidget()
    tab.pause_btn.setChecked(True)
    assert tab.paused and tab.pause_btn.text() == 'Resume'
    tab.refresh(update_stats=True)  # paused refresh is a no-op, not an error
    win2.close()


def _analysis_tab(stream_topic, spec_key, cap):
    stream = SensorStream(stream_topic, REGISTRY[spec_key])
    feed(stream, cap)
    from sensorscope.ui.sensor_tab import SensorTab

    tab = SensorTab(stream)
    return stream, tab, tab.analysis


def test_imu_analysis_tab(app):
    stream, tab, ana = _analysis_tab('/imu/data', 'sensor_msgs/msg/Imu', imu_capture(n=60_000))
    assert not stream.capturing and stream.capture_snapshot().n == 60_000
    ana.analyze_sync()
    assert ana.result is not None
    assert ana.table.rowCount() >= 6 and ana.table.item(0, 3).text() != '–'  # N column filled
    ana.combo.setCurrentText('az')  # redraw PSD/histogram
    ana._copy(__import__('sensorscope.analysis.export', fromlist=['x']).kalibr_yaml, 'Kalibr YAML')
    assert 'gyroscope_noise_density' in QtWidgets.QApplication.clipboard().text()
    assert ana.warn_box.toPlainText().startswith('•')
    tab.modes.setCurrentIndex(1)
    tab.refresh(update_stats=True)  # live refresh is skipped while Analysis is showing


def test_gps_analysis_tab(app):
    _, _, ana = _analysis_tab('/gps/fix', 'sensor_msgs/msg/NavSatFix', gps_capture(n=3000))
    ana.analyze_sync()
    labels = [ana.table.item(i, 0).text() for i in range(ana.table.rowCount())]
    assert 'CEP95 (m)' in labels and 'Measured / reported' in labels
    assert 'Optimistic covariance' in ana.warn_box.toPlainText()


def test_lidar_analysis_tab_manual_sector(app):
    _, _, ana = _analysis_tab('/scan', 'sensor_msgs/msg/LaserScan', lidar_capture(n_scans=40))
    ana.analyze_sync()
    assert ana.result.wall_distance == pytest.approx(3.0, abs=0.05)
    ana.auto_chk.setChecked(False)
    ana.center_spin.setValue(0.0)
    ana.analyze_sync()
    assert ana.result.wall_distance == pytest.approx(4.0, abs=0.05)


def test_analysis_reports_not_enough_data(app):
    stream = SensorStream('/imu/data', REGISTRY['sensor_msgs/msg/Imu'])
    from sensorscope.ui.sensor_tab import SensorTab

    tab = SensorTab(stream)  # keep the parent alive: it owns the analysis tab
    ana = tab.analysis
    ana.run_analysis()
    assert 'Need at least' in ana.status.text()
    ana._toggle_capture()  # start
    assert stream.capturing and ana.capture_btn.text() == 'Stop capture'
    ana._stop_capture()
    assert not stream.capturing


def test_threaded_analysis_path_used_by_the_stop_button(app):
    stream = SensorStream('/imu/data', REGISTRY['sensor_msgs/msg/Imu'])
    feed(stream, imu_capture(n=30_000))
    from sensorscope.ui.sensor_tab import SensorTab

    tab = SensorTab(stream)
    ana = tab.analysis
    ana.run_analysis()  # background QThread, like the real button
    assert not ana.analyze_btn.isEnabled()  # disabled while running
    assert ana._worker.wait(60_000), 'analysis thread did not finish within 60 s'
    for _ in range(20):  # deliver the queued 'done' signal
        app.processEvents()
        if ana.result is not None or ana.analyze_btn.isEnabled():
            break
    reason = ana.warn_box.toPlainText() or ana.status.text()
    assert ana.result is not None, 'analysis returned no result: ' + reason
    assert ana.analyze_btn.isEnabled()
    assert ana.status.text() == 'Analysis updated.'


def test_threaded_analysis_reports_errors(app):
    stream = SensorStream('/scan', REGISTRY['sensor_msgs/msg/LaserScan'])
    feed(stream, lidar_capture(n_scans=5))
    from sensorscope.ui.sensor_tab import SensorTab

    tab = SensorTab(stream)
    ana = tab.analysis
    ana.auto_chk.setChecked(False)
    ana.center_spin.setValue(0.0)
    ana.width_spin.setValue(4.0)  # 4 deg at 1 deg/beam: 4-5 beams, still fine
    ana.run_analysis()
    ana._worker.wait(20_000)
    app.processEvents()
    assert ana.result is not None
    # an impossible sector (no beams) must produce a readable error, not a crash
    stream2 = SensorStream('/scan', REGISTRY['sensor_msgs/msg/LaserScan'])
    feed(stream2, lidar_capture(n_scans=2 + 3))
    cap = stream2.capture_snapshot()
    for s in cap.extras:
        s.ranges[:] = np.inf  # every return invalid
    stream2.capture.__dict__['_extras'] = list(cap.extras)
    tab2 = SensorTab(stream2)
    tab2.analysis.run_analysis()
    tab2.analysis._worker.wait(20_000)
    app.processEvents()
    assert (
        tab2.analysis.result is None
        and 'fewer than 3 good beams' in tab2.analysis.warn_box.toPlainText()
    )


# ---------------------------------------------------------------- Help menu
def test_help_menu_and_window_title(app, monkeypatch):
    from PySide6 import QtGui

    from sensorscope import about

    opened = []
    monkeypatch.setattr(
        QtGui.QDesktopServices,
        'openUrl',
        staticmethod(lambda url: opened.append(url.toString()) or True),
    )
    win = MainWindow(FakeSource({}))
    assert win.windowTitle() == 'SensorScope 0.2.0'
    labels = [a.text().replace('&', '') for a in win.help_menu.actions() if not a.isSeparator()]
    assert labels == [
        'Quick start',
        'Analysis guide (online)',
        'GitHub repository',
        'Report an issue',
        'About SensorScope',
    ]
    win.repo_action.trigger()
    win.issue_action.trigger()
    win.guide_action.trigger()
    assert opened == [about.REPO_URL, about.ISSUES_URL, about.DOCS_URL]
    win.close()


def test_about_and_quick_start_dialog_text(app):
    from sensorscope.ui.help_dialogs import AboutDialog, QuickStartDialog

    about_dialog = AboutDialog()  # keep a reference: Qt deletes children with the parent
    about_text = about_dialog.browser.toPlainText()
    for needle in (
        'Version 0.2.0',
        'Vishal Gaud (@ilovevampire)',
        'https://github.com/ilovevampire/sensorscope',
        'Apache License 2.0',
        'pyqtgraph',
    ):
        assert needle in about_text, needle
    assert 'https://github.com/ilovevampire' in about_dialog.browser.toHtml()  # clickable links
    quick_dialog = QuickStartDialog()
    quick = quick_dialog.browser.toPlainText()
    for needle in ('Start capture', 'Copy Kalibr YAML', 'ros2 run sensorscope report'):
        assert needle in quick, needle


def test_placeholder_mentions_help(app):
    win = MainWindow(FakeSource({}))
    assert 'Help > Quick start' in win.placeholder.text()
    win.close()
