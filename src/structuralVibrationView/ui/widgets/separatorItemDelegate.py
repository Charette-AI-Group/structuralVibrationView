"""Draws a dropdown's separators in a grey that can be seen.

Qt asks the platform style for a separator, and on Windows 11 in dark mode
that line is nearly black on a nearly black list: the gap reads as spacing
rather than as a divider. This paints it in the theme's own divider grey
instead, and leaves every other row to the style.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from structuralVibrationView.ui.theme import currentTokens

separatorHeight = 9  # the line, with air above and below it
sideMargin = 8


def isSeparator(index: QModelIndex) -> bool:
    """What QComboBox.insertSeparator leaves behind for a style to find."""
    return index.data(Qt.ItemDataRole.AccessibleDescriptionRole) == "separator"


class SeparatorItemDelegate(QStyledItemDelegate):
    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        if not isSeparator(index):
            super().paint(painter, option, index)
            return
        rectangle = option.rect
        y = rectangle.center().y()
        # Read at paint time, so the line follows a theme change with the rest.
        painter.save()
        painter.setPen(QColor(currentTokens().divider))
        painter.drawLine(
            rectangle.left() + sideMargin, y, rectangle.right() - sideMargin, y
        )
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        if isSeparator(index):
            return QSize(super().sizeHint(option, index).width(), separatorHeight)
        return super().sizeHint(option, index)
