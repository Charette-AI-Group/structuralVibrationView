"""Tests for the shared settings file."""

from __future__ import annotations

from structuralVibrationView import appConfig
from structuralVibrationView.services import settingsService


def testAFirstRunAdoptsWhatTheOldNameRemembered(tmp_path, monkeypatch) -> None:
    legacy = tmp_path / "old" / "settings.ini"
    legacy.parent.mkdir()
    legacy.write_text("[appearance]\ntheme=dark\n", encoding="utf-8")
    monkeypatch.setattr(appConfig, "legacySettingsFile", legacy)
    monkeypatch.setattr(appConfig, "settingsFile", tmp_path / "new" / "settings.ini")

    assert settingsService.adoptLegacySettings()

    assert settingsService.openSettings().value("appearance/theme") == "dark"
    # Taken as a copy: an older build still finds its own file.
    assert legacy.is_file()


def testSettingsOfItsOwnAreLeftAlone(tmp_path, monkeypatch) -> None:
    legacy = tmp_path / "old" / "settings.ini"
    legacy.parent.mkdir()
    legacy.write_text("[appearance]\ntheme=dark\n", encoding="utf-8")
    current = tmp_path / "new" / "settings.ini"
    current.parent.mkdir()
    current.write_text("[appearance]\ntheme=light\n", encoding="utf-8")
    monkeypatch.setattr(appConfig, "legacySettingsFile", legacy)
    monkeypatch.setattr(appConfig, "settingsFile", current)

    assert not settingsService.adoptLegacySettings()

    assert settingsService.openSettings().value("appearance/theme") == "light"


def testNothingToAdoptIsNotAFailure(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(appConfig, "legacySettingsFile", tmp_path / "gone" / "settings.ini")
    monkeypatch.setattr(appConfig, "settingsFile", tmp_path / "new" / "settings.ini")

    assert not settingsService.adoptLegacySettings()
