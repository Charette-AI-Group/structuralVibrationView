"""A spin box that shows and accepts numbers in scientific notation.

QDoubleSpinBox only writes fixed-point, so 7.0E+10 would show as
70000000000. This one shows "7.00E+10", accepts "7e10" or "70000000000",
and its arrows step the leading digit (7.0E+10 to 7.1E+10), which keeps a
step meaningful at any magnitude.
"""

from __future__ import annotations

import math

from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QDoubleSpinBox, QWidget

significantDigits = 2  # after the point: 7.00E+10


class ScientificSpinBox(QDoubleSpinBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Whole units are enough precision for the magnitudes this is for, and
        # a fixed-point decimals count would otherwise round the value.
        self.setDecimals(0)

    def textFromValue(self, value: float) -> str:
        return f"{value:.{significantDigits}E}"

    def valueFromText(self, text: str) -> float:
        return float(self.stripped(text))

    def validate(self, text: str, position: int) -> tuple[QValidator.State, str, int]:
        body = self.stripped(text)
        if not body:
            return QValidator.State.Intermediate, text, position
        try:
            value = float(body)
        except ValueError:
            # A number being typed, like "7e" or "7.0E+", is not finished yet.
            partial = body.rstrip("+-").rstrip("eE")
            try:
                float(partial)
            except ValueError:
                return QValidator.State.Invalid, text, position
            return QValidator.State.Intermediate, text, position
        if self.minimum() <= value <= self.maximum():
            return QValidator.State.Acceptable, text, position
        return QValidator.State.Intermediate, text, position

    def stepBy(self, steps: int) -> None:
        """Step the second significant figure, so the step scales with the value."""
        value = self.value()
        magnitude = 10 ** math.floor(math.log10(value)) if value > 0 else 1.0
        self.setValue(value + steps * magnitude / 10)

    def stripped(self, text: str) -> str:
        body = text.strip()
        if self.suffix() and body.endswith(self.suffix().strip()):
            body = body[: -len(self.suffix().strip())]
        return body.strip()
