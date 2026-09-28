r"""Tests for splitting a failure between the status bar and a dialog."""

from __future__ import annotations

from structuralVibrationView.ui.dialogs.errorDialog import (
    detailOf,
    headlineOf,
    statusHeadlineLimit,
)

# A real one: this is the shape of message that gets cut mid-word by a bar.
longFailure = (
    "The device did not answer. The usual cause is another application holding "
    "it open, so close anything else using it and try again."
)


def testAShortMessageIsItsOwnHeadline() -> None:
    assert headlineOf("No device found.") == "No device found."


def testTheFirstLineIsTheHeadlineWhenThereAreSeveral() -> None:
    message = "Save failed:\nThe folder is read-only\nPath: C:\\Somewhere"

    assert headlineOf(message) == "Save failed:"


def testALongSingleLineIsCutAtASentenceNotMidWord() -> None:
    """Cut mid-word, a headline reads as the whole message and misleads."""
    headline = headlineOf(longFailure)

    assert headline == "The device did not answer."
    assert len(headline) <= statusHeadlineLimit


def testAHeadlineThatCannotBeCutCleanlyIsMarkedAsTruncated() -> None:
    message = "x" * (statusHeadlineLimit * 2)

    headline = headlineOf(message)

    assert len(headline) <= statusHeadlineLimit
    assert headline.endswith("…")


def testTheDetailIsWhateverTheHeadlineDidNotSay() -> None:
    message = "Save failed:\nThe folder is read-only\nPath: C:\\Somewhere"

    detail = detailOf(message, headlineOf(message))

    assert detail.startswith("The folder is read-only")
    assert "Path:" in detail


def testNothingIsLostWhenTheHeadlineIsCutAtASentence() -> None:
    """Headline plus detail is the message, with no word dropped between them."""
    headline = headlineOf(longFailure)

    assert f"{headline} {detailOf(longFailure, headline)}" == longFailure


def testAnEllipsisedHeadlineLeavesTheWholeMessageInTheDialog() -> None:
    """It said only part of a word, so all of it still needs saying."""
    message = "x" * (statusHeadlineLimit * 2)

    assert detailOf(message, headlineOf(message)) == message


def testAMessageWithNoDetailLeavesTheDialogWithNothingExtra() -> None:
    assert detailOf("No device found.", "No device found.") == ""


def testBlankLinesDoNotBecomeTheHeadline() -> None:
    assert headlineOf("\n\nSave failed\nbecause of a thing") == "Save failed"
