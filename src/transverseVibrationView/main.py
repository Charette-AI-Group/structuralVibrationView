"""Application entry point — wiring only."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from transverseVibrationView import appConfig
from transverseVibrationView.services import themeService
from transverseVibrationView.ui.mainWindow import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(appConfig.appName)
    app.setApplicationVersion(appConfig.appVersion)
    app.setOrganizationName(appConfig.organizationName)
    # Follows Windows unless the user picked an override under Help > Theme.
    themeService.applyTheme(themeService.loadTheme())

    mainWindow = MainWindow()
    mainWindow.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
