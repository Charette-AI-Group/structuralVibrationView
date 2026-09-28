"""A spring and a mass: one degree of freedom.

    f = (1 / 2 pi) sqrt(k / m)

The lumped counterpart of the continuous structures, and the model each of
their modes reduces to. The spring is massless, so it carries no mode shape
of its own: the block moves as one, and a point of the coil follows in
proportion to how far up the coil it sits, which is what stretches it evenly.

The parameters are the ones already on the tab, read for this system:

* the block is a box of the width and half as tall, so its mass is
  density x width^2 x (width / 2) - the material's density, in the shape the
  user set
* the length is the spring's free height, and the amplitude is a fraction of
  it, as for every other system
* the thickness is the wire the coil is drawn with

Only the stiffness is its own, and the tab shows that row for this system
alone. Young's modulus and Poisson's ratio play no part: a spring rate is
given directly rather than derived from the wire.
"""

from __future__ import annotations

import math

import numpy as np

from structuralVibrationView.models.vibrationModel import (
    GeometryPart,
    StructureGeometry,
    StructureKind,
    StructureParameters,
    densityParameter,
    lengthParameter,
    springStiffnessParameter,
    thicknessParameter,
    widthParameter,
)
from structuralVibrationView.services.systems.vibrationSystem import (
    VibrationSystem,
    normaliseParts,
)

coilTurns = 6
pointsPerTurn = 24
coilDimensions = (coilTurns * pointsPerTurn + 1, 2, 2)
blockDimensions = (2, 2, 2)
coilName = "spring"
blockName = "mass"
# The block's height, as a fraction of its width.
blockHeightRatio = 0.5
# The coil's radius, as a fraction of the block's width: narrower than the
# block, so the block reads as sitting on the spring rather than in it.
coilRadiusRatio = 0.3


def blockMass(parameters: StructureParameters) -> float:
    """kg: the block's volume times the material's density."""
    width = parameters.size.width
    return parameters.material.density * width**2 * (width * blockHeightRatio)


def coilPoints(parameters: StructureParameters) -> np.ndarray:
    """A square-section wire wound into a helix, from the base to the block."""
    size = parameters.size
    radius = size.width * coilRadiusRatio
    wire = size.thickness
    angle = np.linspace(0.0, coilTurns * 2.0 * math.pi, coilDimensions[0])
    height = np.linspace(0.0, size.length, coilDimensions[0])
    points = []
    # The wire's own cross-section: out along the radius, and along the axis.
    for outward in (-wire / 2, wire / 2):
        for along in (-wire / 2, wire / 2):
            ring = radius + outward
            points.append(
                np.column_stack(
                    [ring * np.cos(angle), ring * np.sin(angle), height + along]
                )
            )
    # Fortran order over (alongTheHelix, outward, along): the grid's own order.
    return np.vstack(points)


def blockPoints(parameters: StructureParameters) -> np.ndarray:
    """The mass: a box resting on top of the spring."""
    size = parameters.size
    half = size.width / 2
    base = size.length
    top = base + size.width * blockHeightRatio
    xs, ys, zs = (-half, half), (-half, half), (base, top)
    xx, yy, zz = np.meshgrid(xs, ys, zs, indexing="ij")
    return np.column_stack([xx.ravel(order="F"), yy.ravel(order="F"), zz.ravel(order="F")])


class SpringMassSystem(VibrationSystem):
    kinds = (StructureKind.springMass,)
    parameterNames = (
        lengthParameter,
        widthParameter,
        thicknessParameter,
        densityParameter,
        springStiffnessParameter,
    )
    # A block as wide as the spring is tall: it reads as a weight on a spring.
    lengthToWidth = 3.0

    def modeCount(self, kind: StructureKind) -> int:
        return 1  # one degree of freedom, one mode

    def buildParts(
        self, kind: StructureKind, parameters: StructureParameters
    ) -> tuple[GeometryPart, ...]:
        return (
            GeometryPart(coilName, coilDimensions, coilPoints(parameters)),
            GeometryPart(blockName, blockDimensions, blockPoints(parameters)),
        )

    def naturalFrequencyHz(
        self, kind: StructureKind, modeNumber: int, parameters: StructureParameters
    ) -> float:
        mass = blockMass(parameters)
        return math.sqrt(parameters.springStiffness / mass) / (2.0 * math.pi)

    def modeShapes(
        self, kind: StructureKind, modeNumber: int, geometry: StructureGeometry
    ) -> tuple[np.ndarray, ...]:
        coil, block = geometry.parts
        # A massless spring stretches evenly: a coil point at height z moves
        # z / L as far as the block, which moves as one.
        return normaliseParts(
            (
                np.clip(coil.z / geometry.length, 0.0, 1.0),
                np.ones(block.pointCount),
            )
        )

    def modeLabel(
        self, kind: StructureKind, modeNumber: int, parameters: StructureParameters
    ) -> str:
        return "Mode 1"
