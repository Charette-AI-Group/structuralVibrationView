"""Application entry point — wiring only."""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from transverseVibrationView import appConfig
from transverseVibrationView.services import themeService
from transverseVibrationView.ui.mainWindow import MainWindow


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
    app = QApplication(sys.argv)
    app.setApplicationName(appConfig.appName)
    app.setApplicationVersion(appConfig.appVersion)
    app.setOrganizationName(appConfig.organizationName)
    setAppIdentity(app)
    # Follows Windows unless the user picked an override under Help > Theme.
    themeService.applyTheme(themeService.loadTheme())

    mainWindow = MainWindow()
    mainWindow.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
