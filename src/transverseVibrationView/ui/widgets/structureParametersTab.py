"""The Structure Parameters tab: one mode, and what the structure is.

While this tab is open the animation shows the single mode chosen at the top,
built from this tab alone - its dimensions and material, a fixed amplitude,
no damping - so a mode can be studied without the superposition's settings.
Dimensions and material are remembered between sessions; the mode is not.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from transverseVibrationView.models.vibrationModel import (
    MaterialProperties,
    StructureKind,
    StructureParameters,
    StructureSize,
)
from transverseVibrationView.services import materialPresets, vibrationService
from transverseVibrationView.ui.widgets.scientificSpinBox import ScientificSpinBox

selectableModeCount = 5


class StructureParametersTab(QWidget):
    # Any input on the tab changed, the selected mode included.
    changed = Signal()

    def __init__(self, parameters: StructureParameters, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("structureParametersPage")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        size, material = parameters.size, parameters.material

        self.modeCombo = QComboBox()
        self.modeCombo.setObjectName("modeCombo")
        for modeNumber in range(1, selectableModeCount + 1):
            self.modeCombo.addItem(f"Mode {modeNumber}", modeNumber)
        self.modeCombo.setToolTip(
            "The mode animated while this tab is open, with its natural frequency.\n"
            "It plays alone, at a fixed amplitude and undamped."
        )
        self.modeCombo.currentIndexChanged.connect(self.changed)
        form.addRow("Mode", self.modeCombo)

        self.lengthSpin = self.makeSpin(
            QDoubleSpinBox(), "lengthSpin", vibrationService.lengthRange, size.length,
            "Length along the span, x. Amplitudes are fractions of it.",
            suffix=" m", decimals=3, step=0.01,
        )
        form.addRow("Length", self.lengthSpin)
        self.widthSpin = self.makeSpin(
            QDoubleSpinBox(), "widthSpin", vibrationService.widthRange, size.width,
            "Width across the span, y. On the plate it also sets which modes come first.",
            suffix=" m", decimals=4, step=0.001,
        )
        form.addRow("Width", self.widthSpin)
        self.thicknessSpin = self.makeSpin(
            QDoubleSpinBox(), "thicknessSpin", vibrationService.thicknessRange,
            size.thickness, "Thickness in the direction of vibration, z.",
            suffix=" m", decimals=4, step=0.0005,
        )
        form.addRow("Thickness", self.thicknessSpin)

        self.materialCombo = QComboBox()
        self.materialCombo.setObjectName("materialCombo")
        for name, _preset in materialPresets.materialPresets:
            self.materialCombo.addItem(name, name)
        self.materialCombo.addItem(materialPresets.customMaterialName, None)
        self.materialCombo.setToolTip(
            "Fills in density, Young's modulus and Poisson's ratio with typical values.\n"
            "Editing any of them by hand makes it Custom."
        )
        self.materialCombo.activated.connect(self.onMaterialChosen)
        form.addRow("Material", self.materialCombo)

        self.densitySpin = self.makeSpin(
            QDoubleSpinBox(), "densitySpin", vibrationService.densityRange,
            material.density, "Mass per unit volume. Aluminium is about 2700 kg/m³.",
            suffix=" kg/m³", decimals=0, step=100.0,
        )
        form.addRow("Density", self.densitySpin)
        self.youngsModulusSpin = self.makeSpin(
            ScientificSpinBox(), "youngsModulusSpin", vibrationService.youngsModulusRange,
            material.youngsModulus,
            "Material stiffness, Young's modulus. Aluminium is about 7.0E+10 N/m². "
            "Type it as 7e10 if you like.",
            suffix=" N/m²",
        )
        form.addRow("Young's Modulus", self.youngsModulusSpin)
        self.poissonRatioSpin = self.makeSpin(
            QDoubleSpinBox(), "poissonRatioSpin", vibrationService.poissonRatioRange,
            material.poissonRatio,
            "Poisson's ratio: how much the material narrows as it stretches.\n"
            "Aluminium is about 0.33, steel 0.30, rubber close to 0.5.\n"
            "It changes the plate's frequencies only; a beam's bending ignores it.",
            suffix="", decimals=3, step=0.01,
        )
        form.addRow("Poisson's Ratio", self.poissonRatioSpin)
        for spin in self.materialSpins():
            spin.valueChanged.connect(self.showMaterialName)
        self.showMaterialName()
        layout.addLayout(form)
        layout.addStretch()

    def makeSpin(
        self,
        spin: QDoubleSpinBox,
        objectName: str,
        valueRange: tuple[float, float],
        value: float,
        toolTip: str,
        suffix: str,
        decimals: int | None = None,
        step: float | None = None,
    ) -> QDoubleSpinBox:
        spin.setObjectName(objectName)
        if decimals is not None:
            spin.setDecimals(decimals)
        spin.setRange(*valueRange)
        if step is not None:
            spin.setSingleStep(step)
        spin.setSuffix(suffix)
        spin.setValue(value)
        spin.setToolTip(toolTip)
        spin.valueChanged.connect(self.changed)
        return spin

    # ----- mode --------------------------------------------------------------

    def selectedMode(self) -> int:
        return int(self.modeCombo.currentData())

    def refreshModeLabels(self, kind: StructureKind) -> None:
        """Put each mode's natural frequency beside it, for the current structure."""
        size, material = self.currentSize(), self.currentMaterial()
        for index in range(self.modeCombo.count()):
            modeNumber = int(self.modeCombo.itemData(index))
            hertz = vibrationService.naturalFrequencyHz(kind, modeNumber, size, material)
            label = f"Mode {modeNumber} ({vibrationService.formatFrequency(hertz)})"
            self.modeCombo.setItemText(index, label)

    # ----- material ----------------------------------------------------------

    def materialSpins(self) -> tuple[QDoubleSpinBox, ...]:
        return (self.densitySpin, self.youngsModulusSpin, self.poissonRatioSpin)

    def onMaterialChosen(self, index: int) -> None:
        """A preset fills all three properties: one change, one setup."""
        preset = materialPresets.presetNamed(self.materialCombo.itemData(index) or "")
        if preset is None:  # Custom: keep whatever is there
            return
        for spin, value in zip(
            self.materialSpins(),
            (preset.density, preset.youngsModulus, preset.poissonRatio),
            strict=True,
        ):
            blocked = spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(blocked)
        self.showMaterialName()
        self.changed.emit()

    def showMaterialName(self) -> None:
        """Name the preset the values match, or Custom when they match none."""
        name = materialPresets.presetNameFor(self.currentMaterial())
        index = self.materialCombo.findData(name)  # None finds the Custom entry
        blocked = self.materialCombo.blockSignals(True)
        self.materialCombo.setCurrentIndex(index)
        self.materialCombo.blockSignals(blocked)

    # ----- values ------------------------------------------------------------

    def currentSize(self) -> StructureSize:
        return StructureSize(
            length=self.lengthSpin.value(),
            width=self.widthSpin.value(),
            thickness=self.thicknessSpin.value(),
        )

    def currentMaterial(self) -> MaterialProperties:
        return MaterialProperties(
            density=self.densitySpin.value(),
            youngsModulus=self.youngsModulusSpin.value(),
            poissonRatio=self.poissonRatioSpin.value(),
        )

    def currentStructureParameters(self) -> StructureParameters:
        """What the tab shows now, for saving."""
        return StructureParameters(size=self.currentSize(), material=self.currentMaterial())
