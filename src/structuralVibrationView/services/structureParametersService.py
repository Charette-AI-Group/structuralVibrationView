"""The Structure Parameters tab's values and selected mode, remembered between sessions.

The last values the user set become the defaults the next time the app
opens. Anything missing, unreadable or out of range falls back to the app's
own default for that group, so a hand-edited INI cannot stop the app opening.
"""

from __future__ import annotations

import logging

from structuralVibrationView.models.vibrationModel import (
    MaterialProperties,
    StructureParameters,
    StructureSize,
)
from structuralVibrationView.services import settingsService, vibrationService

logger = logging.getLogger(__name__)

lengthKey = "structure/length"
widthKey = "structure/width"
thicknessKey = "structure/thickness"
densityKey = "structure/density"
youngsModulusKey = "structure/youngsModulus"
poissonRatioKey = "structure/poissonRatio"
springStiffnessKey = "structure/springStiffness"
selectedModeKey = "structure/selectedMode"
defaultSelectedMode = 1


def loadStructureParameters() -> StructureParameters:
    settings = settingsService.openSettings()
    defaults = vibrationService.defaultStructureParameters

    def read(key: str, fallback: float) -> float:
        value = settings.value(key, fallback)
        try:
            return float(value)
        except (TypeError, ValueError):
            logger.warning("Ignoring unreadable %s = %r", key, value)
            return fallback

    size = StructureSize(
        length=read(lengthKey, defaults.size.length),
        width=read(widthKey, defaults.size.width),
        thickness=read(thicknessKey, defaults.size.thickness),
    )
    try:
        vibrationService.checkSize(size)
    except ValueError as error:
        logger.warning("Ignoring saved size: %s", error)
        size = defaults.size

    material = MaterialProperties(
        density=read(densityKey, defaults.material.density),
        youngsModulus=read(youngsModulusKey, defaults.material.youngsModulus),
        poissonRatio=read(poissonRatioKey, defaults.material.poissonRatio),
    )
    try:
        vibrationService.checkMaterial(material)
    except ValueError as error:
        logger.warning("Ignoring saved material: %s", error)
        material = defaults.material

    stiffness = read(springStiffnessKey, defaults.springStiffness)
    low, high = vibrationService.springStiffnessRange
    if not low <= stiffness <= high:
        logger.warning("Ignoring saved spring stiffness %r", stiffness)
        stiffness = defaults.springStiffness

    return StructureParameters(size=size, material=material, springStiffness=stiffness)


def saveStructureParameters(parameters: StructureParameters) -> None:
    for key, value in (
        (lengthKey, parameters.size.length),
        (widthKey, parameters.size.width),
        (thicknessKey, parameters.size.thickness),
        (densityKey, parameters.material.density),
        (youngsModulusKey, parameters.material.youngsModulus),
        (poissonRatioKey, parameters.material.poissonRatio),
        (springStiffnessKey, parameters.springStiffness),
    ):
        settingsService.writeValue(key, value)


def loadSelectedMode() -> int:
    """The mode last studied on its own, or mode 1 if none was or it is unusable."""
    value = settingsService.openSettings().value(selectedModeKey, defaultSelectedMode)
    try:
        mode = int(value)
    except (TypeError, ValueError):
        logger.warning("Ignoring unreadable %s = %r", selectedModeKey, value)
        return defaultSelectedMode
    if not 1 <= mode <= vibrationService.selectableModeCount:
        logger.warning("Ignoring out-of-range %s = %r", selectedModeKey, value)
        return defaultSelectedMode
    return mode


def saveSelectedMode(mode: int) -> None:
    settingsService.writeValue(selectedModeKey, mode)
