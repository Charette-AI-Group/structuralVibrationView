"""Main application window."""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QDesktopServices,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
)

from transverseVibrationView import appConfig
from transverseVibrationView.services import themeService, windowGeometryService
from transverseVibrationView.services.manualWorker import ManualWorker
from transverseVibrationView.ui.dialogs.aboutDialog import showAbout
from transverseVibrationView.ui.dialogs.errorDialog import showError
from transverseVibrationView.ui.widgets.reportingView import ReportingView
from transverseVibrationView.ui.widgets.vibrationView import VibrationView


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

        self.newAction = QAction("&New", self)
        self.newAction.setShortcut(QKeySequence.StandardKey.New)
        self.newAction.triggered.connect(self.onFileNew)
        fileMenu.addAction(self.newAction)

        self.openAction = QAction("&Open...", self)
        self.openAction.setShortcut(QKeySequence.StandardKey.Open)
        self.openAction.triggered.connect(self.onFileOpen)
        fileMenu.addAction(self.openAction)

        self.saveAction = QAction("&Save", self)
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

    # Placeholder slots — replace the bodies with your app's file handling.
    def onFileNew(self) -> None:
        self.showStatus("File > New selected")

    def onFileOpen(self) -> None:
        self.showStatus("File > Open selected")

    def onFileSave(self) -> None:
        self.showStatus("File > Save selected")

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
        super().closeEvent(event)

    def onHelpAbout(self) -> None:
        if showAbout(self):
            self.showStatus(
                "Thank you - the donation page is opening in your browser."
            )
