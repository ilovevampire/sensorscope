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

"""Help menu dialogs: About and Quick start."""

from __future__ import annotations

import html

from PySide6 import QtCore, QtGui, QtWidgets

from .. import about


def open_url(url: str) -> bool:
    """Open a URL in the default browser."""
    return QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))


def about_html() -> str:
    """Return the About text as rich text."""
    rows = ''.join(
        f"<li><a href='{u}'>{html.escape(n)}</a>, {html.escape(lic)}</li>"
        for n, lic, u in about.THIRD_PARTY
    )
    return (
        f'<h2>{about.NAME}</h2>'
        f'<p>{html.escape(about.TAGLINE)}</p>'
        f'<p><b>Version {about.VERSION}</b></p>'
        f"<p>Author: <a href='{about.AUTHOR_URL}'>{html.escape(about.AUTHOR)} "
        f'({html.escape(about.AUTHOR_HANDLE)})</a></p>'
        f"<p>Source code: <a href='{about.REPO_URL}'>{about.REPO_URL}</a><br>"
        f'Report a bug or request a feature: '
        f"<a href='{about.ISSUES_URL}'>{about.ISSUES_URL}</a></p>"
        f'<p>License: {html.escape(about.LICENSE_NAME)}<br>{html.escape(about.COPYRIGHT)}</p>'
        f'<p>Built with:</p><ul>{rows}</ul>'
    )


def quick_start_html() -> str:
    """Return the Quick start text as rich text."""
    steps = ''.join(
        f"<li><b>{html.escape(t if t.endswith('?') else t + '.')}</b> {html.escape(body)}</li>"
        for t, body in about.QUICK_START
    )
    return (
        f'<h2>Quick start</h2><ol>{steps}</ol>'
        f"<p>Full guide: <a href='{about.DOCS_URL}'>analysis documentation</a></p>"
    )


class _HtmlDialog(QtWidgets.QDialog):
    """Dialog that shows rich text with clickable links."""

    def __init__(self, title: str, body_html: str, parent=None, size=(560, 520)) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(*size)
        self.browser = QtWidgets.QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.document().setDefaultStyleSheet('a { color: #4fc3f7; }')  # readable on dark
        self.browser.setHtml(body_html)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.browser)
        layout.addWidget(buttons)


class AboutDialog(_HtmlDialog):
    """Version, author, links and licences."""

    def __init__(self, parent=None) -> None:
        super().__init__(f'About {about.NAME}', about_html(), parent, size=(520, 560))


class QuickStartDialog(_HtmlDialog):
    """Short usage guide."""

    def __init__(self, parent=None) -> None:
        super().__init__(f'{about.NAME} quick start', quick_start_html(), parent)
