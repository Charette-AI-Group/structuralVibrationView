"""The control panel beside the 3D view: what to animate, and playback.

Emits a whole `VibrationSetup` whenever any of its inputs change, so the view
never reads widgets one by one. Which tab is open decides what that setup is:
the Modal Superposition tab's mode rows, or the Structure Parameters tab's
single mode. Playback (play, restart, speed, reset view)
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

from structuralVibrationView.models.sessionState import (
    PlaybackState,
    SessionState,
    modalSuperpositionTab,
    structureParametersTab,
)
from structuralVibrationView.models.vibrationModel import (
    ModeSetting,
    StructureKind,
    StructureParameters,
    VibrationSetup,
)
from structuralVibrationView.services import (
    structureParametersService,
    vibrationService,
)
from structuralVibrationView.services.systems import systemFor
from structuralVibrationView.ui.widgets.fullWidthTabWidget import FullWidthTabWidget
from structuralVibrationView.ui.widgets.separatorItemDelegate import SeparatorItemDelegate
from structuralVibrationView.ui.widgets.structureParametersTab import StructureParametersTab

modeRowCount = vibrationService.superposedModeCount
playLabel = "Play"
pauseLabel = "Pause"
modalSuperpositionTabLabel = modalSuperpositionTab
structureParametersTabLabel = structureParametersTab
modalSuperpositionTabIndex = 0
structureParametersTabIndex = 1

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
        self.numberSpin.setRange(1, vibrationService.selectableModeCount)
        self.numberSpin.setValue(defaults.modeNumber)
        self.numberSpin.setObjectName(f"modeNumberSpin{row}")

        self.amplitudeSpin = QDoubleSpinBox()
        self.amplitudeSpin.setRange(*vibrationService.amplitudeRange)
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
        self.phaseSpin.setRange(*vibrationService.phaseRange)
        self.phaseSpin.setSingleStep(15.0)
        self.phaseSpin.setDecimals(0)
        self.phaseSpin.setSuffix("°")
        self.phaseSpin.setValue(defaults.phaseDegrees)
        self.phaseSpin.setObjectName(f"modePhaseSpin{row}")

    def show(self, setting: ModeSetting) -> None:
        """Put a saved setting in the row without announcing each value."""
        for spin, value in zip(
            self.widgets(),
            (setting.modeNumber, setting.amplitude, setting.phaseDegrees),
            strict=True,
        ):
            blocked = spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(blocked)

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
        self.structureTab = StructureParametersTab(
            saved, structureParametersService.loadSelectedMode()
        )
        self.structureTab.changed.connect(self.emitSetup)
        self.tabs.addTab(self.structureTab, structureParametersTabLabel)
        # The open tab chooses what is animated, so switching is a change.
        self.tabs.currentChanged.connect(self.emitSetup)
        layout.addWidget(self.tabs)
        layout.addWidget(self.buildPlaybackGroup())
        layout.addStretch()

        self.showSystem(self.currentKind())

        # As wide as the widest row needs and no wider, so no value is cut off.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

    def buildStructureGroup(self, defaults: VibrationSetup) -> QGroupBox:
        group = QGroupBox("Structure")
        form = QFormLayout(group)

        self.kindCombo = QComboBox()
        self.kindCombo.setObjectName("kindCombo")
        # A line between the families - beams, plates, the oscillator - since
        # they are different theories and should not read as one long run.
        previousSystem = None
        for kind in StructureKind:
            system = systemFor(kind)
            if previousSystem is not None and system is not previousSystem:
                self.kindCombo.insertSeparator(self.kindCombo.count())
            self.kindCombo.addItem(kind.value, kind.value)
            previousSystem = system
        self.showKind(defaults.kind)
        # The platform's own separator is nearly invisible on a dark popup.
        self.kindCombo.setItemDelegate(SeparatorItemDelegate(self.kindCombo))
        self.kindCombo.currentIndexChanged.connect(self.onKindChanged)
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
        self.dampingSpin.setRange(*vibrationService.dampingRange)
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

    def buildPlaybackGroup(self) -> QGroupBox:
        group = QGroupBox("Playback")
        layout = QVBoxLayout(group)

        form = QFormLayout()
        self.speedSpin = QDoubleSpinBox()
        self.speedSpin.setObjectName("speedSpin")
        self.speedSpin.setRange(*vibrationService.speedRange)
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

    def showKind(self, kind: StructureKind) -> None:
        """Select a type by value: a separator makes positions meaningless."""
        self.kindCombo.setCurrentIndex(self.kindCombo.findData(kind.value))
        self.shownKind = kind

    def onKindChanged(self) -> None:
        """A plate and a beam want different proportions, so offer them.

        Crossing between the two gives the new kind its usual width for the
        length that is set - a plate twice as long as it is wide, a beam
        slender - which the user is then free to change. Moving from one beam
        to another changes nothing: the dimensions are theirs.
        """
        kind = self.currentKind()
        if vibrationService.lengthToWidthFor(kind) != vibrationService.lengthToWidthFor(
            self.shownKind
        ):
            length = self.structureTab.currentSize().length
            self.structureTab.showWidth(vibrationService.widthForKind(kind, length))
        self.shownKind = kind
        self.showSystem(kind)
        self.emitSetup()

    def currentKind(self) -> StructureKind:
        # Qt stores the enum as its string value, so it comes back as one.
        return StructureKind(self.kindCombo.currentData())

    def isSingleModeView(self) -> bool:
        """True while the Structure Parameters tab is open."""
        return self.tabs.currentWidget() is self.structureTab

    def showSystem(self, kind: StructureKind) -> None:
        """Offer what this system has, on both tabs.

        An oscillator has one mode, a beam six: the mode rows and the mode
        list follow, rather than offering modes the structure does not have.
        """
        self.structureTab.showSystem(kind)
        modes = vibrationService.maxModeNumber(kind)
        for row in self.modeRows:
            blocked = row.numberSpin.blockSignals(True)
            row.numberSpin.setRange(1, modes)
            row.numberSpin.blockSignals(blocked)

    def currentSetup(self) -> VibrationSetup:
        parameters = self.structureTab.currentStructureParameters()
        size, material = parameters.size, parameters.material
        if self.isSingleModeView():
            # That tab alone: its mode at a fixed amplitude, undamped.
            return VibrationSetup(
                kind=self.currentKind(),
                size=size,
                material=material,
                springStiffness=parameters.springStiffness,
                modes=(
                    ModeSetting(
                        self.structureTab.selectedMode(),
                        vibrationService.singleModeAmplitude,
                    ),
                ),
                dampingRatio=0.0,
                singleMode=True,
            )
        return VibrationSetup(
            kind=self.currentKind(),
            size=size,
            material=material,
            springStiffness=parameters.springStiffness,
            modes=tuple(row.setting() for row in self.modeRows),
            dampingRatio=self.dampingSpin.value(),
        )

    def captureState(self) -> SessionState:
        """Everything these controls show. The view adds its clock and camera."""
        return SessionState(
            kind=self.currentKind(),
            openTab=self.tabs.tabText(self.tabs.currentIndex()),
            dampingRatio=self.dampingSpin.value(),
            modes=tuple(row.setting() for row in self.modeRows),
            selectedMode=self.structureTab.selectedMode(),
            structure=self.structureTab.currentStructureParameters(),
            playback=PlaybackState(
                speed=self.speedSpin.value(),
                playing=self.playButton.isChecked(),
                timeSeconds=0.0,
            ),
        )

    def restoreState(self, state: SessionState) -> None:
        """Show a saved session, then announce it as a single change."""
        inputs = [self.kindCombo, self.dampingSpin, self.tabs]
        blocked = [widget.blockSignals(True) for widget in inputs]
        self.showKind(state.kind)
        self.dampingSpin.setValue(state.dampingRatio)
        for row, setting in zip(self.modeRows, state.modes, strict=True):
            row.show(setting)
        self.structureTab.restore(state.selectedMode, state.structure)
        self.shownKind = state.kind
        self.showSystem(state.kind)
        self.tabs.setCurrentIndex(
            modalSuperpositionTabIndex
            if state.openTab == modalSuperpositionTabLabel
            else structureParametersTabIndex
        )
        for widget, wasBlocked in zip(inputs, blocked, strict=True):
            widget.blockSignals(wasBlocked)
        self.emitSetup()
        # Playback goes through its own signals: the view acts on them.
        self.speedSpin.setValue(state.playback.speed)
        self.playButton.setChecked(state.playback.playing)

    def currentStructureParameters(self) -> StructureParameters:
        """What the Structure Parameters tab shows now, for saving."""
        return self.structureTab.currentStructureParameters()

    def emitSetup(self) -> None:
        # Frequencies follow the kind, size and material, so relabel first.
        self.structureTab.refreshModeLabels(self.currentKind())
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
