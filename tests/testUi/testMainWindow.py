"""Smoke tests for the main window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from transverseVibrationView import appConfig
from transverseVibrationView.services import themeService
from transverseVibrationView.ui.mainWindow import MainWindow


def testMainWindowOpens(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.show()

    assert mainWindow.isVisible()
    assert mainWindow.windowTitle() == "Transverse Structural Vibration View"
    # The bar says what is on screen from the first frame, not "Ready".
    assert mainWindow.statusBar().currentMessage().startswith("Cantilever Beam: Mode 1")


def testTheVibrationViewIsTheCentralWidgetAndReportsToTheBar(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.show()

    assert mainWindow.centralWidget() is mainWindow.vibrationView
    assert mainWindow.vibrationView.isPlaying()

    mainWindow.vibrationView.controls.playButton.click()

    assert mainWindow.statusBar().currentMessage().startswith("Paused")


def testClosingTheWindowStopsTheAnimation(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.show()

    mainWindow.close()

    assert not mainWindow.vibrationView.isPlaying()


def testMenuBarStructure(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    menuTitles = [action.text() for action in mainWindow.menuBar().actions()]
    assert menuTitles == ["&File", "&Help"]

    fileItems = [a.text() for a in mainWindow.fileMenu.actions() if not a.isSeparator()]
    assert fileItems == ["&New", "&Open...", "&Save", "E&xit"]
    assert any(a.isSeparator() for a in mainWindow.fileMenu.actions())

    helpItems = [a.text() for a in mainWindow.helpMenu.actions() if not a.isSeparator()]
    assert helpItems == ["&Theme", "User &Manual...", "&About"]


def testThemeMenuOffersSystemLightDark(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    labels = [a.text() for a in mainWindow.themeMenu.actions()]
    assert labels == ["Use &System Theme", "&Light", "&Dark"]
    assert all(a.isCheckable() for a in mainWindow.themeMenu.actions())
    assert mainWindow.themeGroup.isExclusive()
    # Following Windows is the default.
    assert mainWindow.themeActions[themeService.systemTheme].isChecked()


def testChoosingDarkAppliesAndRemembersIt(qtbot, observableColorScheme) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    mainWindow.themeActions[themeService.darkTheme].trigger()

    # The window's own job: remember the choice and say so.
    assert themeService.loadTheme() == themeService.darkTheme
    assert "Dark theme applied" in mainWindow.statusBar().currentMessage()
    # Whether Qt then paints dark is only observable on some platforms.
    if observableColorScheme:
        assert themeService.currentColorScheme() == Qt.ColorScheme.Dark


def testSavedThemeIsRestoredOnNextLaunch(qtbot) -> None:
    first = MainWindow()
    qtbot.addWidget(first)
    first.themeActions[themeService.lightTheme].trigger()

    reopened = MainWindow()
    qtbot.addWidget(reopened)

    assert reopened.themeActions[themeService.lightTheme].isChecked()


def testFileMenuPlaceholdersUpdateStatus(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    mainWindow.newAction.trigger()
    assert mainWindow.statusBar().currentMessage() == "File > New selected"

    mainWindow.openAction.trigger()
    assert mainWindow.statusBar().currentMessage() == "File > Open selected"

    mainWindow.saveAction.trigger()
    assert mainWindow.statusBar().currentMessage() == "File > Save selected"


def testAboutOpensTheDialogAndReportsADonation(qtbot, monkeypatch) -> None:
    """The About text itself is covered in testAboutDialog."""
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    monkeypatch.setattr(
        "transverseVibrationView.ui.mainWindow.showAbout", lambda parent: True
    )

    mainWindow.onHelpAbout()

    assert "donation page" in mainWindow.statusBar().currentMessage()


def openedUrls(monkeypatch) -> list[str]:
    """Collect what the app asked the desktop to open, and say it worked."""
    opened: list[str] = []
    monkeypatch.setattr(
        "transverseVibrationView.ui.mainWindow.QDesktopServices.openUrl",
        lambda url: opened.append(url.toString()) or True,
    )
    return opened


def testManualHasTheStandardHelpShortcut(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    assert mainWindow.manualAction.shortcut() == QKeySequence.StandardKey.HelpContents


def testTheStubManualShipsWithTheTemplate() -> None:
    """Without it the menu item would fail the first time anybody clicked it."""
    assert appConfig.manualPath.exists()
    assert appConfig.manualPath.read_text(encoding="utf-8").strip()


def testNothingIsPublishedUntilTheAuthorSaysSo() -> None:
    """A new app has no manual online, so the default must not pretend it has."""
    assert appConfig.manualUrl == ""


def testTheLocalCopyIsOpenedWhenNothingIsPublished(qtbot, monkeypatch) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    opened = openedUrls(monkeypatch)

    mainWindow.openManual(publishedIsReachable=False)

    assert len(opened) == 1
    assert opened[0].startswith("file:")
    assert opened[0].endswith("README.md")
    assert "local copy" in mainWindow.statusBar().currentMessage()


def testThePublishedCopyWinsWhenItAnswers(qtbot, monkeypatch) -> None:
    """Set manualUrl and the behaviour switches, with no other change."""
    monkeypatch.setattr(appConfig, "manualUrl", "https://example.invalid/manual")
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    opened = openedUrls(monkeypatch)

    mainWindow.openManual(publishedIsReachable=True)

    assert opened == ["https://example.invalid/manual"]
    assert "browser" in mainWindow.statusBar().currentMessage()


def testAMissingManualLeavesTheReaderAnAddress(qtbot, monkeypatch, tmp_path) -> None:
    """Nothing opened, so the path has to be readable somewhere."""
    monkeypatch.setattr(appConfig, "manualPath", tmp_path / "gone.md")
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    openedUrls(monkeypatch)
    shown: list[str] = []
    monkeypatch.setattr(
        "transverseVibrationView.ui.mainWindow.QMessageBox.information",
        lambda parent, title, text: shown.append(text),
    )

    mainWindow.openManual(publishedIsReachable=False)

    assert shown and "gone.md" in shown[0]
    assert "nothing published" in shown[0]


def testTheCheckRunsOffTheInterfaceThread(qtbot, monkeypatch) -> None:
    """A network probe can hang until its timeout; the window must not."""
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    openedUrls(monkeypatch)

    with qtbot.waitSignal(mainWindow.manualAction.changed, timeout=5000):
        mainWindow.onHelpManual()
    # Disabled while the probe is in flight, so it cannot be started twice.
    assert not mainWindow.manualAction.isEnabled()

    assert mainWindow.manualWorker is not None
    mainWindow.manualWorker.wait(5000)
    qtbot.waitUntil(lambda: mainWindow.manualWorker is None, timeout=5000)
    assert mainWindow.manualAction.isEnabled()


def testTheWindowOpensAtTheDefaultSizeOnAFirstRun(qtbot) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)

    assert mainWindow.width() == appConfig.defaultWindowWidth
    assert mainWindow.height() == appConfig.defaultWindowHeight


def testClosingRemembersPositionAndSizeForTheNextLaunch(qtbot) -> None:
    first = MainWindow()
    qtbot.addWidget(first)
    first.show()
    first.setGeometry(140, 160, 900, 650)
    qtbot.waitUntil(lambda: first.width() == 900)
    savedPosition = first.pos()

    first.close()

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    # The frame, and so pos(), only settles once the window is on screen.
    reopened.show()
    qtbot.waitExposed(reopened)
    assert reopened.width() == 900
    assert reopened.height() == 650
    assert reopened.pos() == savedPosition
    reopened.vibrationView.shutdown()


def testStructureParametersSetAreTheDefaultsAtTheNextLaunch(qtbot) -> None:
    first = MainWindow()
    qtbot.addWidget(first)
    controls = first.vibrationView.controls
    controls.lengthSpin.setValue(0.45)
    controls.widthSpin.setValue(0.02)
    controls.thicknessSpin.setValue(0.005)
    controls.densitySpin.setValue(7850.0)
    controls.youngsModulusSpin.setValue(2.1e11)

    first.close()

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    again = reopened.vibrationView.controls
    assert again.lengthSpin.value() == 0.45
    assert again.widthSpin.value() == 0.02
    assert again.thicknessSpin.value() == 0.005
    assert again.densitySpin.value() == 7850.0
    assert again.youngsModulusSpin.value() == 2.1e11
    # And the structure on screen is built from them, not from the old defaults.
    assert reopened.vibrationView.model.geometry.length == 0.45
    reopened.vibrationView.shutdown()
