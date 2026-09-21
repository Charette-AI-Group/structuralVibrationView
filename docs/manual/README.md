# Transverse Structural Vibration View — user manual

**Replace this page.** It ships with the template so that **Help > User Manual** opens
something real from the first run instead of failing, and so there is an obvious place for the
manual to go. `appConfig.manualPath` points here.

## Publishing it

Left as it is, the menu item opens this file from the checkout and makes no network request.
Once the manual is pushed somewhere that renders markdown — GitHub renders the screenshots that
a local `.md` opened in a text editor cannot — set `manualUrl` in `appConfig.py`:

```python
manualUrl = f"{repoUrl}/blob/main/docs/manual/README.md"
```

The published copy then becomes the preferred one, with this file as the offline fallback. The
app checks whether the published copy actually answers before sending anyone to it, off the
interface thread, so a machine with no signal gets the local copy rather than a browser error.

## A shape that works

One page per task, in the order somebody meets them, with an index here. Written for the person
using the app, not the person maintaining it.

| # | Page | What it covers |
|---|------|----------------|
| 1 | `getting-started.md` | Installing and first run |
| 2 | `<your-first-task>.md` | The thing the app is actually for |

Screenshots live beside the pages. Keep them current: a screenshot of an older layout is worse
than no screenshot, because it is believed.
