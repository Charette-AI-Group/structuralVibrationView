"""Smoke tests for the main window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from structuralVibrationView import appConfig
from structuralVibrationView.models.vibrationModel import StructureKind
from structuralVibrationView.services import themeService, windowGeometryService
from structuralVibrationView.ui.mainWindow import MainWindow


def testMainWindowOpens(qtbot, onScreen) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.show()

    assert mainWindow.isVisible()
    assert mainWindow.windowTitle() == "Structural Vibration View"
    # The bar says what is on screen from the first frame, not "Ready".
    assert mainWindow.statusBar().currentMessage().startswith("Cantilever Beam: Mode 1")


def testTheVibrationViewIsTheCentralWidgetAndReportsToTheBar(qtbot, onScreen) -> None:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.show()

    assert mainWindow.centralWidget() is mainWindow.vibrationView
    assert mainWindow.vibrationView.isPlaying()

    mainWindow.vibrationView.controls.playButton.click()

    assert mainWindow.statusBar().currentMessage().startswith("Paused")


def testClosingTheWindowStopsTheAnimation(qtbot, onScreen) -> None:
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
    assert fileItems == ["&Open...", "&Save...", "E&xit"]
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


def testAboutOpensTheDialogAndReportsADonation(qtbot, monkeypatch) -> None:
    """The About text itself is covered in testAboutDialog."""
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    monkeypatch.setattr(
        "structuralVibrationView.ui.mainWindow.showAbout", lambda parent: True
    )

    mainWindow.onHelpAbout()

    assert "donation page" in mainWindow.statusBar().currentMessage()


def openedUrls(monkeypatch) -> list[str]:
    """Collect what the app asked the desktop to open, and say it worked."""
    opened: list[str] = []
    monkeypatch.setattr(
        "structuralVibrationView.ui.mainWindow.QDesktopServices.openUrl",
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


def testThePublishedManualIsTheOneInTheRepository() -> None:
    """Help > User Manual prefers it, and falls back to the copy in the checkout."""
    assert appConfig.manualUrl == f"{appConfig.repoUrl}/blob/main/docs/manual/README.md"
    assert appConfig.repoUrl.endswith("/structuralVibrationView")


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
        "structuralVibrationView.ui.mainWindow.QMessageBox.information",
        lambda parent, title, text: shown.append(text),
    )

    mainWindow.openManual(publishedIsReachable=False)

    assert shown and "gone.md" in shown[0]
    # Both copies, so the reader can reach whichever one exists.
    assert appConfig.manualUrl in shown[0]


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


def testClosingRemembersPositionAndSizeForTheNextLaunch(qtbot, onScreen) -> None:
    """Where the geometry goes, and that the next window is built from it.

    Asserted through the saved value rather than through pixels: what the app
    controls is what it writes and what it restores from. Where a window
    manager then puts the window is its own business, and macOS in particular
    trims the height and moves the window up to clear its menu bar.
    """
    first = MainWindow()
    qtbot.addWidget(first)
    first.show()
    first.setGeometry(140, 160, 900, 650)
    qtbot.waitUntil(lambda: first.width() == 900)
    closedGeometry = first.saveGeometry()
    closedSize = first.size()

    first.close()

    assert windowGeometryService.loadGeometry() == closedGeometry

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    reopened.show()
    qtbot.waitExposed(reopened)

    # Near enough: the size came back rather than the default one.
    assert abs(reopened.width() - closedSize.width()) <= 12
    assert abs(reopened.height() - closedSize.height()) <= 12
    assert reopened.width() != appConfig.defaultWindowWidth
    reopened.vibrationView.shutdown()


def testStructureParametersSetAreTheDefaultsAtTheNextLaunch(qtbot) -> None:
    first = MainWindow()
    qtbot.addWidget(first)
    controls = first.vibrationView.controls
    controls.structureTab.lengthSpin.setValue(0.45)
    controls.structureTab.widthSpin.setValue(0.02)
    controls.structureTab.thicknessSpin.setValue(0.005)
    controls.structureTab.densitySpin.setValue(7850.0)
    controls.structureTab.youngsModulusSpin.setValue(2.1e11)
    controls.structureTab.poissonRatioSpin.setValue(0.30)

    first.close()

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    again = reopened.vibrationView.controls
    assert again.structureTab.lengthSpin.value() == 0.45
    assert again.structureTab.widthSpin.value() == 0.02
    assert again.structureTab.thicknessSpin.value() == 0.005
    assert again.structureTab.densitySpin.value() == 7850.0
    assert again.structureTab.youngsModulusSpin.value() == 2.1e11
    assert again.structureTab.poissonRatioSpin.value() == 0.30
    # And the structure on screen is built from them, not from the old defaults.
    assert reopened.vibrationView.model.geometry.length == 0.45
    reopened.vibrationView.shutdown()


def testASavedPresetMaterialReopensUnderItsName(qtbot) -> None:
    first = MainWindow()
    qtbot.addWidget(first)
    combo = first.vibrationView.controls.structureTab.materialCombo
    index = combo.findText("Copper")
    combo.setCurrentIndex(index)
    combo.activated.emit(index)

    first.close()

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    assert reopened.vibrationView.controls.structureTab.materialCombo.currentText() == "Copper"
    reopened.vibrationView.shutdown()



def testTheSelectedModeIsTheDefaultAtTheNextLaunch(qtbot) -> None:
    first = MainWindow()
    qtbot.addWidget(first)
    first.vibrationView.controls.structureTab.modeCombo.setCurrentIndex(3)

    first.close()

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    controls = reopened.vibrationView.controls
    assert controls.structureTab.selectedMode() == 4
    # And it is what the tab animates once opened.
    controls.tabs.setCurrentIndex(1)
    assert [term.modeNumber for term in reopened.vibrationView.model.terms] == [4]
    reopened.vibrationView.shutdown()



# ----- File > Save and File > Open -------------------------------------------


def chooseFile(monkeypatch, dialog: str, path) -> None:
    """Answer the next file dialog with this path, or cancel it with None."""
    monkeypatch.setattr(
        f"structuralVibrationView.ui.mainWindow.QFileDialog.{dialog}",
        lambda *args, **kwargs: (str(path) if path else "", ""),
    )


def stageEverything(window: MainWindow) -> None:
    """Change something in every group, so a round trip has something to prove."""
    view = window.vibrationView
    controls = view.controls
    controls.showKind(StructureKind.clampedBeam)
    controls.dampingSpin.setValue(0.02)
    controls.modeRows[1].amplitudeSpin.setValue(0.03)
    controls.modeRows[1].phaseSpin.setValue(90.0)
    controls.modeRows[2].numberSpin.setValue(5)
    tab = controls.structureTab
    tab.modeCombo.setCurrentIndex(2)
    tab.lengthSpin.setValue(0.5)
    tab.thicknessSpin.setValue(0.004)
    index = tab.materialCombo.findText("Steel")
    tab.materialCombo.setCurrentIndex(index)
    tab.materialCombo.activated.emit(index)
    controls.tabs.setCurrentIndex(1)
    controls.speedSpin.setValue(0.25)
    controls.playButton.setChecked(False)
    view.timeSeconds = 0.0123
    view.showPresetView("xz")


def testSaveThenOpenPutsTheWholeWindowBack(qtbot, monkeypatch, tmp_path) -> None:
    path = tmp_path / "study.tvv"
    first = MainWindow()
    qtbot.addWidget(first)
    stageEverything(first)
    saved = first.vibrationView.captureSession()
    chooseFile(monkeypatch, "getSaveFileName", path)

    first.saveAction.trigger()

    assert path.is_file()
    assert first.statusBar().currentMessage() == "Saved study.tvv."
    first.vibrationView.shutdown()

    fresh = MainWindow()
    qtbot.addWidget(fresh)
    chooseFile(monkeypatch, "getOpenFileName", path)

    fresh.openAction.trigger()

    view = fresh.vibrationView
    controls = view.controls
    assert view.captureSession() == saved
    # And what the window shows follows from it, not just the stored values.
    assert controls.tabs.currentIndex() == 1
    assert controls.structureTab.materialCombo.currentText() == "Steel"
    assert not view.isPlaying()
    assert controls.playButton.text() == "Play"
    assert [term.modeNumber for term in view.model.terms] == [3]
    assert view.model.geometry.kind is StructureKind.clampedBeam
    assert fresh.statusBar().currentMessage() == "Opened study.tvv."
    view.shutdown()


def testSaveAddsTheExtensionWhenLeftOff(qtbot, monkeypatch, tmp_path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    chooseFile(monkeypatch, "getSaveFileName", tmp_path / "plain")

    window.saveAction.trigger()

    assert (tmp_path / "plain.tvv").is_file()
    window.vibrationView.shutdown()


def testCancellingTheDialogsChangesNothing(qtbot, monkeypatch) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    before = window.vibrationView.captureSession()
    message = window.statusBar().currentMessage()
    chooseFile(monkeypatch, "getSaveFileName", None)
    chooseFile(monkeypatch, "getOpenFileName", None)

    window.saveAction.trigger()
    window.openAction.trigger()

    assert window.vibrationView.captureSession() == before
    assert window.statusBar().currentMessage() == message
    window.vibrationView.shutdown()


def testABadFileIsReportedAndTheWindowLeftAlone(qtbot, monkeypatch, tmp_path) -> None:
    path = tmp_path / "broken.tvv"
    path.write_text('{"format": "somethingElse"}', encoding="utf-8")
    window = MainWindow()
    qtbot.addWidget(window)
    before = window.vibrationView.captureSession()
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(MainWindow, "showError", lambda self, t, m: shown.append((t, m)))
    chooseFile(monkeypatch, "getOpenFileName", path)

    window.openAction.trigger()

    assert shown and shown[0][0] == "Open Session"
    assert "broken.tvv could not be opened" in shown[0][1]
    assert window.vibrationView.captureSession() == before
    window.vibrationView.shutdown()


def testTheDialogsStartWhereTheLastSessionWas(qtbot, monkeypatch, tmp_path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    chooseFile(monkeypatch, "getSaveFileName", tmp_path / "first.tvv")
    window.saveAction.trigger()
    asked: list[str] = []
    monkeypatch.setattr(
        "structuralVibrationView.ui.mainWindow.QFileDialog.getOpenFileName",
        lambda parent, title, folder, filters: asked.append(folder) or ("", ""),
    )

    window.openAction.trigger()

    assert asked == [str(tmp_path)]
    window.vibrationView.shutdown()


def testTheStiffnessIsSavedAndReopened(qtbot, monkeypatch, tmp_path) -> None:
    path = tmp_path / "oscillator.tvv"
    first = MainWindow()
    qtbot.addWidget(first)
    controls = first.vibrationView.controls
    combo = controls.kindCombo
    combo.setCurrentIndex(combo.findData(StructureKind.springMass.value))
    controls.structureTab.springStiffnessSpin.setValue(2500.0)
    chooseFile(monkeypatch, "getSaveFileName", path)
    first.saveAction.trigger()
    first.close()  # also writes it to the settings

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    assert reopened.vibrationView.controls.structureTab.springStiffnessSpin.value() == 2500.0
    chooseFile(monkeypatch, "getOpenFileName", path)

    reopened.openAction.trigger()

    view = reopened.vibrationView
    assert view.model.geometry.kind is StructureKind.springMass
    assert view.model.setup.springStiffness == 2500.0
    assert len(view.meshes) == 2
    view.shutdown()
