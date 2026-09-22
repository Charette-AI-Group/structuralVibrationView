"""Draw Transverse Structural Vibration View's application icon.

The same method as 26theOneAssets and 26pySPWB: the icon is drawn with
QPainter *at each size* rather than scaled down from one large rendering,
because a 16 px icon shrunk from 256 px is mush - its strokes fall below a
pixel and the shape stops reading. Each size thickens its strokes and drops
detail as it shrinks.

The artwork: a cantilever clamped to a wall on a violet tile - the app's
accent - bent in its first mode shape and coloured as the app colours
displacement, neutral at the root and red at the tip. A faint blue copy bent
the other way is the other half of the swing, so the icon reads as a
vibration rather than a sag. The curve is the real mode shape, taken from the
app's own vibration service.

    python tools/makeIcons.py

Writes ``src/transverseVibrationView/resources/transverseVibrationView.ico``
(16 to 256 px) and a 1024 px PNG of the same drawing, for a macOS .icns.
The app finds them through ``appConfig``, never by path.
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

# Before any QApplication exists: draw on the real platform, not offscreen.
os.environ.pop("QT_QPA_PLATFORM", None)

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / "src"))
outputDir = repo / "src" / "transverseVibrationView" / "resources"
stem = "transverseVibrationView"

import numpy as np  # noqa: E402
from PySide6.QtCore import QBuffer, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication  # noqa: E402

from transverseVibrationView.models.vibrationModel import StructureKind  # noqa: E402
from transverseVibrationView.services import vibrationService  # noqa: E402

# What a .ico carries: 16 is the title bar and taskbar, 256 the extra-large
# view in Explorer; the sizes between are what Windows picks at other DPIs.
iconSizes = (16, 24, 32, 48, 64, 128, 256)

backgroundTop = QColor("#4A3AA7")  # the app's violet accent
backgroundBottom = QColor("#15103A")
wallColour = QColor("#CBD5E1")
hatchColour = QColor("#64748B")
# The ends of the view's "coolwarm" colour map: no displacement, and the most.
neutralColour = QColor("#DDDCDC")
tipColour = QColor("#E4553F")
# Coolwarm's blue end, lightened so it still reads against the violet.
swingColour = QColor(130, 160, 255, 190)
restColour = QColor(255, 255, 255, 70)
# The beam caught between the two ends of its swing, like a long exposure.
blurColour = QColor(255, 255, 255, 45)

# Where the beam sits, as fractions of the icon.
rootX = 0.24
tipX = 0.86
restY = 0.50


def stroke(size: int, weight: float = 1.0) -> float:
    """A stroke that stays visible when the icon is tiny: never under one pixel."""
    return max(1.0, size * 0.075 * weight)


def roundPen(brush: QBrush | QColor, width: float) -> QPen:
    pen = QPen(brush, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def deflection(size: int) -> float:
    """How far the tip swings, as a fraction of the icon.

    Deeper when small: at 16 px a gentle curve is a straight line, and a
    straight beam on a wall says nothing about vibration.
    """
    return 0.30 if size < 32 else 0.24


def beamPath(size: int, sign: float) -> QPainterPath:
    """The cantilever's first mode shape, bent up (sign 1) or down (sign -1)."""
    xi = np.linspace(0.0, 1.0, 41)
    shape = vibrationService.beamModeShape(StructureKind.cantileverBeam, 1, xi, 1.0)
    shape = shape / shape[-1]  # the tip is +1, whichever way the formula leans
    path = QPainterPath()
    for index, (x, w) in enumerate(zip(xi, shape, strict=True)):
        point = QPointF(
            (rootX + x * (tipX - rootX)) * size,
            (restY - sign * deflection(size) * w) * size,
        )
        if index == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    return path


def drawWall(painter: QPainter, size: int) -> None:
    """The clamp: a block on the left, hatched when there is room for it."""
    wall = QRectF(size * 0.12, size * 0.20, size * (rootX - 0.12), size * 0.60)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(wallColour)
    painter.drawRect(wall)
    if size >= 48:
        painter.save()
        painter.setClipRect(wall)
        painter.setPen(roundPen(hatchColour, max(1.0, size * 0.018)))
        step = size * 0.075
        y = wall.top() - wall.width()
        while y < wall.bottom():
            painter.drawLine(
                QPointF(wall.left(), y + wall.width()), QPointF(wall.right(), y)
            )
            y += step
        painter.restore()


def drawBeam(painter: QPainter, size: int) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)
    width = stroke(size, 1.1)
    if size >= 64:
        # Where the beam rests, faintly: the swing is about this line.
        painter.setPen(roundPen(restColour, max(1.0, size * 0.012)))
        painter.drawLine(QPointF(rootX * size, restY * size), QPointF(tipX * size, restY * size))
        # Positions between the two ends, so the fan reads as motion - as a
        # photograph of a vibrating beam does - rather than two strokes.
        painter.setPen(roundPen(blurColour, width * 0.6))
        for sign in (0.55, -0.55):
            painter.drawPath(beamPath(size, sign))
    if size >= 32:
        # The other half of the swing. Left out when small: a wall with two
        # lines fanning from it reads as the letter K and nothing else.
        painter.setPen(roundPen(swingColour, width * 0.8))
        painter.drawPath(beamPath(size, -1.0))
    colour = QLinearGradient(QPointF(rootX * size, 0), QPointF(tipX * size, 0))
    colour.setColorAt(0.0, neutralColour)
    colour.setColorAt(1.0, tipColour)
    painter.setPen(roundPen(QBrush(colour), width))
    painter.drawPath(beamPath(size, 1.0))


def render(size: int) -> QPixmap:
    """The icon at one size, drawn rather than scaled."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Tighter corners when small, or the rounding eats the artwork.
    radius = size * (0.18 if size < 32 else 0.22)
    background = QLinearGradient(QPointF(0, 0), QPointF(0, size))
    background.setColorAt(0.0, backgroundTop)
    background.setColorAt(1.0, backgroundBottom)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(background)
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    drawBeam(painter, size)
    drawWall(painter, size)  # over the beam's root, so it reads as clamped
    painter.end()
    return pixmap


def pngBytes(pixmap: QPixmap) -> bytes:
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(buffer.data())


def packIco(images: list[tuple[int, bytes]]) -> bytes:
    """A multi-size .ico holding PNG entries.

    Written by hand rather than through Qt's writer, so every size is the one
    drawn at that size. Windows since Vista reads PNG inside an ICO, which
    keeps the 256 px entry small.
    """
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, payload = [], []
    for size, data in images:
        side = 0 if size >= 256 else size  # 0 means 256 in an ICO
        entries.append(struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(data), offset))
        payload.append(data)
        offset += len(data)
    return header + b"".join(entries) + b"".join(payload)


def main() -> int:
    application = QApplication.instance() or QApplication([])  # noqa: F841 - kept alive
    outputDir.mkdir(parents=True, exist_ok=True)
    ico = outputDir / f"{stem}.ico"
    ico.write_bytes(packIco([(size, pngBytes(render(size))) for size in iconSizes]))
    png = outputDir / f"{stem}.png"
    render(1024).save(str(png), "PNG")  # macOS wants a large one for its .icns
    sizes = "/".join(str(size) for size in iconSizes)
    print(f"{ico.relative_to(repo)}  {ico.stat().st_size / 1024:.1f} kB  ({sizes} px)")
    print(f"{png.relative_to(repo)}  1024 px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
