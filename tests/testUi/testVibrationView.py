"""Smoke tests for the 3D vibration view and its controls."""

from __future__ import annotations

import numpy as np

from transverseVibrationView.models.vibrationModel import StructureKind
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
    assert view.controls.timeLabel.text().startswith("t = 0.0")
    view.shutdown()


def testRestartPutsTheClockBackToZero(qtbot) -> None:
    view = makeView(qtbot)
    view.onTick()
    view.onTick()

    view.controls.restartButton.click()

    assert view.timeSeconds == 0.0
    assert view.controls.timeLabel.text() == "t = 0.00 s"
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

    view.controls.frequencySpin.setValue(1.5)

    assert len(setups) == 1
    assert setups[0].fundamentalFrequencyHz == 1.5
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
