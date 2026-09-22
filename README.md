# Transverse Structural Vibration View

3D time-domain animation of transverse structural vibration (PySide6 + PyVista)

A beam or plate vibrates in a 3D view you can rotate, pan and zoom while it moves. Up to
three closed-form modes are superposed (Euler-Bernoulli beams, a simply supported Kirchhoff
plate). Natural frequencies are computed from the dimensions, density and Young's modulus;
the damping ratio, amplitudes and phases are set from a control panel. The animation runs in
slow motion so that mode 1 always plays at one cycle every two seconds at Speed 1x. The rendering is PyVista (VTK) embedded in Qt through `pyvistaqt`'s
`QtInteractor`; a `QTimer` advances a continuous clock and each tick moves the points of the
mesh already on screen. See `docs/manual/README.md` for the controls.

## One-time setup

```powershell
cd W:\projects\26transversalVibration
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Daily workflow

```powershell
cd W:\projects\26transversalVibration
.\.venv\Scripts\Activate.ps1
transverse-vibration-view
```

Or without the script entry point:

```powershell
python -m transverseVibrationView.main
```

Or just double-click **`runApp.cmd`** in the project folder (needs the one-time setup done first).

## Tests and lint

```powershell
pytest
ruff check src tests
```

## Structure

| Layer | Folder | Purpose |
|-------|--------|---------|
| Entry | `src/transverseVibrationView/main.py` | Start `QApplication`, show main window |
| Config | `src/transverseVibrationView/appConfig.py` | Paths, defaults, app metadata |
| UI | `src/transverseVibrationView/ui/` | Widgets and dialogs only |
| Services | `src/transverseVibrationView/services/` | Business logic (no Qt widgets) |
| Models | `src/transverseVibrationView/models/` | Plain Python data types |

See `AGENTS.md` for architecture and naming conventions (for you and AI agents).

---
*Created from the Qt App Template.*
