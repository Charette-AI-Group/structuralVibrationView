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
