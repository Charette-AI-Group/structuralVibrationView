"""Typical properties of common engineering materials.

Room-temperature handbook values, rounded: real alloys and grades vary by a
few percent either side. Every material here is treated as isotropic, which
is why wood and fibre composites are left out - their stiffness depends on
direction and one Young's modulus would misrepresent them.
"""

from __future__ import annotations

import math

from transverseVibrationView.models.vibrationModel import MaterialProperties

# (name, properties), in the order the dropdown lists them.
materialPresets: tuple[tuple[str, MaterialProperties], ...] = (
    ("Aluminium", MaterialProperties(density=2700.0, youngsModulus=7.0e10, poissonRatio=0.33)),
    ("Steel", MaterialProperties(density=7850.0, youngsModulus=2.1e11, poissonRatio=0.30)),
    (
        "Stainless Steel",
        MaterialProperties(density=8000.0, youngsModulus=1.93e11, poissonRatio=0.29),
    ),
    ("Titanium", MaterialProperties(density=4500.0, youngsModulus=1.16e11, poissonRatio=0.32)),
    ("Copper", MaterialProperties(density=8960.0, youngsModulus=1.17e11, poissonRatio=0.34)),
    ("Brass", MaterialProperties(density=8500.0, youngsModulus=1.0e11, poissonRatio=0.34)),
    ("Glass", MaterialProperties(density=2500.0, youngsModulus=7.0e10, poissonRatio=0.22)),
    ("Concrete", MaterialProperties(density=2400.0, youngsModulus=3.0e10, poissonRatio=0.20)),
    ("Acrylic", MaterialProperties(density=1180.0, youngsModulus=3.2e9, poissonRatio=0.37)),
    ("Polycarbonate", MaterialProperties(density=1200.0, youngsModulus=2.4e9, poissonRatio=0.37)),
)

customMaterialName = "Custom"


def presetNamed(name: str) -> MaterialProperties | None:
    for presetName, material in materialPresets:
        if presetName == name:
            return material
    return None


def presetNameFor(material: MaterialProperties) -> str | None:
    """The preset these values are, or None when they match none of them.

    Compared with a tolerance, since the values have been through spin boxes
    and an INI file on the way here.
    """
    for name, preset in materialPresets:
        if (
            math.isclose(material.density, preset.density, rel_tol=1e-9)
            and math.isclose(material.youngsModulus, preset.youngsModulus, rel_tol=1e-9)
            and math.isclose(material.poissonRatio, preset.poissonRatio, abs_tol=1e-9)
        ):
            return name
    return None
