"""Plain data describing a vibrating structure and how it is animated.

Nothing here knows about Qt or VTK. The service turns a `VibrationSetup` into
a `StructureGeometry` plus mode-shape vectors; the view turns those into
pixels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np


class StructureKind(StrEnum):
    """The closed-form structures the demo can animate."""

    cantileverBeam = "Cantilever Beam"
    simplySupportedBeam = "Simply Supported Beam"
    clampedBeam = "Clamped-Clamped Beam"
    simplySupportedPlate = "Simply Supported Plate"

    @property
    def isPlate(self) -> bool:
        return self is StructureKind.simplySupportedPlate


@dataclass(frozen=True)
class ModeSetting:
    """One term of the modal superposition.

    `amplitude` is a fraction of the structure length, so 0.05 on a 1 m beam
    is a 50 mm tip deflection. Zero switches the mode off.
    """

    modeNumber: int = 1
    amplitude: float = 0.05
    phaseDegrees: float = 0.0


@dataclass(frozen=True)
class StructureSize:
    """Overall dimensions in metres: along x, across y, and through z."""

    length: float
    width: float
    thickness: float


@dataclass(frozen=True)
class MaterialProperties:
    """What the structure is made of, in SI units."""

    density: float  # kg/m^3
    youngsModulus: float  # N/m^2, the material stiffness
    # Dimensionless. Only the plate uses it; a beam's bending ignores it.
    poissonRatio: float = 0.33


@dataclass(frozen=True)
class StructureParameters:
    """Everything on the Structure Parameters tab: remembered between sessions."""

    size: StructureSize
    material: MaterialProperties


@dataclass(frozen=True)
class VibrationSetup:
    """Everything the user chooses. Frozen so a change is a new value.

    `size` and `material` None mean the app's defaults.
    """

    kind: StructureKind = StructureKind.cantileverBeam
    size: StructureSize | None = None
    material: MaterialProperties | None = None
    modes: tuple[ModeSetting, ...] = (
        ModeSetting(1, 0.05),
        ModeSetting(2, 0.0),
        ModeSetting(3, 0.0),
    )
    dampingRatio: float = 0.0
    # One mode studied on its own: the animation is paced by that mode, not mode 1.
    singleMode: bool = False

    @property
    def activeModes(self) -> tuple[ModeSetting, ...]:
        return tuple(mode for mode in self.modes if mode.amplitude > 0.0)


@dataclass(frozen=True)
class StructureGeometry:
    """An undeformed structured grid: points and the grid dimensions.

    `points` is (N, 3), ordered so that reshaping to `dimensions` (in
    Fortran order, as VTK expects) recovers the grid. `x` and `y` are the
    per-point coordinates the mode shapes are evaluated at.
    """

    kind: StructureKind
    length: float
    width: float
    thickness: float
    dimensions: tuple[int, int, int]
    points: np.ndarray

    @property
    def x(self) -> np.ndarray:
        return self.points[:, 0]

    @property
    def y(self) -> np.ndarray:
        return self.points[:, 1]

    @property
    def pointCount(self) -> int:
        return self.points.shape[0]


@dataclass(frozen=True)
class ModalTerm:
    """A mode shape evaluated on the geometry, ready to be scaled by time."""

    modeNumber: int
    label: str
    frequencyHz: float
    amplitude: float
    phaseRadians: float
    shape: np.ndarray  # (N,), normalised so max |shape| == 1


@dataclass(frozen=True)
class VibrationModel:
    """A geometry plus the modal terms that move it: what the view animates."""

    setup: VibrationSetup
    geometry: StructureGeometry
    # Mode 1, computed from the material and dimensions, active or not.
    fundamentalFrequencyHz: float
    # The frequency the slow motion is set by: the fundamental, or the mode
    # shown when a single mode is.
    referenceFrequencyHz: float
    terms: tuple[ModalTerm, ...] = field(default_factory=tuple)

    @property
    def maxDisplacement(self) -> float:
        """Worst-case |w| for a fixed colour scale, never zero."""
        total = sum(term.amplitude for term in self.terms) * self.geometry.length
        return max(total, 1e-9)
