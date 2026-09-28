"""Base class for a view that tells the window how things are going.

Views should not own the status bar or open dialogs themselves: a view does
not know whether it is a tab, a panel, or the whole window, and two of those
have no status bar to write to. It says what happened; the window decides
where that goes.

Inherit from this for tabs and panels, and hand each one to
`MainWindow.connectView`. Unused until you add a view of your own.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from structuralVibrationView.ui.dialogs.errorDialog import headlineOf


class ReportingView(QWidget):
    """A view that reports status and failures without deciding how to show them."""

    # Ordinary progress: "Saved 3 items", "Connecting...".
    statusMessage = Signal(str)
    # Failures, as (title, whole message). Too long for a status bar by nature.
    errorMessage = Signal(str, str)

    def reportStatus(self, message: str) -> None:
        self.statusMessage.emit(message)

    def reportError(self, title: str, message: str) -> None:
        """A headline on the bar, the whole thing in a dialog.

        The bar elides, and what it elides is the end of the message - which is
        where a failure keeps the part worth acting on. Both go out together so
        no caller has to remember to do both.
        """
        self.statusMessage.emit(headlineOf(message))
        self.errorMessage.emit(title, message)
