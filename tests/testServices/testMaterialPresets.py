"""Tests for the material presets."""

from __future__ import annotations

import pytest

from transverseVibrationView.models.vibrationModel import MaterialProperties
from transverseVibrationView.services import materialPresets, vibrationService


@pytest.mark.parametrize("name, material", materialPresets.materialPresets)
def testEveryPresetIsWithinTheInputRanges(name, material) -> None:
    """A preset the spin boxes would clamp would silently become something else."""
    vibrationService.checkMaterial(material)


def testTheDefaultMaterialIsTheAluminiumPreset() -> None:
    assert materialPresets.presetNameFor(vibrationService.defaultMaterial) == "Aluminium"


def testPresetNamesAreUnique() -> None:
    names = [name for name, _ in materialPresets.materialPresets]

    assert len(names) == len(set(names))
    assert materialPresets.customMaterialName not in names


def testValuesMatchingAPresetAreNamedAfterIt() -> None:
    steel = MaterialProperties(density=7850.0, youngsModulus=2.1e11, poissonRatio=0.30)

    assert materialPresets.presetNameFor(steel) == "Steel"
    assert materialPresets.presetNamed("Steel") == steel


def testValuesMatchingNoPresetHaveNoName() -> None:
    almostSteel = MaterialProperties(density=7851.0, youngsModulus=2.1e11, poissonRatio=0.30)

    assert materialPresets.presetNameFor(almostSteel) is None
    assert materialPresets.presetNamed("Unobtainium") is None
