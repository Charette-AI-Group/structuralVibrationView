"""Plain data describing a vibrating structure and how it is animated.

Nothing here knows about Qt or VTK. A system (see `services/systems/`) turns a
`VibrationSetup` into a `StructureGeometry` of one or more parts plus a mode
shape per part; the view turns those into pixels.

A beam or a plate is one part, a single curvilinear grid. A spring-mass is
two - the coil and the block - which is why geometry is a list rather than a
single mesh.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np


class StructureKind(StrEnum):
    """The systems the app can animate."""

    cantileverBeam = "Cantilever Beam"
    simplySupportedBeam = "Simply Supported Beam"
    clampedBeam = "Clamped-Clamped Beam"
    simplySupportedPlate = "Simply Supported Plate"
    clampedPlate = "Clamped Plate"
    springMass = "Spring-Mass (SDOF)"

    @property
    def isPlate(self) -> bool:
        return self in (StructureKind.simplySupportedPlate, StructureKind.clampedPlate)

    @property
    def isBeam(self) -> bool:
        return self in (
            StructureKind.cantileverBeam,
            StructureKind.simplySupportedBeam,
            StructureKind.clampedBeam,
        )


# The Structure Parameters tab's rows. A system names the ones it uses, and
# the tab shows those and hides the rest: a beam's frequency does not depend
# on Poisson's ratio, and an oscillator's does not depend on Young's modulus.
lengthParameter = "length"
widthParameter = "width"
thicknessParameter = "thickness"
densityParameter = "density"
youngsModulusParameter = "youngsModulus"
poissonRatioParameter = "poissonRatio"
springStiffnessParameter = "springStiffness"


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
    # Dimensionless. Only the plates use it; a beam's bending ignores it.
    poissonRatio: float = 0.33


@dataclass(frozen=True)
class StructureParameters:
    """Everything on the Structure Parameters tab: remembered between sessions."""

    size: StructureSize
    material: MaterialProperties
    # N/m, the spring of the spring-mass system. The other systems ignore it.
    springStiffness: float = 1000.0


@dataclass(frozen=True)
class VibrationSetup:
    """Everything the user chooses. Frozen so a change is a new value.

    `size`, `material` and `springStiffness` None mean the app's defaults.
    """

    kind: StructureKind = StructureKind.cantileverBeam
    size: StructureSize | None = None
    material: MaterialProperties | None = None
    springStiffness: float | None = None
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
class GeometryPart:
    """One curvilinear grid of the structure, drawn as one mesh.

    `points` is (N, 3), ordered so that reshaping to `dimensions` (in Fortran
    order, as VTK expects) recovers the grid.
    """

    name: str
    dimensions: tuple[int, int, int]
    points: np.ndarray

    @property
    def x(self) -> np.ndarray:
        return self.points[:, 0]

    @property
    def y(self) -> np.ndarray:
        return self.points[:, 1]

    @property
    def z(self) -> np.ndarray:
        return self.points[:, 2]

    @property
    def pointCount(self) -> int:
        return self.points.shape[0]


@dataclass(frozen=True)
class StructureGeometry:
    """The undeformed structure: its overall size and the parts it is drawn as."""

    kind: StructureKind
    length: float
    width: float
    thickness: float
    parts: tuple[GeometryPart, ...]

    @property
    def part(self) -> GeometryPart:
        """The only part, for the systems that have exactly one."""
        if len(self.parts) != 1:
            raise ValueError(f"{self.kind.value} is drawn as {len(self.parts)} parts")
        return self.part0

    @property
    def part0(self) -> GeometryPart:
        return self.parts[0]

    @property
    def dimensions(self) -> tuple[int, int, int]:
        return self.part.dimensions

    @property
    def points(self) -> np.ndarray:
        if len(self.parts) == 1:
            return self.part0.points
        return np.vstack([part.points for part in self.parts])

    @property
    def x(self) -> np.ndarray:
        return self.points[:, 0]

    @property
    def y(self) -> np.ndarray:
        return self.points[:, 1]

    @property
    def pointCount(self) -> int:
        return sum(part.pointCount for part in self.parts)


@dataclass(frozen=True)
class ModalTerm:
    """A mode shape evaluated on the geometry, ready to be scaled by time."""

    modeNumber: int
    label: str
    frequencyHz: float
    amplitude: float
    phaseRadians: float
    # One array per geometry part, each normalised so the largest |value| is 1
    # across the whole structure.
    shapes: tuple[np.ndarray, ...]


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
