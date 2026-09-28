"""Tests for the systems behind the structures, and for the spring-mass.

What every system must answer is checked once for all of them, so a system
added later is held to the same contract without new tests.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from structuralVibrationView.models.vibrationModel import (
    MaterialProperties,
    ModeSetting,
    StructureKind,
    StructureParameters,
    StructureSize,
    VibrationSetup,
    springStiffnessParameter,
)
from structuralVibrationView.services import vibrationService
from structuralVibrationView.services.systems import allSystems, systemFor
from structuralVibrationView.services.systems.springMassSystem import (
    SpringMassSystem,
    blockMass,
    blockName,
    coilName,
)

parameters = StructureParameters(
    size=StructureSize(0.3, 0.1, 0.003),
    material=MaterialProperties(2700.0, 7.0e10, 0.33),
    springStiffness=1000.0,
)


# ----- the contract every system keeps ---------------------------------------


def testEveryKindHasExactlyOneSystem() -> None:
    for kind in StructureKind:
        handlers = [system for system in allSystems if system.handles(kind)]
        assert len(handlers) == 1, kind.value
        assert systemFor(kind) is handlers[0]


@pytest.mark.parametrize("kind", list(StructureKind))
def testASystemDrawsWhatItCanMove(kind) -> None:
    """Every part has points, a grid that fits them, and a shape to move them."""
    system = systemFor(kind)
    geometry = vibrationService.buildGeometry(kind, parameters)
    shapes = system.modeShapes(kind, 1, geometry)

    assert geometry.parts
    assert len(shapes) == len(geometry.parts)
    for part, shape in zip(geometry.parts, shapes, strict=True):
        nx, ny, nz = part.dimensions
        assert part.pointCount == nx * ny * nz
        assert part.points.shape == (part.pointCount, 3)
        assert shape.shape == (part.pointCount,)
    assert math.isclose(max(float(np.max(np.abs(shape))) for shape in shapes), 1.0)


@pytest.mark.parametrize("kind", list(StructureKind))
def testASystemNamesItsModesAndRaisesTheirFrequencies(kind) -> None:
    system = systemFor(kind)
    modes = system.modeCount(kind)

    assert modes >= 1
    previous = 0.0
    for mode in range(1, modes + 1):
        hertz = system.naturalFrequencyHz(kind, mode, parameters)
        assert hertz > previous, f"{kind.value} mode {mode}"
        assert system.modeLabel(kind, mode, parameters).startswith(f"Mode {mode}")
        previous = hertz


@pytest.mark.parametrize("kind", list(StructureKind))
def testASystemUsesTheParametersItNames(kind) -> None:
    """A row a system does not name must not change its frequencies."""
    system = systemFor(kind)
    named = set(system.parameterNames)
    unnamed = {
        "youngsModulus": MaterialProperties(2700.0, 2.0e11, 0.33),
        "poissonRatio": MaterialProperties(2700.0, 7.0e10, 0.10),
    }
    base = system.naturalFrequencyHz(kind, 1, parameters)

    for name, material in unnamed.items():
        changed = system.naturalFrequencyHz(
            kind, 1, StructureParameters(parameters.size, material, parameters.springStiffness)
        )
        if name in named:
            assert changed != base, f"{kind.value} says it uses {name}"
        else:
            assert changed == base, f"{kind.value} does not say it uses {name}"


# ----- the spring-mass system -------------------------------------------------


def testTheOscillatorHasOneModeAtTheTextbookFrequency() -> None:
    system = SpringMassSystem()
    kind = StructureKind.springMass

    assert system.modeCount(kind) == 1
    mass = blockMass(parameters)
    expected = math.sqrt(parameters.springStiffness / mass) / (2.0 * math.pi)
    assert system.naturalFrequencyHz(kind, 1, parameters) == pytest.approx(expected)


def testItsMassIsTheBlockTheUserSized() -> None:
    """Density and width, not a number of its own to keep in step."""
    width = parameters.size.width
    expected = parameters.material.density * width**2 * (width / 2)

    assert blockMass(parameters) == pytest.approx(expected)


def testFourTimesTheStiffnessDoublesTheFrequency() -> None:
    kind = StructureKind.springMass
    soft = vibrationService.naturalFrequencyHz(kind, 1, parameters)
    stiff = vibrationService.naturalFrequencyHz(
        kind,
        1,
        StructureParameters(
            parameters.size, parameters.material, parameters.springStiffness * 4
        ),
    )

    assert stiff == pytest.approx(2 * soft)


def testItIsDrawnAsACoilAndABlock() -> None:
    geometry = vibrationService.buildGeometry(StructureKind.springMass, parameters)
    coil, block = geometry.parts

    assert (coil.name, block.name) == (coilName, blockName)
    # The coil winds about the axis and rises to the block, which sits on top.
    assert coil.z.min() == pytest.approx(-parameters.size.thickness / 2)
    assert coil.z.max() == pytest.approx(parameters.size.length + parameters.size.thickness / 2)
    assert np.hypot(coil.x, coil.y).max() < parameters.size.width / 2
    assert block.z.min() == pytest.approx(parameters.size.length)


def testTheBlockMovesAsOneAndTheSpringStretchesEvenly() -> None:
    geometry = vibrationService.buildGeometry(StructureKind.springMass, parameters)
    coil, block = geometry.parts
    coilShape, blockShape = systemFor(StructureKind.springMass).modeShapes(
        StructureKind.springMass, 1, geometry
    )

    assert np.allclose(blockShape, 1.0)  # rigid: every corner together
    # A massless spring stretches in proportion to height: the base is still.
    assert coilShape.min() == pytest.approx(0.0, abs=1e-3)
    assert coilShape.max() == pytest.approx(1.0, abs=1e-2)
    assert np.allclose(coilShape, np.clip(coil.z / geometry.length, 0.0, 1.0), atol=1e-9)


def testTheStiffnessRowIsItsOwn() -> None:
    """It is the only system that reads it, and it reads no Young's modulus."""
    for kind in StructureKind:
        names = vibrationService.parameterNamesFor(kind)
        assert (springStiffnessParameter in names) == (kind is StructureKind.springMass)


def testTheOscillatorAnimatesLikeEverythingElse() -> None:
    setup = VibrationSetup(
        kind=StructureKind.springMass,
        size=parameters.size,
        material=parameters.material,
        springStiffness=parameters.springStiffness,
        modes=(ModeSetting(1, 0.05),),
    )
    model = vibrationService.buildModel(setup)

    (coilPoints, coilW), (blockPoints, blockW) = vibrationService.deformedPoints(model, 0.0)

    peak = 0.05 * parameters.size.length
    assert np.allclose(blockW, peak)
    # The block has moved bodily up; the coil's base has not moved at all.
    assert blockPoints[:, 2].min() == pytest.approx(parameters.size.length + peak)
    assert coilW.min() == pytest.approx(0.0, abs=1e-4)
    # A quarter period later it is back through zero, as one oscillator is.
    quarter = 0.25 / model.fundamentalFrequencyHz
    assert np.allclose(np.concatenate(vibrationService.displacementAt(model, quarter)), 0.0,
                       atol=1e-9)
