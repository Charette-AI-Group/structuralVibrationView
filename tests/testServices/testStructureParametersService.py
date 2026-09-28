"""Tests for remembering the Structure Parameters tab between sessions."""

from __future__ import annotations

from structuralVibrationView.models.vibrationModel import (
    MaterialProperties,
    StructureParameters,
    StructureSize,
)
from structuralVibrationView.services import (
    settingsService,
    structureParametersService,
    vibrationService,
)

steel = StructureParameters(
    size=StructureSize(length=0.5, width=0.02, thickness=0.004),
    material=MaterialProperties(density=7850.0, youngsModulus=2.1e11, poissonRatio=0.30),
)


def testAFirstRunGetsTheAppDefaults() -> None:
    parameters = structureParametersService.loadStructureParameters()

    assert parameters == vibrationService.defaultStructureParameters
    assert parameters.size == StructureSize(0.3, 0.01, 0.003)
    assert parameters.material == MaterialProperties(2700.0, 7.0e10, 0.33)


def testSavedValuesComeBackAsTheNewDefaults() -> None:
    structureParametersService.saveStructureParameters(steel)

    assert structureParametersService.loadStructureParameters() == steel


def testAnUnreadableValueFallsBackToTheDefault() -> None:
    """A hand-edited INI must not stop the app opening."""
    structureParametersService.saveStructureParameters(steel)
    settingsService.writeValue(structureParametersService.densityKey, "heavy")

    loaded = structureParametersService.loadStructureParameters()

    assert loaded.material.density == vibrationService.defaultMaterial.density
    assert loaded.size == steel.size


def testASavedSizeOutOfRangeFallsBackToTheDefaultSize() -> None:
    structureParametersService.saveStructureParameters(steel)
    settingsService.writeValue(structureParametersService.lengthKey, 500.0)

    loaded = structureParametersService.loadStructureParameters()

    assert loaded.size == vibrationService.defaultSize
    # The material was fine, so it is kept.
    assert loaded.material == steel.material



def testAFirstRunStudiesMode1() -> None:
    assert structureParametersService.loadSelectedMode() == 1


def testTheSelectedModeComesBack() -> None:
    structureParametersService.saveSelectedMode(4)

    assert structureParametersService.loadSelectedMode() == 4


def testAnUnusableSelectedModeFallsBackToMode1() -> None:
    for bad in ("fourth", 0, vibrationService.selectableModeCount + 1):
        settingsService.writeValue(structureParametersService.selectedModeKey, bad)
        assert structureParametersService.loadSelectedMode() == 1, bad
