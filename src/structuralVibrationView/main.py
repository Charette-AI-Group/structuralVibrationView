"""Application entry point — wiring only.

The order here is deliberate. Qt costs about 0.2 s to import, while the main
window drags in PyVista and VTK for another 1.1 s and builds its first 3D
scene in 0.7 s more. So the splash goes up first and the window is imported
afterwards: importing it at module scope would spend the whole wait before
`main` runs, and leave nothing to put on screen.
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from structuralVibrationView import appConfig
from structuralVibrationView.services import settingsService, themeService
from structuralVibrationView.ui import splashScreen


def setAppIdentity(app: QApplication) -> None:
    """The app's icon on every window, and a taskbar button under its own name.

    Call before the first window appears: Windows files a window under the
    ID its process had when the window was created.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                appConfig.appUserModelId
            )
        except (AttributeError, OSError):
            pass  # the taskbar files it under Python instead - nothing worse
    if appConfig.iconFile.is_file():
        app.setWindowIcon(QIcon(str(appConfig.iconFile)))


def main() -> int:
    # A packaged build has no console, so the way to ask it whether it is
    # intact is to have it write a report: see selftest.py.
    if "--selftest" in sys.argv:
        from structuralVibrationView.selftest import runSelfTest

        index = sys.argv.index("--selftest")
        reportPath = sys.argv[index + 1] if len(sys.argv) > index + 1 else None
        return runSelfTest(reportPath)

    app = QApplication(sys.argv)
    app.setApplicationName(appConfig.appName)
    app.setApplicationVersion(appConfig.appVersion)
    app.setOrganizationName(appConfig.organizationName)
    setAppIdentity(app)
    # Anything the app remembered under its former name, before it is read.
    settingsService.adoptLegacySettings()
    # Follows Windows unless the user picked an override under Help > Theme.
    themeService.applyTheme(themeService.loadTheme())

    # Up now, while Qt is the only thing loaded, and covering the import
    # below - which is where the wait actually is.
    splash = splashScreen.makeSplash()
    splashScreen.report(splash, "Loading 3D graphics...")

    from structuralVibrationView.ui.mainWindow import MainWindow

    splashScreen.report(splash, "Building the structure...")
    mainWindow = MainWindow()
    mainWindow.show()
    splashScreen.finish(splash, mainWindow)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
