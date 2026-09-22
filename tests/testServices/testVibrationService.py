"""Tests for the closed-form vibration service. No Qt, no VTK."""

from __future__ import annotations

import math

import numpy as np
import pytest

from transverseVibrationView.models.vibrationModel import (
    MaterialProperties,
    ModeSetting,
    StructureKind,
    StructureSize,
    VibrationSetup,
)
from transverseVibrationView.services import vibrationService


@pytest.mark.parametrize("kind", list(StructureKind))
def testGeometryIsAGridWithXVaryingFastest(kind) -> None:
    """VTK reads a structured grid in that order; get it wrong and the mesh is spaghetti."""
    geometry = vibrationService.buildGeometry(kind)
    nx, ny, nz = geometry.dimensions

    assert geometry.pointCount == nx * ny * nz
    # The first nx points walk along x at the same y and z.
    firstRow = geometry.points[:nx]
    assert np.allclose(firstRow[:, 1], firstRow[0, 1])
    assert np.allclose(firstRow[:, 2], firstRow[0, 2])
    assert firstRow[0, 0] == 0.0
    assert math.isclose(firstRow[-1, 0], geometry.length)


def testCantileverModeIsFixedAtTheRootAndFreeAtTheTip() -> None:
    x = np.linspace(0.0, 1.0, 201)
    shape = vibrationService.beamModeShape(StructureKind.cantileverBeam, 1, x, 1.0)

    assert math.isclose(shape[0], 0.0, abs_tol=1e-9)
    assert math.isclose(abs(shape[-1]), 1.0, abs_tol=1e-6)
    # First mode has no interior node.
    assert np.all(shape[1:] * shape[-1] > 0)


def testClampedBeamIsFixedAtBothEnds() -> None:
    x = np.linspace(0.0, 1.0, 201)
    for mode in (1, 2, 3):
        shape = vibrationService.beamModeShape(StructureKind.clampedBeam, mode, x, 1.0)
        assert math.isclose(shape[0], 0.0, abs_tol=1e-6)
        assert math.isclose(shape[-1], 0.0, abs_tol=1e-3)
        assert math.isclose(float(np.max(np.abs(shape))), 1.0)


def testSimplySupportedModeNHasNMinusOneInteriorNodes() -> None:
    x = np.linspace(0.0, 1.0, 1001)
    for mode in (1, 2, 3, 4):
        shape = vibrationService.beamModeShape(StructureKind.simplySupportedBeam, mode, x, 1.0)
        signChanges = int(np.sum(np.diff(np.sign(shape[1:-1])) != 0))
        assert signChanges == mode - 1


def testFrequencyRatiosFollowTheory() -> None:
    assert vibrationService.beamFrequencyRatio(StructureKind.simplySupportedBeam, 3) == 9.0
    cantilever2 = vibrationService.beamFrequencyRatio(StructureKind.cantileverBeam, 2)
    assert math.isclose(cantilever2, 6.267, rel_tol=1e-3)
    clamped2 = vibrationService.beamFrequencyRatio(StructureKind.clampedBeam, 2)
    assert math.isclose(clamped2, 2.757, rel_tol=1e-3)


def testPlateModesAreOrderedByFrequency() -> None:
    order = vibrationService.plateModeOrder(1.0, 0.6)

    assert order[0] == (1, 1)
    assert len(order) == vibrationService.maxModeNumber
    parameters = [vibrationService.plateFrequencyParameter(mn, 1.0, 0.6) for mn in order]
    assert parameters == sorted(parameters)
    # A long plate bends along its length before across its width.
    assert order.index((2, 1)) < order.index((1, 2))


def testPlateModeIsZeroOnEveryEdge() -> None:
    geometry = vibrationService.buildGeometry(StructureKind.simplySupportedPlate)
    shape = vibrationService.plateModeShape(
        (2, 1), geometry.x, geometry.y, geometry.length, geometry.width
    )
    onEdge = (
        np.isclose(geometry.x, 0.0)
        | np.isclose(geometry.x, geometry.length)
        | np.isclose(geometry.y, -geometry.width / 2)
        | np.isclose(geometry.y, geometry.width / 2)
    )
    assert np.allclose(shape[onEdge], 0.0, atol=1e-9)
    assert math.isclose(float(np.max(np.abs(shape))), 1.0)


def testModesWithZeroAmplitudeAreDropped() -> None:
    setup = VibrationSetup(modes=(ModeSetting(1, 0.05), ModeSetting(2, 0.0), ModeSetting(3, 0.02)))
    model = vibrationService.buildModel(setup)

    assert [term.modeNumber for term in model.terms] == [1, 3]
    assert model.terms[0].frequencyHz == model.fundamentalFrequencyHz
    assert model.terms[1].frequencyHz > model.terms[0].frequencyHz


def testDisplacementStartsAtFullAmplitudeAndOnlyMovesAlongZ() -> None:
    setup = VibrationSetup(kind=StructureKind.cantileverBeam, modes=(ModeSetting(1, 0.1),))
    model = vibrationService.buildModel(setup)

    points, w = vibrationService.deformedPoints(model, 0.0)

    assert math.isclose(float(np.max(np.abs(w))), 0.1 * model.geometry.length)
    assert np.array_equal(points[:, :2], model.geometry.points[:, :2])
    assert np.allclose(points[:, 2] - model.geometry.points[:, 2], w)


def testAQuarterPeriodLaterTheFirstModeIsFlat() -> None:
    setup = VibrationSetup(modes=(ModeSetting(1, 0.1),))
    model = vibrationService.buildModel(setup)

    w = vibrationService.displacementAt(model, 0.25 / model.fundamentalFrequencyHz)

    assert np.allclose(w, 0.0, atol=1e-9)


def testDampingDecaysTheMotion() -> None:
    undamped = vibrationService.buildModel(VibrationSetup())
    damped = vibrationService.buildModel(VibrationSetup(dampingRatio=0.1))
    # Three whole cycles in, where the undamped beam is back at its peak.
    later = 3.0 / undamped.fundamentalFrequencyHz

    peakUndamped = float(np.max(np.abs(vibrationService.displacementAt(undamped, later))))
    peakDamped = float(np.max(np.abs(vibrationService.displacementAt(damped, later))))

    assert peakDamped < peakUndamped
    assert peakDamped > 0.0


def testDescriptionNamesTheModesAndTheirFrequencies() -> None:
    model = vibrationService.buildModel(VibrationSetup())
    text = vibrationService.describeModel(model)
    assert text == "Cantilever Beam: Mode 1 at 27.4 Hz"

    silent = vibrationService.buildModel(VibrationSetup(modes=(ModeSetting(1, 0.0),)))
    assert "nothing moves" in vibrationService.describeModel(silent)


def testTheGeometryTakesTheSizeItIsGiven() -> None:
    size = StructureSize(length=2.5, width=0.2, thickness=0.05)

    geometry = vibrationService.buildGeometry(StructureKind.cantileverBeam, size)

    assert (geometry.length, geometry.width, geometry.thickness) == (2.5, 0.2, 0.05)
    assert math.isclose(float(geometry.x.max()), 2.5)
    assert math.isclose(float(np.ptp(geometry.y)), 0.2)
    assert math.isclose(float(np.ptp(geometry.points[:, 2])), 0.05)
    # Same grid as the default size, so the view can keep its mesh.
    assert geometry.dimensions == vibrationService.beamDimensions


def testWithoutASizeEveryKindUsesTheDefaultSize() -> None:
    """30 cm by 1 cm by 3 mm, whatever the kind, until the user sets their own."""
    for kind in StructureKind:
        geometry = vibrationService.buildModel(VibrationSetup(kind=kind)).geometry
        assert (geometry.length, geometry.width, geometry.thickness) == (0.3, 0.01, 0.003)


def testTheDefaultMaterialIsAluminium() -> None:
    material = vibrationService.defaultMaterial

    assert material.density == 2700.0
    assert material.youngsModulus == 7.0e10
    assert material.poissonRatio == 0.33


@pytest.mark.parametrize(
    "material, name",
    [
        (MaterialProperties(density=0.0, youngsModulus=7.0e10), "Density"),
        (MaterialProperties(density=2700.0, youngsModulus=-1.0), "Young's modulus"),
        (MaterialProperties(2700.0, 7.0e10, poissonRatio=0.5), "Poisson's ratio"),
        (MaterialProperties(2700.0, 7.0e10, poissonRatio=-1.0), "Poisson's ratio"),
    ],
)
def testAMaterialOutsideItsRangeIsRefusedByName(material, name) -> None:
    with pytest.raises(ValueError, match=name):
        vibrationService.buildModel(VibrationSetup(material=material))


def testAmplitudesScaleWithTheLength() -> None:
    modes = (ModeSetting(1, 0.1),)
    short = vibrationService.buildModel(
        VibrationSetup(modes=modes, size=StructureSize(1.0, 0.08, 0.03))
    )
    long = vibrationService.buildModel(
        VibrationSetup(modes=modes, size=StructureSize(3.0, 0.08, 0.03))
    )

    peakShort = float(np.max(np.abs(vibrationService.displacementAt(short, 0.0))))
    peakLong = float(np.max(np.abs(vibrationService.displacementAt(long, 0.0))))

    assert math.isclose(peakLong, 3 * peakShort)


def testASquarePlateHasItsTwoSecondModesAtTheSameFrequency() -> None:
    """Width changes which plate modes come first, and a square is symmetric."""
    square = StructureSize(1.0, 1.0, 0.01)
    setup = VibrationSetup(
        kind=StructureKind.simplySupportedPlate,
        size=square,
        modes=(ModeSetting(2, 0.05), ModeSetting(3, 0.05)),
    )

    terms = vibrationService.buildModel(setup).terms

    assert {term.label for term in terms} == {"Mode 2 (1,2)", "Mode 3 (2,1)"}
    assert math.isclose(terms[0].frequencyHz, terms[1].frequencyHz)


@pytest.mark.parametrize(
    "size, name",
    [
        (StructureSize(0.0, 0.08, 0.03), "Length"),
        (StructureSize(1.0, -0.1, 0.03), "Width"),
        (StructureSize(1.0, 0.08, 2.0), "Thickness"),
    ],
)
def testASizeOutsideItsRangeIsRefusedByName(size, name) -> None:
    with pytest.raises(ValueError, match=name):
        vibrationService.buildGeometry(StructureKind.cantileverBeam, size)


# ----- natural frequencies from material and dimensions -------------------

aluminium = MaterialProperties(density=2700.0, youngsModulus=7.0e10)
steel = MaterialProperties(density=7850.0, youngsModulus=2.1e11)


def textbookBeamHz(coefficient: float, size: StructureSize, material: MaterialProperties) -> float:
    """f = C sqrt(E I / (rho A L^4)), the handbook form with its tabulated C."""
    inertia = size.width * size.thickness**3 / 12.0
    area = size.width * size.thickness
    return coefficient * math.sqrt(
        material.youngsModulus * inertia / (material.density * area * size.length**4)
    )


@pytest.mark.parametrize(
    "kind, coefficient",
    [
        # Handbook values of (beta_1 L)^2 / (2 pi) for the first mode.
        (StructureKind.cantileverBeam, 0.5596),
        (StructureKind.simplySupportedBeam, 1.5708),
        (StructureKind.clampedBeam, 3.5608),
    ],
)
def testBeamFundamentalsMatchTheHandbook(kind, coefficient) -> None:
    size = StructureSize(length=0.5, width=0.04, thickness=0.006)

    computed = vibrationService.naturalFrequencyHz(kind, 1, size, steel)

    assert math.isclose(computed, textbookBeamHz(coefficient, size, steel), rel_tol=1e-3)


def testTheDefaultAluminiumCantileverIsAbout27Hz() -> None:
    model = vibrationService.buildModel(VibrationSetup())

    assert math.isclose(model.fundamentalFrequencyHz, 27.42, rel_tol=1e-3)


def testASquarePlateFundamentalMatchesTheClosedForm() -> None:
    """Simply supported square: f_11 = (pi / a^2) sqrt(D / (rho h))."""
    size = StructureSize(length=0.4, width=0.4, thickness=0.002)
    nu = aluminium.poissonRatio
    flexural = aluminium.youngsModulus * size.thickness**3 / (12 * (1 - nu**2))
    expected = math.pi / size.length**2 * math.sqrt(flexural / (aluminium.density * size.thickness))

    computed = vibrationService.naturalFrequencyHz(
        StructureKind.simplySupportedPlate, 1, size, aluminium
    )

    assert math.isclose(computed, expected, rel_tol=1e-9)


def testBeamFrequencyScalesWithThicknessOverLengthSquared() -> None:
    kind = StructureKind.cantileverBeam
    base = StructureSize(0.3, 0.01, 0.003)
    f = vibrationService.naturalFrequencyHz(kind, 1, base, aluminium)

    twiceAsThick = vibrationService.naturalFrequencyHz(
        kind, 1, StructureSize(0.3, 0.01, 0.006), aluminium
    )
    twiceAsLong = vibrationService.naturalFrequencyHz(
        kind, 1, StructureSize(0.6, 0.01, 0.003), aluminium
    )
    twiceAsWide = vibrationService.naturalFrequencyHz(
        kind, 1, StructureSize(0.3, 0.02, 0.003), aluminium
    )

    assert math.isclose(twiceAsThick, 2 * f)
    assert math.isclose(twiceAsLong, f / 4)
    # Width cancels out of I / A for a rectangular beam.
    assert math.isclose(twiceAsWide, f)


def testFrequencyScalesWithTheSquareRootOfStiffnessOverDensity() -> None:
    size = StructureSize(0.3, 0.2, 0.003)
    stiffer = MaterialProperties(density=2700.0, youngsModulus=4 * 7.0e10)
    for kind in StructureKind:
        f = vibrationService.naturalFrequencyHz(kind, 1, size, aluminium)
        assert math.isclose(
            vibrationService.naturalFrequencyHz(kind, 1, size, stiffer), 2 * f
        ), kind


def testHigherBeamModesKeepTheTheoreticalRatios() -> None:
    size = StructureSize(0.3, 0.01, 0.003)
    for kind in (StructureKind.cantileverBeam, StructureKind.clampedBeam,
                 StructureKind.simplySupportedBeam):
        f1 = vibrationService.naturalFrequencyHz(kind, 1, size, aluminium)
        for mode in (2, 3):
            fn = vibrationService.naturalFrequencyHz(kind, mode, size, aluminium)
            assert math.isclose(fn / f1, vibrationService.beamFrequencyRatio(kind, mode))


@pytest.mark.parametrize(
    "hertz, text",
    [(0.5, "0.50 Hz"), (27.42, "27.4 Hz"), (171.9, "172 Hz"), (73457.6, "73.5 kHz")],
)
def testFrequenciesReadAsThreeFigures(hertz, text) -> None:
    assert vibrationService.formatFrequency(hertz) == text



def testPoissonsRatioStiffensThePlateOnly() -> None:
    """D grows as 1 / (1 - nu^2); a beam's frequency has no nu in it."""
    size = StructureSize(0.4, 0.3, 0.002)
    cork = MaterialProperties(2700.0, 7.0e10, poissonRatio=0.0)
    rubbery = MaterialProperties(2700.0, 7.0e10, poissonRatio=0.45)
    plate = StructureKind.simplySupportedPlate

    ratio = vibrationService.naturalFrequencyHz(
        plate, 1, size, rubbery
    ) / vibrationService.naturalFrequencyHz(plate, 1, size, cork)

    assert math.isclose(ratio, 1 / math.sqrt(1 - 0.45**2))
    for beam in (StructureKind.cantileverBeam, StructureKind.simplySupportedBeam):
        assert vibrationService.naturalFrequencyHz(
            beam, 1, size, rubbery
        ) == vibrationService.naturalFrequencyHz(beam, 1, size, cork)


def testASingleModeSetupIsPacedByItsOwnMode() -> None:
    single = vibrationService.buildModel(
        VibrationSetup(modes=(ModeSetting(4, 0.05),), singleMode=True)
    )
    superposed = vibrationService.buildModel(VibrationSetup(modes=(ModeSetting(4, 0.05),)))

    assert single.referenceFrequencyHz == single.terms[0].frequencyHz
    assert single.referenceFrequencyHz > single.fundamentalFrequencyHz
    assert superposed.referenceFrequencyHz == superposed.fundamentalFrequencyHz
