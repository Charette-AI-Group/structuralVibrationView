"""Tests for the view base that reports status and failures."""

from __future__ import annotations

from structuralVibrationView.ui.mainWindow import MainWindow
from structuralVibrationView.ui.widgets.reportingView import ReportingView

longFailure = (
    "The device did not answer. The usual cause is another application holding "
    "it open, so close anything else using it and try again."
)


def testStatusGoesOutAsGiven(qtbot) -> None:
    view = ReportingView()
    qtbot.addWidget(view)
    messages: list[str] = []
    view.statusMessage.connect(messages.append)

    view.reportStatus("Connecting...")

    assert messages == ["Connecting..."]


def testAFailureGoesToBothPlacesAtOnce(qtbot) -> None:
    """One call, so no caller has to remember to do both."""
    view = ReportingView()
    qtbot.addWidget(view)
    messages: list[str] = []
    errors: list[tuple[str, str]] = []
    view.statusMessage.connect(messages.append)
    view.errorMessage.connect(lambda title, message: errors.append((title, message)))

    view.reportError("Device", longFailure)

    # The bar gets a headline it can hold; the dialog gets all of it.
    assert messages == ["The device did not answer."]
    assert errors == [("Device", longFailure)]


def testAConnectedViewReachesTheWindow(qtbot, monkeypatch) -> None:
    """The wiring a created app is expected to use for every view it adds."""
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    view = ReportingView()
    qtbot.addWidget(view)
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        MainWindow,
        "showError",
        lambda self, title, message: shown.append((title, message)),
    )

    mainWindow.connectView(view)
    view.reportStatus("Working...")
    assert mainWindow.statusBar().currentMessage() == "Working..."

    view.reportError("Device", longFailure)

    assert shown == [("Device", longFailure)]
    # The bar is left with something true rather than half a sentence.
    assert mainWindow.statusBar().currentMessage() == "The device did not answer."
