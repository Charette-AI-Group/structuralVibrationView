"""Interface colours, light and dark.

The same values as the other Charette AI Group apps (26simCarla, theOneAssets'
chart theme), so the apps look alike: the open tab is ink on the surface,
underlined in the violet accent.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication


@dataclass(frozen=True)
class ThemeTokens:
    surface: str
    primaryInk: str
    secondaryInk: str
    gridline: str
    # A line between groups in a list or menu: lighter than the platform's
    # own, which is nearly black on a dark popup and cannot be seen.
    divider: str
    accent: str


lightTokens = ThemeTokens(
    surface="#fcfcfb",
    primaryInk="#0b0b0b",
    secondaryInk="#52514e",
    gridline="#e1e0d9",
    divider="#b0afa6",
    accent="#4a3aa7",
)
darkTokens = ThemeTokens(
    surface="#1a1a19",
    primaryInk="#ffffff",
    secondaryInk="#c3c2b7",
    gridline="#2c2c2a",
    divider="#6f6e6a",
    accent="#9085e9",
)


def currentTokens() -> ThemeTokens:
    dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    return darkTokens if dark else lightTokens
