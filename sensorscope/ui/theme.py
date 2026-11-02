"""Dark theme for Qt widgets and pyqtgraph. Call before creating any window."""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets
import pyqtgraph as pg


def apply_dark_theme(app: QtWidgets.QApplication) -> None:
    app.setStyle("Fusion")
    role = QtGui.QPalette.ColorRole
    pal = QtGui.QPalette()
    colors = {
        role.Window: "#1e2126", role.WindowText: "#d7dae0",
        role.Base: "#14171b", role.AlternateBase: "#1e2126",
        role.ToolTipBase: "#2b2f36", role.ToolTipText: "#d7dae0",
        role.Text: "#d7dae0", role.Button: "#2b2f36", role.ButtonText: "#d7dae0",
        role.BrightText: "#ff5555", role.Highlight: "#3d8bfd",
        role.HighlightedText: "#ffffff",
    }
    for r, c in colors.items():
        pal.setColor(r, QtGui.QColor(c))
    app.setPalette(pal)
    pg.setConfigOptions(background="#14171b", foreground="#c9d1d9", antialias=False)
