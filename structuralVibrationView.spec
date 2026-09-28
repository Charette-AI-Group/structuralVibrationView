# -*- mode: python ; coding: utf-8 -*-
r"""PyInstaller build of the application. Driven by tools\buildExe.py.

A one-folder build rather than one-file, on purpose:

  - It starts immediately. A one-file build unpacks the whole Qt and VTK
    runtime to a temporary folder on every launch, which for a bundle this
    size is a long wait before anything appears, every single time.
  - The installer wants a folder anyway, and an uninstaller that removes a
    folder is easier to reason about than one chasing a self-extractor.

VTK is the awkward part. Its Python modules are loaded by name at run time
rather than imported in the source, so PyInstaller's analysis cannot see
them: without collecting them here the bundle builds happily and then shows
an empty panel where the structure should be. The self-test builds the real
3D view for that reason.

What ships is the read-only half: the package with its icons, and the manual
that Help falls back to when there is no network. Everything the app writes
lives under APPDATA and is created on first run.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

projectRoot = Path(SPECPATH)
isMac = sys.platform == "darwin"

# The one place the version comes from, here as everywhere else. appConfig
# imports nothing but the standard library, so reading it costs nothing and a
# bundle can never claim a version the application does not report.
sys.path.insert(0, str(projectRoot / "src"))
from structuralVibrationView import appConfig  # noqa: E402

package = "structuralVibrationView"

# PyInstaller wants the platform's own icon format. Windows takes the
# multi-size .ico; macOS takes .icns, which PyInstaller renders from this PNG
# at build time - which is why pillow is in the build extra.
appIcon = str(appConfig.largeIconFile if isMac else appConfig.iconFile)

# PyInstaller does not collect package data on its own, and appConfig looks
# for the icons inside the package. Without this the executable wears the
# icon while the running window does not, which is a confusing half of the
# job: the taskbar looks right and the window looks unfinished.
datas = [
    (str(projectRoot / "src" / package / "resources"), f"{package}/resources"),
    (str(projectRoot / "docs" / "manual"), "docs/manual"),
]
# PyVista ships colour maps and example data it reads at run time.
datas += collect_data_files("pyvista")
datas += collect_data_files("vtkmodules")

# vtkmodules is imported by name, module by module, as VTK's Python layer
# wires itself up; pyvista then reaches for whichever ones a filter needs.
hiddenimports = collect_submodules("vtkmodules")
hiddenimports += ["vtkmodules.all", "vtkmodules.util", "vtkmodules.util.numpy_support"]
hiddenimports += collect_submodules("pyvista")
hiddenimports += ["pyvistaqt"]

# Development-only, or simply never reached, and large enough to be worth
# refusing. Nothing here plays a video or renders a web page, and the Qt hook
# is otherwise happy to bring both along. Matplotlib comes in with pyvista's
# colour maps; the app never draws with it.
excludes = [
    "pytest",
    "_pytest",
    "pytest_qt",
    "ruff",
    "tkinter",
    "PyInstaller",
    "IPython",
    "jupyter",
    "trame",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtCharts",
    "PySide6.Qt3DCore",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.QtSql",
    "PySide6.QtTest",
]

analysis = Analysis(
    [str(projectRoot / "src" / package / "main.py")],
    pathex=[str(projectRoot / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="StructuralVibrationView",
    icon=appIcon,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # No console: this is a windowed app, and a console behind a GUI is a
    # thing users close by accident, taking the app with it. --selftest
    # writes to a file for the same reason.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collected = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="StructuralVibrationView",
)

# macOS wants an application bundle, not a folder of files: a .app is what
# Finder opens, what the Dock shows, and what a person drags to Applications.
if isMac:
    bundle = BUNDLE(
        collected,
        name="StructuralVibrationView.app",
        icon=appIcon,
        bundle_identifier="com.charette-ai-group.structuralvibrationview",
        info_plist={
            # Without this the window is drawn at half resolution on a
            # Retina display and every glyph in it looks soft.
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": appConfig.appVersion,
            "CFBundleVersion": appConfig.appVersion,
            "CFBundleDisplayName": appConfig.appName,
        },
    )
