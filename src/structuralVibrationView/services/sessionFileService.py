"""Read and write session files: File > Save and File > Open.

A session file is small, readable JSON with a `.tvv` extension. Reading one
checks every value against what the controls accept, and a file that fails
says which entry and why, so nothing half-read ever reaches the window.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from structuralVibrationView.models.sessionState import (
    CameraState,
    PlaybackState,
    SessionState,
    Vector,
    sessionTabs,
)
from structuralVibrationView.models.vibrationModel import (
    MaterialProperties,
    ModeSetting,
    StructureKind,
    StructureParameters,
    StructureSize,
)
from structuralVibrationView.services import settingsService, vibrationService

fileFormat = "structuralVibrationView.session"
# What the app wrote before it was renamed. Read, never written: a session
# saved by the old name still opens.
legacyFileFormat = "transverseVibrationView.session"
formatVersion = 1
fileExtension = ".tvv"
fileFilter = "Vibration View Sessions (*.tvv);;All Files (*)"
lastFolderKey = "session/lastFolder"


class SessionFileError(ValueError):
    """A session file that cannot be opened, with the reason in words."""


# ----- writing -------------------------------------------------------------------


def sessionToDict(state: SessionState) -> dict[str, Any]:
    size, material = state.structure.size, state.structure.material
    data: dict[str, Any] = {
        "format": fileFormat,
        "version": formatVersion,
        "structure": {"kind": state.kind.value},
        "openTab": state.openTab,
        "modalSuperposition": {
            "dampingRatio": state.dampingRatio,
            "modes": [
                {"mode": m.modeNumber, "amplitude": m.amplitude, "phaseDegrees": m.phaseDegrees}
                for m in state.modes
            ],
        },
        "structureParameters": {
            "selectedMode": state.selectedMode,
            "length": size.length,
            "width": size.width,
            "thickness": size.thickness,
            "density": material.density,
            "youngsModulus": material.youngsModulus,
            "poissonRatio": material.poissonRatio,
            "springStiffness": state.structure.springStiffness,
        },
        "playback": {
            "speed": state.playback.speed,
            "playing": state.playback.playing,
            "timeSeconds": state.playback.timeSeconds,
        },
    }
    if state.camera is not None:
        data["camera"] = {
            "position": list(state.camera.position),
            "focalPoint": list(state.camera.focalPoint),
            "viewUp": list(state.camera.viewUp),
        }
    return data


def saveSession(path: Path, state: SessionState) -> None:
    text = json.dumps(sessionToDict(state), indent=2)
    Path(path).write_text(text + "\n", encoding="utf-8")


# ----- reading -------------------------------------------------------------------


def loadSession(path: Path) -> SessionState:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        raise SessionFileError(f"The file could not be read. {error.strerror or error}.") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise SessionFileError(
            f"The file is not a session: it is not valid JSON (line {error.lineno})."
        ) from error
    return sessionFromDict(data)


def sessionFromDict(data: Any) -> SessionState:
    if not isinstance(data, dict) or data.get("format") not in (fileFormat, legacyFileFormat):
        raise SessionFileError(
            "The file is not a Structural Vibration View session."
        )
    version = data.get("version")
    if version != formatVersion:
        raise SessionFileError(
            f"The file is session version {version}, and this app reads version "
            f"{formatVersion}. It was probably saved by a newer version of the app."
        )
    structure = section(data, "structure")
    modal = section(data, "modalSuperposition")
    parameters = section(data, "structureParameters")
    playback = section(data, "playback")

    kindText = field(structure, "structure", "kind", str)
    try:
        kind = StructureKind(kindText)
    except ValueError:
        choices = ", ".join(k.value for k in StructureKind)
        raise SessionFileError(
            f"structure.kind is '{kindText}', which is not one of: {choices}."
        ) from None

    openTab = field(data, "", "openTab", str)
    if openTab not in sessionTabs:
        raise SessionFileError(f"openTab must be one of {', '.join(sessionTabs)}, not '{openTab}'.")

    size = StructureSize(
        length=number(parameters, "structureParameters", "length", vibrationService.lengthRange),
        width=number(parameters, "structureParameters", "width", vibrationService.widthRange),
        thickness=number(
            parameters, "structureParameters", "thickness", vibrationService.thicknessRange
        ),
    )
    stiffness = optionalNumber(
        parameters,
        "structureParameters",
        "springStiffness",
        vibrationService.springStiffnessRange,
        vibrationService.defaultSpringStiffness,
    )
    material = MaterialProperties(
        density=number(parameters, "structureParameters", "density", vibrationService.densityRange),
        youngsModulus=number(
            parameters, "structureParameters", "youngsModulus", vibrationService.youngsModulusRange
        ),
        poissonRatio=number(
            parameters, "structureParameters", "poissonRatio", vibrationService.poissonRatioRange
        ),
    )

    return SessionState(
        kind=kind,
        openTab=openTab,
        dampingRatio=number(modal, "modalSuperposition", "dampingRatio",
                            vibrationService.dampingRange),
        modes=readModes(modal, kind),
        selectedMode=integer(parameters, "structureParameters", "selectedMode",
                             (1, vibrationService.selectableModeCount)),
        structure=StructureParameters(
            size=size, material=material, springStiffness=stiffness
        ),
        playback=PlaybackState(
            speed=number(playback, "playback", "speed", vibrationService.speedRange),
            playing=field(playback, "playback", "playing", bool),
            timeSeconds=number(playback, "playback", "timeSeconds", (0.0, math.inf)),
        ),
        camera=readCamera(data.get("camera")),
    )


def readModes(modal: dict[str, Any], kind: StructureKind) -> tuple[ModeSetting, ...]:
    rows = field(modal, "modalSuperposition", "modes", list)
    count = vibrationService.superposedModeCount
    if len(rows) != count:
        raise SessionFileError(
            f"modalSuperposition.modes must list {count} modes, not {len(rows)}."
        )
    modes = []
    for index, row in enumerate(rows):
        where = f"modalSuperposition.modes[{index}]"
        if not isinstance(row, dict):
            raise SessionFileError(f"{where} must be an object with mode, amplitude and phase.")
        modes.append(ModeSetting(
            modeNumber=integer(
                row, where, "mode", (1, vibrationService.maxModeNumber(kind))
            ),
            amplitude=number(row, where, "amplitude", vibrationService.amplitudeRange),
            phaseDegrees=number(row, where, "phaseDegrees", vibrationService.phaseRange),
        ))
    return tuple(modes)


def readCamera(camera: Any) -> CameraState | None:
    """The camera is optional: a file without one opens with the view as it is."""
    if camera is None:
        return None
    if not isinstance(camera, dict):
        raise SessionFileError("camera must be an object with position, focalPoint and viewUp.")
    return CameraState(
        position=vector(camera, "position"),
        focalPoint=vector(camera, "focalPoint"),
        viewUp=vector(camera, "viewUp"),
    )


# ----- field checks -----------------------------------------------------------


def optionalNumber(
    data: dict[str, Any],
    where: str,
    name: str,
    valueRange: tuple[float, float],
    fallback: float,
) -> float:
    """A value a session may not carry: files written before it existed."""
    if name not in data:
        return fallback
    return number(data, where, name, valueRange)


def section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise SessionFileError(f"The file has no '{name}' section.")
    return value


def field(data: dict[str, Any], where: str, name: str, kind: type) -> Any:
    label = f"{where}.{name}" if where else name
    if name not in data:
        raise SessionFileError(f"{label} is missing.")
    value = data[name]
    # bool is an int in Python; keep true/false out of number fields and back.
    if (kind is not bool and isinstance(value, bool)) or not isinstance(value, kind):
        raise SessionFileError(f"{label} must be {kindName(kind)}, not {value!r}.")
    return value


def number(data: dict[str, Any], where: str, name: str, valueRange: tuple[float, float]) -> float:
    label = f"{where}.{name}"
    if name not in data:
        raise SessionFileError(f"{label} is missing.")
    value = data[name]
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise SessionFileError(f"{label} must be a number, not {value!r}.")
    low, high = valueRange
    if not low <= value <= high:
        upper = "" if math.isinf(high) else f" and at most {high:g}"
        raise SessionFileError(f"{label} must be at least {low:g}{upper}, not {value:g}.")
    return float(value)


def integer(data: dict[str, Any], where: str, name: str, valueRange: tuple[int, int]) -> int:
    value = number(data, where, name, valueRange)
    if value != int(value):
        raise SessionFileError(f"{where}.{name} must be a whole number, not {value:g}.")
    return int(value)


def vector(camera: dict[str, Any], name: str) -> Vector:
    value = camera.get(name)
    if (
        not isinstance(value, list)
        or len(value) != 3
        or not all(isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)
                   for v in value)
    ):
        raise SessionFileError(f"camera.{name} must be a list of three numbers.")
    return (float(value[0]), float(value[1]), float(value[2]))


def kindName(kind: type) -> str:
    return {str: "text", bool: "true or false", list: "a list", dict: "an object"}.get(
        kind, kind.__name__
    )


# ----- where the dialogs start ---------------------------------------------------


def loadLastFolder() -> Path | None:
    """The folder a session was last opened from or saved to, if it still exists."""
    value = settingsService.openSettings().value(lastFolderKey, "")
    folder = Path(str(value)) if value else None
    return folder if folder is not None and folder.is_dir() else None


def saveLastFolder(folder: Path) -> None:
    settingsService.writeValue(lastFolderKey, str(folder))
