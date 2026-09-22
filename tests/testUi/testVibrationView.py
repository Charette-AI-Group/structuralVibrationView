"""Smoke tests for the 3D vibration view and its controls."""

from __future__ import annotations

import numpy as np

from transverseVibrationView.models.vibrationModel import StructureKind
from transverseVibrationView.ui.theme import currentTokens
from transverseVibrationView.ui.widgets.vibrationControls import pauseLabel, playLabel
from transverseVibrationView.ui.widgets.vibrationView import (
    VibrationView,
    deformedMeshName,
    displacementArrayName,
    referenceMeshName,
)


def makeView(qtbot) -> VibrationView:
    view = VibrationView()
    qtbot.addWidget(view)
    # Stop the clock so the tests, not the timer, decide when frames happen.
    view.timer.stop()
    return view


def testTheViewOpensWithABeamOnScreen(qtbot) -> None:
    view = makeView(qtbot)
    view.show()

    assert view.model is not None
    assert view.model.geometry.kind is StructureKind.cantileverBeam
    assert view.mesh is not None
    assert view.mesh.n_points == view.model.geometry.pointCount
    assert deformedMeshName in view.interactor.actors
    assert referenceMeshName in view.interactor.actors
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
    before = np.array(view.mesh.points)
    frames = view.frameCount

    view.onTick()

    assert view.timeSeconds > 0.0
    assert view.frameCount == frames + 1
    assert not np.array_equal(np.array(view.mesh.points), before)
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
    beamMesh = view.mesh

    plateIndex = list(StructureKind).index(StructureKind.simplySupportedPlate)
    view.controls.kindCombo.setCurrentIndex(plateIndex)

    assert view.model.geometry.kind is StructureKind.simplySupportedPlate
    assert view.mesh is not beamMesh
    assert view.mesh.n_points == view.model.geometry.pointCount
    assert statuses and statuses[-1].startswith("Simply Supported Plate: Mode 1")
    view.shutdown()


def testChangingAnAmplitudeKeepsTheMeshAndRescalesColours(qtbot) -> None:
    view = makeView(qtbot)
    mesh = view.mesh

    view.controls.modeRows[1].amplitudeSpin.setValue(0.05)

    assert view.mesh is mesh
    assert [term.modeNumber for term in view.model.terms] == [1, 2]
    limit = view.model.maxDisplacement
    mapper = view.interactor.actors[deformedMeshName].mapper
    assert np.allclose(mapper.scalar_range, (-limit, limit))
    assert displacementArrayName in view.mesh.point_data
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


def testThePlaybackGroupEndsWithThreePresetViewButtons(qtbot) -> None:
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


def testEachPresetLooksAlongTheAxisNormalToItsPlane(qtbot) -> None:
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


def testTheModalControlsLiveOnTheFirstTab(qtbot) -> None:
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


def testAmplitudeBoxesAreWideEnoughForThreeDecimals(qtbot) -> None:
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
        (controls.lengthSpin, 0.3, " m"),
        (controls.widthSpin, 0.01, " m"),
        (controls.thicknessSpin, 0.003, " m"),
        (controls.densitySpin, 2700.0, " kg/m³"),
        (controls.youngsModulusSpin, 7.0e10, " N/m²"),
        (controls.poissonRatioSpin, 0.33, ""),
    ):
        assert page.isAncestorOf(spin), spin.objectName()
        assert spin.suffix() == suffix
        assert spin.value() == value
    assert controls.youngsModulusSpin.text() == "7.00E+10 N/m²"
    view.shutdown()


def testChangingTheLengthRebuildsTheStructureAtThatLength(qtbot) -> None:
    view = makeView(qtbot)
    cameraBefore = view.interactor.camera_position

    view.controls.lengthSpin.setValue(2.0)

    assert view.model.geometry.length == 2.0
    assert np.isclose(np.array(view.mesh.points)[:, 0].max(), 2.0)
    # A size change keeps the camera where the user left it.
    assert view.interactor.camera_position == cameraBefore
    view.shutdown()


def testChangingTheTypeKeepsTheUsersDimensionsAndMaterial(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    controls.widthSpin.setValue(0.3)
    controls.densitySpin.setValue(7850.0)
    setups = []
    controls.setupChanged.connect(setups.append)

    controls.kindCombo.setCurrentIndex(list(StructureKind).index(StructureKind.simplySupportedPlate))

    assert len(setups) == 1
    assert setups[0].size.width == 0.3
    assert setups[0].material.density == 7850.0
    assert view.model.geometry.width == 0.3
    view.shutdown()


def testMaterialChangesReachTheSetup(qtbot) -> None:
    view = makeView(qtbot)
    setups = []
    view.controls.setupChanged.connect(setups.append)

    view.controls.youngsModulusSpin.setValue(2.1e11)

    assert setups[-1].material.youngsModulus == 2.1e11
    assert view.model.setup.material.youngsModulus == 2.1e11
    view.shutdown()



def testTheFundamentalIsComputedAndShown(qtbot) -> None:
    view = makeView(qtbot)
    label = view.controls.fundamentalLabel

    assert label.text() == "27.4 Hz"

    view.controls.thicknessSpin.setValue(0.006)

    # Twice as thick, twice the frequency.
    assert label.text() == "54.8 Hz"
    view.shutdown()


def testAtSpeedOneMode1TakesTwoScreenSecondsPerCycle(qtbot) -> None:
    """Slow motion is set by the physics, so a stiff structure is not a blur."""
    from transverseVibrationView import appConfig

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
    view.controls.youngsModulusSpin.setValue(2.8e11)
    view.onTick()

    assert np.isclose(view.timeSeconds * view.model.fundamentalFrequencyHz, cyclesPerTick)
    view.shutdown()



def testPoissonsRatioChangesTheFundamentalOfThePlateOnly(qtbot) -> None:
    view = makeView(qtbot)
    controls = view.controls
    beamHz = view.model.fundamentalFrequencyHz

    controls.poissonRatioSpin.setValue(0.45)
    assert view.model.setup.material.poissonRatio == 0.45
    assert view.model.fundamentalFrequencyHz == beamHz

    controls.kindCombo.setCurrentIndex(list(StructureKind).index(StructureKind.simplySupportedPlate))
    plateHz = view.model.fundamentalFrequencyHz
    controls.poissonRatioSpin.setValue(0.0)

    assert view.model.fundamentalFrequencyHz < plateHz
    view.shutdown()
