"""Tests for the application icon."""

from __future__ import annotations

import struct

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

from structuralVibrationView import appConfig
from structuralVibrationView.main import setAppIdentity

pngSignature = b"\x89PNG\r\n\x1a\n"


def testTheIconShipsWithEveryWindowsSize() -> None:
    data = appConfig.iconFile.read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", data, 0)
    assert (reserved, kind) == (0, 1)  # an icon, not a cursor

    sizes = []
    for index in range(count):
        width, height, _, _, _, _, length, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + 16 * index
        )
        sizes.append(width or 256)  # 0 means 256
        assert width == height
        assert data[offset:offset + 8] == pngSignature
        assert offset + length <= len(data)

    assert sizes == [16, 24, 32, 48, 64, 128, 256]


def testTheLargePngShipsBesideIt() -> None:
    png = appConfig.iconFile.with_suffix(".png")

    assert png.read_bytes()[:8] == pngSignature


def testTheAppWearsTheIcon(qapp) -> None:
    try:
        setAppIdentity(qapp)

        icon = qapp.windowIcon()
        assert not icon.isNull()
        assert {QSize(16, 16), QSize(256, 256)} <= set(icon.availableSizes())
    finally:
        qapp.setWindowIcon(QIcon())


def testAMissingIconIsNotAFailure(qapp, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(appConfig, "iconFile", tmp_path / "missing.ico")
    qapp.setWindowIcon(QIcon())

    setAppIdentity(qapp)

    assert qapp.windowIcon().isNull()
