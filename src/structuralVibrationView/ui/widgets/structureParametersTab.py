"""The Structure Parameters tab: one mode, and what the structure is.

While this tab is open the animation shows the single mode chosen at the top,
built from this tab alone - its dimensions and material, a fixed amplitude,
no damping - so a mode can be studied without the superposition's settings.
Dimensions, material and the selected mode are remembered between sessions.
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

from structuralVibrationView.models.vibrationModel import (
    MaterialProperties,
    StructureKind,
    StructureParameters,
    StructureSize,
    densityParameter,
    lengthParameter,
    poissonRatioParameter,
    springStiffnessParameter,
    thicknessParameter,
    widthParameter,
    youngsModulusParameter,
)
from structuralVibrationView.services import materialPresets, vibrationService
from structuralVibrationView.ui.widgets.scientificSpinBox import ScientificSpinBox


class StructureParametersTab(QWidget):
    # Any input on the tab changed, the selected mode included.
    changed = Signal()

    def __init__(
        self,
        parameters: StructureParameters,
        selectedMode: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("structureParametersPage")
        layout = QVBoxLayout(self)
        form = self.form = QFormLayout()
        size, material = parameters.size, parameters.material

        self.modeCombo = QComboBox()
        self.modeCombo.setObjectName("modeCombo")
        for modeNumber in range(1, vibrationService.selectableModeCount + 1):
            self.modeCombo.addItem(f"Mode {modeNumber}", modeNumber)
        self.wantedMode = selectedMode
        # Before the signal is connected: restoring a choice is not a change.
        self.modeCombo.setCurrentIndex(max(0, self.modeCombo.findData(selectedMode)))
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
        self.springStiffnessSpin = self.makeSpin(
            ScientificSpinBox(), "springStiffnessSpin", vibrationService.springStiffnessRange,
            parameters.springStiffness,
            "The spring's rate, force per metre of stretch.\n"
            "Only the spring-mass system uses it.",
            suffix=" N/m",
        )
        form.addRow("Spring Stiffness", self.springStiffnessSpin)
        # Which row holds which parameter, so a system can hide the rest.
        self.parameterRows = {
            lengthParameter: self.lengthSpin,
            widthParameter: self.widthSpin,
            thicknessParameter: self.thicknessSpin,
            densityParameter: self.densitySpin,
            youngsModulusParameter: self.youngsModulusSpin,
            poissonRatioParameter: self.poissonRatioSpin,
            springStiffnessParameter: self.springStiffnessSpin,
        }
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

    def showSystem(self, kind: StructureKind) -> None:
        """Offer what this system has: its modes, and the rows it reads.

        A beam's frequencies do not depend on Poisson's ratio and an
        oscillator's do not depend on Young's modulus, so those rows go away
        rather than sit there looking as if they did something.
        """
        wanted = set(vibrationService.parameterNamesFor(kind))
        for name, spin in self.parameterRows.items():
            self.form.setRowVisible(spin, name in wanted)
        self.showModes(kind)
        self.refreshModeLabels(kind)

    def showModes(self, kind: StructureKind) -> None:
        """List the modes this system has, keeping the user's choice if it fits."""
        available = min(
            vibrationService.maxModeNumber(kind), vibrationService.selectableModeCount
        )
        if self.modeCombo.currentData() is not None:
            self.wantedMode = int(self.modeCombo.currentData())
        blocked = self.modeCombo.blockSignals(True)
        self.modeCombo.clear()
        for modeNumber in range(1, available + 1):
            self.modeCombo.addItem(f"Mode {modeNumber}", modeNumber)
        self.modeCombo.setCurrentIndex(max(0, self.modeCombo.findData(self.wantedMode)))
        self.modeCombo.blockSignals(blocked)
        # One mode is not a choice; the box says so rather than looking broken.
        self.modeCombo.setEnabled(available > 1)

    def refreshModeLabels(self, kind: StructureKind) -> None:
        """Put each mode's natural frequency beside it, for the current structure."""
        parameters = self.currentStructureParameters()
        for index in range(self.modeCombo.count()):
            modeNumber = int(self.modeCombo.itemData(index))
            hertz = vibrationService.naturalFrequencyHz(kind, modeNumber, parameters)
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
        return StructureParameters(
            size=self.currentSize(),
            material=self.currentMaterial(),
            springStiffness=self.springStiffnessSpin.value(),
        )

    def showWidth(self, width: float) -> None:
        """Set the width without announcing it: the caller emits one change."""
        blocked = self.widthSpin.blockSignals(True)
        self.widthSpin.setValue(width)
        self.widthSpin.blockSignals(blocked)

    def restore(self, selectedMode: int, parameters: StructureParameters) -> None:
        """Show a saved mode and structure without announcing each value.

        The caller emits one change afterwards, so the scene is rebuilt once
        rather than once per input.
        """
        size, material = parameters.size, parameters.material
        values = (
            (self.springStiffnessSpin, parameters.springStiffness),
            (self.lengthSpin, size.length),
            (self.widthSpin, size.width),
            (self.thicknessSpin, size.thickness),
            (self.densitySpin, material.density),
            (self.youngsModulusSpin, material.youngsModulus),
            (self.poissonRatioSpin, material.poissonRatio),
        )
        for spin, value in values:
            blocked = spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(blocked)
        blocked = self.modeCombo.blockSignals(True)
        self.modeCombo.setCurrentIndex(max(0, self.modeCombo.findData(selectedMode)))
        self.modeCombo.blockSignals(blocked)
        self.showMaterialName()
