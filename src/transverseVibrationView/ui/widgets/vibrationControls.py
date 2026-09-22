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
    ModeSetting,
    StructureKind,
    VibrationSetup,
)
from transverseVibrationView.services import vibrationService
from transverseVibrationView.ui.widgets.fullWidthTabWidget import FullWidthTabWidget

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
        defaults = VibrationSetup()

        layout = QVBoxLayout(self)
        layout.addWidget(self.buildStructureGroup(defaults))
        self.tabs = FullWidthTabWidget(labelScale=1.0)
        self.tabs.setObjectName("parameterTabs")
        self.tabs.addTab(self.buildModalSuperpositionTab(defaults), modalSuperpositionTabLabel)
        self.tabs.addTab(self.buildStructureParametersTab(), structureParametersTabLabel)
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
        self.kindCombo.currentIndexChanged.connect(self.emitSetup)
        form.addRow("Type", self.kindCombo)
        return group

    def buildModalSuperpositionTab(self, defaults: VibrationSetup) -> QWidget:
        page = QWidget()
        page.setObjectName("modalSuperpositionPage")
        layout = QVBoxLayout(page)

        # The clock and the decay apply to every mode, so they sit above the table.
        form = QFormLayout()
        self.frequencySpin = QDoubleSpinBox()
        self.frequencySpin.setObjectName("frequencySpin")
        self.frequencySpin.setRange(0.05, 5.0)
        self.frequencySpin.setSingleStep(0.1)
        self.frequencySpin.setDecimals(2)
        self.frequencySpin.setSuffix(" Hz")
        self.frequencySpin.setValue(defaults.fundamentalFrequencyHz)
        self.frequencySpin.setToolTip(
            "Frequency of mode 1. Higher modes follow beam and plate theory."
        )
        self.frequencySpin.valueChanged.connect(self.emitSetup)
        form.addRow("Fundamental", self.frequencySpin)

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

    def buildStructureParametersTab(self) -> QWidget:
        """Empty for now: the place for the structure's own parameters."""
        page = QWidget()
        page.setObjectName("structureParametersPage")
        layout = QVBoxLayout(page)
        note = QLabel("Structure parameters will be set here.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        return page

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
        self.speedSpin.setToolTip("Slow the clock down to watch a fast mode.")
        self.speedSpin.valueChanged.connect(self.speedChanged)
        form.addRow("Speed", self.speedSpin)

        self.timeLabel = QLabel("t = 0.00 s")
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
            modes=tuple(row.setting() for row in self.modeRows),
            fundamentalFrequencyHz=self.frequencySpin.value(),
            dampingRatio=self.dampingSpin.value(),
        )

    def emitSetup(self) -> None:
        self.setupChanged.emit(self.currentSetup())

    def onPlayToggled(self, playing: bool) -> None:
        self.playButton.setText(pauseLabel if playing else playLabel)
        self.playToggled.emit(playing)

    def showTime(self, timeSeconds: float) -> None:
        self.timeLabel.setText(f"t = {timeSeconds:.2f} s")
