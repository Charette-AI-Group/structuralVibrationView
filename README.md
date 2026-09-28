# Structural Vibration View

3D time-domain animation of structural vibration (PySide6 + PyVista)

A beam, a plate or a spring-mass oscillator vibrates in a 3D view you can rotate, pan and zoom
while it moves. Up to
three closed-form modes are superposed (Euler-Bernoulli beams, a simply supported Kirchhoff
plate). Natural frequencies are computed from the dimensions, density and Young's modulus;
the damping ratio, amplitudes and phases are set from a control panel. The animation runs in
slow motion so that mode 1 always plays at one cycle every two seconds at Speed 1x. The rendering is PyVista (VTK) embedded in Qt through `pyvistaqt`'s
`QtInteractor`; a `QTimer` advances a continuous clock and each tick moves the points of the
mesh already on screen. See `docs/manual/README.md` for the controls.

## One-time setup

```powershell
cd W:\projects\26structuralVibration
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Daily workflow

```powershell
cd W:\projects\26structuralVibration
.\.venv\Scripts\Activate.ps1
structural-vibration-view
```

Or without the script entry point:

```powershell
python -m structuralVibrationView.main
```

Or just double-click **`runApp.cmd`** in the project folder (needs the one-time setup done first).

## Tests and lint

```powershell
pytest
ruff check src tests
```

## Starting up

Starting takes about 2.0 s, nearly all of it importing PyVista and VTK (1.1 s) and building the
first 3D scene (0.7 s); Qt itself is ready after 0.2 s. A splash screen covers the wait
(`src/structuralVibrationView/ui/splashScreen.py`) and is on screen at 0.28 s, which works only
because `main.py` imports the main window *after* putting the splash up.

It is a frameless window of our own rather than Qt's `QSplashScreen`: measured here,
`QSplashScreen` takes about 1.0 s to appear whatever pixmap it holds, and added that second to
startup. The replacement takes 0.02 s, and total startup is the same with the splash as without.

Set `STRUCTURAL_VIBRATION_VIEW_NO_SPLASH=1` to start straight into the window.

## App icon

The icon - a cantilever clamped to a wall, caught mid-swing in its first mode shape - is drawn
in code, like 26theOneAssets' and 26pySPWB's: `tools/makeIcons.py` paints it separately at each
size from 16 to 256 px and packs them into `src/structuralVibrationView/resources/structuralVibrationView.ico`,
plus a 1024 px PNG. Small sizes drop the swing and keep a bent beam on a wall, which is what
still reads at 16 px. To redraw it after changing the design:

```powershell
python tools/makeIcons.py
```

## Structure

| Layer | Folder | Purpose |
|-------|--------|---------|
| Entry | `src/structuralVibrationView/main.py` | Start `QApplication`, show main window |
| Config | `src/structuralVibrationView/appConfig.py` | Paths, defaults, app metadata |
| UI | `src/structuralVibrationView/ui/` | Widgets and dialogs only |
| Services | `src/structuralVibrationView/services/` | Business logic (no Qt widgets) |
| Models | `src/structuralVibrationView/models/` | Plain Python data types |

Each family of structures is a **system** under `src/structuralVibrationView/services/systems/`:
it says how many modes it has, what they are called, what their frequencies are, what the
structure is drawn as (one grid, or several), how each mode moves those points, and which
Structure Parameters rows it uses. `vibrationService` assembles a model from whichever system
the chosen type belongs to, and nothing above it asks what kind of structure is on screen.
Adding a system is one module there plus a line in that package's `__init__.py`.

See `AGENTS.md` for architecture and naming conventions (for you and AI agents).

---
*Created from the Qt App Template.*
