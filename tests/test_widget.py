"""Tests for the main viewer widget."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockerFixture
from qtpy.QtCore import QCoreApplication
from qtpy.QtWidgets import QWidget


def test_widget_creation(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test creating an NTNDAViewerWidget instance."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    # Mock the provider
    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")
    assert widget is not None
    assert isinstance(widget, QWidget)


def test_widget_initial_state(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test initial state of the widget."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    # Check initial values
    assert widget._max_fps == 30
    assert widget._show_roi_labels is False
    assert len(widget._roi_suffixes) >= 1
    assert widget._current_image is None


def test_normalize_roi_suffixes(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test ROI suffix normalization."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    # Test normalization
    suffixes = widget._normalize_roi_suffixes(["ROI1", "ROI2:", "", "ROI3"])
    assert "ROI1:" in suffixes
    assert "ROI2:" in suffixes
    assert "ROI3:" in suffixes
    assert "" not in suffixes
    assert len(suffixes) == 3


def test_widget_set_max_framerate(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test setting max framerate."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")
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


def test_widget_roi_field_channel(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test ROI field channel naming."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")
    widget._prefix = "DEV:XSPD1:Pva1:"

    # Test channel naming
    channel = widget._roi_field_channel("ROI1:", "MinX")
    assert channel == "DEV:XSPD1:Pva1:ROI1:MinX"

    channel = widget._roi_field_channel("ROI2:", "SizeY")
    assert channel == "DEV:XSPD1:Pva1:ROI2:SizeY"


def test_widget_build_image_channel(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test image channel naming."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")
    widget._prefix = "DEV:XSPD1:Pva1:"
    widget._pva_suffix = "Image"

    channel = widget._build_image_channel()
    assert channel == "DEV:XSPD1:Pva1:Image"


def test_widget_raw_array_uses_prefix_as_pv(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    provider_cls = mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget(
        "DEV:Array:", raw_waveform=True, image_shape=(480, 640), color=True
    )

    assert widget._build_image_channel() == "DEV:Array:"
    provider_cls.assert_called_once_with(
        "DEV:Array:",
        raw_waveform=True,
        image_shape=(480, 640),
        color=True,
        use_ca=False,
    )
    assert widget._roi_field_channel("ROI1:", "MinX") == "DEV:Array:ROI1:MinX"


def test_widget_invalid_image_shape_options(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    import pytest

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")

    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:Array:", raw_waveform=True)
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:Array:", raw_waveform=True, image_shape=(0, 640))
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", image_shape=(480, 640))
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", use_ca=True)


def test_widget_num_rois_with_pattern(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:", num_rois=3, roi_suffix_pattern="Roi{:02d}:")
    assert widget._roi_suffixes == ["Roi01:", "Roi02:", "Roi03:"]

    widget = NTNDAViewerWidget("DEV:", num_rois=2)
    assert widget._roi_suffixes == ["ROI1:", "ROI2:"]

    widget = NTNDAViewerWidget("DEV:", num_rois=0)
    assert widget._roi_suffixes == []

    widget = NTNDAViewerWidget("DEV:")
    assert widget._roi_suffixes == ["ROI1:", "ROI2:", "ROI3:", "ROI4:"]


def test_widget_num_rois_invalid(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    import pytest

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")

    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", num_rois=-1)


def test_widget_colormap_defaults_to_grayscale(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")
    assert widget._selected_colormap == "Grayscale"

    widget._current_image = np.zeros((4, 4), dtype=np.uint8)
    widget._on_colormap_changed("JET")
    cast(MagicMock, widget._image_item.setLookupTable).assert_called_with(
        widget._jet_lut
    )


def test_widget_auto_levels_ignore_hot_pixels() -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    image = np.tile(np.arange(100, dtype=np.float32), (100, 1))
    image[0, :5] = 65535.0
    lo, hi = NTNDAViewerWidget._auto_levels(image)
    assert lo >= 0.0
    assert hi < 100.0

    flat = np.full((100, 100), 7.0, dtype=np.float32)
    flat[0, 0] = 9.0
    assert NTNDAViewerWidget._auto_levels(flat) == (7.0, 9.0)


def test_widget_auto_levels_robust_sigma() -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    rng = np.random.default_rng(0)
    image = rng.normal(100.0, 5.0, (200, 200)).astype(np.float32)
    image[::20, ::20] = 65535.0
    lo, hi = NTNDAViewerWidget._auto_levels(image, "sigma", n_sigma=3.0)
    assert 80.0 < lo < 90.0
    assert 110.0 < hi < 120.0

    narrow = NTNDAViewerWidget._auto_levels(image, "sigma", n_sigma=1.0)
    assert lo < narrow[0] < narrow[1] < hi

    lo_pct, hi_pct = NTNDAViewerWidget._auto_levels(image, percentiles=(5.0, 95.0))
    assert 85.0 < lo_pct < hi_pct < 115.0


def test_widget_auto_levels_minmax_uses_full_range() -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    image = np.full((1000, 1000), 10.0, dtype=np.float32)
    image[123, 457] = 500.0
    image[999, 1] = -3.0
    assert NTNDAViewerWidget._auto_levels(image, "minmax") == (-3.0, 500.0)


def test_widget_auto_scale_init_options(mocker: MockerFixture, qapp) -> None:
    import pytest

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget(
        "DEV:",
        auto_scale_method="sigma",
        auto_scale_percentiles=(1, 99),
        auto_scale_n_sigma=5,
    )
    assert widget._auto_method == "sigma"
    assert widget._auto_percentiles == (1.0, 99.0)
    assert widget._auto_n_sigma == 5.0

    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", auto_scale_method="bogus")
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", auto_scale_percentiles=(99.0, 1.0))
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", auto_scale_n_sigma=0)


def test_widget_log_scale_option(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")

    assert NTNDAViewerWidget("DEV:")._log_scale is False
    widget = NTNDAViewerWidget("DEV:", log_scale=True)
    assert widget._log_scale is True
    np.testing.assert_allclose(
        widget._transform_for_scaling(np.array([0.0, np.e - 1])), [0.0, 1.0]
    )


def test_widget_colormap_ignored_for_color_image(
    mocker: MockerFixture, qapp: QCoreApplication, caplog: pytest.LogCaptureFixture
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")
    color_image = np.zeros((4, 4, 3), dtype=np.uint8)

    widget = NTNDAViewerWidget("DEV:")
    widget._current_image = color_image
    with caplog.at_level("WARNING"):
        widget._apply_colormap()
    cast(MagicMock, widget._image_item.setLookupTable).assert_called_with(None)
    assert "Ignoring colormap" not in caplog.text

    widget = NTNDAViewerWidget("DEV:", colormap="JET")
    widget._current_image = color_image
    with caplog.at_level("WARNING"):
        widget._apply_colormap()
        widget._apply_colormap()
    cast(MagicMock, widget._image_item.setLookupTable).assert_called_with(None)
    assert caplog.text.count("Ignoring colormap") == 1


def test_widget_dtype_min_max(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test dtype min/max calculation."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    # Test uint8
    min_val, max_val = widget._dtype_min_max(np.dtype(np.uint8))
    assert min_val == 0
    assert max_val == 255

    # Test float32
    min_val, max_val = widget._dtype_min_max(np.dtype(np.float32))
    assert np.isfinite(min_val)
    assert np.isfinite(max_val)


def test_widget_build_jet_lut(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test JET colormap LUT generation."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    lut = widget._build_jet_lut(256)
    assert isinstance(lut, np.ndarray)
    assert lut.shape == (256, 3)
    assert lut.dtype == np.uint8
    assert lut.min() >= 0
    assert lut.max() <= 255


def test_widget_on_show_roi_labels_toggled(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test ROI labels toggle."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    # Initially false
    assert widget._show_roi_labels is False

    # Toggle on
    widget._on_show_roi_labels_toggled(True)
    assert widget._show_roi_labels is True

    # Toggle off
    widget._on_show_roi_labels_toggled(False)
    assert widget._show_roi_labels is False


def test_widget_set_active_roi(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test setting active ROI."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    widget._set_active_roi(0)
    assert widget._active_roi_idx == 0

    widget._set_active_roi(1)
    assert widget._active_roi_idx == 1


def test_widget_source_to_display_roi(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test source to display ROI coordinate transformation."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    # Source coordinates: 100x100 image at (10, 20) with size 50x60
    x0, y0, sx, sy = widget._source_to_display_roi(10, 20, 50, 60, 480, 640)

    # Should return same coordinates when no transform applied
    assert x0 >= 0
    assert y0 >= 0
    assert sx > 0
    assert sy > 0


def test_widget_display_to_source_roi(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test display to source ROI coordinate transformation."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    # Display coordinates: 100x100 display at (10, 20) with size 50x60
    x0, y0, sx, sy = widget._display_to_source_roi(10, 20, 50, 60, 480, 640)

    # Should return same coordinates when no transform applied
    assert x0 >= 0
    assert y0 >= 0
    assert sx > 0
    assert sy > 0


def test_widget_on_colormap_changed(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test colormap change handler."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")
    widget._current_image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

    # Change to Grayscale
    widget._on_colormap_changed("Grayscale")
    assert widget._current_colormap == "Grayscale"

    # Change to JET
    widget._on_colormap_changed("JET")
    assert widget._current_colormap == "JET"


def test_widget_on_profile_lines_toggled(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test profile lines toggle."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    # Initially False
    assert widget._show_profile_lines is False

    # Toggle on
    widget._on_profile_lines_toggled(True)
    assert widget._show_profile_lines is True

    # Toggle off
    widget._on_profile_lines_toggled(False)
    assert widget._show_profile_lines is False


def test_widget_set_roi_mode(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test setting ROI mode."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    # Test enabling ROI mode
    widget._set_roi_mode_enabled(True)
    assert widget._roi_set_mode_active is True

    # Test disabling ROI mode
    widget._set_roi_mode_enabled(False)
    assert widget._roi_set_mode_active is False


def test_widget_update_dtype_defaults(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test updating dtype defaults."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")

    # Set uint8 dtype
    widget._update_dtype_defaults(np.dtype(np.uint8))
    assert widget._manual_min == 0
    assert widget._manual_max == 255

    # Set float32 dtype
    widget._update_dtype_defaults(np.dtype(np.float32))
    assert widget._manual_min < 0
    assert widget._manual_max > 0


def test_widget_initial_scaling(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")
    assert widget._scale_mode == "auto"
    assert widget._log_scale is False

    widget = NTNDAViewerWidget("DEV:", scale_min=10, scale_max=200, log_scale=True)
    assert widget._scale_mode == "manual"
    assert widget._log_scale is True
    widget._update_dtype_defaults(np.dtype(np.uint16))
    assert widget._manual_levels() == (np.log1p(10.0), np.log1p(200.0))


def test_widget_initial_scaling_invalid(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    import pytest

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch("ntnda_qt_viewer._widget.pg")

    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", scale_min=10)
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", scale_min=10, scale_max=10)


def test_widget_start_stop(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")
    widget.start()
    provider.start.assert_called_once()
    assert provider.channel_name == "DEV:Pva1:Image"
    assert not widget._start_btn.isEnabled()
    assert widget._stop_btn.isEnabled()
    assert widget._display_timer.isActive()

    widget.stop()
    provider.stop.assert_called_once()
    assert widget._start_btn.isEnabled()
    assert not widget._stop_btn.isEnabled()
    assert not widget._display_timer.isActive()


def test_widget_start_requires_prefix(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=provider)
    mocker.patch("ntnda_qt_viewer._widget.pg")

    widget = NTNDAViewerWidget("DEV:")
    widget._prefix_edit.setText("  ")
    widget.start()
    provider.start.assert_not_called()
