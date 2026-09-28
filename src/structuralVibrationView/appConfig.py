"""Application configuration — paths, defaults, and metadata."""

from __future__ import annotations

import os
from pathlib import Path

appName = "Structural Vibration View"
appVersion = "0.1.0"
organizationName = "Charette-AI-Group"

# Help > About contents
editorName = "Francois Charette, PhD"
aiAgentName = "Claude - Opus 5"
copyrightHolder = "Charette AI Group, LLC"
# createNewApp rewrites the package name throughout, so this follows the repo
# it actually creates without anyone having to remember to edit it.
repoUrl = "https://github.com/Charette-AI-Group/structuralVibrationView"

# Donate button, shared across the Charette AI Group applications so they look
# like they come from the same place.
donateUrl = "https://www.paypal.com/donate/?hosted_button_id=FEM4WLD7LHY36"
donateColour = "#f0b232"
donateTextColour = "#1f1e1b"
donatePressedColour = "#d9991f"

projectRoot = Path(__file__).resolve().parents[2]
resourcesDir = Path(__file__).resolve().parent / "resources"
# Drawn by tools/makeIcons.py. The app runs without one if it is missing.
iconFile = resourcesDir / "structuralVibrationView.ico"
# Set this to 1 to start straight into the window, with no splash screen.
noSplashEnvVar = "STRUCTURAL_VIBRATION_VIEW_NO_SPLASH"
# Windows groups taskbar buttons by this ID. Without one, a window started by
# pythonw.exe (as runApp.cmd does) is filed under Python and shows its icon.
appUserModelId = f"{organizationName}.StructuralVibrationView"

# Help > User Manual. The copy in the checkout is what a new app has, and it is
# enough: the menu item works from the first run rather than being a promise.
manualPath = projectRoot / "docs" / "manual" / "README.md"
# Publishing is opt-in. Set this once the manual is pushed somewhere that
# renders markdown - GitHub shows screenshots that a local .md opened in an
# editor does not - and the published copy becomes the preferred one, with the
# local copy as the offline fallback. Left empty it stays local and no network
# request is made at all, which is the honest default: a new app has nothing
# published yet, and deriving a URL from repoUrl would hand most apps an
# address that 404s and a wait to discover it.
manualUrl = f"{repoUrl}/blob/main/docs/manual/README.md"
# How long to wait for the published copy before falling back to the local one.
manualTimeoutSeconds = 3.0

appDataDir = Path(os.environ.get("APPDATA", str(Path.home()))) / appName
settingsFile = appDataDir / "settings.ini"
# What the app was called before. Its settings are taken over on the first
# run under the new name, so a rename does not lose the window's position,
# the theme, or the structure the user last set.
legacyAppName = "Transverse Structural Vibration View"
legacySettingsFile = (
    Path(os.environ.get("APPDATA", str(Path.home()))) / legacyAppName / "settings.ini"
)
windowTitle = appName
defaultWindowWidth = 1200
defaultWindowHeight = 760

# The animation clock. 33 ms is 30 frames per second, smooth enough for a
# rotation and cheap enough that the view stays responsive on a laptop.
animationIntervalMs = 33
# Real structures vibrate far faster than a screen can show, so the animation
# runs in slow motion: at Speed 1x, mode 1 appears at this frequency whatever
# its real one. Half a hertz is a cycle every two seconds, easy to follow.
displayedFundamentalHz = 0.5
