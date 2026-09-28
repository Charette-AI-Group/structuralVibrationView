"""The 3D vibration view: a PyVista interactor plus its control panel.

The interactor is an OpenGL widget from pyvistaqt, so the user rotates, pans
and zooms with the mouse while the structure keeps moving. A QTimer advances
a continuous clock; each tick asks the service for the deformed points and
hands them to the mesh already on screen, so nothing is rebuilt per frame.
"""

from __future__ import annotations

import os
from dataclasses import replace

# qtpy, which pyvistaqt is written against, must pick PySide6 - the only
# binding this app ships with - before it is imported anywhere.
os.environ.setdefault("QT_API", "pyside6")

import numpy as np
import pyvista as pv
from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QHBoxLayout, QWidget
from pyvistaqt import QtInteractor

from structuralVibrationView import appConfig
from structuralVibrationView.models.sessionState import CameraState, SessionState
from structuralVibrationView.models.vibrationModel import VibrationModel, VibrationSetup
from structuralVibrationView.services import vibrationService
from structuralVibrationView.ui.widgets.reportingView import ReportingView
from structuralVibrationView.ui.widgets.vibrationControls import (
    VibrationControls,
    presetViewLabels,
    xyView,
    xzView,
    yzView,
)

# Room around the structure when the camera is fitted: it is about to move,
# and a fit to its rest position clips whatever leaves that box.
cameraMargin = 0.82

displacementArrayName = "Displacement"
deformedMeshName = "deformed"
referenceMeshName = "reference"


def deformedName(index: int) -> str:
    return f"{deformedMeshName}{index}"


def referenceName(index: int) -> str:
    return f"{referenceMeshName}{index}"


class VibrationView(ReportingView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model: VibrationModel | None = None
        # One mesh per geometry part: a beam or plate has one, the
        # spring-mass has its coil and its block.
        self.meshes: list[pv.StructuredGrid] = []
        self.timeSeconds = 0.0
        self.speed = 1.0
        self.frameCount = 0
        # The last thing said about the model, for a window that connects
        # after the first setup has already been reported.
        self.description = ""

        self.interactor = QtInteractor(self)
        self.interactor.setObjectName("interactor")
        self.controls = VibrationControls(self)
        self.controls.setObjectName("controls")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.interactor, stretch=1)
        layout.addWidget(self.controls)

        self.timer = QTimer(self)
        self.timer.setInterval(appConfig.animationIntervalMs)
        self.timer.timeout.connect(self.onTick)

        self.controls.setupChanged.connect(self.applySetup)
        self.controls.playToggled.connect(self.setPlaying)
        self.controls.restartRequested.connect(self.restart)
        self.controls.resetViewRequested.connect(self.resetView)
        self.controls.presetViewRequested.connect(self.showPresetView)
        self.controls.speedChanged.connect(self.setSpeed)

        self.applyPalette()
        self.applySetup(self.controls.currentSetup())
        self.interactor.add_axes()
        self.resetView()
        self.timer.start()

    # ----- model -----------------------------------------------------------

    def applySetup(self, setup: VibrationSetup) -> None:
        """Rebuild the scene for a new setup; the clock keeps running."""
        try:
            model = vibrationService.buildModel(setup)
        except Exception as error:  # a bad mode number should not kill the window
            self.reportError(
                "Cannot Build Structure",
                f"The structure could not be built for these settings. {error}",
            )
            return
        previous = self.model
        self.model = model
        if previous is None or previous.geometry.kind is not model.geometry.kind:
            self.buildScene()
        elif previous.setup.size != model.setup.size or len(self.meshes) != len(
            model.geometry.parts
        ):
            # Same kind, new size: rebuild, but leave the camera where the
            # user put it rather than jumping on every step of a spin box.
            self.buildScene(resetCamera=False)
        else:
            self.updateColourRange()
        self.updateFrame()
        self.controls.showFundamental(model.fundamentalFrequencyHz)
        self.description = vibrationService.describeModel(model)
        self.reportStatus(self.description)

    def buildScene(self, resetCamera: bool = True) -> None:
        assert self.model is not None
        self.clearScene()
        limit = self.model.maxDisplacement
        for index, part in enumerate(self.model.geometry.parts):
            mesh = pv.StructuredGrid()
            mesh.points = part.points.copy()
            mesh.dimensions = part.dimensions
            mesh[displacementArrayName] = np.zeros(part.pointCount)
            self.meshes.append(mesh)

            self.interactor.add_mesh(
                mesh.extract_surface(algorithm="dataset_surface"),
                name=referenceName(index),
                style="wireframe",
                color="gray",
                opacity=0.35,
                line_width=1,
            )
            self.interactor.add_mesh(
                mesh,
                name=deformedName(index),
                scalars=displacementArrayName,
                cmap="coolwarm",
                clim=[-limit, limit],
                smooth_shading=True,
                # One bar for the structure, on the first part it is drawn from.
                show_scalar_bar=index == 0,
                scalar_bar_args=(
                    {"title": "Displacement (m)", "vertical": False}
                    if index == 0
                    else None
                ),
            )
        self.applyPalette()
        if resetCamera:
            self.resetView()
        else:
            self.interactor.reset_camera_clipping_range()

    def clearScene(self) -> None:
        """Take down whatever the last structure was drawn as."""
        for index in range(len(self.meshes)):
            self.interactor.remove_actor(deformedName(index), render=False)
            self.interactor.remove_actor(referenceName(index), render=False)
        for title in list(self.interactor.scalar_bars.keys()):
            self.interactor.remove_scalar_bar(title, render=False)
        self.meshes = []

    def updateColourRange(self) -> None:
        """Keep the colour scale at the worst case so it never saturates."""
        assert self.model is not None
        limit = self.model.maxDisplacement
        for index in range(len(self.meshes)):
            actor = self.interactor.actors.get(deformedName(index))
            if actor is not None:
                # The scalar bar reads the same lookup table, so it follows.
                actor.mapper.scalar_range = (-limit, limit)

    # ----- animation -------------------------------------------------------

    def slowMotionFactor(self) -> float:
        """Structural seconds per screen second at Speed 1x.

        Chosen so mode 1 appears at `displayedFundamentalHz` whatever its real
        frequency, so a stiffer or shorter structure is not a blur.
        """
        if self.model is None:
            return 1.0
        return appConfig.displayedFundamentalHz / self.model.referenceFrequencyHz

    def onTick(self) -> None:
        screenSeconds = appConfig.animationIntervalMs / 1000.0
        self.timeSeconds += self.speed * self.slowMotionFactor() * screenSeconds
        self.updateFrame()

    def updateFrame(self) -> None:
        if self.model is None or not self.meshes:
            return
        moved = vibrationService.deformedPoints(self.model, self.timeSeconds)
        for mesh, (points, w) in zip(self.meshes, moved, strict=True):
            mesh.points = points
            mesh[displacementArrayName] = w
        self.controls.showTime(self.timeSeconds)
        self.frameCount += 1
        self.interactor.render()

    def setPlaying(self, playing: bool) -> None:
        if playing:
            self.timer.start()
            self.reportStatus("Playing.")
        else:
            self.timer.stop()
            self.reportStatus("Paused. Drag in the view to rotate the structure.")

    def isPlaying(self) -> bool:
        return self.timer.isActive()

    def restart(self) -> None:
        self.timeSeconds = 0.0
        self.updateFrame()

    def setSpeed(self, speed: float) -> None:
        self.speed = speed

    def fitCamera(self) -> None:
        """Fit the structure, then stand back far enough for it to move."""
        self.interactor.reset_camera()
        self.interactor.camera.Zoom(cameraMargin)

    def showPresetView(self, plane: str) -> None:
        """Look square-on at a coordinate plane, fitted to the structure.

        X-Z shows the transverse deflection along the length, X-Y looks down
        on the top face, and Y-Z looks along the length at the cross-section.
        The animation carries on; only the camera moves.
        """
        setters = {
            xzView: self.interactor.view_xz,
            xyView: self.interactor.view_xy,
            yzView: self.interactor.view_yz,
        }
        setter = setters.get(plane)
        if setter is None:
            return
        setter()
        self.fitCamera()
        self.interactor.render()
        self.reportStatus(f"{presetViewLabels[plane]}.")

    def resetView(self) -> None:
        """A three-quarter view with the length running left to right.

        The isometric default looks down the beam and foreshortens it, which
        hides the very shape the app is for.
        """
        self.interactor.view_xz()
        camera = self.interactor.camera
        camera.Azimuth(-35)
        camera.Elevation(22)
        camera.OrthogonalizeViewUp()
        self.fitCamera()
        self.interactor.render()

    # ----- sessions --------------------------------------------------------

    def captureSession(self) -> SessionState:
        """The whole window's state: the controls, the clock and the camera."""
        state = self.controls.captureState()
        camera = self.interactor.camera
        return replace(
            state,
            playback=replace(state.playback, timeSeconds=self.timeSeconds),
            camera=CameraState(
                position=tuple(camera.position),
                focalPoint=tuple(camera.focal_point),
                viewUp=tuple(camera.up),
            ),
        )

    def restoreSession(self, state: SessionState) -> None:
        """Put the window back as the session was saved.

        The controls go first, since a new structure type rebuilds the scene
        and resets the camera; the clock and the camera are set after that.
        """
        self.controls.restoreState(state)
        self.timeSeconds = state.playback.timeSeconds
        self.updateFrame()
        if state.camera is not None:
            camera = self.interactor.camera
            camera.position = state.camera.position
            camera.focal_point = state.camera.focalPoint
            camera.up = state.camera.viewUp
            self.interactor.reset_camera_clipping_range()
            self.interactor.render()

    # ----- appearance ------------------------------------------------------

    def changeEvent(self, event: QEvent) -> None:
        # Qt delivers the new palette after the theme is applied, so colours
        # read here are the ones the rest of the window is painted with.
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self.applyPalette()

    def applyPalette(self) -> None:
        palette = self.palette()
        background = palette.window().color()
        text = palette.windowText().color()
        self.interactor.set_background(background.name())
        textRgb = (text.redF(), text.greenF(), text.blueF())
        for bar in self.interactor.scalar_bars.values():
            bar.GetTitleTextProperty().SetColor(*textRgb)
            bar.GetLabelTextProperty().SetColor(*textRgb)
        self.interactor.render()

    # ----- lifecycle -------------------------------------------------------

    def shutdown(self) -> None:
        """Stop the clock and release the render window before Qt tears down."""
        self.timer.stop()
        self.interactor.close()
