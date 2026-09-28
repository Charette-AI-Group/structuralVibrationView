"""Check that a build has everything it needs, and say so.

Worth having because what packaging loses, it loses quietly. A missing icon
gives a blank tile, a missing manual gives a menu item that opens nothing,
and a VTK that did not ship gives a window with an empty grey panel where
the structure should be. None of those crash, and a build can look fine from
the outside while broken in exactly the ways nobody checks by hand.

So the build runs this and refuses to publish a bundle that fails it:

    structuralVibrationView.exe --selftest report.txt

Everything here is read-only: it writes only the report it is asked for, and
touches no settings file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from structuralVibrationView import appConfig


def resourceChecks() -> list[tuple[str, bool, str]]:
    """Every bundled file the app reaches for, and whether it is there."""
    return [
        ("applicationIcon", appConfig.iconFile.is_file(), str(appConfig.iconFile)),
        ("largeIcon", appConfig.largeIconFile.is_file(), str(appConfig.largeIconFile)),
        ("manual", appConfig.manualPath.is_file(), str(appConfig.manualPath)),
    ]


def windowCheck() -> tuple[bool, str]:
    """Build the window offscreen: proof that Qt, VTK and PyVista all came up.

    The heaviest thing a packaged build can drop is a Qt plugin or a VTK
    library, and that shows up here rather than as a window that never
    appears on a machine with no console to print the reason to. The 3D view
    is built for real, so a missing renderer cannot pass.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication

        from structuralVibrationView.main import setAppIdentity
        from structuralVibrationView.ui.mainWindow import MainWindow

        application = QApplication.instance() or QApplication([])
        # The same wiring a real start does, so the icon check means something.
        setAppIdentity(application)
        window = MainWindow()
        title = window.windowTitle()
        wornIcon = not window.windowIcon().isNull()
        view = window.vibrationView
        meshes = len(view.meshes)
        frequency = view.model.fundamentalFrequencyHz if view.model else 0.0
        view.shutdown()
        window.close()
        del application
    except Exception as exc:  # a build that cannot start must say why
        return False, f"{type(exc).__name__}: {exc}"
    if not title:
        return False, "the window has no title"
    if not wornIcon:
        return False, "the window is not wearing its icon"
    if not meshes:
        return False, "the 3D view drew nothing"
    if frequency <= 0.0:
        return False, "the structure has no computed frequency"
    return True, f"{title}, {meshes} mesh(es), mode 1 at {frequency:.1f} Hz"


def report() -> tuple[str, bool]:
    """The whole report, and whether the build is shippable."""
    lines = [
        f"app={appConfig.appName} {appConfig.appVersion}",
        f"platform={sys.platform}",
        f"frozen={appConfig.isFrozen}",
        f"bundleRoot={appConfig.bundleRoot}",
        f"resourcesDir={appConfig.resourcesDir}",
    ]
    passed = True
    for name, found, detail in resourceChecks():
        lines.append(f"{name}={'ok' if found else 'MISSING'}  {detail}")
        passed = passed and found

    windowOk, detail = windowCheck()
    lines.append(f"window={'ok' if windowOk else 'FAILED'}  {detail}")
    passed = passed and windowOk

    lines.append(f"result={'ok' if passed else 'FAILED'}")
    return "\n".join(lines), passed


def runSelfTest(reportPath: str | None = None) -> int:
    text, passed = report()
    if reportPath:
        Path(reportPath).write_text(text, encoding="utf-8")
    print(text)
    return 0 if passed else 1
