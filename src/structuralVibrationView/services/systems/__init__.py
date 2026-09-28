"""The systems the app can animate, and how to find the right one.

Adding a system means writing one module here and listing it below: the
service, the view and the controls all work through `VibrationSystem` and
never ask what kind of structure they are looking at.
"""

from __future__ import annotations

from structuralVibrationView.models.vibrationModel import StructureKind
from structuralVibrationView.services.systems.beamSystem import BeamSystem
from structuralVibrationView.services.systems.plateSystem import PlateSystem
from structuralVibrationView.services.systems.springMassSystem import SpringMassSystem
from structuralVibrationView.services.systems.vibrationSystem import VibrationSystem

allSystems: tuple[VibrationSystem, ...] = (BeamSystem(), PlateSystem(), SpringMassSystem())


def systemFor(kind: StructureKind) -> VibrationSystem:
    for system in allSystems:
        if system.handles(kind):
            return system
    raise ValueError(f"No system handles {kind.value}")


__all__ = [
    "BeamSystem",
    "PlateSystem",
    "SpringMassSystem",
    "VibrationSystem",
    "allSystems",
    "systemFor",
]
