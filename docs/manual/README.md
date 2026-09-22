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

Below the Structure group are two tabs. The open one is underlined in the accent colour, and
it also decides what the 3D view animates:

- **Modal Superposition** open: the modes in its table, added together, with its damping.
- **Structure Parameters** open: the single mode chosen at the top of that tab, on its own.

Switching tabs switches the animation straight away; each tab keeps its own settings.

The top of the **Modal Superposition** tab sets what every mode shares:

| Control | Meaning |
|---------|---------|
| Fundamental | The natural frequency of mode 1, computed from the Structure Parameters and the type's boundary conditions. Read-only: change the dimensions or material to change it. The status bar shows the computed frequency of every active mode |
| Damping Ratio | 0 keeps the motion going forever. Anything above 0 makes it decay; press **Restart** to kick it again |

Below that, up to three modes are superposed. For each row:

| Column | Meaning |
|--------|---------|
| Mode | Mode number, 1 to 6. For the plate, mode *k* is the *k*-th lowest, and the status bar shows its (m, n) half-wave numbers |
| Amplitude | Peak displacement as a fraction of the length. 0.05 on the 1 m beam is a 50 mm tip deflection. **0 switches the row off** |
| Phase | Starting phase in degrees, for watching how two modes interfere |

## Structure Parameters tab

The mode to study on its own, and the structure's dimensions and material, in SI units. The mode, dimensions and material you leave here
when you close the app become the defaults the next time it opens. The same values apply whichever **Type** you
choose, so switching type keeps them.

| Control | Default | Meaning |
|---------|---------|---------|
| Mode | Mode 1 | Which of the first five modes to animate while this tab is open, each with its natural frequency in brackets. The frequencies update as you change the type, dimensions or material. The mode plays alone at 5 % of the length, undamped, and the slow motion follows it, so mode 5 is as easy to watch as mode 1 |
| Length | 0.300 m | Along the span, x, from 1 cm to 10 m. Mode amplitudes are fractions of it, so a longer structure moves further |
| Width | 0.0100 m | Across the span, y, from 1 mm to 5 m. On the plate it also decides which modes come first: a square plate has modes 2 and 3 at the same frequency |
| Thickness | 0.0030 m | In the direction of vibration, z, from 0.1 mm to 0.5 m |
| Material | Aluminium | Fills in the three properties below with typical values for Aluminium, Steel, Stainless Steel, Titanium, Copper, Brass, Glass, Concrete, Acrylic or Polycarbonate. Editing any of them by hand shows **Custom**; choosing Custom keeps the values as they are |
| Density | 2700 kg/m³ | Mass per unit volume, aluminium by default |
| Young's Modulus | 7.00E+10 N/m² | The material stiffness, aluminium by default. Type it as `7e10`, `7.0E+10` or in full; the arrows step the second digit, 7.00E+10 to 7.10E+10 |
| Poisson's Ratio | 0.330 | How much the material narrows as it stretches, aluminium by default; steel is about 0.30 and rubber close to 0.5. Accepts -0.99 to 0.499. It changes the plate's frequencies only, since a beam's bending does not depend on it |

The 3D view follows a change of dimension straight away and keeps the camera where you left it;
press **Reset View** to fit the new size.

All five values set the natural frequencies. The beams use Euler-Bernoulli theory, where the
frequency grows with thickness and the square root of stiffness over density, and falls with
the square of the length; the width of a beam does not change its frequencies. The plate uses
Kirchhoff plate theory, where Poisson's ratio stiffens the plate a little and its narrower
side matters most: the
default 1 cm wide strip, held on all four edges, vibrates at tens of kilohertz. Widen it to see
plate-like frequencies.

## Playback

| Control | Meaning |
|---------|---------|
| Speed | Real vibrations are far too fast to see, so the animation runs in slow motion. At 1x, mode 1 takes two seconds per cycle on screen whatever its real frequency. Set it lower to follow a higher mode, or higher to see damping run out |
| Time | Real time in the structure, not time on screen: milliseconds while under a second |
| Pause / Play | Freezes the structure at the current instant. You can still rotate it |
| Restart | Puts the clock back to zero, which is when every mode is at its peak |
| Reset View | Returns the camera to the three-quarter starting view and fits the structure |
| X-Z View | Looks square-on at the side of the structure, the best view of the deflected shape along its length |
| X-Y View | Looks straight down on the top face. On the plate, this shows the nodal lines as the white bands in the colour |
| Y-Z View | Looks along the length at the cross-section, so you see the ends move up and down |

## Theme

**Help > Theme** follows the Windows light or dark setting by default. The 3D view's background
and the colour bar text follow whichever theme is active.
