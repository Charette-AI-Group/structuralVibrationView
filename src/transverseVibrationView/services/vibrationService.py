"""Closed-form transverse vibration of beams and plates.

Builds the undeformed grid, evaluates the analytic mode shapes on it, and
gives the displacement field at any instant. Pure NumPy so it is testable
without a window and could drive any renderer.

Beam modes are Euler-Bernoulli; the plate is a simply supported Kirchhoff
plate. Frequencies are relative to the fundamental the user sets, using the
theoretical ratios, so the demo stays honest about which mode moves faster
without needing material properties.
"""

from __future__ import annotations

import math

import numpy as np

from transverseVibrationView.models.vibrationModel import (
    MaterialProperties,
    ModalTerm,
    ModeSetting,
    StructureGeometry,
    StructureKind,
    StructureParameters,
    StructureSize,
    VibrationModel,
    VibrationSetup,
)

# Roots of the beam frequency equations, beta * L, for the first six modes.
cantileverRoots = (1.8751, 4.6941, 7.8548, 10.9955, 14.1372, 17.2788)
clampedRoots = (4.7300, 7.8532, 10.9956, 14.1372, 17.2788, 20.4204)
maxModeNumber = 6

# Defaults until the user sets their own, which are then remembered. One size
# for every kind, so switching kind keeps what the user chose. Metres; the
# length is the reference for amplitudes.
defaultSize = StructureSize(length=0.3, width=0.01, thickness=0.003)
# Aluminium.
defaultMaterial = MaterialProperties(density=2700.0, youngsModulus=7.0e10)
defaultStructureParameters = StructureParameters(size=defaultSize, material=defaultMaterial)

# Grid points along x, y and z. Fixed per kind so a size change only moves
# points, and the view can keep the mesh it already has.
beamDimensions = (61, 5, 3)
plateDimensions = (41, 25, 2)

# What the inputs accept: (minimum, maximum). Metres, kg/m^3 and N/m^2.
lengthRange = (0.01, 10.0)
widthRange = (0.001, 5.0)
thicknessRange = (0.0001, 0.5)
densityRange = (1.0, 25000.0)  # aerogel to osmium, with room either side
youngsModulusRange = (1.0e5, 1.2e12)  # soft rubber to diamond


def checkInRange(name: str, value: float, valueRange: tuple[float, float], unit: str) -> None:
    low, high = valueRange
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low:g} {unit} and {high:g} {unit}, "
                         f"not {value:g} {unit}.")


def checkSize(size: StructureSize) -> None:
    """Refuse sizes a grid cannot be built from, saying which and why."""
    checkInRange("Length", size.length, lengthRange, "m")
    checkInRange("Width", size.width, widthRange, "m")
    checkInRange("Thickness", size.thickness, thicknessRange, "m")


def checkMaterial(material: MaterialProperties) -> None:
    checkInRange("Density", material.density, densityRange, "kg/m^3")
    checkInRange("Young's modulus", material.youngsModulus, youngsModulusRange, "N/m^2")


def checkStructureParameters(parameters: StructureParameters) -> None:
    checkSize(parameters.size)
    checkMaterial(parameters.material)


def buildGeometry(kind: StructureKind, size: StructureSize | None = None) -> StructureGeometry:
    """An undeformed structured grid, points ordered with x varying fastest."""
    size = size or defaultSize
    checkSize(size)
    length, width, thickness = size.length, size.width, size.thickness
    dimensions = plateDimensions if kind.isPlate else beamDimensions
    xs = np.linspace(0.0, length, dimensions[0])
    ys = np.linspace(-width / 2, width / 2, dimensions[1])
    zs = np.linspace(-thickness / 2, thickness / 2, dimensions[2])
    xx, yy, zz = np.meshgrid(xs, ys, zs, indexing="ij")
    points = np.column_stack(
        [xx.ravel(order="F"), yy.ravel(order="F"), zz.ravel(order="F")]
    )
    return StructureGeometry(kind, length, width, thickness, dimensions, points)


def beamModeShape(kind: StructureKind, modeNumber: int, x: np.ndarray, length: float) -> np.ndarray:
    """Normalised mode shape of a beam along x in [0, length]."""
    xi = x / length
    if kind is StructureKind.simplySupportedBeam:
        shape = np.sin(modeNumber * math.pi * xi)
    else:
        roots = cantileverRoots if kind is StructureKind.cantileverBeam else clampedRoots
        beta = roots[modeNumber - 1]
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
    roots = cantileverRoots if kind is StructureKind.cantileverBeam else clampedRoots
    return (roots[modeNumber - 1] / roots[0]) ** 2


def plateModeOrder(length: float, width: float) -> list[tuple[int, int]]:
    """(m, n) half-wave pairs of a simply supported plate, lowest frequency first."""
    pairs = [(m, n) for m in range(1, maxModeNumber + 1) for n in range(1, maxModeNumber + 1)]
    pairs.sort(key=lambda mn: plateFrequencyParameter(mn, length, width))
    return pairs[:maxModeNumber]


def plateFrequencyParameter(mn: tuple[int, int], length: float, width: float) -> float:
    m, n = mn
    return (m / length) ** 2 + (n / width) ** 2


def plateModeShape(
    mn: tuple[int, int], x: np.ndarray, y: np.ndarray, length: float, width: float
) -> np.ndarray:
    m, n = mn
    # y runs from -width/2 to +width/2; the plate edge is at -width/2.
    shape = np.sin(m * math.pi * x / length) * np.sin(n * math.pi * (y + width / 2) / width)
    return normalise(shape)


def normalise(shape: np.ndarray) -> np.ndarray:
    peak = float(np.max(np.abs(shape)))
    return shape / peak if peak > 0.0 else shape


def modalTerm(setup: VibrationSetup, geometry: StructureGeometry, mode: ModeSetting) -> ModalTerm:
    """Evaluate one mode on the geometry, with its frequency and label."""
    modeNumber = min(max(mode.modeNumber, 1), maxModeNumber)
    if geometry.kind.isPlate:
        order = plateModeOrder(geometry.length, geometry.width)
        mn = order[modeNumber - 1]
        shape = plateModeShape(mn, geometry.x, geometry.y, geometry.length, geometry.width)
        ratio = math.sqrt(
            plateFrequencyParameter(mn, geometry.length, geometry.width)
            / plateFrequencyParameter(order[0], geometry.length, geometry.width)
        )
        label = f"Mode {modeNumber} ({mn[0]},{mn[1]})"
    else:
        shape = beamModeShape(geometry.kind, modeNumber, geometry.x, geometry.length)
        ratio = beamFrequencyRatio(geometry.kind, modeNumber)
        label = f"Mode {modeNumber}"
    return ModalTerm(
        modeNumber=modeNumber,
        label=label,
        frequencyHz=setup.fundamentalFrequencyHz * ratio,
        amplitude=mode.amplitude,
        phaseRadians=math.radians(mode.phaseDegrees),
        shape=shape,
    )


def buildModel(setup: VibrationSetup) -> VibrationModel:
    checkMaterial(setup.material or defaultMaterial)
    geometry = buildGeometry(setup.kind, setup.size)
    terms = tuple(modalTerm(setup, geometry, mode) for mode in setup.activeModes)
    return VibrationModel(setup=setup, geometry=geometry, terms=terms)


def displacementAt(model: VibrationModel, timeSeconds: float) -> np.ndarray:
    """Transverse displacement (N,) of every grid point at one instant.

    Free vibration: each mode oscillates at its own frequency, decaying with
    the damping ratio. Nothing is precomputed per frame, so time is continuous
    and the animation never has a loop seam.
    """
    w = np.zeros(model.geometry.pointCount)
    length = model.geometry.length
    zeta = model.setup.dampingRatio
    for term in model.terms:
        omega = 2.0 * math.pi * term.frequencyHz
        decay = math.exp(-zeta * omega * timeSeconds) if zeta > 0.0 else 1.0
        w += term.amplitude * length * decay * term.shape * math.cos(
            omega * timeSeconds + term.phaseRadians
        )
    return w


def deformedPoints(model: VibrationModel, timeSeconds: float) -> tuple[np.ndarray, np.ndarray]:
    """(points (N, 3), displacement (N,)) with the transverse motion along z."""
    w = displacementAt(model, timeSeconds)
    points = model.geometry.points.copy()
    points[:, 2] += w
    return points, w


def describeModel(model: VibrationModel) -> str:
    """One line for the status bar: what is moving and how fast."""
    if not model.terms:
        return f"{model.setup.kind.value}: no mode has an amplitude, so nothing moves."
    parts = [f"{term.label} at {term.frequencyHz:.2f} Hz" for term in model.terms]
    return f"{model.setup.kind.value}: " + ", ".join(parts)
