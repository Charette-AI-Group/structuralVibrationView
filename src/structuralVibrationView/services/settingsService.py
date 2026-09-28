"""Shared access to the app's INI settings file."""

from __future__ import annotations

import logging
import shutil

from PySide6.QtCore import QSettings

from structuralVibrationView import appConfig

logger = logging.getLogger(__name__)


def openSettings() -> QSettings:
    return QSettings(str(appConfig.settingsFile), QSettings.Format.IniFormat)


def writeValue(key: str, value: object) -> None:
    appConfig.settingsFile.parent.mkdir(parents=True, exist_ok=True)
    settings = openSettings()
    settings.setValue(key, value)
    settings.sync()


def adoptLegacySettings() -> bool:
    """Take over the settings the app wrote under its former name.

    Only on a first run under the new name, and only as a copy: the old file
    is left alone, so an older build of the app still finds its own.
    """
    if appConfig.settingsFile.exists() or not appConfig.legacySettingsFile.is_file():
        return False
    try:
        appConfig.settingsFile.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(appConfig.legacySettingsFile, appConfig.settingsFile)
    except OSError as error:  # the app opens with its defaults instead
        logger.warning("Could not adopt the settings from %s: %s",
                       appConfig.legacyAppName, error)
        return False
    return True
