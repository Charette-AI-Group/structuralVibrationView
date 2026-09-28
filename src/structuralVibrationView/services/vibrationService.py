"""What the app asks about a vibrating structure, whichever kind it is.

The mathematics lives in `services/systems/`, one module per family: beams,
plates, and the spring-mass oscillator. This module holds what they share -
the limits the inputs accept, the app's defaults, and the assembly of a
`VibrationModel` from a `VibrationSetup` - and delegates the rest, so nothing
above it needs to know which kind of structure is on screen.
"""

from __future__ import annotations

import math

import numpy as np

from structuralVibrationView.models.vibrationModel import (
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
from structuralVibrationView.services.systems import systemFor

# How many modes the Structure Parameters tab offers on their own, for a
# system that has that many.
selectableModeCount = 5
# How many rows the Modal Superposition tab adds together.
superposedModeCount = 3
# What the Modal Superposition and Playback inputs accept: (minimum, maximum).
amplitudeRange = (0.0, 0.3)  # fraction of the length
phaseRange = (-180.0, 180.0)  # degrees
dampingRange = (0.0, 0.5)  # damping ratio
speedRange = (0.05, 5.0)  # times the slow-motion pace

# Defaults until the user sets their own, which are then remembered. One size
# for every kind, so switching kind keeps what the user chose. Metres; the
# length is the reference for amplitudes.
defaultSize = StructureSize(length=0.3, width=0.01, thickness=0.003)
# Aluminium.
defaultMaterial = MaterialProperties(density=2700.0, youngsModulus=7.0e10, poissonRatio=0.33)
defaultSpringStiffness = 1000.0  # N/m
defaultStructureParameters = StructureParameters(
    size=defaultSize, material=defaultMaterial, springStiffness=defaultSpringStiffness
)

# Peak displacement of a mode shown on its own, as a fraction of the length.
singleModeAmplitude = 0.05

# What the inputs accept: (minimum, maximum). Metres, kg/m^3 and N/m^2.
lengthRange = (0.01, 10.0)
widthRange = (0.001, 5.0)
thicknessRange = (0.0001, 0.5)
densityRange = (1.0, 25000.0)  # aerogel to osmium, with room either side
youngsModulusRange = (1.0e5, 1.2e12)  # soft rubber to diamond
# An isotropic material needs -1 < nu < 0.5: auxetic foams to near-incompressible
# rubber. The ends themselves are excluded, since the plate formula divides by
# 1 - nu^2 and 0.5 would mean a material that cannot change volume.
poissonRatioRange = (-0.99, 0.499)
springStiffnessRange = (0.01, 1.0e9)  # N/m: a soft toy spring to a machine mount


def maxModeNumber(kind: StructureKind) -> int:
    """How many modes this kind has: one for an oscillator, six for a beam."""
    return systemFor(kind).modeCount(kind)


def parameterNamesFor(kind: StructureKind) -> tuple[str, ...]:
    """Which Structure Parameters rows this kind uses; the tab hides the rest."""
    return systemFor(kind).parameterNames


def lengthToWidthFor(kind: StructureKind) -> float:
    return systemFor(kind).lengthToWidth


def widthForKind(kind: StructureKind, length: float) -> float:
    """The width that gives `kind` its usual proportions, within the limits."""
    low, high = widthRange
    return min(max(length / lengthToWidthFor(kind), low), high)


# ----- what the inputs accept -------------------------------------------------


def checkInRange(name: str, value: float, valueRange: tuple[float, float], unit: str) -> None:
    low, high = valueRange
    if not low <= value <= high:
        units = f" {unit}" if unit else ""
        raise ValueError(
            f"{name} must be between {low:g}{units} and {high:g}{units}, not {value:g}{units}."
        )


def checkSize(size: StructureSize) -> None:
    """Refuse sizes a grid cannot be built from, saying which and why."""
    checkInRange("Length", size.length, lengthRange, "m")
    checkInRange("Width", size.width, widthRange, "m")
    checkInRange("Thickness", size.thickness, thicknessRange, "m")


def checkMaterial(material: MaterialProperties) -> None:
    checkInRange("Density", material.density, densityRange, "kg/m^3")
    checkInRange("Young's modulus", material.youngsModulus, youngsModulusRange, "N/m^2")
    checkInRange("Poisson's ratio", material.poissonRatio, poissonRatioRange, "")


def checkStructureParameters(parameters: StructureParameters) -> None:
    checkSize(parameters.size)
    checkMaterial(parameters.material)
    checkInRange("Spring stiffness", parameters.springStiffness, springStiffnessRange, "N/m")


# ----- geometry, frequencies and shapes ---------------------------------------


def parametersOf(setup: VibrationSetup) -> StructureParameters:
    """The setup's parameters, with the app's defaults where it has none."""
    return StructureParameters(
        size=setup.size or defaultSize,
        material=setup.material or defaultMaterial,
        springStiffness=(
            defaultSpringStiffness if setup.springStiffness is None else setup.springStiffness
        ),
    )


def buildGeometry(
    kind: StructureKind, parameters: StructureParameters | None = None
) -> StructureGeometry:
    """The undeformed structure, as the parts its system draws it in."""
    parameters = parameters or defaultStructureParameters
    checkSize(parameters.size)
    size = parameters.size
    return StructureGeometry(
        kind=kind,
        length=size.length,
        width=size.width,
        thickness=size.thickness,
        parts=systemFor(kind).buildParts(kind, parameters),
    )


def naturalFrequencyHz(
    kind: StructureKind, modeNumber: int, parameters: StructureParameters
) -> float:
    """Mode `modeNumber` (1 is the lowest) of the given structure, in hertz."""
    system = systemFor(kind)
    modeNumber = min(max(modeNumber, 1), system.modeCount(kind))
    return system.naturalFrequencyHz(kind, modeNumber, parameters)


def modalTerm(
    geometry: StructureGeometry, parameters: StructureParameters, mode: ModeSetting
) -> ModalTerm:
    """Evaluate one mode on the geometry, with its frequency and label."""
    kind = geometry.kind
    system = systemFor(kind)
    modeNumber = min(max(mode.modeNumber, 1), system.modeCount(kind))
    return ModalTerm(
        modeNumber=modeNumber,
        label=system.modeLabel(kind, modeNumber, parameters),
        frequencyHz=system.naturalFrequencyHz(kind, modeNumber, parameters),
        amplitude=mode.amplitude,
        phaseRadians=math.radians(mode.phaseDegrees),
        shapes=system.modeShapes(kind, modeNumber, geometry),
    )


def buildModel(setup: VibrationSetup) -> VibrationModel:
    parameters = parametersOf(setup)
    checkMaterial(parameters.material)
    checkInRange(
        "Spring stiffness", parameters.springStiffness, springStiffnessRange, "N/m"
    )
    geometry = buildGeometry(setup.kind, parameters)
    terms = tuple(modalTerm(geometry, parameters, mode) for mode in setup.activeModes)
    fundamental = naturalFrequencyHz(setup.kind, 1, parameters)
    reference = terms[0].frequencyHz if setup.singleMode and terms else fundamental
    return VibrationModel(
        setup=setup,
        geometry=geometry,
        fundamentalFrequencyHz=fundamental,
        referenceFrequencyHz=reference,
        terms=terms,
    )


# ----- the structure at one instant -------------------------------------------


def displacementAt(model: VibrationModel, timeSeconds: float) -> tuple[np.ndarray, ...]:
    """Transverse displacement of every point at one instant, one array per part.

    Free vibration: each mode oscillates at its own frequency, decaying with
    the damping ratio. Nothing is precomputed per frame, so time is continuous
    and the animation never has a loop seam.
    """
    length = model.geometry.length
    zeta = model.setup.dampingRatio
    displacement = [np.zeros(part.pointCount) for part in model.geometry.parts]
    for term in model.terms:
        omega = 2.0 * math.pi * term.frequencyHz
        decay = math.exp(-zeta * omega * timeSeconds) if zeta > 0.0 else 1.0
        swing = (
            term.amplitude * length * decay
            * math.cos(omega * timeSeconds + term.phaseRadians)
        )
        for index, shape in enumerate(term.shapes):
            displacement[index] = displacement[index] + swing * shape
    return tuple(displacement)


def deformedPoints(
    model: VibrationModel, timeSeconds: float
) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
    """Per part: (points (N, 3), displacement (N,)), the motion along z."""
    displacement = displacementAt(model, timeSeconds)
    moved = []
    for part, w in zip(model.geometry.parts, displacement, strict=True):
        points = part.points.copy()
        points[:, 2] += w
        moved.append((points, w))
    return tuple(moved)


def describeModel(model: VibrationModel) -> str:
    """One line for the status bar: what is moving and how fast."""
    if not model.terms:
        return f"{model.setup.kind.value}: no mode has an amplitude, so nothing moves."
    parts = [f"{term.label} at {formatFrequency(term.frequencyHz)}" for term in model.terms]
    return f"{model.setup.kind.value}: " + ", ".join(parts)


def formatFrequency(hertz: float) -> str:
    """Three significant figures, in Hz or kHz, never in exponent notation."""
    if hertz >= 1000.0:
        return f"{hertz / 1000.0:.3g} kHz"
    if hertz >= 100.0:
        return f"{hertz:.0f} Hz"
    if hertz >= 10.0:
        return f"{hertz:.1f} Hz"
    return f"{hertz:.2f} Hz"
