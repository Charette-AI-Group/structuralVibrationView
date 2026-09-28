"""Tests for reading and writing session files."""

from __future__ import annotations

import json

import pytest

from structuralVibrationView.models.sessionState import (
    CameraState,
    PlaybackState,
    SessionState,
    structureParametersTab,
)
from structuralVibrationView.models.vibrationModel import (
    MaterialProperties,
    ModeSetting,
    StructureKind,
    StructureParameters,
    StructureSize,
)
from structuralVibrationView.services import sessionFileService
from structuralVibrationView.services.sessionFileService import SessionFileError

session = SessionState(
    kind=StructureKind.clampedBeam,
    openTab=structureParametersTab,
    dampingRatio=0.02,
    modes=(ModeSetting(1, 0.05, 0.0), ModeSetting(2, 0.03, 90.0), ModeSetting(4, 0.0, -45.0)),
    selectedMode=3,
    structure=StructureParameters(
        size=StructureSize(0.5, 0.02, 0.004),
        material=MaterialProperties(7850.0, 2.1e11, 0.30),
    ),
    playback=PlaybackState(speed=0.25, playing=False, timeSeconds=0.0123),
    camera=CameraState((1.0, -2.0, 0.5), (0.25, 0.0, 0.0), (0.0, 0.0, 1.0)),
)


def writeData(tmp_path, data) -> object:
    path = tmp_path / "session.tvv"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def testASavedSessionReadsBackUnchanged(tmp_path) -> None:
    path = tmp_path / "beam.tvv"

    sessionFileService.saveSession(path, session)

    assert sessionFileService.loadSession(path) == session


def testTheFileIsReadableJsonThatSaysWhatItIs(tmp_path) -> None:
    path = tmp_path / "beam.tvv"
    sessionFileService.saveSession(path, session)

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["format"] == "structuralVibrationView.session"
    assert data["version"] == 1
    assert data["structure"]["kind"] == "Clamped-Clamped Beam"
    assert data["structureParameters"]["youngsModulus"] == 2.1e11
    assert data["playback"]["playing"] is False


def testASessionWithoutACameraStillOpens(tmp_path) -> None:
    data = sessionFileService.sessionToDict(session)
    del data["camera"]

    loaded = sessionFileService.loadSession(writeData(tmp_path, data))

    assert loaded.camera is None
    assert loaded.structure == session.structure


def breakIt(change):
    data = sessionFileService.sessionToDict(session)
    change(data)
    return data


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda d: d.update(format="somethingElse"), "not a Structural Vibration View"),
        (lambda d: d.update(version=2), "version 2"),
        (lambda d: d.pop("playback"), "no 'playback' section"),
        (lambda d: d["structure"].update(kind="Arch"), "structure.kind is 'Arch'"),
        (lambda d: d.update(openTab="Somewhere"), "openTab must be one of"),
        (lambda d: d["structureParameters"].update(length=50.0), "structureParameters.length"),
        (lambda d: d["structureParameters"].update(selectedMode=9), "selectedMode"),
        (lambda d: d["structureParameters"].update(selectedMode=2.5), "whole number"),
        (lambda d: d["modalSuperposition"]["modes"].pop(), "must list 3 modes"),
        (lambda d: d["modalSuperposition"]["modes"][1].update(amplitude=0.9),
         "modalSuperposition.modes[1].amplitude"),
        (lambda d: d["modalSuperposition"].update(dampingRatio="none"), "must be a number"),
        (lambda d: d["playback"].update(playing=1), "true or false"),
        (lambda d: d["playback"].update(speed=True), "must be a number"),
        (lambda d: d["camera"].update(viewUp=[0, 1]), "camera.viewUp"),
    ],
)
def testABadEntryIsRefusedByName(tmp_path, change, message) -> None:
    with pytest.raises(SessionFileError, match=message.replace("[", r"\[").replace("]", r"\]")):
        sessionFileService.loadSession(writeData(tmp_path, breakIt(change)))


def testAFileThatIsNotJsonIsRefusedPlainly(tmp_path) -> None:
    path = tmp_path / "notes.tvv"
    path.write_text("Just some notes", encoding="utf-8")

    with pytest.raises(SessionFileError, match="not valid JSON"):
        sessionFileService.loadSession(path)


def testAMissingFileIsRefusedPlainly(tmp_path) -> None:
    with pytest.raises(SessionFileError, match="could not be read"):
        sessionFileService.loadSession(tmp_path / "gone.tvv")


def testTheLastFolderIsRememberedOnlyWhileItExists(tmp_path) -> None:
    assert sessionFileService.loadLastFolder() is None

    sessionFileService.saveLastFolder(tmp_path)
    assert sessionFileService.loadLastFolder() == tmp_path

    sessionFileService.saveLastFolder(tmp_path / "deleted")
    assert sessionFileService.loadLastFolder() is None


def testASessionSavedUnderTheOldAppNameStillOpens(tmp_path) -> None:
    """The app was renamed; files people already saved were not."""
    data = sessionFileService.sessionToDict(session)
    data["format"] = sessionFileService.legacyFileFormat

    loaded = sessionFileService.loadSession(writeData(tmp_path, data))

    assert loaded == session
