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

"""Dark theme for Qt widgets and pyqtgraph. Call before creating any window."""

from __future__ import annotations

import pyqtgraph as pg
from PySide6 import QtGui, QtWidgets


def apply_dark_theme(app: QtWidgets.QApplication) -> None:
    app.setStyle('Fusion')
    role = QtGui.QPalette.ColorRole
    pal = QtGui.QPalette()
    colors = {
        role.Window: '#1e2126',
        role.WindowText: '#d7dae0',
        role.Base: '#14171b',
        role.AlternateBase: '#1e2126',
        role.ToolTipBase: '#2b2f36',
        role.ToolTipText: '#d7dae0',
        role.Text: '#d7dae0',
        role.Button: '#2b2f36',
        role.ButtonText: '#d7dae0',
        role.BrightText: '#ff5555',
        role.Highlight: '#3d8bfd',
        role.HighlightedText: '#ffffff',
    }
    for r, c in colors.items():
        pal.setColor(r, QtGui.QColor(c))
    app.setPalette(pal)
    pg.setConfigOptions(background='#14171b', foreground='#c9d1d9', antialias=False)
