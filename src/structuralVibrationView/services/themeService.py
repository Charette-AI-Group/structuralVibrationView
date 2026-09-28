"""Application colour theme.

By default the app follows the Windows light/dark setting. The user can
override it for this app alone, which is remembered between sessions.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from structuralVibrationView.services import settingsService

logger = logging.getLogger(__name__)

systemTheme = "system"
lightTheme = "light"
darkTheme = "dark"
themeChoices = (systemTheme, lightTheme, darkTheme)
themeLabels = {
    systemTheme: "Use &System Theme",
    lightTheme: "&Light",
    darkTheme: "&Dark",
}

themeKey = "appearance/theme"


def loadTheme() -> str:
    value = settingsService.openSettings().value(themeKey, systemTheme)
    return value if value in themeChoices else systemTheme


def saveTheme(theme: str) -> None:
    settingsService.writeValue(themeKey, theme)


def applyTheme(theme: str) -> None:
    """Force Qt's colour scheme, or hand control back to Windows."""
    hints = QGuiApplication.styleHints()
    if not hasattr(hints, "setColorScheme"):  # pragma: no cover - needs Qt < 6.8
        logger.warning("This Qt build cannot override the colour scheme")
        return
    if theme == lightTheme:
        hints.setColorScheme(Qt.ColorScheme.Light)
    elif theme == darkTheme:
        hints.setColorScheme(Qt.ColorScheme.Dark)
    else:
        hints.unsetColorScheme()


def currentColorScheme() -> Qt.ColorScheme:
    """What Qt is actually painting with right now, override or not."""
    return QGuiApplication.styleHints().colorScheme()
