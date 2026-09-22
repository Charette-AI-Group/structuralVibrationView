"""Tests for the full-width tab widget."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from transverseVibrationView.ui.widgets.fullWidthTabWidget import FullWidthTabWidget


def tabsFillHalves(tabWidget: FullWidthTabWidget) -> bool:
    tabBar = tabWidget.tabBar()
    share = tabWidget.width() // tabBar.count()
    return all(
        abs(tabBar.tabRect(i).width() - share) <= 1 for i in range(tabBar.count())
    )


def testTabsShareWidthEqually(qtbot) -> None:
    tabWidget = FullWidthTabWidget()
    qtbot.addWidget(tabWidget)
    tabWidget.addTab(QWidget(), "First")
    tabWidget.addTab(QWidget(), "Second")
    tabWidget.resize(600, 400)
    tabWidget.show()

    qtbot.waitUntil(lambda: tabsFillHalves(tabWidget), timeout=5000)


def testTabsKeepEqualShareAfterResize(qtbot) -> None:
    tabWidget = FullWidthTabWidget()
    qtbot.addWidget(tabWidget)
    tabWidget.addTab(QWidget(), "First")
    tabWidget.addTab(QWidget(), "Second")
    tabWidget.resize(600, 400)
    tabWidget.show()
    qtbot.waitUntil(lambda: tabsFillHalves(tabWidget), timeout=5000)

    tabWidget.resize(840, 400)

    qtbot.waitUntil(lambda: tabsFillHalves(tabWidget), timeout=5000)


def testThreeTabsShareThirds(qtbot) -> None:
    tabWidget = FullWidthTabWidget()
    qtbot.addWidget(tabWidget)
    for title in ("One", "Two", "Three"):
        tabWidget.addTab(QWidget(), title)
    tabWidget.resize(600, 400)
    tabWidget.show()

    qtbot.waitUntil(lambda: tabsFillHalves(tabWidget), timeout=5000)


def testTheOpenTabHighlightFollowsTheTheme(qtbot, observableColorScheme) -> None:
    """Built in light, switched to dark: the accent must switch with it."""
    import pytest

    from transverseVibrationView.services import themeService
    from transverseVibrationView.ui.theme import darkTokens, lightTokens

    if not observableColorScheme:
        pytest.skip("this platform does not report a forced colour scheme")
    themeService.applyTheme(themeService.lightTheme)
    tabWidget = FullWidthTabWidget()
    qtbot.addWidget(tabWidget)
    assert lightTokens.accent in tabWidget.tabBar().styleSheet()

    themeService.applyTheme(themeService.darkTheme)

    qtbot.waitUntil(lambda: darkTokens.accent in tabWidget.tabBar().styleSheet(), timeout=5000)


def testTabPagesTakeTheNewThemeToo(qtbot, observableColorScheme) -> None:
    """A styled tab bar stops Qt passing the palette down; the widget must do it."""
    import pytest
    from PySide6.QtWidgets import QApplication, QSpinBox

    from transverseVibrationView.services import themeService

    if not observableColorScheme:
        pytest.skip("this platform does not report a forced colour scheme")
    themeService.applyTheme(themeService.darkTheme)
    tabWidget = FullWidthTabWidget()
    qtbot.addWidget(tabWidget)
    spin = QSpinBox()
    tabWidget.addTab(spin, "First")
    tabWidget.show()

    themeService.applyTheme(themeService.lightTheme)

    qtbot.waitUntil(
        lambda: spin.palette().base().color() == QApplication.palette().base().color(),
        timeout=5000,
    )


def testADeletedTabWidgetIgnoresLaterThemeChanges(qtbot) -> None:
    """The colour-scheme signal outlives the widget; it must not reach a dead one."""
    from PySide6.QtWidgets import QApplication

    from transverseVibrationView.services import themeService

    tabWidget = FullWidthTabWidget()
    tabWidget.deleteLater()
    QApplication.sendPostedEvents(None, 0)
    qtbot.wait(10)

    themeService.applyTheme(themeService.darkTheme)
    themeService.applyTheme(themeService.lightTheme)
    qtbot.wait(50)
