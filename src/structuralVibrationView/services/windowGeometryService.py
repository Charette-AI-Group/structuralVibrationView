"""Main window position and size, remembered between sessions.

Stored as Qt's own geometry blob, which carries the screen, the maximised
state and the normal size underneath it. Restoring it through
`QWidget.restoreGeometry` also pulls a window back onto a visible screen
when the monitor it was on has since been unplugged.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray

from structuralVibrationView.services import settingsService

geometryKey = "window/geometry"


def loadGeometry() -> QByteArray | None:
    """The saved geometry, or None on a first run or an unreadable value."""
    value = settingsService.openSettings().value(geometryKey)
    if isinstance(value, QByteArray) and not value.isEmpty():
        return value
    return None


def saveGeometry(geometry: QByteArray) -> None:
    settingsService.writeValue(geometryKey, geometry)
