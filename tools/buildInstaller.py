r"""Compile the Windows installer from the bundle tools\buildExe.py produced.

The version is read from the application rather than typed into the .iss, so
the installer, the About box and the wheel cannot disagree about what this is.
Somebody has to keep them together, and a person editing three files is the
one thing here that is certain to drift.

    .venv\Scripts\python.exe tools\buildInstaller.py

Needs Inno Setup 6. On a GitHub Windows runner it is already there; locally,
winget install JRSoftware.InnoSetup puts it under LOCALAPPDATA rather than in
Program Files, so both are looked for.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

projectRoot = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(projectRoot / "src"))

scriptFile = projectRoot / "installer" / "structuralVibrationView.iss"
bundleDir = projectRoot / "dist" / "StructuralVibrationView"
outputDir = projectRoot / "dist"
compileTimeoutSeconds = 1200.0

compilerCandidates = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
]


def findCompiler() -> Path | None:
    for candidate in compilerCandidates:
        if candidate.name and candidate.is_file():
            return candidate
    return None


def appVersion() -> str:
    from structuralVibrationView import appConfig

    return appConfig.appVersion


def main() -> int:
    if not bundleDir.is_dir():
        print(f"No bundle at {bundleDir}. Run tools\\buildExe.py first.")
        return 1

    compiler = findCompiler()
    if compiler is None:
        print("Inno Setup 6 was not found. Looked in:")
        for candidate in compilerCandidates:
            print(f"  {candidate}")
        print("\nInstall it with:  winget install JRSoftware.InnoSetup")
        return 1

    version = appVersion()
    command = [
        str(compiler),
        f"/DAppVersion={version}",
        str(scriptFile),
    ]
    print(f"$ {subprocess.list2cmdline(command)}")
    completed = subprocess.run(command, cwd=projectRoot, timeout=compileTimeoutSeconds)
    if completed.returncode != 0:
        print(f"\nInno Setup failed with code {completed.returncode}.")
        return completed.returncode

    installer = outputDir / f"structuralVibrationViewSetup-{version}.exe"
    if not installer.is_file():
        print(f"\nInno Setup reported success but {installer} is not there.")
        return 1
    print(f"\nInstaller: {installer}")
    print(f"Size     : {installer.stat().st_size / 1_000_000:.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
