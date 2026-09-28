"""Everything the window shows, as plain data: what File > Save writes.

A session is the whole state of the controls plus what the view adds to it -
the structure's clock and the camera - so opening one puts the window back
exactly as it was.
"""

from __future__ import annotations

from dataclasses import dataclass

from structuralVibrationView.models.vibrationModel import (
    ModeSetting,
    StructureKind,
    StructureParameters,
)

modalSuperpositionTab = "Modal Superposition"
structureParametersTab = "Structure Parameters"
sessionTabs = (modalSuperpositionTab, structureParametersTab)

Vector = tuple[float, float, float]


@dataclass(frozen=True)
class PlaybackState:
    speed: float
    playing: bool
    timeSeconds: float  # structural time, not screen time


@dataclass(frozen=True)
class CameraState:
    position: Vector
    focalPoint: Vector
    viewUp: Vector


@dataclass(frozen=True)
class SessionState:
    kind: StructureKind
    openTab: str  # one of sessionTabs
    # Modal Superposition tab.
    dampingRatio: float
    modes: tuple[ModeSetting, ...]
    # Structure Parameters tab.
    selectedMode: int
    structure: StructureParameters
    playback: PlaybackState
    # None when a session is captured without a view, as the controls alone do.
    camera: CameraState | None = None
