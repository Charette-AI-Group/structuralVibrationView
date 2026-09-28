"""What every vibrating system in the app has to be able to say.

A system answers five questions about a structure, and nothing else knows
which kind it is looking at:

* how many modes it has, and what each one is called
* what each mode's natural frequency is, from the user's parameters
* what it is drawn as: one or more grids of points
* how each mode moves those points
* which parameters it actually uses, so the tab can hide the rest

Beams and plates are continuous structures with a mode shape per point; the
spring-mass is a lumped model whose "mode shape" is the block moving as one.
Both fit, because the app only ever asks for points and a factor per point.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from structuralVibrationView.models.vibrationModel import (
    GeometryPart,
    StructureGeometry,
    StructureKind,
    StructureParameters,
)


def normalise(shape: np.ndarray) -> np.ndarray:
    """Scale so the largest |value| is 1, leaving a shape that is all zero."""
    peak = float(np.max(np.abs(shape)))
    return shape / peak if peak > 0.0 else shape


def normaliseParts(shapes: tuple[np.ndarray, ...]) -> tuple[np.ndarray, ...]:
    """Normalise across the parts together, so their motion stays relative."""
    peak = max((float(np.max(np.abs(shape))) for shape in shapes), default=0.0)
    if peak <= 0.0:
        return shapes
    return tuple(shape / peak for shape in shapes)


class VibrationSystem(ABC):
    """One family of structures: the beams, the plates, or the oscillator."""

    #: the kinds this system answers for
    kinds: tuple[StructureKind, ...] = ()
    #: the Structure Parameters rows it uses; the tab hides the others
    parameterNames: tuple[str, ...] = ()
    #: length over width when the user switches to one of these kinds
    lengthToWidth: float = 1.0

    def handles(self, kind: StructureKind) -> bool:
        return kind in self.kinds

    def modeCount(self, kind: StructureKind) -> int:
        """How many modes the app offers for this kind."""
        return 1

    @abstractmethod
    def buildParts(
        self, kind: StructureKind, parameters: StructureParameters
    ) -> tuple[GeometryPart, ...]:
        """The undeformed grids this structure is drawn as."""

    @abstractmethod
    def naturalFrequencyHz(
        self, kind: StructureKind, modeNumber: int, parameters: StructureParameters
    ) -> float:
        """Mode `modeNumber` (1 is the lowest), in hertz."""

    @abstractmethod
    def modeShapes(
        self, kind: StructureKind, modeNumber: int, geometry: StructureGeometry
    ) -> tuple[np.ndarray, ...]:
        """How far each point moves in that mode, one array per part."""

    def modeLabel(
        self, kind: StructureKind, modeNumber: int, parameters: StructureParameters
    ) -> str:
        """What to call the mode in the status bar and the mode list."""
        return f"Mode {modeNumber}"
