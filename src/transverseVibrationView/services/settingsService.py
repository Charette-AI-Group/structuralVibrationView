"""Shared access to the app's INI settings file."""

from __future__ import annotations

from PySide6.QtCore import QSettings

from transverseVibrationView import appConfig


def openSettings() -> QSettings:
    return QSettings(str(appConfig.settingsFile), QSettings.Format.IniFormat)


def writeValue(key: str, value: object) -> None:
    appConfig.settingsFile.parent.mkdir(parents=True, exist_ok=True)
    settings = openSettings()
    settings.setValue(key, value)
    settings.sync()
