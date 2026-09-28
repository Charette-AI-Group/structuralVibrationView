"""Euler-Bernoulli beams: cantilever, simply supported, and clamped at both ends.

    f_n = (beta_n L)^2 / (2 pi L^2) * sqrt(E I / (rho A)),  I / A = t^2 / 12

so a beam's frequencies follow its length and thickness, its stiffness and
its density, but not its width, which cancels out of I / A.
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
    thicknessParameter,
    widthParameter,
    youngsModulusParameter,
)
from structuralVibrationView.services.systems.vibrationSystem import (
    VibrationSystem,
    normalise,
)

# Roots of the beam frequency equations, beta * L, for the first six modes.
cantileverRoots = (1.8751, 4.6941, 7.8548, 10.9955, 14.1372, 17.2788)
clampedRoots = (4.7300, 7.8532, 10.9956, 14.1372, 17.2788, 20.4204)
beamModeCount = 6
# Grid points along x, y and z. Fixed, so a size change only moves points and
# the view can keep the mesh it already has.
beamDimensions = (61, 5, 3)
beamName = "beam"


def betaL(kind: StructureKind, modeNumber: int) -> float:
    if kind is StructureKind.simplySupportedBeam:
        return modeNumber * math.pi
    roots = cantileverRoots if kind is StructureKind.cantileverBeam else clampedRoots
    return roots[modeNumber - 1]


def beamModeShape(
    kind: StructureKind, modeNumber: int, x: np.ndarray, length: float
) -> np.ndarray:
    """Normalised mode shape of a beam along x in [0, length]."""
    xi = x / length
    if kind is StructureKind.simplySupportedBeam:
        shape = np.sin(modeNumber * math.pi * xi)
    else:
        beta = betaL(kind, modeNumber)
        if kind is StructureKind.cantileverBeam:
            sigma = (math.cosh(beta) + math.cos(beta)) / (math.sinh(beta) + math.sin(beta))
        else:
            sigma = (math.cosh(beta) - math.cos(beta)) / (math.sinh(beta) - math.sin(beta))
        shape = (
            np.cosh(beta * xi) - np.cos(beta * xi)
            - sigma * (np.sinh(beta * xi) - np.sin(beta * xi))
        )
    return normalise(shape)


def beamFrequencyRatio(kind: StructureKind, modeNumber: int) -> float:
    """omega_n / omega_1 from theory."""
    if kind is StructureKind.simplySupportedBeam:
        return float(modeNumber**2)
    return (betaL(kind, modeNumber) / betaL(kind, 1)) ** 2


class BeamSystem(VibrationSystem):
    kinds = (
        StructureKind.cantileverBeam,
        StructureKind.simplySupportedBeam,
        StructureKind.clampedBeam,
    )
    parameterNames = (
        lengthParameter,
        widthParameter,
        thicknessParameter,
        densityParameter,
        youngsModulusParameter,
    )
    # A beam wants to be slender: the app's own default size, 0.3 m by 1 cm.
    lengthToWidth = 30.0

    def modeCount(self, kind: StructureKind) -> int:
        return beamModeCount

    def buildParts(
        self, kind: StructureKind, parameters: StructureParameters
    ) -> tuple[GeometryPart, ...]:
        size = parameters.size
        xs = np.linspace(0.0, size.length, beamDimensions[0])
        ys = np.linspace(-size.width / 2, size.width / 2, beamDimensions[1])
        zs = np.linspace(-size.thickness / 2, size.thickness / 2, beamDimensions[2])
        xx, yy, zz = np.meshgrid(xs, ys, zs, indexing="ij")
        points = np.column_stack(
            [xx.ravel(order="F"), yy.ravel(order="F"), zz.ravel(order="F")]
        )
        return (GeometryPart(beamName, beamDimensions, points),)

    def naturalFrequencyHz(
        self, kind: StructureKind, modeNumber: int, parameters: StructureParameters
    ) -> float:
        size, material = parameters.size, parameters.material
        stiffnessPerMass = (
            material.youngsModulus * size.thickness**2 / (12.0 * material.density)
        )
        omega = betaL(kind, modeNumber) ** 2 / size.length**2 * math.sqrt(stiffnessPerMass)
        return omega / (2.0 * math.pi)

    def modeShapes(
        self, kind: StructureKind, modeNumber: int, geometry: StructureGeometry
    ) -> tuple[np.ndarray, ...]:
        part = geometry.part
        return (beamModeShape(kind, modeNumber, part.x, geometry.length),)
