"""MainWindow: one tab per discovered sensor topic."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from .. import __version__
from .sensor_tab import SensorTab

FRAME_MS = 33         # plot refresh (~30 fps)
STATS_EVERY = 8       # numeric stats refresh every N frames (~4 Hz)
DISCOVERY_MS = 1000   # how often to check for newly discovered topics


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, source) -> None:
        """``source`` is any object with ``get_streams() -> {topic: SensorStream}``."""
        super().__init__()
        self.source = source
        self._tabs = {}
        self._frame = 0
        self.setWindowTitle(f"SensorScope {__version__}")
        self.resize(1280, 800)

        self.placeholder = QtWidgets.QLabel(
            "Waiting for sensor topics…\n\n"
            "Supported: sensor_msgs/Imu, LaserScan, NavSatFix, nav_msgs/Odometry.\n"
            "No hardware? Run:  ros2 run sensorscope fake_sensors")
        self.placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setVisible(False)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(self.placeholder, 1)
        layout.addWidget(self.tab_widget, 1)
        self.setCentralWidget(central)

        file_menu = self.menuBar().addMenu("&File")
        quit_action = file_menu.addAction("&Quit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

        self._frame_timer = QtCore.QTimer(self, interval=FRAME_MS, timeout=self._on_frame)
        self._discovery_timer = QtCore.QTimer(self, interval=DISCOVERY_MS, timeout=self._sync_tabs)
        self._frame_timer.start()
        self._discovery_timer.start()
        self._sync_tabs()

    def _sync_tabs(self) -> None:
        for topic, stream in sorted(self.source.get_streams().items()):
            if topic in self._tabs:
                continue
            tab = SensorTab(stream)
            self._tabs[topic] = tab
            self.tab_widget.addTab(tab, f"{stream.spec.label}  {topic}")
        if self._tabs:
            self.placeholder.setVisible(False)
            self.tab_widget.setVisible(True)
        self.statusBar().showMessage(f"{len(self._tabs)} sensor topic(s) monitored")

    def _on_frame(self) -> None:
        self._frame += 1
        tab = self.tab_widget.currentWidget()
        if tab is not None:
            tab.refresh(update_stats=(self._frame % STATS_EVERY == 0))

    def closeEvent(self, event) -> None:
        self._frame_timer.stop()
        self._discovery_timer.stop()
        super().closeEvent(event)
