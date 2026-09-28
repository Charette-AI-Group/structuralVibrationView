"""Smoke tests for the 3D vibration view and its controls."""

from __future__ import annotations

import numpy as np
import pytest

from structuralVibrationView.models.vibrationModel import StructureKind
from structuralVibrationView.services import vibrationService
from structuralVibrationView.ui.theme import currentTokens
from structuralVibrationView.ui.widgets.vibrationControls import pauseLabel, playLabel
from structuralVibrationView.ui.widgets.vibrationView import (
    VibrationView,
    deformedName,
    displacementArrayName,
    referenceName,
)


def makeView(qtbot) -> VibrationView:
    view = VibrationView()
    qtbot.addWidget(view)
    # Stop the clock so the tests, not the timer, decide when frames happen.
    view.timer.stop()
    return view


def testTheViewOpensWithABeamOnScreen(qtbot, onScreen) -> None:
    view = makeView(qtbot)
    view.show()

    assert view.model is not None
    assert view.model.geometry.kind is StructureKind.cantileverBeam
    assert view.meshes
    assert view.meshes[0].n_points == view.model.geometry.pointCount
    assert deformedName(0) in view.interactor.actors
    assert referenceName(0) in view.interactor.actors
    view.shutdown()


def testTheClockRunsByDefaultAndPauseStopsIt(qtbot) -> None:
    view = VibrationView()
    qtbot.addWidget(view)
    assert view.isPlaying()
    assert view.controls.playButton.text() == pauseLabel

    view.controls.playButton.click()

    assert not view.isPlaying()
    assert view.controls.playButton.text() == playLabel
    view.shutdown()


def testATickMovesTheMesh(qtbot) -> None:
    view = makeView(qtbot)
    before = np.array(view.meshes[0].points)
    frames = view.frameCount

    view.onTick()

    assert view.timeSeconds > 0.0
    assert view.frameCount == frames + 1
    assert not np.array_equal(np.array(view.meshes[0].points), before)
    assert view.controls.timeLabel.text().endswith(" ms")
    view.shutdown()


def testRestartPutsTheClockBackToZero(qtbot) -> None:
    view = makeView(qtbot)
    view.onTick()
    view.onTick()

    view.controls.restartButton.click()

    assert view.timeSeconds == 0.0
    assert view.controls.timeLabel.text() == "t = 0.0 ms"
    view.shutdown()


def testSpeedScalesTheClock(qtbot) -> None:
    view = makeView(qtbot)
    view.controls.speedSpin.setValue(2.0)
    view.onTick()
    fast = view.timeSeconds

    view.restart()
    view.controls.speedSpin.setValue(0.5)
    view.onTick()

    assert fast == 4 * view.timeSeconds
    view.shutdown()


def testChangingTheStructureRebuildsTheMesh(qtbot) -> None:
    view = makeView(qtbot)
    statuses: list[str] = []
    view.statusMessage.connect(statuses.append)
    beamMesh = view.meshes[0]

    view.controls.showKind(StructureKind.simplySupportedPlate)

    assert view.model.geometry.kind is StructureKind.simplySupportedPlate
    assert view.meshes[0] is not beamMesh
    assert view.meshes[0].n_points == view.model.geometry.pointCount
    assert statuses and statuses[-1].startswith("Simply Supported Plate: Mode 1")
    view.shutdown()


def testChangingAnAmplitudeKeepsTheMeshAndRescalesColours(qtbot) -> None:
    view = makeView(qtbot)
    mesh = view.meshes[0]

    view.controls.modeRows[1].amplitudeSpin.setValue(0.05)

    assert view.meshes[0] is mesh
    assert [term.modeNumber for term in view.model.terms] == [1, 2]
    limit = view.model.maxDisplacement
    mapper = view.interactor.actors[deformedName(0)].mapper
    assert np.allclose(mapper.scalar_range, (-limit, limit))
    assert displacementArrayName in view.meshes[0].point_data
    view.shutdown()


def testControlsEmitAWholeSetup(qtbot) -> None:
    view = makeView(qtbot)
    setups = []
    view.controls.setupChanged.connect(setups.append)

    view.controls.dampingSpin.setValue(0.05)

    assert len(setups) == 1
    assert setups[0].dampingRatio == 0.05
    assert setups[0].kind is StructureKind.cantileverBeam
    assert len(setups[0].modes) == 3
    view.shutdown()


def testThePlaybackGroupEndsWithThreePresetViewButtons(qtbot, onScreen) -> None:
    view = makeView(qtbot)
    # Positions are only laid out once the widget is on screen.
    view.show()
    qtbot.waitExposed(view)
    buttons = view.controls.presetViewButtons

    assert [button.text() for button in buttons.values()] == [
        "X-Z View",
        "X-Y View",
        "Y-Z View",
    ]
    # Below Play, Restart and Reset View, inside the Playback group.
    playback = view.controls.playButton.parentWidget()
    for button in buttons.values():
        assert button.parentWidget() is playback
        assert button.y() > view.controls.playButton.y()
    view.shutdown()


def testEachPresetLooksAlongTheAxisNormalToItsPlane(qtbot, onScreen) -> None:
    view = makeView(qtbot)
    view.show()
    statuses: list[str] = []
    view.statusMessage.connect(statuses.append)
    # The axis the camera looks along for each plane.
    normals = {"xz": 1, "xy": 2, "yz": 0}

    for plane, axis in normals.items():
        view.controls.presetViewButtons[plane].click()
        direction = np.array(view.interactor.camera.direction)
        assert abs(direction[axis]) > 0.999, plane
        assert statuses[-1] == view.controls.presetViewButtons[plane].text() + "."
    view.shutdown()


def testAPresetViewDoesNotStopTheAnimation(qtbot) -> None:
    view = VibrationView()
    qtbot.addWidget(view)

    view.controls.presetViewButtons["xz"].click()

    assert view.isPlaying()
    view.shutdown()


def testModalSuperpositionIsTheFirstOfTwoTabs(qtbot) -> None:
    view = makeView(qtbot)
    tabs = view.controls.tabs

    assert [tabs.tabText(i) for i in range(tabs.count())] == [
        "Modal Superposition",
        "Structure Parameters",
    ]
    assert tabs.currentIndex() == 0
    view.shutdown()


def testTheModalControlsLiveOnTheFirstTab(qtbot, onScreen) -> None:
    view = makeView(qtbot)
    view.show()
    qtbot.waitExposed(view)
    controls = view.controls
    firstPage = controls.tabs.widget(0)

    widgets = [controls.fundamentalLabel, controls.dampingSpin]
    for row in controls.modeRows:
        widgets += list(row.widgets())
    for widget in widgets:
        assert firstPage.isAncestorOf(widget), widget.objectName()
    # Fundamental and damping stay above the mode table.
    assert controls.fundamentalLabel.y() < controls.dampingSpin.y()
    assert controls.dampingSpin.y() < controls.modeRows[0].numberSpin.y()
    view.shutdown()


def testTheOpenTabIsUnderlinedInTheAccent(qtbot) -> None:
    view = makeView(qtbot)
    style = view.controls.tabs.tabBar().styleSheet()

    assert "QTabBar::tab:selected" in style
    assert currentTokens().accent in style
    view.shutdown()


def testAmplitudeBoxesAreWideEnoughForThreeDecimals(qtbot, onScreen) -> None:
    view = makeView(qtbot)
    view.show()
    qtbot.waitExposed(view)

    for row in view.controls.modeRows:
        spin = row.amplitudeSpin
        spin.setValue(0.300)
        needed = spin.fontMetrics().horizontalAdvance(spin.text())
        # The editable text area is the box minus its arrow buttons.
        assert spin.lineEdit().width() >= needed, spin.objectName()
    view.shutdown()


def testStructureParametersTabHoldsLengthWidthAndThickness(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    page = controls.tabs.widget(1)

    for spin, value, suffix in (
        (controls.structureTab.lengthSpin, 0.3, " m"),
        (controls.structureTab.widthSpin, 0.01, " m"),
        (controls.structureTab.thicknessSpin, 0.003, " m"),
        (controls.structureTab.densitySpin, 2700.0, " kg/m³"),
        (controls.structureTab.youngsModulusSpin, 7.0e10, " N/m²"),
        (controls.structureTab.poissonRatioSpin, 0.33, ""),
    ):
        assert page.isAncestorOf(spin), spin.objectName()
        assert spin.suffix() == suffix
        assert spin.value() == value
    assert controls.structureTab.youngsModulusSpin.text() == "7.00E+10 N/m²"
    view.shutdown()


def testChangingTheLengthRebuildsTheStructureAtThatLength(qtbot) -> None:
    view = makeView(qtbot)
    cameraBefore = view.interactor.camera_position

    view.controls.structureTab.lengthSpin.setValue(2.0)

    assert view.model.geometry.length == 2.0
    assert np.isclose(np.array(view.meshes[0].points)[:, 0].max(), 2.0)
    # A size change keeps the camera where the user left it.
    assert view.interactor.camera_position == cameraBefore
    view.shutdown()


def testChangingTheTypeKeepsTheMaterialAndTheOtherDimensions(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    controls.structureTab.lengthSpin.setValue(0.4)
    controls.structureTab.thicknessSpin.setValue(0.005)
    controls.structureTab.densitySpin.setValue(7850.0)
    setups = []
    controls.setupChanged.connect(setups.append)

    chooseKind(controls, StructureKind.simplySupportedPlate)

    assert len(setups) == 1
    assert setups[0].size.length == 0.4
    assert setups[0].size.thickness == 0.005
    assert setups[0].material.density == 7850.0
    view.shutdown()


def testMaterialChangesReachTheSetup(qtbot) -> None:
    view = makeView(qtbot)
    setups = []
    view.controls.setupChanged.connect(setups.append)

    view.controls.structureTab.youngsModulusSpin.setValue(2.1e11)

    assert setups[-1].material.youngsModulus == 2.1e11
    assert view.model.setup.material.youngsModulus == 2.1e11
    view.shutdown()



def testTheFundamentalIsComputedAndShown(qtbot) -> None:
    view = makeView(qtbot)
    label = view.controls.fundamentalLabel

    assert label.text() == "27.4 Hz"

    view.controls.structureTab.thicknessSpin.setValue(0.006)

    # Twice as thick, twice the frequency.
    assert label.text() == "54.8 Hz"
    view.shutdown()


def testAtSpeedOneMode1TakesTwoScreenSecondsPerCycle(qtbot) -> None:
    """Slow motion is set by the physics, so a stiff structure is not a blur."""
    from structuralVibrationView import appConfig

    view = makeView(qtbot)
    ticksPerScreenSecond = 1000.0 / appConfig.animationIntervalMs

    for _ in range(round(2 * ticksPerScreenSecond)):
        view.onTick()

    cycles = view.timeSeconds * view.model.fundamentalFrequencyHz
    assert abs(cycles - 1.0) < 0.02
    view.shutdown()


def testAStifferStructureStillPlaysAtTheSameScreenPace(qtbot) -> None:
    view = makeView(qtbot)
    view.onTick()
    cyclesPerTick = view.timeSeconds * view.model.fundamentalFrequencyHz

    view.restart()
    view.controls.structureTab.youngsModulusSpin.setValue(2.8e11)
    view.onTick()

    assert np.isclose(view.timeSeconds * view.model.fundamentalFrequencyHz, cyclesPerTick)
    view.shutdown()



def testPoissonsRatioChangesTheFundamentalOfThePlateOnly(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    beamHz = view.model.fundamentalFrequencyHz

    controls.structureTab.poissonRatioSpin.setValue(0.45)
    assert view.model.setup.material.poissonRatio == 0.45
    assert view.model.fundamentalFrequencyHz == beamHz

    controls.showKind(StructureKind.simplySupportedPlate)
    plateHz = view.model.fundamentalFrequencyHz
    controls.structureTab.poissonRatioSpin.setValue(0.0)

    assert view.model.fundamentalFrequencyHz < plateHz
    view.shutdown()


def selectMaterial(controls, name: str) -> None:
    """Pick from the dropdown the way a user does: activated, not just set."""
    index = controls.structureTab.materialCombo.findText(name)
    controls.structureTab.materialCombo.setCurrentIndex(index)
    controls.structureTab.materialCombo.activated.emit(index)


def testTheMaterialDropdownSitsAboveDensityAndStartsOnAluminium(qtbot, onScreen) -> None:
    view = makeView(qtbot)
    view.show()
    qtbot.waitExposed(view)
    controls = view.controls
    combo = controls.structureTab.materialCombo
    # A tab is only laid out once it is shown.
    controls.tabs.setCurrentIndex(1)
    qtbot.waitUntil(lambda: combo.isVisible() and combo.y() > 0, timeout=5000)

    assert controls.tabs.widget(1).isAncestorOf(combo)
    assert combo.y() < controls.structureTab.densitySpin.y()
    assert combo.currentText() == "Aluminium"
    assert combo.itemText(combo.count() - 1) == "Custom"
    view.shutdown()


def testChoosingAPresetFillsAllThreePropertiesInOneUpdate(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    setups = []
    controls.setupChanged.connect(setups.append)

    selectMaterial(controls, "Steel")

    assert len(setups) == 1
    assert setups[0].material.density == 7850.0
    assert setups[0].material.youngsModulus == 2.1e11
    assert setups[0].material.poissonRatio == 0.30
    assert controls.structureTab.densitySpin.value() == 7850.0
    assert controls.structureTab.materialCombo.currentText() == "Steel"
    view.shutdown()


def testEditingAPropertyByHandMakesItCustomAndBack(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls

    controls.structureTab.densitySpin.setValue(2800.0)
    assert controls.structureTab.materialCombo.currentText() == "Custom"

    controls.structureTab.densitySpin.setValue(2700.0)
    assert controls.structureTab.materialCombo.currentText() == "Aluminium"
    view.shutdown()


def testChoosingCustomKeepsTheValues(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    selectMaterial(controls, "Titanium")
    setups = []
    controls.setupChanged.connect(setups.append)

    selectMaterial(controls, "Custom")

    assert setups == []
    assert controls.structureTab.densitySpin.value() == 4500.0
    # What the user picked stays picked, rather than snapping back to Titanium.
    assert controls.structureTab.materialCombo.currentText() == "Custom"
    view.shutdown()


def testAPresetChangesTheComputedFundamental(qtbot) -> None:
    view = makeView(qtbot)
    aluminiumHz = view.model.fundamentalFrequencyHz

    selectMaterial(view.controls, "Polycarbonate")

    assert view.model.fundamentalFrequencyHz < aluminiumHz / 3
    view.shutdown()


def openStructureTab(view) -> None:
    view.controls.tabs.setCurrentIndex(1)


def testTheModeDropdownIsFirstAndListsFiveModesWithFrequencies(qtbot, onScreen) -> None:
    view = makeView(qtbot)
    view.show()
    qtbot.waitExposed(view)
    openStructureTab(view)
    tab = view.controls.structureTab
    qtbot.waitUntil(lambda: tab.modeCombo.isVisible() and tab.lengthSpin.y() > 0, timeout=5000)
    combo = tab.modeCombo

    assert [combo.itemText(i) for i in range(combo.count())] == [
        "Mode 1 (27.4 Hz)",
        "Mode 2 (172 Hz)",
        "Mode 3 (481 Hz)",
        "Mode 4 (943 Hz)",
        "Mode 5 (1.56 kHz)",
    ]
    assert combo.y() < tab.lengthSpin.y()
    view.shutdown()


def testOpeningTheTabAnimatesOnlyItsSelectedMode(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    # Superposition settings that must not leak into the single-mode view.
    controls.modeRows[1].amplitudeSpin.setValue(0.1)
    controls.dampingSpin.setValue(0.2)
    statuses: list[str] = []
    view.statusMessage.connect(statuses.append)

    openStructureTab(view)

    assert view.model.setup.singleMode
    assert [term.modeNumber for term in view.model.terms] == [1]
    assert view.model.terms[0].amplitude == 0.05
    assert view.model.setup.dampingRatio == 0.0
    assert statuses[-1] == "Cantilever Beam: Mode 1 at 27.4 Hz"
    view.shutdown()


def testTheSuperpositionTabCannotChangeTheSingleModeAnimation(qtbot) -> None:
    view = makeView(qtbot)
    openStructureTab(view)

    view.controls.modeRows[0].amplitudeSpin.setValue(0.2)
    view.controls.dampingSpin.setValue(0.3)

    assert view.model.terms[0].amplitude == 0.05
    assert view.model.setup.dampingRatio == 0.0
    view.shutdown()


def testChoosingAModeAnimatesItAndPacesTheClockByIt(qtbot) -> None:
    from structuralVibrationView import appConfig

    view = makeView(qtbot)
    openStructureTab(view)

    view.controls.structureTab.modeCombo.setCurrentIndex(2)

    term = view.model.terms[0]
    assert term.modeNumber == 3
    assert view.model.referenceFrequencyHz == term.frequencyHz
    # Mode 3 plays at the same screen pace mode 1 would: a cycle in two seconds.
    for _ in range(round(2 * 1000.0 / appConfig.animationIntervalMs)):
        view.onTick()
    assert abs(view.timeSeconds * term.frequencyHz - 1.0) < 0.02
    view.shutdown()


def testGoingBackToSuperpositionRestoresItsSettings(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    controls.modeRows[1].amplitudeSpin.setValue(0.02)
    controls.dampingSpin.setValue(0.05)
    openStructureTab(view)

    controls.tabs.setCurrentIndex(0)

    assert not view.model.setup.singleMode
    assert [term.modeNumber for term in view.model.terms] == [1, 2]
    assert view.model.setup.dampingRatio == 0.05
    assert view.model.referenceFrequencyHz == view.model.fundamentalFrequencyHz
    view.shutdown()


def testModeFrequenciesFollowTheStructure(qtbot) -> None:
    view = makeView(qtbot)
    tab = view.controls.structureTab

    tab.thicknessSpin.setValue(0.006)
    assert tab.modeCombo.itemText(0) == "Mode 1 (54.8 Hz)"

    view.controls.showKind(StructureKind.simplySupportedBeam)
    assert tab.modeCombo.itemText(0) == "Mode 1 (154 Hz)"
    view.shutdown()


def testTheTypeListSeparatesTheFamilies(qtbot) -> None:
    view = makeView(qtbot)
    combo = view.controls.kindCombo

    rows = [
        "---" if combo.itemData(i) is None else combo.itemText(i)
        for i in range(combo.count())
    ]
    assert rows == [
        "Cantilever Beam",
        "Simply Supported Beam",
        "Clamped-Clamped Beam",
        "---",
        "Simply Supported Plate",
        "Clamped Plate",
        "---",
        "Spring-Mass (SDOF)",
    ]
    view.shutdown()


def testEveryTypeIsStillSelectableWithTheSeparatorThere(qtbot) -> None:
    view = makeView(qtbot)

    for kind in StructureKind:
        view.controls.showKind(kind)
        assert view.controls.currentKind() is kind
        assert view.model.geometry.kind is kind
    view.shutdown()


def testTheTypeSeparatorIsDrawnInAGreyThatCanBeSeen(qtbot) -> None:
    """The platform's own line is nearly black on a dark popup."""
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QColor, QPainter, QPixmap
    from PySide6.QtWidgets import QStyleOptionViewItem

    from structuralVibrationView.ui.theme import currentTokens
    from structuralVibrationView.ui.widgets.separatorItemDelegate import (
        SeparatorItemDelegate,
        isSeparator,
    )

    view = makeView(qtbot)
    combo = view.controls.kindCombo
    delegate = combo.itemDelegate()
    assert isinstance(delegate, SeparatorItemDelegate)
    row = next(i for i in range(combo.count()) if combo.itemData(i) is None)
    index = combo.model().index(row, 0)
    assert isSeparator(index)

    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 200, delegate.sizeHint(option, index).height())
    canvas = QPixmap(option.rect.size())
    canvas.fill(QColor("#000000"))
    painter = QPainter(canvas)
    delegate.paint(painter, option, index)
    painter.end()

    middle = canvas.toImage().pixelColor(100, option.rect.height() // 2)
    assert middle == QColor(currentTokens().divider)
    view.shutdown()


# ----- the width that comes with a change of type -----------------------------


def chooseKind(controls, kind) -> None:
    """Pick a type the way a user does, through the dropdown's own signal."""
    combo = controls.kindCombo
    combo.setCurrentIndex(combo.findData(kind.value))


def testChoosingThePlateMakesItTwiceAsLongAsItIsWide(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    controls.structureTab.lengthSpin.setValue(0.4)
    setups = []
    controls.setupChanged.connect(setups.append)

    chooseKind(controls, StructureKind.simplySupportedPlate)

    assert controls.structureTab.widthSpin.value() == 0.2
    assert view.model.geometry.width == 0.2
    assert len(setups) == 1  # the new width and type arrive together
    view.shutdown()


def testGoingBackToABeamMakesItSlenderAgain(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    chooseKind(controls, StructureKind.simplySupportedPlate)

    chooseKind(controls, StructureKind.cantileverBeam)

    ratio = vibrationService.lengthToWidthFor(StructureKind.cantileverBeam)
    assert controls.structureTab.widthSpin.value() == pytest.approx(0.3 / ratio)
    assert ratio == 30.0  # 0.3 m by 0.01 m, the app's default beam
    view.shutdown()


def testOneBeamToAnotherLeavesTheWidthAlone(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    controls.structureTab.widthSpin.setValue(0.05)

    chooseKind(controls, StructureKind.clampedBeam)

    assert controls.structureTab.widthSpin.value() == 0.05
    view.shutdown()


def testAWidthSetAfterTheTypeChangeIsKept(qtbot) -> None:
    """The proportions are an offer, not a rule."""
    view = makeView(qtbot)
    controls = view.controls
    chooseKind(controls, StructureKind.simplySupportedPlate)

    controls.structureTab.widthSpin.setValue(0.25)

    assert view.model.geometry.width == 0.25
    assert controls.currentKind() is StructureKind.simplySupportedPlate
    view.shutdown()


def testOpeningASessionKeepsTheWidthItWasSavedWith(qtbot, tmp_path) -> None:
    """A saved plate may be any shape; opening it must not reshape it."""
    from structuralVibrationView.services import sessionFileService

    view = makeView(qtbot)
    controls = view.controls
    chooseKind(controls, StructureKind.simplySupportedPlate)
    controls.structureTab.widthSpin.setValue(0.05)
    path = tmp_path / "narrow.tvv"
    sessionFileService.saveSession(path, view.captureSession())
    view.shutdown()

    reopened = makeView(qtbot)
    reopened.restoreSession(sessionFileService.loadSession(path))

    assert reopened.controls.structureTab.widthSpin.value() == 0.05
    assert reopened.model.geometry.width == 0.05
    reopened.shutdown()


def testTheClampedPlateAnimatesAsTheLastPlate(qtbot) -> None:
    view = makeView(qtbot)
    combo = view.controls.kindCombo
    statuses: list[str] = []
    view.statusMessage.connect(statuses.append)

    plates = [combo.itemData(i) for i in range(combo.count()) if combo.itemData(i)]
    assert plates[-2] == StructureKind.clampedPlate.value

    chooseKind(view.controls, StructureKind.clampedPlate)

    assert view.model.geometry.kind is StructureKind.clampedPlate
    assert view.meshes[0].n_points == view.model.geometry.pointCount
    assert statuses[-1].startswith("Clamped Plate: Mode 1 (1,1)")
    # Clamped edges are stiffer, so it sits well above the supported plate.
    view.shutdown()


def testBothPlatesGetThePlateProportions(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    controls.structureTab.lengthSpin.setValue(0.4)

    chooseKind(controls, StructureKind.clampedPlate)

    assert controls.structureTab.widthSpin.value() == 0.2
    view.shutdown()


# ----- the spring-mass system on screen ---------------------------------------


def testTheOscillatorIsDrawnAsTwoMeshes(qtbot) -> None:
    view = makeView(qtbot)
    statuses: list[str] = []
    view.statusMessage.connect(statuses.append)

    chooseKind(view.controls, StructureKind.springMass)

    assert len(view.meshes) == 2
    assert [part.name for part in view.model.geometry.parts] == ["spring", "mass"]
    for index in range(2):
        assert deformedName(index) in view.interactor.actors
        assert referenceName(index) in view.interactor.actors
    assert statuses[-1].startswith("Spring-Mass (SDOF): Mode 1 at")
    view.shutdown()


def testBothOfItsMeshesMoveOnATick(qtbot) -> None:
    view = makeView(qtbot)
    chooseKind(view.controls, StructureKind.springMass)
    before = [np.array(mesh.points) for mesh in view.meshes]

    view.onTick()

    for mesh, was in zip(view.meshes, before, strict=True):
        assert not np.array_equal(np.array(mesh.points), was)
    view.shutdown()


def testGoingBackToABeamLeavesNoOscillatorBehind(qtbot) -> None:
    view = makeView(qtbot)
    chooseKind(view.controls, StructureKind.springMass)

    chooseKind(view.controls, StructureKind.cantileverBeam)

    assert len(view.meshes) == 1
    assert deformedName(1) not in view.interactor.actors
    assert referenceName(1) not in view.interactor.actors
    view.shutdown()


def testItOffersOneModeAndTheBeamsSix(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    assert controls.structureTab.modeCombo.count() == 5  # the app offers five
    assert controls.modeRows[0].numberSpin.maximum() == 6

    chooseKind(controls, StructureKind.springMass)

    assert controls.structureTab.modeCombo.count() == 1
    assert not controls.structureTab.modeCombo.isEnabled()
    assert controls.modeRows[0].numberSpin.maximum() == 1
    view.shutdown()


def testTheStiffnessRowAppearsOnlyForTheOscillator(qtbot, onScreen) -> None:
    view = makeView(qtbot)
    view.show()
    qtbot.waitExposed(view)
    tab = view.controls.structureTab
    view.controls.tabs.setCurrentIndex(1)

    assert not tab.springStiffnessSpin.isVisible()
    assert tab.youngsModulusSpin.isVisible()

    chooseKind(view.controls, StructureKind.springMass)

    assert tab.springStiffnessSpin.isVisible()
    # Young's modulus says nothing about a given spring rate, so it goes.
    assert not tab.youngsModulusSpin.isVisible()
    assert not tab.poissonRatioSpin.isVisible()
    view.shutdown()


def testChangingTheStiffnessRetunesIt(qtbot) -> None:
    view = makeView(qtbot)
    chooseKind(view.controls, StructureKind.springMass)
    before = view.model.fundamentalFrequencyHz

    view.controls.structureTab.springStiffnessSpin.setValue(
        4 * view.controls.structureTab.springStiffnessSpin.value()
    )

    assert view.model.fundamentalFrequencyHz == pytest.approx(2 * before)
    view.shutdown()


def testTheOscillatorGetsABlockYouCanSee(qtbot) -> None:
    """Its proportions on switching: a block a third of the spring's height."""
    view = makeView(qtbot)
    view.controls.structureTab.lengthSpin.setValue(0.3)

    chooseKind(view.controls, StructureKind.springMass)

    assert view.controls.structureTab.widthSpin.value() == pytest.approx(0.1)
    view.shutdown()
