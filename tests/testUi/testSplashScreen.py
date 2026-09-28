"""Tests for the startup splash screen."""

from __future__ import annotations

import structuralVibrationView.main as entry
from structuralVibrationView import appConfig
from structuralVibrationView.ui import splashScreen


def testTheSplashCarriesTheAppsNameAndIcon(qapp) -> None:
    splash = splashScreen.makeSplash()

    try:
        assert splash is not None
        assert splash.isVisible()
        assert splash.width() == splashScreen.splashWidth
        assert splash.height() == splashScreen.splashHeight
        assert not splash.pixmap.isNull()
    finally:
        splash.close()


def testItCanBeSwitchedOff(qapp, monkeypatch) -> None:
    monkeypatch.setenv(appConfig.noSplashEnvVar, "1")

    assert splashScreen.splashDisabled()
    assert splashScreen.makeSplash() is None


def testWithoutASplashTheHelpersDoNothing(qapp) -> None:
    """main() calls these whether or not there is a splash to call them on."""
    splashScreen.report(None, "Loading...")
    splashScreen.finish(None, qapp.activeWindow())


def testTheSplashIsTakenDownAsTheWindowAppears(qapp, qtbot, onScreen) -> None:
    from PySide6.QtWidgets import QWidget

    splash = splashScreen.makeSplash()
    window = QWidget()
    qtbot.addWidget(window)
    splashScreen.report(splash, "Loading 3D graphics...")
    assert splash.message == "Loading 3D graphics..."
    window.show()

    splashScreen.finish(splash, window)

    assert not splash.isVisible()


def testTheWindowIsImportedOnlyAfterTheSplashIsUp() -> None:
    """The point of the splash: the wait it covers must come after it."""
    assert not hasattr(entry, "MainWindow")
    source = entry.main.__code__.co_consts
    assert any("Loading 3D graphics" in c for c in source if isinstance(c, str))


def testTheSplashIsCheapToPutUp(qapp) -> None:
    """Qt's own QSplashScreen takes about a second here, which defeats it."""
    import time

    started = time.perf_counter()
    splash = splashScreen.makeSplash()
    elapsed = time.perf_counter() - started

    try:
        assert splash is not None
        assert elapsed < 0.5, f"the splash took {elapsed:.2f} s to appear"
    finally:
        splash.close()


def testTheTitleFitsBesideTheIcon(qapp) -> None:
    """A title wider than its space would be clipped mid-word."""
    from PySide6.QtGui import QFont, QFontMetrics

    font = QFont()
    font.setPointSize(18)
    font.setWeight(QFont.Weight.Bold)
    left = 28 + splashScreen.artworkSize + 24

    needed = QFontMetrics(font).horizontalAdvance(appConfig.appName)

    assert needed <= splashScreen.splashWidth - left - 20
