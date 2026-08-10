"""Tests for the main viewer widget."""

from __future__ import annotations

import numpy as np
from pytest_mock import MockerFixture
from qtpy.QtWidgets import QWidget


def test_widget_creation(mocker: MockerFixture, qapp) -> None:
    """Test creating an NTNDViewerWidget instance."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    # Mock the provider
    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)
    assert widget is not None
    assert isinstance(widget, QWidget)


def test_widget_initial_state(mocker: MockerFixture, qapp) -> None:
    """Test initial state of the widget."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    # Check initial values
    assert widget._max_fps == 30
    assert widget._show_roi_labels is False
    assert len(widget._roi_suffixes) >= 1
    assert widget._current_image is None


def test_normalize_roi_suffixes(mocker: MockerFixture, qapp) -> None:
    """Test ROI suffix normalization."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    # Test normalization
    suffixes = widget._normalize_roi_suffixes(["ROI1", "ROI2:", "", "ROI3"])
    assert "ROI1:" in suffixes
    assert "ROI2:" in suffixes
    assert "ROI3:" in suffixes
    assert "" not in suffixes
    assert len(suffixes) == 3


def test_widget_set_max_framerate(mocker: MockerFixture, qapp) -> None:
    """Test setting max framerate."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)
    initial_fps = widget._max_fps

    # Set new framerate
    widget._set_max_framerate(60)
    assert widget._max_fps != initial_fps
    assert widget._max_fps == 60

    # Test boundary conditions
    widget._set_max_framerate(1)
    assert widget._max_fps == 1

    widget._set_max_framerate(240)
    assert widget._max_fps == 240


def test_widget_roi_field_channel(mocker: MockerFixture, qapp) -> None:
    """Test ROI field channel naming."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)
    widget._prefix = "DEV:XSPD1:Pva1:"

    # Test channel naming
    channel = widget._roi_field_channel("ROI1:", "MinX")
    assert channel == "DEV:XSPD1:Pva1:ROI1:MinX"

    channel = widget._roi_field_channel("ROI2:", "SizeY")
    assert channel == "DEV:XSPD1:Pva1:ROI2:SizeY"


def test_widget_build_image_channel(mocker: MockerFixture, qapp) -> None:
    """Test image channel naming."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)
    widget._prefix = "DEV:XSPD1:Pva1:"
    widget._pva_suffix = "Image"

    channel = widget._build_image_channel()
    assert channel == "DEV:XSPD1:Pva1:Image"


def test_widget_dtype_min_max(mocker: MockerFixture, qapp) -> None:
    """Test dtype min/max calculation."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    # Test uint8
    min_val, max_val = widget._dtype_min_max(np.dtype(np.uint8))
    assert min_val == 0
    assert max_val == 255

    # Test float32
    min_val, max_val = widget._dtype_min_max(np.dtype(np.float32))
    assert np.isfinite(min_val)
    assert np.isfinite(max_val)


def test_widget_build_jet_lut(mocker: MockerFixture, qapp) -> None:
    """Test JET colormap LUT generation."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    lut = widget._build_jet_lut(256)
    assert isinstance(lut, np.ndarray)
    assert lut.shape == (256, 3)
    assert lut.dtype == np.uint8
    assert lut.min() >= 0
    assert lut.max() <= 255


def test_widget_on_show_roi_labels_toggled(mocker: MockerFixture, qapp) -> None:
    """Test ROI labels toggle."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    # Initially false
    assert widget._show_roi_labels is False

    # Toggle on
    widget._on_show_roi_labels_toggled(True)
    assert widget._show_roi_labels is True

    # Toggle off
    widget._on_show_roi_labels_toggled(False)
    assert widget._show_roi_labels is False


def test_widget_set_active_roi(mocker: MockerFixture, qapp) -> None:
    """Test setting active ROI."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    widget._set_active_roi(0)
    assert widget._active_roi_idx == 0

    widget._set_active_roi(1)
    assert widget._active_roi_idx == 1


def test_widget_source_to_display_roi(mocker: MockerFixture, qapp) -> None:
    """Test source to display ROI coordinate transformation."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    # Source coordinates: 100x100 image at (10, 20) with size 50x60
    x0, y0, sx, sy = widget._source_to_display_roi(10, 20, 50, 60, 480, 640)

    # Should return same coordinates when no transform applied
    assert x0 >= 0
    assert y0 >= 0
    assert sx > 0
    assert sy > 0


def test_widget_display_to_source_roi(mocker: MockerFixture, qapp) -> None:
    """Test display to source ROI coordinate transformation."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    # Display coordinates: 100x100 display at (10, 20) with size 50x60
    x0, y0, sx, sy = widget._display_to_source_roi(10, 20, 50, 60, 480, 640)

    # Should return same coordinates when no transform applied
    assert x0 >= 0
    assert y0 >= 0
    assert sx > 0
    assert sy > 0


def test_widget_on_colormap_changed(mocker: MockerFixture, qapp) -> None:
    """Test colormap change handler."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)
    widget._current_image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

    # Change to Grayscale
    widget._on_colormap_changed("Grayscale")
    assert widget._current_colormap == "Grayscale"

    # Change to JET
    widget._on_colormap_changed("JET")
    assert widget._current_colormap == "JET"


def test_widget_on_profile_lines_toggled(mocker: MockerFixture, qapp) -> None:
    """Test profile lines toggle."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    # Initially False
    assert widget._show_profile_lines is False

    # Toggle on
    widget._on_profile_lines_toggled(True)
    assert widget._show_profile_lines is True

    # Toggle off
    widget._on_profile_lines_toggled(False)
    assert widget._show_profile_lines is False


def test_widget_set_roi_mode(mocker: MockerFixture, qapp) -> None:
    """Test setting ROI mode."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    # Test enabling ROI mode
    widget._set_roi_mode_enabled(True)
    assert widget._roi_set_mode_active is True

    # Test disabling ROI mode
    widget._set_roi_mode_enabled(False)
    assert widget._roi_set_mode_active is False


def test_widget_update_dtype_defaults(mocker: MockerFixture, qapp) -> None:
    """Test updating dtype defaults."""
    from ntnda_qt_viewer._widget import NTNDViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDViewerWidget(qapp)

    # Set uint8 dtype
    widget._update_dtype_defaults(np.dtype(np.uint8))
    assert widget._manual_min == 0
    assert widget._manual_max == 255

    # Set float32 dtype
    widget._update_dtype_defaults(np.dtype(np.float32))
    assert widget._manual_min < 0
    assert widget._manual_max > 0
