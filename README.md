# Structural Vibration View

**This is teaching software.** It exists so that students, engineers, researchers and anyone
curious - including people building something in a garage - can *see* how a simple structure
deflects while it vibrates, instead of reading a mode shape off a page. A mode shape drawn in a
textbook is a frozen curve with arrows; here it is a structure bending, at a pace slow enough to
follow, from an angle you choose.

Animate the free vibration of a beam, a plate or a spring-mass oscillator in a 3D view you can
rotate, pan and zoom while it moves. Natural frequencies come from the dimensions and the
material, not from a number typed in. Built with PySide6 and PyVista.

It is a teaching tool, not an analysis package: every structure is uniform, every result comes
from closed-form theory, and nothing here replaces a finite element model for a real part.

## What it does

- **Pick a system.** Three families, separated in the list: the beams (cantilever, simply
  supported, clamped-clamped), the plates (simply supported, clamped on all four edges), and a
  spring-mass oscillator. Each carries its own theory, and the controls show only the parameters
  that family uses.
- **Natural frequencies, computed.** Euler-Bernoulli for the beams, Kirchhoff for the plates -
  with Warburton's formula for the clamped one, within about 1 % of the published values - and
  one over two pi times the square root of stiffness over mass for the oscillator. Change the
  thickness or the material and every frequency follows.
- **Slow motion that fits the structure.** Real modes run from tens of hertz to kilohertz, far
  too fast to watch. At Speed 1x, mode 1 always takes two seconds per cycle whatever it really
  runs at, so a high mode is as watchable as a low one. The time readout stays in real
  structural time.
- **One mode, or three at once.** The **Structure Parameters** tab animates the mode chosen at
  its top, alone and undamped, with its frequency beside it. The **Modal Superposition** tab adds
  up to three modes with their own amplitudes and phases, and a damping ratio for the decay.
  Whichever tab is open is what the view animates.
- **Materials.** A preset list - aluminium, steel, stainless, titanium, copper, brass, glass,
  concrete, acrylic, polycarbonate - or your own density, Young's modulus and Poisson's ratio.
  Editing any of them says **Custom**.
- **Colour by displacement**, on a fixed scale so the colours mean the same thing from frame to
  frame, over a grey wireframe of the structure at rest.
- **Rotate while it moves.** Drag to orbit, or jump to the X-Z, X-Y and Y-Z planes.
- **Save the window to a file.** **File > Save** writes the type, both tabs, the playback state
  and the camera to a readable `.tvv` file; **File > Open** puts it all back.
- The dimensions, material, selected mode, window position and theme are remembered between
  sessions.

**Website:** <https://charette-ai-group.github.io/structuralVibrationView/> — screenshots and the
downloads, built from [`docs/`](docs/).

See [`docs/manual/README.md`](docs/manual/README.md) for the user manual (also under
**Help > User Manual**, F1).

## Systems

Each family of structures is a **system** under
[`src/structuralVibrationView/services/systems/`](src/structuralVibrationView/services/systems/),
and answers the same five questions:

| The system says | Used for |
|-----------------|----------|
| How many modes it has, and what each is called | The mode list, the mode rows, the status bar |
| Each mode's natural frequency | The label beside every mode, and the animation's pace |
| What it is drawn as: one grid of points, or several | The meshes in the 3D view |
| How a mode moves those points | Every frame |
| Which parameters it uses | Which rows the Structure Parameters tab shows |

Nothing above that interface asks what kind of structure is on screen, which is why the
spring-mass - two parts, one mode, a stiffness instead of a Young's modulus - needed no changes
in the view or the controls beyond following what the system says. Adding a system is one module
there plus a line in that package's `__init__.py`.

## Icons

Generated, never hand-drawn:

```powershell
python tools\makeIcons.py
```

This writes the application icon, a multi-size `.ico` plus a 1024 px PNG for macOS. Every size
is drawn at that size rather than shrunk from the largest, and the small ones drop detail that
stops reading: below 32 px the swing goes, since a wall with two lines fanning from it reads as
the letter K.

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
ruff check src tests tools
```

## Standalone builds

Users do not need Python.
[Releases](https://github.com/Charette-AI-Group/structuralVibrationView/releases) carry a Windows
installer, a Windows portable zip and a macOS app bundle, all built by
[`.github/workflows/build.yml`](.github/workflows/build.yml) and attached automatically when a
version tag is pushed.

To build them yourself:

```powershell
pip install -e ".[build]"
python tools\buildExe.py
python tools\buildInstaller.py
```

| Step | Produces | Notes |
|------|----------|-------|
| `tools/buildExe.py` on Windows | `dist\StructuralVibrationView\` | One-folder PyInstaller bundle |
| `tools/buildExe.py` on macOS | `dist/StructuralVibrationView.app` | Application bundle, from the same spec |
| `tools\buildInstaller.py` | `dist\structuralVibrationViewSetup-<version>.exe` | Inno Setup 6. Per-user install, no administrator rights. Needs `winget install JRSoftware.InnoSetup`. Windows only |

The Windows build is one folder rather than one file so it starts immediately, and because an
installer wants a folder anyway.

VTK is the awkward part of packaging this app: its Python modules are loaded by name rather than
imported in the source, so PyInstaller's analysis cannot see them, and a bundle that dropped them
builds happily and then shows an empty panel where the structure should be. The spec collects
them, `tools/buildExe.py` checks the renderer actually shipped, and `--selftest report.txt` asks
a built copy whether it kept its icons and its manual and can build the real 3D view - which is
the only way a windowed build can answer, since it has no console. The build script refuses to
call a bundle shippable until it does.

### A note for macOS users

The app bundle is **not code-signed or notarised**, so Gatekeeper will refuse it on first open
with a message about an unidentified developer. Right-click the app and choose **Open**, which
offers a button the plain double-click does not, or clear the quarantine flag:

```bash
xattr -dr com.apple.quarantine StructuralVibrationView.app
```

Signing needs a paid Apple Developer account, which this project does not have.

To publish a release, tag a commit whose `appConfig.appVersion` matches. The workflow refuses a
tag that disagrees, because a release named after a version the app does not report leaves a bug
report unanswerable.

```powershell
git tag -a v1.0.0 -m "What changed in this release" ; git push origin v1.0.0
```

The tag's message becomes the release notes. `git tag` deletes lines starting with `#` by
default, so if the notes use Markdown headings, write them to a file and tag with
`--cleanup=whitespace` instead:

```powershell
git tag -a v1.0.1 --cleanup=whitespace -F notes.md ; git push origin v1.0.1
```

## Starting up

Starting takes about 2.0 s, nearly all of it importing PyVista and VTK (1.1 s) and building the
first 3D scene (0.7 s); Qt itself is ready after 0.2 s. A splash screen covers the wait
([`ui/splashScreen.py`](src/structuralVibrationView/ui/splashScreen.py)) and is on screen at
0.28 s, which works only because `main.py` imports the main window *after* putting the splash up.

It is a frameless window of our own rather than Qt's `QSplashScreen`: measured here,
`QSplashScreen` takes about 1.0 s to appear whatever pixmap it holds, and added that second to
startup. The replacement takes 0.02 s, and total startup is the same with the splash as without.

Set `STRUCTURAL_VIBRATION_VIEW_NO_SPLASH=1` to start straight into the window.

## Structure

| Layer | Folder | Purpose |
|-------|--------|---------|
| Entry | `src/structuralVibrationView/main.py` | Start `QApplication`, show main window |
| Config | `src/structuralVibrationView/appConfig.py` | Paths, defaults, app metadata |
| UI | `src/structuralVibrationView/ui/` | Widgets and dialogs only |
| Services | `src/structuralVibrationView/services/` | Business logic (no Qt widgets) |
| Models | `src/structuralVibrationView/models/` | Plain Python data types |

The vibration feature, by file:

| File | Role |
|------|------|
| `models/vibrationModel.py` | The kinds, the parameters, the geometry parts, the modal terms |
| `models/sessionState.py` | What a saved session holds |
| `services/systems/vibrationSystem.py` | What every system must answer |
| `services/systems/beamSystem.py` | Euler-Bernoulli beams, three boundary conditions |
| `services/systems/plateSystem.py` | Kirchhoff plates, simply supported and clamped |
| `services/systems/springMassSystem.py` | The oscillator: a coil, a block, one mode |
| `services/vibrationService.py` | The limits, the defaults, and a model from a setup |
| `services/sessionFileService.py` | Read and write `.tvv` session files |
| `services/structureParametersService.py` | Remember the tab between sessions |
| `services/materialPresets.py` | Ten materials, and naming the one the values match |
| `ui/widgets/vibrationView.py` | The PyVista interactor, the clock, the camera |
| `ui/widgets/vibrationControls.py` | The panel: type, tabs, playback |
| `ui/widgets/structureParametersTab.py` | Mode, dimensions and material |
| `ui/splashScreen.py` | The startup splash |
| `selftest.py` | What a built copy reports when asked whether it is intact |
| `tools/makeIcons.py` | Draw the application icon (not imported by the app) |
| `tools/buildExe.py` | PyInstaller build, payload inventory, self-test |
| `tools/buildInstaller.py` | Compile the Windows installer from the bundle |
| `tools/recordTraffic.py` | Snapshot the GitHub traffic numbers, which GitHub keeps 14 days |

See `AGENTS.md` for architecture and naming conventions (for you and AI agents).

## License

MIT, see [`LICENSE`](LICENSE). © 2026 Charette AI Group, LLC.

---
*Created from the Qt App Template.*
