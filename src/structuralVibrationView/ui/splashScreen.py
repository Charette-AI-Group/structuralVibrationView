"""The splash screen, shown while the heavy imports happen.

Starting the app takes about two seconds, and almost none of it is Qt:
PySide6 costs about 0.2 s, while importing the main window drags in PyVista
and VTK for another 1.1 s and building the first 3D scene takes 0.7 s more.
So Qt is up and able to draw long before there is anything to show, which is
exactly the gap a splash screen is for.

That only works if the main window is imported *after* the splash is on
screen - see `structuralVibrationView.main.main`. Importing it at module
scope spends the whole wait before `main` runs, and leaves nothing to show
it with.

The splash is a frameless window of our own rather than Qt's QSplashScreen:
measured here, QSplashScreen takes about 1.0 s to appear whatever it holds,
while this takes 0.02 s. A splash that costs a second of the wait it exists
to cover is worse than none.

Set the environment variable named by `appConfig.noSplashEnvVar` to 1 to
skip it; screenshot tooling and anyone who finds it irritating can then
start straight into the window.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from structuralVibrationView import appConfig

# The icon's tile, so the two are recognisably one thing.
backgroundTop = QColor("#4A3AA7")
backgroundBottom = QColor("#15103A")
titleColour = QColor("#FFFFFF")
subtleColour = QColor("#C3C2D8")

splashWidth, splashHeight = 480, 240
artworkSize = 112
cornerRadius = 16


def splashDisabled() -> bool:
    return os.environ.get(appConfig.noSplashEnvVar, "") == "1"


def artwork() -> QPixmap:
    """Drawn rather than loaded, so it needs no file beyond the icon."""
    pixmap = QPixmap(splashWidth, splashHeight)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    background = QLinearGradient(0, 0, 0, splashHeight)
    background.setColorAt(0.0, backgroundTop)
    background.setColorAt(1.0, backgroundBottom)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(background)
    painter.drawRoundedRect(0, 0, splashWidth, splashHeight, cornerRadius, cornerRadius)

    if appConfig.iconFile.is_file():
        # QIcon, not QPixmap: a .ico holds seven sizes and QPixmap picks a
        # small one, which then has to be scaled *up* and turns to mush.
        # QIcon.pixmap chooses the best entry and scales down.
        icon = QIcon(str(appConfig.iconFile)).pixmap(artworkSize, artworkSize)
        if not icon.isNull():
            painter.drawPixmap(28, (splashHeight - icon.height()) // 2 - 16, icon)

    left = 28 + artworkSize + 24
    painter.setPen(titleColour)
    font = painter.font()
    font.setPointSize(18)
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    # One line: measured at 18 pt it fits the space beside the icon.
    painter.drawText(left, 112, appConfig.appName)

    painter.setPen(subtleColour)
    font.setPointSize(9)
    font.setWeight(QFont.Weight.Normal)
    painter.setFont(font)
    painter.drawText(left, 140, f"Version {appConfig.appVersion}")
    painter.drawText(left, 158, appConfig.copyrightHolder)
    painter.end()
    return pixmap


class SplashWindow(QWidget):
    """The artwork, centred on screen, with a line of progress along the bottom."""

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            # Not decoration alone: this flag is also what makes the window
            # cheap to put up, and keeps it off the taskbar.
            | Qt.WindowType.SplashScreen,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("splashWindow")
        self.pixmap = artwork()
        self.message = ""
        self.resize(splashWidth, splashHeight)
        self.centreOnScreen()

    def centreOnScreen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is not None:
            self.move(screen.availableGeometry().center() - self.rect().center())

    def showMessage(self, message: str) -> None:
        self.message = message
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        if self.message:
            painter.setPen(subtleColour)
            font = painter.font()
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(28, splashHeight - 22, self.message)
        painter.end()


def makeSplash() -> SplashWindow | None:
    """The splash, already shown, or None if it is switched off."""
    if splashDisabled():
        return None
    splash = SplashWindow()
    splash.show()
    QApplication.processEvents()  # painted now, not after the imports below
    return splash


def report(splash: SplashWindow | None, message: str) -> None:
    """Say what is happening, and let Qt actually paint it."""
    if splash is None:
        return
    splash.showMessage(message)
    QApplication.processEvents()


def finish(splash: SplashWindow | None, window: QWidget) -> None:
    """Take the splash down as the window appears, not a moment before."""
    if splash is not None:
        splash.close()
        splash.deleteLater()
        window.raise_()
        window.activateWindow()
