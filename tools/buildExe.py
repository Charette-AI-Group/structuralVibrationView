r"""Build the standalone application, and check that what shipped is right.

PyInstaller succeeds cheerfully while leaving out a data file, and the symptom
turns up later as a window with no icon, a manual that will not open, or an
empty panel where the 3D view should be. So the build is followed by an
inventory of what actually landed in the bundle, and then by the
application's own --selftest, which is the only thing that proves a windowed
build starts at all: it has no console to print to.

    .venv\Scripts\python.exe tools\buildExe.py
    .venv\Scripts\python.exe tools\buildExe.py --no-selftest
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

projectRoot = Path(__file__).resolve().parents[1]
specFile = projectRoot / "structuralVibrationView.spec"
outputRoot = projectRoot / "dist"
isMac = sys.platform == "darwin"
bundleName = "StructuralVibrationView"

# What PyInstaller leaves behind, which is not the same shape on the two
# platforms: Windows gets a folder to install, macOS an application bundle.
if isMac:
    distDir = outputRoot / f"{bundleName}.app"
    executable = distDir / "Contents" / "MacOS" / bundleName
else:
    distDir = outputRoot / bundleName
    executable = distDir / f"{bundleName}.exe"

reportFile = outputRoot / "selftest.txt"
buildTimeoutSeconds = 2400.0
selfTestTimeoutSeconds = 300.0

# Everything the application reaches for at run time, as paths relative to
# wherever the bundle keeps its data. That location differs by platform and by
# PyInstaller version, so these are searched for rather than looked up: what
# matters is that they shipped, not which folder they landed in.
expectedPayload = [
    Path("structuralVibrationView/resources/structuralVibrationView.ico"),
    Path("structuralVibrationView/resources/structuralVibrationView.png"),
    Path("docs/manual/README.md"),
]
# Nothing here belongs to a user, but a stray settings file would hand every
# install somebody else's window position and last structure.
refusedPayload = [
    Path("settings.ini"),
]


def folderSize(folder: Path) -> int:
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())


def humanSize(byteCount: int) -> str:
    return f"{byteCount / 1_000_000:.0f} MB"


def build() -> int:
    if distDir.exists():
        shutil.rmtree(distDir)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(specFile),
        "--noconfirm",
        "--clean",
        "--distpath",
        str(outputRoot),
        "--workpath",
        str(projectRoot / "build"),
    ]
    print(f"$ {subprocess.list2cmdline(command)}")
    return subprocess.run(command, cwd=projectRoot, timeout=buildTimeoutSeconds).returncode


def shippedSomewhere(relative: Path) -> bool:
    """Whether the bundle holds this path under any of its data roots.

    Windows puts data in _internal; a macOS .app splits it between
    Contents/Frameworks and Contents/Resources, with symlinks between them.
    Hard-coding either is how this check starts passing for the wrong reason
    on the other platform.
    """
    return any(
        candidate.exists()
        for candidate in (
            distDir / relative,
            distDir / "_internal" / relative,
            distDir / "Contents" / "Frameworks" / relative,
            distDir / "Contents" / "Resources" / relative,
        )
    )


def checkPayload() -> list[str]:
    problems: list[str] = []
    for relative in expectedPayload:
        if not shippedSomewhere(relative):
            problems.append(f"missing from the bundle: {relative}")
    for relative in refusedPayload:
        if shippedSomewhere(relative):
            problems.append(f"should not have shipped: {relative}")
    # VTK is loaded by name rather than imported, so its absence is silent
    # until the view is built. One of its libraries standing in for the rest.
    pattern = "*vtkRenderingOpenGL2*" if not isMac else "*vtkRenderingOpenGL2*"
    if not any(distDir.rglob(pattern)):
        problems.append("VTK's OpenGL renderer did not ship: the 3D view would be empty")
    return problems


def runSelfTest() -> list[str]:
    """Start the built executable and ask it whether it is intact."""
    print(f"$ {executable} --selftest {reportFile}")
    try:
        completed = subprocess.run(
            [str(executable), "--selftest", str(reportFile)],
            cwd=outputRoot,
            timeout=selfTestTimeoutSeconds,
        )
    except subprocess.TimeoutExpired:
        return [f"--selftest did not finish within {selfTestTimeoutSeconds:.0f} s"]

    if reportFile.exists():
        print("\nWhat it reported:")
        for line in reportFile.read_text(encoding="utf-8").splitlines():
            print(f"  {line}")
    if completed.returncode != 0:
        return [f"--selftest failed with code {completed.returncode}"]
    if not reportFile.exists():
        return [f"--selftest wrote no report to {reportFile}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--no-selftest",
        action="store_true",
        help="skip launching the built executable (payload inventory only)",
    )
    arguments = parser.parse_args()

    code = build()
    if code != 0:
        print(f"\nPyInstaller failed with code {code}.")
        return code
    if not executable.exists():
        print(f"\nBuild reported success but {executable} is not there.")
        return 1

    problems = checkPayload()
    if not problems and not arguments.no_selftest:
        problems += runSelfTest()

    print()
    print(f"Bundle    : {distDir}")
    print(f"Executable: {executable.name} ({humanSize(executable.stat().st_size)})")
    print(f"Total     : {humanSize(folderSize(distDir))}")
    if problems:
        print("\nNOT SHIPPABLE:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nPayload is complete and the built application reports itself intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
