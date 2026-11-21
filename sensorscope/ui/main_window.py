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

"""MainWindow: one tab per discovered sensor topic."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .help_dialogs import AboutDialog, open_url, QuickStartDialog
from .sensor_tab import SensorTab
from .. import about

FRAME_MS = 33  # plot refresh (~30 fps)
STATS_EVERY = 8  # numeric stats refresh every N frames (~4 Hz)
DISCOVERY_MS = 1000  # how often to check for newly discovered topics


class MainWindow(QtWidgets.QMainWindow):
    """Top-level window with one tab per sensor topic and a Help menu."""

    def __init__(self, source) -> None:
        """Create the window. ``source`` needs ``get_streams() -> {topic: SensorStream}``."""
        super().__init__()
        self.source = source
        self._tabs = {}
        self._frame = 0
        self.setWindowTitle(f'{about.NAME} {about.VERSION}')
        self.resize(1280, 800)

        self.placeholder = QtWidgets.QLabel(
            'Waiting for sensor topics…\n\n'
            'Supported: sensor_msgs/Imu, LaserScan, NavSatFix, nav_msgs/Odometry.\n'
            'No hardware? Run:  ros2 launch sensorscope demo.launch.py\n'
            'Need help? Open Help > Quick start (F1).'
        )
        self.placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setVisible(False)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(self.placeholder, 1)
        layout.addWidget(self.tab_widget, 1)
        self.setCentralWidget(central)

        self._build_menus()

        self._frame_timer = QtCore.QTimer(self, interval=FRAME_MS, timeout=self._on_frame)
        self._discovery_timer = QtCore.QTimer(self, interval=DISCOVERY_MS, timeout=self._sync_tabs)
        self._frame_timer.start()
        self._discovery_timer.start()
        self._sync_tabs()

    # -- menus --------------------------------------------------------------------
    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu('&File')
        quit_action = file_menu.addAction('&Quit')
        quit_action.setShortcut('Ctrl+Q')
        quit_action.triggered.connect(self.close)

        self.help_menu = self.menuBar().addMenu('&Help')
        self.quick_action = self.help_menu.addAction('&Quick start')
        self.quick_action.setShortcut(QtGui.QKeySequence.StandardKey.HelpContents)
        self.quick_action.triggered.connect(self.show_quick_start)
        self.guide_action = self.help_menu.addAction('Analysis &guide (online)')
        self.guide_action.triggered.connect(lambda: open_url(about.DOCS_URL))
        self.help_menu.addSeparator()
        self.repo_action = self.help_menu.addAction('&GitHub repository')
        self.repo_action.triggered.connect(lambda: open_url(about.REPO_URL))
        self.issue_action = self.help_menu.addAction('&Report an issue')
        self.issue_action.triggered.connect(lambda: open_url(about.ISSUES_URL))
        self.help_menu.addSeparator()
        self.about_action = self.help_menu.addAction(f'&About {about.NAME}')
        self.about_action.triggered.connect(self.show_about)

    def show_quick_start(self) -> None:
        """Show the Quick start dialog."""
        QuickStartDialog(self).exec()

    def show_about(self) -> None:
        """Show the About dialog."""
        AboutDialog(self).exec()

    # -- tabs ---------------------------------------------------------------------
    def _sync_tabs(self) -> None:
        for topic, stream in sorted(self.source.get_streams().items()):
            if topic in self._tabs:
                continue
            tab = SensorTab(stream)
            self._tabs[topic] = tab
            self.tab_widget.addTab(tab, f'{stream.spec.label}  {topic}')
        if self._tabs:
            self.placeholder.setVisible(False)
            self.tab_widget.setVisible(True)
        self.statusBar().showMessage(f'{len(self._tabs)} sensor topic(s) monitored')

    def _on_frame(self) -> None:
        self._frame += 1
        tab = self.tab_widget.currentWidget()
        if tab is not None:
            tab.refresh(update_stats=(self._frame % STATS_EVERY == 0))

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """Stop timers before closing."""
        self._frame_timer.stop()
        self._discovery_timer.stop()
        super().closeEvent(event)
