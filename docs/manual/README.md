# Transverse Structural Vibration View — user manual

The app animates the free transverse vibration of a beam or plate in a 3D view that you can
rotate, pan and zoom while it moves. Mode shapes and frequency ratios come from closed-form
Euler-Bernoulli beam and Kirchhoff plate theory, so what you see is the textbook motion.

## The window

![Main window: a cantilever beam in mode 1, dark theme](mainWindow.png)

- **Left: the 3D view.** Drag with the left mouse button to rotate, right button or wheel to
  zoom, middle button (or Shift + left) to pan. The structure keeps vibrating while you do.
  The colour is the transverse displacement, blue down and red up, on a fixed scale so the
  colours mean the same thing from one frame to the next. The grey wireframe is the undeformed
  structure.
- **Right: the controls.** Every change takes effect immediately; nothing needs applying.
- **Bottom: the status bar.** It names the structure and the frequency of each active mode.

The window opens where you last closed it, at the same size, and maximised if it was.

## Structure

| Control | Meaning |
|---------|---------|
| Type | Cantilever beam, simply supported beam, clamped-clamped beam, or simply supported plate |

## Modal Superposition tab

Below the Structure group are two tabs. The open one is underlined in the accent colour.

The top of the **Modal Superposition** tab sets what every mode shares:

| Control | Meaning |
|---------|---------|
| Fundamental | Frequency of mode 1 in hertz. Higher modes are scaled from it using theory, so mode 2 of a cantilever runs at about 6.3 times this value |
| Damping Ratio | 0 keeps the motion going forever. Anything above 0 makes it decay; press **Restart** to kick it again |

Below that, up to three modes are superposed. For each row:

| Column | Meaning |
|--------|---------|
| Mode | Mode number, 1 to 6. For the plate, mode *k* is the *k*-th lowest, and the status bar shows its (m, n) half-wave numbers |
| Amplitude | Peak displacement as a fraction of the length. 0.05 on the 1 m beam is a 50 mm tip deflection. **0 switches the row off** |
| Phase | Starting phase in degrees, for watching how two modes interfere |

## Structure Parameters tab

The structure's dimensions and material, in SI units. The values you leave here when you close
the app become the defaults the next time it opens. The same values apply whichever **Type** you
choose, so switching type keeps them.

| Control | Default | Meaning |
|---------|---------|---------|
| Length | 0.300 m | Along the span, x, from 1 cm to 10 m. Mode amplitudes are fractions of it, so a longer structure moves further |
| Width | 0.0100 m | Across the span, y, from 1 mm to 5 m. On the plate it also decides which modes come first: a square plate has modes 2 and 3 at the same frequency |
| Thickness | 0.0030 m | In the direction of vibration, z, from 0.1 mm to 0.5 m |
| Density | 2700 kg/m³ | Mass per unit volume, aluminium by default |
| Young's Modulus | 7.00E+10 N/m² | The material stiffness, aluminium by default. Type it as `7e10`, `7.0E+10` or in full; the arrows step the second digit, 7.00E+10 to 7.10E+10 |

The 3D view follows a change of dimension straight away and keeps the camera where you left it;
press **Reset View** to fit the new size. Density and Young's modulus are stored with the
structure, but the animation frequencies still come from **Fundamental** on the Modal
Superposition tab.

## Playback

| Control | Meaning |
|---------|---------|
| Speed | Multiplies the clock. Set it below 1 to watch a fast mode, or above 1 to see damping run out |
| Time | The animation clock, in seconds of structural time |
| Pause / Play | Freezes the structure at the current instant. You can still rotate it |
| Restart | Puts the clock back to zero, which is when every mode is at its peak |
| Reset View | Returns the camera to the three-quarter starting view and fits the structure |
| X-Z View | Looks square-on at the side of the structure, the best view of the deflected shape along its length |
| X-Y View | Looks straight down on the top face. On the plate, this shows the nodal lines as the white bands in the colour |
| Y-Z View | Looks along the length at the cross-section, so you see the ends move up and down |

## Theme

**Help > Theme** follows the Windows light or dark setting by default. The 3D view's background
and the colour bar text follow whichever theme is active.
