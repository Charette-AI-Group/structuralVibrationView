"""Tests for the light/dark theme override."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from transverseVibrationView.services import themeService


class StubStyleHints:
    """Records what applyTheme asked Qt to do."""

    def __init__(self) -> None:
        self.scheme: Qt.ColorScheme | None = None
        self.unsetCalls = 0

    def setColorScheme(self, scheme: Qt.ColorScheme) -> None:
        self.scheme = scheme

    def unsetColorScheme(self) -> None:
        self.unsetCalls += 1


class StubApplication:
    def __init__(self, hints: StubStyleHints) -> None:
        self.hints = hints

    def styleHints(self) -> StubStyleHints:
        return self.hints


@pytest.fixture
def stubHints(monkeypatch) -> StubStyleHints:
    """Stand in for Qt, so the dispatch can be checked on any platform."""
    hints = StubStyleHints()
    monkeypatch.setattr(themeService, "QGuiApplication", StubApplication(hints))
    return hints


def testDefaultIsFollowTheSystem(qapp) -> None:
    assert themeService.loadTheme() == themeService.systemTheme


def testSaveAndLoadRoundTrip(qapp) -> None:
    themeService.saveTheme(themeService.darkTheme)

    assert themeService.loadTheme() == themeService.darkTheme


def testUnknownStoredValueFallsBackToSystem(qapp) -> None:
    themeService.saveTheme("chartreuse")

    assert themeService.loadTheme() == themeService.systemTheme


# --- what applyTheme asks Qt to do, checkable on any platform ---------------


def testLightForcesTheLightScheme(stubHints: StubStyleHints) -> None:
    themeService.applyTheme(themeService.lightTheme)

    assert stubHints.scheme == Qt.ColorScheme.Light
    assert stubHints.unsetCalls == 0


def testDarkForcesTheDarkScheme(stubHints: StubStyleHints) -> None:
    themeService.applyTheme(themeService.darkTheme)

    assert stubHints.scheme == Qt.ColorScheme.Dark
    assert stubHints.unsetCalls == 0


def testSystemReleasesTheOverride(stubHints: StubStyleHints) -> None:
    """Following the system means handing the choice back, not picking one."""
    themeService.applyTheme(themeService.systemTheme)

    assert stubHints.unsetCalls == 1
    assert stubHints.scheme is None


def testAnOlderQtIsToleratedRatherThanCrashing(monkeypatch) -> None:
    """Qt before 6.8 has no setColorScheme; the app must still start."""

    class AncientHints:
        pass

    monkeypatch.setattr(
        themeService, "QGuiApplication", StubApplication(AncientHints())
    )

    themeService.applyTheme(themeService.darkTheme)  # must not raise


# --- what Qt then paints with, where the platform can tell us ---------------


def testApplyLightAndDarkChangeThePalette(qapp, observableColorScheme) -> None:
    if not observableColorScheme:
        pytest.skip("this platform plugin does not report a colour scheme")

    themeService.applyTheme(themeService.lightTheme)
    assert themeService.currentColorScheme() == Qt.ColorScheme.Light
    lightWindow = qapp.palette().color(qapp.palette().ColorRole.Window)

    themeService.applyTheme(themeService.darkTheme)
    assert themeService.currentColorScheme() == Qt.ColorScheme.Dark
    darkWindow = qapp.palette().color(qapp.palette().ColorRole.Window)

    assert lightWindow.lightness() > darkWindow.lightness()
