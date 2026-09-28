"""Tab widget whose tabs share the full width equally, labels centred.

The open tab is marked the way the other Charette AI Group apps mark it: ink
on the surface, underlined in the accent colour, with the others quiet - not
left to a hairline that reads as part of the background. Top-level tabs get
labels a little larger than the interface's text; tabs inside a panel keep
the interface's own size so they read as part of it.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, QTimer
from PySide6.QtGui import QFont, QGuiApplication, QResizeEvent
from PySide6.QtWidgets import QApplication, QTabBar, QTabWidget, QWidget

from structuralVibrationView.ui.theme import currentTokens

topLevelScale = 1.15  # of the interface's own text size
underline = 3  # px under the open tab


class FullWidthTabBar(QTabBar):
    def tabSizeHint(self, index: int) -> QSize:
        size = super().tabSizeHint(index)
        tabWidget = self.parentWidget()
        if self.count() and tabWidget is not None:
            size.setWidth(tabWidget.width() // self.count())
        return size


class FullWidthTabWidget(QTabWidget):
    def __init__(
        self, parent: QWidget | None = None, labelScale: float = topLevelScale
    ) -> None:
        """labelScale: label size against the interface's text; 1.0 inside a panel."""
        super().__init__(parent)
        self.setTabBar(FullWidthTabBar(self))
        font = QFont()
        font.setPointSizeF(font.pointSizeF() * labelScale)
        font.setWeight(QFont.Weight.DemiBold)
        self.tabBar().setFont(font)
        self.applyTheme()
        # Connected to a method, so Qt drops the connection with the widget.
        QGuiApplication.styleHints().colorSchemeChanged.connect(self.onColorSchemeChanged)

    def applyTheme(self) -> None:
        """The open tab in ink on the surface, underlined in the accent; the rest quiet."""
        tokens = currentTokens()
        self.tabBar().setStyleSheet(
            "QTabBar::tab {"
            f"color: {tokens.secondaryInk};"
            f"background: {tokens.gridline};"
            f"border: none; border-bottom: {underline}px solid {tokens.gridline};"
            "padding: 5px 10px;"
            "}"
            "QTabBar::tab:hover {"
            f"color: {tokens.primaryInk};"
            "}"
            "QTabBar::tab:selected {"
            f"color: {tokens.primaryInk};"
            f"background: {tokens.surface};"
            f"border-bottom: {underline}px solid {tokens.accent};"
            "}"
        )

    def onColorSchemeChanged(self, *_args: object) -> None:
        # The signal arrives before Qt has rebuilt the application palette, so
        # the refresh waits one turn of the event loop for it.
        QTimer.singleShot(0, self.refreshTheme)

    def refreshTheme(self) -> None:
        """Take the new palette and restyle the open-tab highlight to match.

        A styled tab bar stops Qt handing theme changes down through this
        widget, so without the explicit palette the pages keep the old
        theme's colours while the rest of the window changes.
        """
        self.setPalette(QApplication.palette())
        self.applyTheme()

    def resizeEvent(self, event: QResizeEvent) -> None:
        # Tab widths derive from the widget width, so a resize must make the
        # tab bar re-query its size hints. QTabBar has no public relayout;
        # re-setting the icon size is the standard way to force one.
        super().resizeEvent(event)
        tabBar = self.tabBar()
        tabBar.setIconSize(tabBar.iconSize())
