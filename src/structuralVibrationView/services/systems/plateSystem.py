"""Kirchhoff plates: simply supported on all four edges, or clamped on all four.

    f_mn = lambda_mn / (2 pi a^2) sqrt(D / (rho h)),  D = E h^3 / (12 (1 - nu^2))

The simply supported plate has an exact lambda. The clamped plate has none,
so it uses the standard approximation: mode shapes as products of
clamped-clamped beam functions, and Warburton's (1954) formula for lambda,
which is within about 1 % of the published exact values. Poisson's ratio
cancels out of that formula for clamped edges, and reaches the frequency only
through the bending stiffness.
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
    poissonRatioParameter,
    thicknessParameter,
    widthParameter,
    youngsModulusParameter,
)
from structuralVibrationView.services.systems.beamSystem import beamModeShape
from structuralVibrationView.services.systems.vibrationSystem import (
    VibrationSystem,
    normalise,
)

plateModeCount = 6
plateDimensions = (41, 25, 2)
plateName = "plate"


def warburtonTerms(index: int) -> tuple[float, float]:
    """(G, H) for a clamped-clamped edge pair, from Warburton's tables.

    The first mode's pair is tabulated rather than taken from the general
    expression, which only holds from the second mode up. H and J are equal
    for clamped edges, which is why Poisson's ratio drops out.
    """
    if index == 1:
        return 1.506, 1.248
    g = index + 0.5
    return g, g**2 * (1.0 - 2.0 / (g * math.pi))


def plateFrequencyParameter(
    kind: StructureKind, mn: tuple[int, int], length: float, width: float
) -> float:
    """Dimensionless lambda = omega a^2 sqrt(rho h / D): the shape's share.

    Everything the edges and the proportions contribute, with the material
    and the thickness left to the caller.
    """
    m, n = mn
    ratio = length / width
    if kind is StructureKind.clampedPlate:
        gx, hx = warburtonTerms(m)
        gy, hy = warburtonTerms(n)
        return math.pi**2 * math.sqrt(gx**4 + gy**4 * ratio**4 + 2.0 * ratio**2 * hx * hy)
    return math.pi**2 * (m**2 + (n * ratio) ** 2)


def plateModeOrder(kind: StructureKind, length: float, width: float) -> list[tuple[int, int]]:
    """(m, n) half-wave pairs of a plate, lowest frequency first."""
    pairs = [(m, n) for m in range(1, plateModeCount + 1) for n in range(1, plateModeCount + 1)]
    pairs.sort(key=lambda mn: plateFrequencyParameter(kind, mn, length, width))
    return pairs[:plateModeCount]


def plateModeShape(
    kind: StructureKind,
    mn: tuple[int, int],
    x: np.ndarray,
    y: np.ndarray,
    length: float,
    width: float,
) -> np.ndarray:
    """A product of one-dimensional shapes, one per direction."""
    m, n = mn
    # y runs from -width/2 to +width/2; the plate edge is at -width/2.
    across = y + width / 2
    if kind is StructureKind.clampedPlate:
        shape = beamModeShape(StructureKind.clampedBeam, m, x, length) * beamModeShape(
            StructureKind.clampedBeam, n, across, width
        )
    else:
        shape = np.sin(m * math.pi * x / length) * np.sin(n * math.pi * across / width)
    return normalise(shape)


class PlateSystem(VibrationSystem):
    kinds = (StructureKind.simplySupportedPlate, StructureKind.clampedPlate)
    parameterNames = (
        lengthParameter,
        widthParameter,
        thicknessParameter,
        densityParameter,
        youngsModulusParameter,
        poissonRatioParameter,
    )
    # A plate wants a width within a couple of times its length, or it spans
    # one way and behaves as a beam strip, where plate theory is the wrong tool.
    lengthToWidth = 2.0

    def modeCount(self, kind: StructureKind) -> int:
        return plateModeCount

    def buildParts(
        self, kind: StructureKind, parameters: StructureParameters
    ) -> tuple[GeometryPart, ...]:
        size = parameters.size
        xs = np.linspace(0.0, size.length, plateDimensions[0])
        ys = np.linspace(-size.width / 2, size.width / 2, plateDimensions[1])
        zs = np.linspace(-size.thickness / 2, size.thickness / 2, plateDimensions[2])
        xx, yy, zz = np.meshgrid(xs, ys, zs, indexing="ij")
        points = np.column_stack(
            [xx.ravel(order="F"), yy.ravel(order="F"), zz.ravel(order="F")]
        )
        return (GeometryPart(plateName, plateDimensions, points),)

    def naturalFrequencyHz(
        self, kind: StructureKind, modeNumber: int, parameters: StructureParameters
    ) -> float:
        size, material = parameters.size, parameters.material
        mn = plateModeOrder(kind, size.length, size.width)[modeNumber - 1]
        h = size.thickness
        nu = material.poissonRatio
        bendingStiffness = material.youngsModulus * h**3 / (12.0 * (1.0 - nu**2))
        omega = (
            plateFrequencyParameter(kind, mn, size.length, size.width)
            / size.length**2
            * math.sqrt(bendingStiffness / (material.density * h))
        )
        return omega / (2.0 * math.pi)

    def modeShapes(
        self, kind: StructureKind, modeNumber: int, geometry: StructureGeometry
    ) -> tuple[np.ndarray, ...]:
        part = geometry.part
        mn = plateModeOrder(kind, geometry.length, geometry.width)[modeNumber - 1]
        return (
            plateModeShape(
                kind, mn, part.x, part.y, geometry.length, geometry.width
            ),
        )

    def modeLabel(
        self, kind: StructureKind, modeNumber: int, parameters: StructureParameters
    ) -> str:
        size = parameters.size
        m, n = plateModeOrder(kind, size.length, size.width)[modeNumber - 1]
        return f"Mode {modeNumber} ({m},{n})"
