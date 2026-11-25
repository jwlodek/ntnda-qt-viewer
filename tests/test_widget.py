"""Tests for the main viewer widget."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockerFixture
from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtWidgets import QWidget

if TYPE_CHECKING:
    from ntnda_qt_viewer import NTNDAViewerWidget


@pytest.mark.usefixtures("mock_pg")
def test_widget_creation(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test creating an NTNDAViewerWidget instance."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    # Mock the provider
    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")
    assert widget is not None
    assert isinstance(widget, QWidget)


@pytest.mark.usefixtures("mock_pg")
def test_widget_initial_state(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test initial state of the widget."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")

    # Check initial values
    assert widget._max_fps == 30
    assert widget._show_roi_labels is False
    assert len(widget._roi_suffixes) >= 1
    assert widget._current_image is None


@pytest.mark.usefixtures("mock_pg")
def test_normalize_roi_suffixes(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test ROI suffix normalization."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")

    # Test normalization
    suffixes = widget._normalize_roi_suffixes(["ROI1", "ROI2:", "", "ROI3"])
    assert "ROI1:" in suffixes
    assert "ROI2:" in suffixes
    assert "ROI3:" in suffixes
    assert "" not in suffixes
    assert len(suffixes) == 3


@pytest.mark.usefixtures("mock_pg")
def test_widget_set_max_framerate(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test setting max framerate."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

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


@pytest.mark.usefixtures("mock_pg")
def test_widget_roi_field_channel(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test ROI field channel naming."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")
    widget._prefix = "DEV:XSPD1:Pva1:"

    # Test channel naming
    channel = widget._roi_field_channel("ROI1:", "MinX")
    assert channel == "DEV:XSPD1:Pva1:ROI1:MinX"

    channel = widget._roi_field_channel("ROI2:", "SizeY")
    assert channel == "DEV:XSPD1:Pva1:ROI2:SizeY"


@pytest.mark.usefixtures("mock_pg")
def test_widget_build_image_channel(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test image channel naming."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")
    widget._prefix = "DEV:XSPD1:Pva1:"
    widget._pva_suffix = "Image"

    channel = widget._build_image_channel()
    assert channel == "DEV:XSPD1:Pva1:Image"


@pytest.mark.usefixtures("mock_pg")
def test_widget_raw_array_uses_prefix_as_pv(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    provider_cls = mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

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


@pytest.mark.usefixtures("mock_pg")
def test_widget_invalid_image_shape_options(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    import pytest

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:Array:", raw_waveform=True)
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:Array:", raw_waveform=True, image_shape=(0, 640))
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", image_shape=(480, 640))
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", use_ca=True)


@pytest.mark.usefixtures("mock_pg")
def test_widget_num_rois_with_pattern(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

    widget = NTNDAViewerWidget("DEV:", num_rois=3, roi_suffix_pattern="Roi{:02d}:")
    assert widget._roi_suffixes == ["Roi01:", "Roi02:", "Roi03:"]

    widget = NTNDAViewerWidget("DEV:", num_rois=2)
    assert widget._roi_suffixes == ["ROI1:", "ROI2:"]

    widget = NTNDAViewerWidget("DEV:", num_rois=0)
    assert widget._roi_suffixes == []

    widget = NTNDAViewerWidget("DEV:")
    assert widget._roi_suffixes == ["ROI1:", "ROI2:", "ROI3:", "ROI4:"]


@pytest.mark.usefixtures("mock_pg")
def test_widget_num_rois_invalid(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    import pytest

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", num_rois=-1)


@pytest.mark.usefixtures("mock_pg")
def test_widget_colormap_defaults_to_grayscale(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

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


@pytest.mark.usefixtures("mock_pg")
def test_widget_auto_scale_init_options(mocker: MockerFixture, qapp) -> None:
    import pytest

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

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


@pytest.mark.usefixtures("mock_pg")
def test_widget_log_scale_option(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

    assert NTNDAViewerWidget("DEV:")._log_scale is False
    widget = NTNDAViewerWidget("DEV:", log_scale=True)
    assert widget._log_scale is True
    np.testing.assert_allclose(
        widget._transform_for_scaling(np.array([0.0, np.e - 1])), [0.0, 1.0]
    )


@pytest.mark.usefixtures("mock_pg")
def test_widget_colormap_ignored_for_color_image(
    mocker: MockerFixture, qapp: QCoreApplication, caplog: pytest.LogCaptureFixture
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
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


@pytest.mark.usefixtures("mock_pg")
def test_widget_dtype_min_max(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test dtype min/max calculation."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")

    # Test uint8
    min_val, max_val = widget._dtype_min_max(np.dtype(np.uint8))
    assert min_val == 0
    assert max_val == 255

    # Test float32
    min_val, max_val = widget._dtype_min_max(np.dtype(np.float32))
    assert np.isfinite(min_val)
    assert np.isfinite(max_val)


@pytest.mark.usefixtures("mock_pg")
def test_widget_build_jet_lut(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test JET colormap LUT generation."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")

    lut = widget._build_jet_lut(256)
    assert isinstance(lut, np.ndarray)
    assert lut.shape == (256, 3)
    assert lut.dtype == np.uint8
    assert lut.min() >= 0
    assert lut.max() <= 255


@pytest.mark.usefixtures("mock_pg")
def test_widget_on_show_roi_labels_toggled(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test ROI labels toggle."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")

    # Initially false
    assert widget._show_roi_labels is False

    # Toggle on
    widget._on_show_roi_labels_toggled(True)
    assert widget._show_roi_labels is True

    # Toggle off
    widget._on_show_roi_labels_toggled(False)
    assert widget._show_roi_labels is False


@pytest.mark.usefixtures("mock_pg")
def test_widget_set_active_roi(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test setting active ROI."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")

    widget._set_active_roi(0)
    assert widget._active_roi_idx == 0

    widget._set_active_roi(1)
    assert widget._active_roi_idx == 1


@pytest.mark.usefixtures("mock_pg")
def test_widget_frame_and_rois_use_source_coordinates(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    context_cls = mocker.patch("ntnda_qt_viewer._widget.Context")

    widget = NTNDAViewerWidget("DEV:")
    image = np.arange(12, dtype=np.uint16).reshape(3, 4)
    widget._pending_image = image
    widget._refresh_display()
    assert widget._current_image is not None
    np.testing.assert_array_equal(widget._current_image, image)

    widget._write_roi(0, 1, 2, 3, 1)
    put = context_cls.return_value.put
    written = {c.args[0]: c.args[1] for c in put.call_args_list}
    assert written == {
        "DEV:ROI1:MinX": 1,
        "DEV:ROI1:MinY": 2,
        "DEV:ROI1:SizeX": 3,
        "DEV:ROI1:SizeY": 1,
    }


@pytest.mark.usefixtures("mock_pg")
def test_widget_rescales_views_when_image_shape_changes(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

    widget = NTNDAViewerWidget("DEV:")
    image_vb = widget._image_vb
    widget._pending_image = np.zeros((4, 6), dtype=np.uint16)
    widget._refresh_display()
    assert image_vb.viewRange() == [[0, 6], [0, 4]]

    set_x_range = mocker.spy(image_vb, "setXRange")
    widget._pending_image = np.zeros((4, 6), dtype=np.uint16)
    widget._refresh_display()
    set_x_range.assert_not_called()

    widget._cross_row, widget._cross_col = 3, 5
    widget._pending_image = np.zeros((2, 3), dtype=np.uint16)
    widget._refresh_display()
    assert image_vb.state["limits"]["xLimits"] == [0, 3]
    assert image_vb.state["limits"]["yLimits"] == [0, 2]
    assert image_vb.viewRange() == [[0, 3], [0, 2]]
    cast(MagicMock, widget._h_image_line.setBounds).assert_called_with((0, 1))
    cast(MagicMock, widget._v_image_line.setBounds).assert_called_with((0, 2))
    assert (widget._cross_row, widget._cross_col) == (1, 2)


@pytest.mark.usefixtures("mock_pg")
def test_widget_on_colormap_changed(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test colormap change handler."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")
    widget._current_image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

    # Change to Grayscale
    widget._on_colormap_changed("Grayscale")
    assert widget._current_colormap == "Grayscale"

    # Change to JET
    widget._on_colormap_changed("JET")
    assert widget._current_colormap == "JET"


@pytest.mark.usefixtures("mock_pg")
def test_widget_on_profile_lines_toggled(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test profile lines toggle."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")

    # Initially False
    assert widget._show_profile_lines is False

    # Toggle on
    widget._on_profile_lines_toggled(True)
    assert widget._show_profile_lines is True
    cast(MagicMock, widget._h_image_line.setVisible).assert_called_with(False)

    widget._pending_image = np.zeros((4, 4), dtype=np.uint16)
    widget._refresh_display()
    cast(MagicMock, widget._h_image_line.setVisible).assert_called_with(True)

    # Toggle off
    widget._on_profile_lines_toggled(False)
    assert widget._show_profile_lines is False
    cast(MagicMock, widget._h_image_line.setVisible).assert_called_with(False)


@pytest.mark.usefixtures("mock_pg")
def test_widget_set_roi_mode(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    """Test setting ROI mode."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")

    # Test enabling ROI mode
    widget._set_roi_mode_enabled(True)
    assert widget._roi_set_mode_active is True

    # Test disabling ROI mode
    widget._set_roi_mode_enabled(False)
    assert widget._roi_set_mode_active is False


@pytest.mark.usefixtures("mock_pg")
def test_widget_update_dtype_defaults(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    """Test updating dtype defaults."""
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mock_provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=mock_provider)

    widget = NTNDAViewerWidget("DEV:")

    # Set uint8 dtype
    widget._update_dtype_defaults(np.dtype(np.uint8))
    assert widget._manual_min == 0
    assert widget._manual_max == 255

    # Set float32 dtype
    widget._update_dtype_defaults(np.dtype(np.float32))
    assert widget._manual_min < 0
    assert widget._manual_max > 0


@pytest.mark.usefixtures("mock_pg")
def test_widget_initial_scaling(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

    widget = NTNDAViewerWidget("DEV:")
    assert widget._scale_mode == "auto"
    assert widget._log_scale is False

    widget = NTNDAViewerWidget("DEV:", scale_min=10, scale_max=200, log_scale=True)
    assert widget._scale_mode == "manual"
    assert widget._log_scale is True
    widget._update_dtype_defaults(np.dtype(np.uint16))
    assert widget._manual_levels() == (np.log1p(10.0), np.log1p(200.0))


@pytest.mark.usefixtures("mock_pg")
def test_widget_initial_scaling_invalid(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    import pytest

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", scale_min=10)
    with pytest.raises(ValueError):
        NTNDAViewerWidget("DEV:", scale_min=10, scale_max=10)


@pytest.mark.usefixtures("mock_pg")
def test_widget_start_stop(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=provider)

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


@pytest.mark.usefixtures("mock_pg")
def test_widget_push_frame(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=provider)

    hooks: list[object] = []
    widget = NTNDAViewerWidget("", push_frame=hooks.append)
    assert hooks == [widget.push_frame]
    image = np.arange(12, dtype=np.uint16).reshape(3, 4)
    widget.push_frame(image)
    assert widget._pending_image is None

    widget.start()
    widget.push_frame(image)
    image[0, 0] = 99

    provider.start.assert_not_called()
    assert widget._display_timer.isActive()
    assert widget._pending_image is not None
    assert widget._pending_image[0, 0] == 0

    widget._refresh_display()
    assert widget._current_image is not None
    assert widget._current_image.shape == (3, 4)

    widget.push_frame(np.zeros((2, 2, 3), dtype=np.uint8))
    assert widget._pending_image is not None
    with pytest.raises(ValueError):
        widget.push_frame(np.zeros((2, 2, 4)))
    with pytest.raises(ValueError):
        widget.push_frame(np.zeros(5))

    widget.stop()
    provider.stop.assert_not_called()
    widget._pending_image = None
    widget.push_frame(image)
    assert widget._pending_image is None


@pytest.mark.usefixtures("mock_pg")
def test_widget_callback_mode_rois_in_memory(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    context_cls = mocker.patch("ntnda_qt_viewer._widget.Context")
    mocker.patch.object(NTNDAViewerWidget, "_show_roi_warning")

    widget = NTNDAViewerWidget("", push_frame=lambda _hook: None)
    widget._toggle_roi_visibility(0, True)
    assert widget._roi_models[0].visible is False

    widget._current_image = np.zeros((10, 10), dtype=np.uint16)
    widget._toggle_roi_visibility(0, True)
    assert widget._roi_models[0].visible is True
    widget._on_set_roi_rectangle(1, 4, 2, 6)
    widget._write_roi(0, 1, 2, 3, 4)
    context_cls.assert_not_called()


@pytest.mark.usefixtures("mock_pg")
def test_widget_hover_reports_source_pixel(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

    widget = NTNDAViewerWidget("DEV:")
    widget._current_image = np.arange(40, dtype=np.uint8).reshape(4, 10)
    widget._hover_x, widget._hover_y = 2, 1
    widget._update_hover_value()
    assert widget._hover_pos == " | x=2 y=1 val=12"


@pytest.mark.usefixtures("mock_pg")
def test_widget_no_image_shows_warning(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")

    widget = NTNDAViewerWidget("DEV:")
    widget._on_no_image()
    assert widget._status_label.text() == (
        "Warning: DEV:Pva1:Image has no image data yet"
    )


def test_widget_click_hook(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    from qtpy.QtCore import QPointF

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    widget = NTNDAViewerWidget("DEV:")
    hook = mocker.MagicMock()
    widget.add_click_hook(hook)

    event = mocker.MagicMock()
    event.button.return_value = Qt.MouseButton.LeftButton
    vb = mocker.patch.object(widget, "_image_vb")
    vb.sceneBoundingRect.return_value.contains.return_value = True
    vb.mapSceneToView.return_value = QPointF(3.7, 1.2)
    on_overlay = mocker.patch.object(widget, "_click_hits_overlay", return_value=False)

    widget._on_mouse_clicked(event)
    hook.assert_not_called()

    widget._current_image = np.zeros((4, 10), dtype=np.uint8)
    widget._on_mouse_clicked(event)
    hook.assert_called_once_with(3, 1)

    event.button.return_value = Qt.MouseButton.RightButton
    widget._on_mouse_clicked(event)
    event.button.return_value = Qt.MouseButton.LeftButton
    on_overlay.return_value = True
    widget._on_mouse_clicked(event)
    on_overlay.return_value = False
    assert hook.call_count == 1

    vb.mapSceneToView.return_value = QPointF(10.5, 1.0)
    widget._on_mouse_clicked(event)
    vb.mapSceneToView.return_value = QPointF(3.0, 1.0)
    vb.sceneBoundingRect.return_value.contains.return_value = False
    widget._on_mouse_clicked(event)
    assert hook.call_count == 1

    widget.remove_click_hook(hook)
    vb.sceneBoundingRect.return_value.contains.return_value = True
    widget._on_mouse_clicked(event)
    assert hook.call_count == 1


def test_widget_click_overlay_detection(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from qtpy.QtCore import QPointF

    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    widget = NTNDAViewerWidget("DEV:")
    roi = widget._roi_models[0].rect
    handle = roi.getHandles()[0]
    items = mocker.patch.object(widget._glw.scene(), "items")
    pos = QPointF(0, 0)

    items.return_value = [widget._image_item]
    assert widget._click_hits_overlay(pos) is False

    items.return_value = [handle]
    assert widget._click_hits_overlay(pos) is False  # ROI hidden
    roi.setVisible(True)
    assert widget._click_hits_overlay(pos) is True

    widget._h_image_line.setVisible(False)
    items.return_value = [widget._h_image_line]
    assert widget._click_hits_overlay(pos) is False
    widget._h_image_line.setVisible(True)
    assert widget._click_hits_overlay(pos) is True


@pytest.mark.usefixtures("mock_pg")
def test_widget_start_requires_prefix(
    mocker: MockerFixture, qapp: QCoreApplication
) -> None:
    from ntnda_qt_viewer._widget import NTNDAViewerWidget

    provider = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider", return_value=provider)

    widget = NTNDAViewerWidget("DEV:")
    widget._prefix_edit.setText("  ")
    widget.start()
    provider.start.assert_not_called()


def test_viewer_colors_validation() -> None:
    from ntnda_qt_viewer import ViewerColors

    colors = ViewerColors(roi=["red", "#00ff00"])  # type: ignore[arg-type]
    assert colors.roi == ("red", "#00ff00")
    with pytest.raises(ValueError, match="background"):
        ViewerColors(background="not-a-color")
    with pytest.raises(ValueError, match=r"roi\[1\]"):
        ViewerColors(roi=("red", "bogus"))


def test_viewer_colors_generates_distinct_roi_colors() -> None:
    from ntnda_qt_viewer import ViewerColors

    defaults = [ViewerColors().roi_color(i) for i in range(12)]
    # Pinned so ROI colors stay the same across releases and restarts.
    assert defaults[:6] == [
        "#00ff66",
        "#ffcc00",
        "#00d9ff",
        "#ff3366",
        "#7300ff",
        "#66ff00",
    ]
    assert len(set(defaults)) == len(defaults)
    # A short custom palette is extended rather than repeated.
    assert ViewerColors(roi=("#ff0000", "#0000ff")).roi_color(2) == "#00ff00"
    assert [ViewerColors(roi=()).roi_color(i) for i in range(2)] == [
        "#ff0000",
        "#00ffff",
    ]


def _rendered_colors(widget: NTNDAViewerWidget) -> dict[str, object]:
    """Colors actually set on the (real) pyqtgraph items of a viewer."""
    import pyqtgraph as pg

    curves = (widget._h_profile_curve, widget._v_profile_curve)
    lines = (widget._h_image_line, widget._v_image_line)
    axes = widget._profile_axes
    return {
        "background": widget._glw.backgroundBrush().color().name(),
        "curves": {pg.mkPen(c.opts["pen"]).color().name() for c in curves},
        "lines": {line.pen.color().name() for line in lines},
        "axes": {a.pen().color().name() for a in axes}
        | {a.textPen().color().name() for a in axes},
        "roi": [m.rect.pen.color().name() for m in widget._roi_models],
        "roi_labels": [
            m.label.color.name() for m in widget._roi_models if m.label is not None
        ],
    }


def test_widget_applies_colors(mocker: MockerFixture, qapp: QCoreApplication) -> None:
    from ntnda_qt_viewer import NTNDAViewerWidget, ViewerColors

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    colors = ViewerColors(
        background="#101010",
        axes="#202020",
        profile_curves="#303030",
        profile_lines="#404040",
        roi=("#ff0000", "#0000ff"),
    )
    widget = NTNDAViewerWidget("DEV:", num_rois=3, colors=colors)
    assert widget.colors is colors
    assert _rendered_colors(widget) == {
        "background": "#101010",
        "curves": {"#303030"},
        "lines": {"#404040"},
        "axes": {"#202020"},
        "roi": ["#ff0000", "#0000ff", "#00ff00"],
        "roi_labels": ["#ff0000", "#0000ff", "#00ff00"],
    }
    hover = widget._roi_models[0].rect.hoverPen.color()
    assert hover.lightness() > widget._roi_models[0].rect.pen.color().lightness()

    widget.set_colors(ViewerColors(background="white", axes="#000000"))
    # Axes are re-created when the layout changes and must keep the colors.
    widget._set_v_profile_position("right")
    rendered = _rendered_colors(widget)
    assert rendered["background"] == "#ffffff"
    assert rendered["axes"] == {"#000000"}
    assert rendered["curves"] == {"#00ffff"}
    assert rendered["roi"] == ["#00ff66", "#ffcc00", "#00d9ff"]


@pytest.mark.parametrize("accepted", [True, False])
def test_widget_colors_dialog(
    mocker: MockerFixture, qapp: QCoreApplication, accepted: bool
) -> None:
    from qtpy.QtGui import QColor
    from qtpy.QtWidgets import QDialog, QPushButton

    from ntnda_qt_viewer import NTNDAViewerWidget, ViewerColors

    mocker.patch("ntnda_qt_viewer._widget.NTNDAProvider")
    mocker.patch(
        "ntnda_qt_viewer._widget.QColorDialog.getColor",
        return_value=QColor("#123456"),
    )

    def run_dialog(dialog: QDialog) -> QDialog.DialogCode:
        for name in ("color_background", "color_roi1"):
            button = dialog.findChild(QPushButton, name)
            assert button is not None
            button.click()
        if accepted:
            return QDialog.DialogCode.Accepted
        return QDialog.DialogCode.Rejected

    # A plain function patched onto the class receives the dialog as self.
    mocker.patch.object(QDialog, "exec", new=run_dialog)

    widget = NTNDAViewerWidget("DEV:", num_rois=2)
    widget._open_colors_dialog()

    if accepted:
        assert widget.colors == ViewerColors(
            background="#123456", roi=("#00ff66", "#123456")
        )
    else:
        assert widget.colors == ViewerColors()
    assert widget._glw.backgroundBrush().color().name() == widget.colors.background
