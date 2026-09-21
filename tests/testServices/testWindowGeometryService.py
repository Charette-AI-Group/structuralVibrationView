"""Tests for remembering the window position and size."""

from __future__ import annotations

from PySide6.QtCore import QByteArray

from transverseVibrationView.services import settingsService, windowGeometryService


def testNothingIsSavedOnAFirstRun() -> None:
    assert windowGeometryService.loadGeometry() is None


def testSavedGeometryComesBackUnchanged() -> None:
    blob = QByteArray(b"\x01\xd9\xd0\xcb\x00\x03geometry")

    windowGeometryService.saveGeometry(blob)

    assert windowGeometryService.loadGeometry() == blob


def testAnUnreadableValueIsIgnored() -> None:
    """A hand-edited INI must not stop the window opening."""
    settingsService.writeValue(windowGeometryService.geometryKey, "not geometry")

    assert windowGeometryService.loadGeometry() is None
