"""Tests for the spin box that works in scientific notation."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QValidator

from structuralVibrationView.ui.widgets.scientificSpinBox import ScientificSpinBox


@pytest.fixture
def spin(qtbot) -> ScientificSpinBox:
    box = ScientificSpinBox()
    qtbot.addWidget(box)
    box.setRange(1.0e5, 1.2e12)
    box.setSuffix(" N/m²")
    box.setValue(7.0e10)
    return box


def testLargeValuesShowInScientificNotation(spin) -> None:
    assert spin.text() == "7.00E+10 N/m²"
    assert spin.value() == 7.0e10


@pytest.mark.parametrize("typed", ["7e10", "7.0E+10", "70000000000", "7E10 N/m²"])
def testTheUsualWaysOfWritingItAreAccepted(spin, typed) -> None:
    state, _, _ = spin.validate(typed, len(typed))

    assert state == QValidator.State.Acceptable
    assert spin.valueFromText(typed) == 7.0e10


@pytest.mark.parametrize("typed", ["7e", "7.0E+", ""])
def testANumberBeingTypedIsNotRejected(spin, typed) -> None:
    state, _, _ = spin.validate(typed, len(typed))

    assert state == QValidator.State.Intermediate


def testLettersAreRejected(spin) -> None:
    state, _, _ = spin.validate("abc", 3)

    assert state == QValidator.State.Invalid


def testTheArrowsStepTheSecondSignificantFigure(spin) -> None:
    spin.stepBy(1)
    assert spin.value() == pytest.approx(7.1e10)

    spin.setValue(2.0e5)
    spin.stepBy(-1)
    assert spin.value() == pytest.approx(1.9e5)
