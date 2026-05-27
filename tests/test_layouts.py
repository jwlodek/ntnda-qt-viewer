"""Tests for custom layouts."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from qtpy.QtWidgets import QWidget, QLabel, QPushButton
from qtpy.QtCore import QRect, QSize


def test_flow_layout_creation() -> None:
    """Test creating a _FlowLayout."""
    from ntnda_qt_viewer._widget import _FlowLayout
    
    layout = _FlowLayout()
    assert layout is not None
    assert layout.margin() >= 0
    assert layout.horizontalSpacing() >= 0
    assert layout.verticalSpacing() >= 0


def test_flow_layout_with_custom_spacing() -> None:
    """Test _FlowLayout with custom spacing."""
    from ntnda_qt_viewer._widget import _FlowLayout
    
    layout = _FlowLayout(margin=5, hspacing=10, vspacing=8)
    assert layout.margin() == 5
    assert layout.horizontalSpacing() == 10
    assert layout.verticalSpacing() == 8


def test_flow_layout_add_widget(mocker: MockerFixture) -> None:
    """Test adding widgets to _FlowLayout."""
    from ntnda_qt_viewer._widget import _FlowLayout
    
    layout = _FlowLayout()
    widget1 = mocker.MagicMock()
    widget2 = mocker.MagicMock()
    
    layout.addWidget(widget1)
    layout.addWidget(widget2)
    
    # Layout should track added widgets
    assert layout.count() >= 2


def test_flow_layout_wrapping(mocker: MockerFixture) -> None:
    """Test that _FlowLayout wraps items properly."""
    from ntnda_qt_viewer._widget import _FlowLayout
    
    layout = _FlowLayout(hspacing=10, vspacing=10)
    
    # Create mock widgets with size hints
    widgets = []
    for i in range(5):
        widget = mocker.MagicMock()
        widget.sizeHint = mocker.MagicMock(return_value=QSize(100, 50))
        widget.setGeometry = mocker.MagicMock()
        widgets.append(widget)
        layout.addWidget(widget)
    
    # Simulate layout with limited width
    layout.setGeometry(QRect(0, 0, 250, 500))
    
    # Widgets should be laid out (wrapping should occur)
    for widget in widgets:
        assert widget.setGeometry.called


def test_flow_layout_size_hint(mocker: MockerFixture) -> None:
    """Test _FlowLayout size hint calculation."""
    from ntnda_qt_viewer._widget import _FlowLayout
    
    layout = _FlowLayout()
    widget1 = mocker.MagicMock()
    widget1.sizeHint = mocker.MagicMock(return_value=QSize(100, 50))
    widget1.minimumSize = mocker.MagicMock(return_value=QSize(50, 25))
    widget1.maximumSize = mocker.MagicMock(return_value=QSize(200, 100))
    
    layout.addWidget(widget1)
    
    hint = layout.sizeHint()
    assert hint.width() > 0
    assert hint.height() > 0


def test_flow_layout_minimum_size(mocker: MockerFixture) -> None:
    """Test _FlowLayout minimum size calculation."""
    from ntnda_qt_viewer._widget import _FlowLayout
    
    layout = _FlowLayout()
    widget1 = mocker.MagicMock()
    widget1.minimumSize = mocker.MagicMock(return_value=QSize(50, 25))
    widget1.sizeHint = mocker.MagicMock(return_value=QSize(100, 50))
    
    layout.addWidget(widget1)
    
    min_size = layout.minimumSize()
    assert min_size.width() > 0
    assert min_size.height() > 0
