"""The Structure Parameters tab's values, remembered between sessions.

The last values the user set become the defaults the next time the app
opens. Anything missing, unreadable or out of range falls back to the app's
own default for that group, so a hand-edited INI cannot stop the app opening.
"""

from __future__ import annotations

import logging

from transverseVibrationView.models.vibrationModel import (
    MaterialProperties,
    StructureParameters,
    StructureSize,
)
from transverseVibrationView.services import settingsService, vibrationService

logger = logging.getLogger(__name__)

lengthKey = "structure/length"
widthKey = "structure/width"
thicknessKey = "structure/thickness"
densityKey = "structure/density"
youngsModulusKey = "structure/youngsModulus"
poissonRatioKey = "structure/poissonRatio"


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

    return StructureParameters(size=size, material=material)


def saveStructureParameters(parameters: StructureParameters) -> None:
    for key, value in (
        (lengthKey, parameters.size.length),
        (widthKey, parameters.size.width),
        (thicknessKey, parameters.size.thickness),
        (densityKey, parameters.material.density),
        (youngsModulusKey, parameters.material.youngsModulus),
        (poissonRatioKey, parameters.material.poissonRatio),
    ):
        settingsService.writeValue(key, value)
