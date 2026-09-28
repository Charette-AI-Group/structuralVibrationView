"""Tests for what a built copy reports when asked whether it is intact."""

from __future__ import annotations

from structuralVibrationView import appConfig, selftest


def testTheCheckoutReportsItselfIntact(qapp) -> None:
    """The same question a bundle is asked, answered from the source tree."""
    text, passed = selftest.report()

    assert passed, text
    assert "result=ok" in text
    assert f"app={appConfig.appName} {appConfig.appVersion}" in text.splitlines()[0]


def testItNamesEveryBundledFileItLookedFor() -> None:
    names = [name for name, _found, _detail in selftest.resourceChecks()]

    assert names == ["applicationIcon", "largeIcon", "manual"]
    assert all(found for _name, found, _detail in selftest.resourceChecks())


def testAMissingFileMakesTheBuildUnshippable(qapp, monkeypatch, tmp_path) -> None:
    """The whole point: packaging loses files quietly, so this must not."""
    monkeypatch.setattr(appConfig, "manualPath", tmp_path / "gone.md")

    text, passed = selftest.report()

    assert not passed
    assert "manual=MISSING" in text
    assert "result=FAILED" in text


def testAWindowThatCannotBeBuiltIsReportedNotRaised(qapp, monkeypatch) -> None:
    """A bundle missing VTK must say so, not disappear without a word."""
    def explode() -> None:
        raise RuntimeError("no OpenGL here")

    monkeypatch.setattr(selftest, "windowCheck", lambda: (False, "RuntimeError: no OpenGL here"))

    text, passed = selftest.report()

    assert not passed
    assert "window=FAILED  RuntimeError: no OpenGL here" in text


def testTheReportIsWrittenWhereTheBuildAsksForIt(qapp, tmp_path) -> None:
    reportFile = tmp_path / "report.txt"

    code = selftest.runSelfTest(str(reportFile))

    assert code == 0
    assert "result=ok" in reportFile.read_text(encoding="utf-8")
