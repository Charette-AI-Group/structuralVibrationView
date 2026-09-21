"""Application configuration — paths, defaults, and metadata."""

from __future__ import annotations

import os
from pathlib import Path

appName = "Transverse Structural Vibration View"
appVersion = "0.1.0"
organizationName = "Charette-AI-Group"

# Help > About contents
editorName = "Francois Charette, PhD"
aiAgentName = "Claude - Opus 5"
copyrightHolder = "Charette AI Group, LLC"
# createNewApp rewrites the package name throughout, so this follows the repo
# it actually creates without anyone having to remember to edit it.
repoUrl = "https://github.com/Charette-AI-Group/transverseVibrationView"

# Donate button, shared across the Charette AI Group applications so they look
# like they come from the same place.
donateUrl = "https://www.paypal.com/donate/?hosted_button_id=FEM4WLD7LHY36"
donateColour = "#f0b232"
donateTextColour = "#1f1e1b"
donatePressedColour = "#d9991f"

projectRoot = Path(__file__).resolve().parents[2]
resourcesDir = Path(__file__).resolve().parent / "resources"

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
#     manualUrl = f"{repoUrl}/blob/main/docs/manual/README.md"
manualUrl = ""
# How long to wait for the published copy before falling back to the local one.
manualTimeoutSeconds = 3.0

appDataDir = Path(os.environ.get("APPDATA", str(Path.home()))) / appName
settingsFile = appDataDir / "settings.ini"
windowTitle = appName
defaultWindowWidth = 1200
defaultWindowHeight = 760

# The animation clock. 33 ms is 30 frames per second, smooth enough for a
# rotation and cheap enough that the view stays responsive on a laptop.
animationIntervalMs = 33
