"""The control panel beside the 3D view: what to animate, and playback.

Emits a whole `VibrationSetup` whenever any of its inputs change, so the view
never reads widgets one by one. Playback (play, restart, speed, reset view)
is emitted separately because it does not change the model.
"""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from transverseVibrationView.models.vibrationModel import (
    MaterialProperties,
    ModeSetting,
    StructureKind,
    StructureParameters,
    StructureSize,
    VibrationSetup,
)
from transverseVibrationView.services import structureParametersService, vibrationService
from transverseVibrationView.ui.widgets.fullWidthTabWidget import FullWidthTabWidget
from transverseVibrationView.ui.widgets.scientificSpinBox import ScientificSpinBox

modeRowCount = 3
playLabel = "Play"
pauseLabel = "Pause"
modalSuperpositionTabLabel = "Modal Superposition"
structureParametersTabLabel = "Structure Parameters"

# Preset camera views: the plane seen, and its button label.
xzView = "xz"
xyView = "xy"
yzView = "yz"
presetViewLabels = {
    xzView: "X-Z View",
    xyView: "X-Y View",
    yzView: "Y-Z View",
}


class ModeRow:
    """The three inputs that describe one mode: number, amplitude, phase."""

    def __init__(self, row: int, defaults: ModeSetting) -> None:
        self.numberSpin = QSpinBox()
        self.numberSpin.setRange(1, vibrationService.maxModeNumber)
        self.numberSpin.setValue(defaults.modeNumber)
        self.numberSpin.setObjectName(f"modeNumberSpin{row}")

        self.amplitudeSpin = QDoubleSpinBox()
        self.amplitudeSpin.setRange(0.0, 0.3)
        self.amplitudeSpin.setSingleStep(0.01)
        self.amplitudeSpin.setDecimals(3)
        self.amplitudeSpin.setValue(defaults.amplitude)
        self.amplitudeSpin.setToolTip(
            "Peak displacement as a fraction of the length. 0 turns the mode off."
        )
        self.amplitudeSpin.setObjectName(f"modeAmplitudeSpin{row}")
        # Three decimals need the room; left to the grid, "0.050" shows as "0.05".
        self.amplitudeSpin.setMinimumWidth(self.amplitudeSpin.sizeHint().width())

        self.phaseSpin = QDoubleSpinBox()
        self.phaseSpin.setRange(-180.0, 180.0)
        self.phaseSpin.setSingleStep(15.0)
        self.phaseSpin.setDecimals(0)
        self.phaseSpin.setSuffix("°")
        self.phaseSpin.setValue(defaults.phaseDegrees)
        self.phaseSpin.setObjectName(f"modePhaseSpin{row}")

    def setting(self) -> ModeSetting:
        return ModeSetting(
            modeNumber=self.numberSpin.value(),
            amplitude=self.amplitudeSpin.value(),
            phaseDegrees=self.phaseSpin.value(),
        )

    def widgets(self) -> tuple[QWidget, ...]:
        return (self.numberSpin, self.amplitudeSpin, self.phaseSpin)


class VibrationControls(QWidget):
    setupChanged = Signal(object)  # VibrationSetup
    playToggled = Signal(bool)  # True when playing
    restartRequested = Signal()
    resetViewRequested = Signal()
    presetViewRequested = Signal(str)  # one of the keys of presetViewLabels
    speedChanged = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # The last structure parameters the user set, or the app's defaults.
        saved = structureParametersService.loadStructureParameters()
        defaults = VibrationSetup(size=saved.size, material=saved.material)

        layout = QVBoxLayout(self)
        layout.addWidget(self.buildStructureGroup(defaults))
        self.tabs = FullWidthTabWidget(labelScale=1.0)
        self.tabs.setObjectName("parameterTabs")
        self.tabs.addTab(self.buildModalSuperpositionTab(defaults), modalSuperpositionTabLabel)
        self.tabs.addTab(
            self.buildStructureParametersTab(saved), structureParametersTabLabel
        )
        layout.addWidget(self.tabs)
        layout.addWidget(self.buildPlaybackGroup())
        layout.addStretch()

        # As wide as the widest row needs and no wider, so no value is cut off.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

    def buildStructureGroup(self, defaults: VibrationSetup) -> QGroupBox:
        group = QGroupBox("Structure")
        form = QFormLayout(group)

        self.kindCombo = QComboBox()
        self.kindCombo.setObjectName("kindCombo")
        for kind in StructureKind:
            self.kindCombo.addItem(kind.value, kind)
        self.kindCombo.setCurrentIndex(list(StructureKind).index(defaults.kind))
        # The dimensions and material are the user's, so a new kind keeps them.
        self.kindCombo.currentIndexChanged.connect(self.emitSetup)
        form.addRow("Type", self.kindCombo)
        return group

    def buildModalSuperpositionTab(self, defaults: VibrationSetup) -> QWidget:
        page = QWidget()
        page.setObjectName("modalSuperpositionPage")
        layout = QVBoxLayout(page)

        # The clock and the decay apply to every mode, so they sit above the table.
        form = QFormLayout()
        # Computed, not chosen: the view fills it in from the model.
        self.fundamentalLabel = QLabel("")
        self.fundamentalLabel.setObjectName("fundamentalLabel")
        self.fundamentalLabel.setToolTip(
            "Natural frequency of mode 1, computed from the Structure Parameters\n"
            "and the type's boundary conditions. Higher modes are computed the same way."
        )
        form.addRow("Fundamental", self.fundamentalLabel)

        self.dampingSpin = QDoubleSpinBox()
        self.dampingSpin.setObjectName("dampingSpin")
        self.dampingSpin.setRange(0.0, 0.5)
        self.dampingSpin.setSingleStep(0.01)
        self.dampingSpin.setDecimals(3)
        self.dampingSpin.setValue(defaults.dampingRatio)
        self.dampingSpin.setToolTip(
            "Damping ratio. Above 0 the motion decays; use Restart to kick it again."
        )
        self.dampingSpin.valueChanged.connect(self.emitSetup)
        form.addRow("Damping Ratio", self.dampingSpin)
        layout.addLayout(form)

        grid = QGridLayout()
        layout.addLayout(grid)
        for column, title in enumerate(("Mode", "Amplitude", "Phase"), start=1):
            grid.addWidget(QLabel(title), 0, column)

        self.modeRows: list[ModeRow] = []
        for index in range(modeRowCount):
            if index < len(defaults.modes):
                defaultMode = defaults.modes[index]
            else:
                defaultMode = ModeSetting(index + 1, 0.0)
            row = ModeRow(index, defaultMode)
            grid.addWidget(QLabel(f"{index + 1}"), index + 1, 0)
            for column, widget in enumerate(row.widgets(), start=1):
                grid.addWidget(widget, index + 1, column)
            row.numberSpin.valueChanged.connect(self.emitSetup)
            row.amplitudeSpin.valueChanged.connect(self.emitSetup)
            row.phaseSpin.valueChanged.connect(self.emitSetup)
            self.modeRows.append(row)
        layout.addStretch()
        return page

    def buildStructureParametersTab(self, parameters: StructureParameters) -> QWidget:
        """Dimensions and material, in SI units. Remembered between sessions."""
        page = QWidget()
        page.setObjectName("structureParametersPage")
        layout = QVBoxLayout(page)
        form = QFormLayout()
        size, material = parameters.size, parameters.material

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
        layout.addLayout(form)
        layout.addStretch()
        return page

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
        spin.valueChanged.connect(self.emitSetup)
        return spin

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
        )

    def currentStructureParameters(self) -> StructureParameters:
        """What the Structure Parameters tab shows now, for saving."""
        return StructureParameters(size=self.currentSize(), material=self.currentMaterial())

    def buildPlaybackGroup(self) -> QGroupBox:
        group = QGroupBox("Playback")
        layout = QVBoxLayout(group)

        form = QFormLayout()
        self.speedSpin = QDoubleSpinBox()
        self.speedSpin.setObjectName("speedSpin")
        self.speedSpin.setRange(0.05, 5.0)
        self.speedSpin.setSingleStep(0.1)
        self.speedSpin.setDecimals(2)
        self.speedSpin.setSuffix("x")
        self.speedSpin.setValue(1.0)
        self.speedSpin.setToolTip(
            "Real vibrations are too fast to see, so the animation runs in slow motion.\n"
            "At 1x, mode 1 takes two seconds per cycle whatever its real frequency."
        )
        self.speedSpin.valueChanged.connect(self.speedChanged)
        form.addRow("Speed", self.speedSpin)

        self.timeLabel = QLabel(formatTime(0.0))
        self.timeLabel.setToolTip("Real time in the structure, not time on screen.")
        self.timeLabel.setObjectName("timeLabel")
        form.addRow("Time", self.timeLabel)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.playButton = QPushButton(pauseLabel)
        self.playButton.setObjectName("playButton")
        self.playButton.setCheckable(True)
        self.playButton.setChecked(True)
        self.playButton.toggled.connect(self.onPlayToggled)
        buttons.addWidget(self.playButton)

        self.restartButton = QPushButton("Restart")
        self.restartButton.setObjectName("restartButton")
        self.restartButton.clicked.connect(self.restartRequested)
        buttons.addWidget(self.restartButton)

        self.resetViewButton = QPushButton("Reset View")
        self.resetViewButton.setObjectName("resetViewButton")
        self.resetViewButton.clicked.connect(self.resetViewRequested)
        buttons.addWidget(self.resetViewButton)
        layout.addLayout(buttons)

        presets = QHBoxLayout()
        self.presetViewButtons: dict[str, QPushButton] = {}
        for plane, label in presetViewLabels.items():
            button = QPushButton(label)
            button.setObjectName(f"{plane}ViewButton")
            button.setToolTip(f"Look straight at the {label.removesuffix(' View')} plane.")
            button.clicked.connect(partial(self.presetViewRequested.emit, plane))
            presets.addWidget(button)
            self.presetViewButtons[plane] = button
        layout.addLayout(presets)
        return group

    def currentSetup(self) -> VibrationSetup:
        # Qt stores the enum as its string value, so it comes back as one.
        return VibrationSetup(
            kind=StructureKind(self.kindCombo.currentData()),
            size=self.currentSize(),
            material=self.currentMaterial(),
            modes=tuple(row.setting() for row in self.modeRows),
            dampingRatio=self.dampingSpin.value(),
        )

    def emitSetup(self) -> None:
        self.setupChanged.emit(self.currentSetup())

    def onPlayToggled(self, playing: bool) -> None:
        self.playButton.setText(pauseLabel if playing else playLabel)
        self.playToggled.emit(playing)

    def showTime(self, timeSeconds: float) -> None:
        self.timeLabel.setText(formatTime(timeSeconds))

    def showFundamental(self, hertz: float) -> None:
        self.fundamentalLabel.setText(vibrationService.formatFrequency(hertz))


def formatTime(timeSeconds: float) -> str:
    """Structural time: milliseconds while short, since most modes are fast."""
    if timeSeconds < 1.0:
        return f"t = {timeSeconds * 1000.0:.1f} ms"
    return f"t = {timeSeconds:.3f} s"
