"""Tests for choosing between the published manual and the local copy."""

from __future__ import annotations

import urllib.error

import pytest

from structuralVibrationView import appConfig
from structuralVibrationView.services.manualService import ManualService

publishedUrl = "https://example.invalid/manual"


class FakeReply:
    def __init__(self, status: int | None = 200) -> None:
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args) -> bool:
        return False


def openerReturning(status: int | None, seen: list | None = None):
    def opener(request, timeout=None):
        if seen is not None:
            seen.append((request.full_url, request.get_method(), timeout))
        return FakeReply(status)

    return opener


def testAPublishedManualThatAnswersIsUsed() -> None:
    assert ManualService(openerReturning(200)).isOnlineCopyAvailable(publishedUrl)


def testTheCheckAsksForHeadersOnly() -> None:
    """Choosing between two copies does not need the page downloaded."""
    seen: list = []

    ManualService(openerReturning(200, seen)).isOnlineCopyAvailable(publishedUrl)

    url, method, timeout = seen[0]
    assert url == publishedUrl
    assert method == "HEAD"
    assert timeout == appConfig.manualTimeoutSeconds


def testAnEmptyUrlNeverTouchesTheNetwork() -> None:
    """How every new app starts: nothing published, so nothing to ask.

    Deriving a URL from repoUrl instead would hand most apps an address that
    404s, and a wait on every click to find that out.
    """
    seen: list = []

    service = ManualService(openerReturning(200, seen))

    assert not service.isOnlineCopyAvailable("")
    assert seen == [], "no request should be made when nothing is published"


def testTheConfiguredUrlIsUsedWhenNoneIsGiven(monkeypatch) -> None:
    monkeypatch.setattr(appConfig, "manualUrl", publishedUrl)
    seen: list = []

    ManualService(openerReturning(200, seen)).isOnlineCopyAvailable()

    assert seen[0][0] == publishedUrl


def testAnEmptyConfiguredUrlIsAlsoLocalOnly(monkeypatch) -> None:
    """The template ships with manualUrl empty, so this is the default path."""
    monkeypatch.setattr(appConfig, "manualUrl", "")
    seen: list = []

    assert not ManualService(openerReturning(200, seen)).isOnlineCopyAvailable()
    assert seen == []


@pytest.mark.parametrize("status", [404, 500])
def testAnErrorStatusMeansUseTheLocalCopy(status: int) -> None:
    assert not ManualService(openerReturning(status)).isOnlineCopyAvailable(publishedUrl)


def testAReplyWithNoStatusIsTreatedAsReachable() -> None:
    """Some openers answer without one; that is not a reason to give up."""
    assert ManualService(openerReturning(None)).isOnlineCopyAvailable(publishedUrl)


def testNoNetworkIsAnAnswerRatherThanAnError() -> None:
    """The local copy is always a fine outcome, so nothing here may raise."""

    def opener(request, timeout=None):
        raise urllib.error.URLError("no route to host")

    assert not ManualService(opener).isOnlineCopyAvailable(publishedUrl)


def testAMalformedUrlIsAlsoJustAnAnswer() -> None:
    def opener(request, timeout=None):
        raise ValueError("unknown url type")

    assert not ManualService(opener).isOnlineCopyAvailable("not-a-url")
