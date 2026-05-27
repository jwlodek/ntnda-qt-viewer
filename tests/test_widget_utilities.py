"""Tests for widget utilities and integration."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
import numpy as np
from qtpy.QtCore import Qt, QRect, QPoint, QSize
from qtpy.QtWidgets import QWidget


def test_image_viewbox_creation(mocker: MockerFixture, qapp) -> None:
    """Test creating an _ImageViewBox."""
    from ntnda_qt_viewer._widget import _ImageViewBox
    
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    viewbox = _ImageViewBox()
    assert viewbox is not None


def test_status_indicator_creation(mocker: MockerFixture, qapp) -> None:
    """Test creating a _StatusIndicator."""
    from ntnda_qt_viewer._widget import _StatusIndicator
    
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    indicator = _StatusIndicator()
    assert indicator is not None
    assert isinstance(indicator, QWidget)


def test_status_indicator_set_connected(mocker: MockerFixture, qapp) -> None:
    """Test status indicator connection state."""
    from ntnda_qt_viewer._widget import _StatusIndicator
    
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    indicator = _StatusIndicator()
    
    # Set connected
    indicator.set_connected(True)
    # Visual state should update (depends on implementation)
    
    # Set disconnected
    indicator.set_connected(False)
    # Visual state should update


def test_widget_clear_roi_overlays(mocker: MockerFixture, qapp) -> None:
    """Test clearing ROI overlays."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget, _ROIModel
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    # Add some mock ROI models
    mock_rect = mocker.MagicMock()
    mock_label = mocker.MagicMock()
    model = _ROIModel(suffix="TEST:", rect=mock_rect, label=mock_label, visible=False)
    widget._roi_models.append(model)
    
    # Clear overlays
    widget._clear_roi_overlays()
    
    # Should remove items and clear list
    widget._image_plot.removeItem.assert_called()
    assert len(widget._roi_models) == 0


def test_widget_clear_roi_controls(mocker: MockerFixture, qapp) -> None:
    """Test clearing ROI controls."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    # Add mock controls
    widget._roi_enable_checks.append(mocker.MagicMock())
    widget._roi_set_buttons.append(mocker.MagicMock())
    
    # Clear controls
    widget._clear_roi_controls()
    
    # Should clear lists
    assert len(widget._roi_enable_checks) == 0
    assert len(widget._roi_set_buttons) == 0


def test_widget_ensure_roi_context(mocker: MockerFixture, qapp, mock_context) -> None:
    """Test getting or creating ROI context."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    # Mock the Context creation
    mocker.patch('ntnda_qt_viewer._widget.Context', return_value=mock_context)
    context = widget._ensure_roi_context()
    assert context is not None

    # Calling again should return same context
    context2 = widget._ensure_roi_context()
    assert context2 is context


def test_widget_on_new_frame(mocker: MockerFixture, qapp) -> None:
    """Test handling new frame."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    widget._on_new_frame(image)
    
    assert widget._pending_image is image


def test_widget_manual_levels(mocker: MockerFixture, qapp) -> None:
    """Test getting manual levels for scaling."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    # Initially None when manual scaling disabled
    widget._manual_scaling_enabled = False
    levels = widget._manual_levels()
    assert levels is None
    
    # Return values when enabled
    widget._manual_scaling_enabled = True
    widget._manual_min = 0.0
    widget._manual_max = 100.0
    levels = widget._manual_levels()
    assert levels == (0.0, 100.0)


def test_widget_refresh_display_increments_fps(mocker: MockerFixture, qapp) -> None:
    """Test that refresh display increments FPS counter."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    initial_count = widget._fps_frame_count
    
    # Set a pending image
    widget._pending_image = np.zeros((100, 100), dtype=np.uint8)
    widget._refresh_display()
    
    # FPS counter should increment
    assert widget._fps_frame_count > initial_count


def test_widget_normalize_roi_suffix_normalization(mocker: MockerFixture, qapp) -> None:
    """Test ROI suffix normalization edge cases."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    # Test with whitespace
    suffixes = widget._normalize_roi_suffixes(["  ROI1  ", "ROI2:"])
    assert "ROI1:" in suffixes
    assert "ROI2:" in suffixes
    
    # Test with duplicate colons
    suffixes = widget._normalize_roi_suffixes(["ROI1::", "ROI2::"])
    assert "ROI1::" in suffixes
    assert "ROI2::" in suffixes


def test_widget_pva_suffix_action_gating(mocker: MockerFixture, qapp) -> None:
    """Test that PVA suffix action is gated during connection."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    # Initially should be enabled
    assert widget._pva_suffix_action.isEnabled()
    
    # Mock starting connection
    widget._set_pva_suffix_action_enabled(False)
    assert not widget._pva_suffix_action.isEnabled()
    
    # Re-enable
    widget._set_pva_suffix_action_enabled(True)
    assert widget._pva_suffix_action.isEnabled()


def test_widget_refresh_max_framerate_action_text(mocker: MockerFixture, qapp) -> None:
    """Test updating max framerate action text."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    # Set FPS and refresh text
    widget._max_fps = 60
    widget._refresh_max_framerate_action_text()
    
    # Action text should include FPS value
    assert "60" in widget._max_framerate_action.text()


def test_widget_exit_set_roi_mode(mocker: MockerFixture, qapp) -> None:
    """Test exiting ROI set mode."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    # Enter mode
    widget._set_roi_mode_enabled(True)
    assert widget._roi_set_mode_active is True
    
    # Exit mode
    widget._exit_set_roi_mode()
    assert widget._roi_set_mode_active is False


def test_widget_transform_for_scaling(mocker: MockerFixture, qapp) -> None:
    """Test image transformation for scaling."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget
    
    mock_provider = mocker.MagicMock()
    mocker.patch('ntnda_qt_viewer._widget.NTNDProvider', return_value=mock_provider)
    mocker.patch('ntnda_qt_viewer._widget.pg')
    
    widget = NTNDViewerWidget(qapp)
    
    image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    
    # No scaling applied by default
    transformed = widget._transform_for_scaling(image)
    assert isinstance(transformed, np.ndarray)
    assert transformed.shape == image.shape
