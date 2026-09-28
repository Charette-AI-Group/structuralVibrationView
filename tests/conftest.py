"""Shared pytest configuration."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from structuralVibrationView import appConfig


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolatedSettings(tmp_path, monkeypatch):
    """Keep tests out of the real %APPDATA% settings file."""
    monkeypatch.setattr(appConfig, "settingsFile", tmp_path / "settings.ini")


@pytest.fixture(autouse=True)
def restoreColorScheme(qapp):
    """A forced colour scheme is global; put it back after every test."""
    yield
    qapp.styleHints().unsetColorScheme()


@pytest.fixture
def observableColorScheme(qapp) -> bool:
    """Whether this platform plugin reports a forced colour scheme back.

    The offscreen plugin accepts setColorScheme and then still answers
    Unknown, and createNewApp runs the suite that way - so asserting on what
    Qt ended up painting with would fail a brand new app over something that
    works. Tests that want to observe the result skip when this is False; what
    the service actually does is covered separately, with no platform involved.
    """
    hints = qapp.styleHints()
    hints.setColorScheme(Qt.ColorScheme.Dark)
    supported = hints.colorScheme() == Qt.ColorScheme.Dark
    hints.unsetColorScheme()
    return supported


@pytest.fixture(scope="session")
def modernOpenGl(qapp) -> bool:
    """Whether this machine can give VTK the OpenGL it draws through.

    A build runner has no graphics card and answers with Windows' own 1.1
    implementation, which VTK cannot use: showing the 3D view there takes the
    process down inside initializeGL rather than raising something a test
    could catch. So the tests that put a window on screen ask first.
    """
    from PySide6.QtGui import QOffscreenSurface, QOpenGLContext

    surface = QOffscreenSurface()
    surface.create()
    context = QOpenGLContext()
    if not context.create() or not context.makeCurrent(surface):
        return False
    version = context.format().version()
    context.doneCurrent()
    return version >= (3, 2)


@pytest.fixture
def onScreen(modernOpenGl):
    """For a test that shows a window: skip where nothing can draw one."""
    if not modernOpenGl:
        pytest.skip("this machine has no OpenGL 3.2, so VTK cannot draw a window")
