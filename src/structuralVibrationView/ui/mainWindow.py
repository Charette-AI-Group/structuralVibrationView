"""Main application window."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QDesktopServices,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from structuralVibrationView import appConfig
from structuralVibrationView.services import (
    sessionFileService,
    structureParametersService,
    themeService,
    windowGeometryService,
)
from structuralVibrationView.services.manualWorker import ManualWorker
from structuralVibrationView.ui.dialogs.aboutDialog import showAbout
from structuralVibrationView.ui.dialogs.errorDialog import showError
from structuralVibrationView.ui.widgets.reportingView import ReportingView
from structuralVibrationView.ui.widgets.vibrationView import VibrationView


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(appConfig.windowTitle)
        self.resize(appConfig.defaultWindowWidth, appConfig.defaultWindowHeight)
        self.restoreSavedGeometry()
        self.manualWorker: ManualWorker | None = None

        self.buildMenuBar()
        self.showStatus("Ready")

        self.vibrationView = VibrationView(self)
        self.connectView(self.vibrationView)
        self.setCentralWidget(self.vibrationView)
        # The view described itself while it was built, before it was wired.
        self.showStatus(self.vibrationView.description)

    def buildMenuBar(self) -> None:
        # Menus are kept as attributes: features can extend them later, and it
        # prevents the Python wrappers from being garbage-collected.
        fileMenu = self.fileMenu = self.menuBar().addMenu("&File")

        self.openAction = QAction("&Open...", self)
        self.openAction.setShortcut(QKeySequence.StandardKey.Open)
        self.openAction.triggered.connect(self.onFileOpen)
        fileMenu.addAction(self.openAction)

        self.saveAction = QAction("&Save...", self)
        self.saveAction.setShortcut(QKeySequence.StandardKey.Save)
        self.saveAction.triggered.connect(self.onFileSave)
        fileMenu.addAction(self.saveAction)

        fileMenu.addSeparator()

        self.exitAction = QAction("E&xit", self)
        self.exitAction.setShortcut(QKeySequence("Ctrl+Q"))
        self.exitAction.triggered.connect(self.close)
        fileMenu.addAction(self.exitAction)

        helpMenu = self.helpMenu = self.menuBar().addMenu("&Help")

        self.themeMenu = helpMenu.addMenu("&Theme")
        self.themeGroup = QActionGroup(self)
        self.themeGroup.setExclusive(True)
        self.themeActions: dict[str, QAction] = {}
        activeTheme = themeService.loadTheme()
        for theme in themeService.themeChoices:
            action = QAction(themeService.themeLabels[theme], self)
            action.setCheckable(True)
            action.setChecked(theme == activeTheme)
            action.triggered.connect(partial(self.onThemeChosen, theme))
            self.themeGroup.addAction(action)
            self.themeMenu.addAction(action)
            self.themeActions[theme] = action

        helpMenu.addSeparator()

        self.manualAction = QAction("User &Manual...", self)
        self.manualAction.setShortcut(QKeySequence.StandardKey.HelpContents)  # F1
        self.manualAction.triggered.connect(self.onHelpManual)
        helpMenu.addAction(self.manualAction)

        self.aboutAction = QAction("&About", self)
        self.aboutAction.triggered.connect(self.onHelpAbout)
        helpMenu.addAction(self.aboutAction)

    def restoreSavedGeometry(self) -> None:
        """Put the window back where it was last closed, if it was.

        The default size set just before stays when nothing is saved, or when
        Qt cannot use what is - a restore that fails leaves the window alone.
        """
        geometry = windowGeometryService.loadGeometry()
        if geometry is not None:
            self.restoreGeometry(geometry)

    def connectView(self, view: ReportingView) -> None:
        """Wire a view's status and failures into this window.

        Call this for every view you add. Status goes to the bar, failures go
        to a dialog, and the view is spared knowing which is which.
        """
        view.statusMessage.connect(self.showStatus)
        view.errorMessage.connect(self.showError)

    def showStatus(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def showError(self, title: str, message: str) -> None:
        """Kept a method so tests can watch for it without a dialog opening."""
        showError(self, title, message)

    def onThemeChosen(self, theme: str) -> None:
        themeService.saveTheme(theme)
        themeService.applyTheme(theme)
        if theme == themeService.systemTheme:
            self.showStatus("Theme follows the Windows setting.")
        else:
            self.showStatus(f"{theme.capitalize()} theme applied.")

    def onFileOpen(self) -> None:
        """Read a session file and put the whole window back as it was saved."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Session", self.sessionFolder(), sessionFileService.fileFilter
        )
        if not path:
            return
        try:
            state = sessionFileService.loadSession(Path(path))
        except sessionFileService.SessionFileError as error:
            self.showError("Open Session", f"{Path(path).name} could not be opened. {error}")
            return
        self.vibrationView.restoreSession(state)
        sessionFileService.saveLastFolder(Path(path).parent)
        self.showStatus(f"Opened {Path(path).name}.")

    def onFileSave(self) -> None:
        """Write everything the window shows to a session file."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", self.sessionFolder(), sessionFileService.fileFilter
        )
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(sessionFileService.fileExtension)
        try:
            sessionFileService.saveSession(target, self.vibrationView.captureSession())
        except OSError as error:
            self.showError(
                "Save Session",
                f"{target.name} could not be written. {error.strerror or error}. "
                "Choose another folder, or check the file is not open elsewhere.",
            )
            return
        sessionFileService.saveLastFolder(target.parent)
        self.showStatus(f"Saved {target.name}.")

    def sessionFolder(self) -> str:
        folder = sessionFileService.loadLastFolder()
        return str(folder) if folder is not None else ""

    def onHelpManual(self) -> None:
        """Open the manual, preferring the published copy when there is one.

        Whether it is reachable has to be asked separately: openUrl reports
        that a browser launched, not that the page loaded. The ask can hang
        until its timeout, so it happens off this thread. With manualUrl empty
        - which is how a new app starts - the service answers no immediately
        and the local copy is used without touching the network.
        """
        if self.manualWorker is not None:
            return
        self.manualAction.setEnabled(False)
        self.showStatus("Looking for the manual...")
        worker = ManualWorker(parent=self)
        worker.resolved.connect(self.openManual)
        worker.finished.connect(self.onManualCheckFinished)
        self.manualWorker = worker
        worker.start()

    def openManual(self, publishedIsReachable: bool) -> None:
        if publishedIsReachable and QDesktopServices.openUrl(
            QUrl(appConfig.manualUrl)
        ):
            self.showStatus("The manual is opening in your browser.")
            return
        local = appConfig.manualPath
        if local.exists() and QDesktopServices.openUrl(QUrl.fromLocalFile(str(local))):
            self.showStatus(f"Opening the local copy, {local}")
            return
        # Leaving the reader with nothing is worse than making them copy a path.
        QMessageBox.information(
            self,
            "User Manual",
            "Could not open the manual. It is at:\n\n"
            f"{appConfig.manualUrl or '(nothing published)'}\n\n{local}",
        )

    def onManualCheckFinished(self) -> None:
        if self.manualWorker is not None:
            self.manualWorker.deleteLater()
            self.manualWorker = None
        self.manualAction.setEnabled(True)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.manualWorker is not None:
            # Short, but a thread running into interpreter shutdown turns a
            # clean exit into a crash.
            self.manualWorker.wait(int(appConfig.manualTimeoutSeconds * 1000) + 1000)
        # The VTK render window must go before Qt does, or exit is not clean.
        self.vibrationView.shutdown()
        windowGeometryService.saveGeometry(self.saveGeometry())
        # The last structure parameters and mode set become the defaults next time.
        controls = self.vibrationView.controls
        structureParametersService.saveStructureParameters(controls.currentStructureParameters())
        structureParametersService.saveSelectedMode(controls.structureTab.selectedMode())
        super().closeEvent(event)

    def onHelpAbout(self) -> None:
        if showAbout(self):
            self.showStatus(
                "Thank you - the donation page is opening in your browser."
            )
