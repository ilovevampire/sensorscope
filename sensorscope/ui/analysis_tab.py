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

"""AnalysisTab: capture controls, background analysis, warnings. Subclasses add the plots."""

from __future__ import annotations

import time
from typing import Callable

from PySide6 import QtCore, QtWidgets


class _Worker(QtCore.QThread):
    """Runs a function off the GUI thread; emits (result, error_text)."""

    done = QtCore.Signal(object, str)

    def __init__(self, fn: Callable, parent=None) -> None:
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            self.done.emit(self._fn(), '')
        except Exception as exc:  # noqa: BLE001 - report any failure to the user
            self.done.emit(None, str(exc))


class AnalysisTab(QtWidgets.QWidget):
    """
    Base class. Override ``guidance``, ``min_samples``, ``analyze`` and ``show_result``.

    Optional hooks: ``build_controls(row)`` to add widgets next to the buttons,
    ``make_job(cap)`` to read GUI settings on the GUI thread before analysing.
    """

    guidance = ''
    min_samples = 200

    def __init__(self, stream, parent=None) -> None:
        super().__init__(parent)
        self.stream = stream
        self.result = None
        self._worker = None
        self._t_start = None

        self.capture_btn = QtWidgets.QPushButton('Start capture')
        self.capture_btn.clicked.connect(self._toggle_capture)
        self.analyze_btn = QtWidgets.QPushButton('Analyze now')
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.save_btn = QtWidgets.QPushButton('Save capture…')
        self.save_btn.clicked.connect(self._save_capture)
        self.status = QtWidgets.QLabel('No capture yet.')

        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.capture_btn)
        row.addWidget(self.analyze_btn)
        row.addWidget(self.save_btn)
        self.build_controls(row)
        row.addStretch(1)
        row.addWidget(self.status)

        guide = QtWidgets.QLabel(self.guidance)
        guide.setWordWrap(True)
        guide.setStyleSheet('color: #9aa4b2;')

        self.warn_box = QtWidgets.QPlainTextEdit()
        self.warn_box.setReadOnly(True)
        self.warn_box.setMaximumHeight(84)
        self.warn_box.setPlaceholderText('Notes and warnings about the analysis appear here.')

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(guide)
        layout.addLayout(row)
        body = QtWidgets.QVBoxLayout()
        self.build_results(body)
        layout.addLayout(body, 1)
        layout.addWidget(self.warn_box)

        self._timer = QtCore.QTimer(self, interval=500, timeout=self._tick)
        self._timer.start()

    # -- hooks for subclasses ----------------------------------------------------
    def build_controls(self, row: QtWidgets.QHBoxLayout) -> None:
        pass

    def build_results(self, layout: QtWidgets.QVBoxLayout) -> None:
        raise NotImplementedError

    def analyze(self, cap):
        raise NotImplementedError

    def show_result(self, result) -> None:
        raise NotImplementedError

    def make_job(self, cap) -> Callable:
        return lambda: self.analyze(cap)

    # -- capture lifecycle ---------------------------------------------------------
    def _toggle_capture(self) -> None:
        if not self.stream.capturing:
            self.stream.start_capture()
            self._t_start = time.monotonic()
            self.capture_btn.setText('Stop capture')
        else:
            self._stop_capture()
            self.run_analysis()

    def _stop_capture(self) -> None:
        self.stream.stop_capture()
        self.capture_btn.setText('Start capture')

    def _tick(self) -> None:
        cap = self.stream.capture
        if cap is None:
            return
        if self.stream.capturing:
            if cap.full:
                self._stop_capture()
                self.status.setText(f'Capture buffer full ({cap.n:,} samples). Stopped.')
                self.run_analysis()
                return
            elapsed = time.monotonic() - (self._t_start or time.monotonic())
            self.status.setText(f'Capturing… {elapsed:,.0f} s, {cap.n:,} samples')

    # -- analysis ------------------------------------------------------------------
    def run_analysis(self) -> None:
        """Analyse the capture so far on a background thread."""
        cap = self.stream.capture_snapshot()
        if cap is None or cap.n < self.min_samples:
            have = 0 if cap is None else cap.n
            self.status.setText(
                f'Need at least {self.min_samples} samples (have {have}). Start a capture first.'
            )
            return
        if self._worker is not None and self._worker.isRunning():
            return
        self.analyze_btn.setEnabled(False)
        self.status.setText(f'Analysing {cap.n:,} samples…')
        self._worker = _Worker(self.make_job(cap), self)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def analyze_sync(self) -> None:
        """Run the analysis in the calling thread, blocking (used by tests and scripts)."""
        cap = self.stream.capture_snapshot()
        if cap is None or cap.n < self.min_samples:
            raise ValueError('not enough samples captured')
        self._apply(self.make_job(cap)())

    def _on_done(self, result, error: str) -> None:
        self.analyze_btn.setEnabled(True)
        if error:
            self.status.setText('Analysis failed.')
            self.warn_box.setPlainText(error)
            return
        self._apply(result)

    def _apply(self, result) -> None:
        self.result = result
        self.show_result(result)
        self.warn_box.setPlainText('\n'.join('• ' + w for w in getattr(result, 'warnings', [])))
        self.status.setText('Analysis updated.')

    def _save_capture(self) -> None:
        cap = self.stream.capture_snapshot()
        if cap is None or cap.n == 0:
            self.status.setText('Nothing to save yet.')
            return
        default = self.stream.topic.strip('/').replace('/', '_') + '_capture.csv'
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save capture', default, 'CSV (*.csv)'
        )
        if path:
            rows = cap.to_csv(path)
            self.status.setText(f'Saved {rows:,} rows.')

    def closeEvent(self, event) -> None:  # pragma: no cover - GUI shutdown
        self._timer.stop()
        super().closeEvent(event)
