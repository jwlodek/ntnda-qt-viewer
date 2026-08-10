"""Tests for p4p provider."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockerFixture


def test_ntnda_provider_creation() -> None:
    """Test creating an NTNDAProvider instance."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    provider = NTNDAProvider(channel_name="DEV:XSPD1:Pva1:Image")
    assert provider.channel_name == "DEV:XSPD1:Pva1:Image"


def test_ntnda_provider_channel_name_property() -> None:
    """Test getting and setting channel name."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    provider = NTNDAProvider()
    assert provider.channel_name == "DEV:XSPD1:Pva1:Image"

    provider.channel_name = "DEV:NEW:PV"
    assert provider.channel_name == "DEV:NEW:PV"


def test_ntnda_provider_signals(qapp) -> None:
    """Test that NTNDAProvider has correct signals."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    provider = NTNDAProvider()
    assert hasattr(provider, "new_frame")
    assert hasattr(provider, "disconnected")


def test_ntnda_provider_start(mocker: MockerFixture) -> None:
    """Test starting the provider."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    mock_context = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._p4p.Context", return_value=mock_context)
    mock_subscription = mocker.MagicMock()
    mock_context.monitor.return_value = mock_subscription

    provider = NTNDAProvider()
    provider.start()

    assert provider._subscription is not None
    assert provider._ctxt is not None
    mock_context.monitor.assert_called_once()


def test_ntnda_provider_stop(mocker: MockerFixture) -> None:
    """Test stopping the provider."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    mock_context = mocker.MagicMock()
    mocker.patch("ntnda_qt_viewer._p4p.Context", return_value=mock_context)
    mock_subscription = mocker.MagicMock()
    mock_context.monitor.return_value = mock_subscription

    provider = NTNDAProvider()
    provider.start()
    provider.stop()

    assert provider._subscription is None
    assert provider._ctxt is None
    mock_subscription.close.assert_called_once()
    mock_context.close.assert_called_once()


def test_ntnda_provider_dtype_mapping() -> None:
    """Test dtype mapping from codec parameters."""
    from ntnda_qt_viewer._p4p import _SCALAR_CODE_TO_DTYPE

    # Test various dtype codes
    assert _SCALAR_CODE_TO_DTYPE[1] == np.dtype(np.int8)
    assert _SCALAR_CODE_TO_DTYPE[5] == np.dtype(np.uint8)
    assert _SCALAR_CODE_TO_DTYPE[9] == np.dtype(np.float32)
    assert _SCALAR_CODE_TO_DTYPE[10] == np.dtype(np.float64)


def test_ntnda_provider_extract_uncompressed(mocker: MockerFixture, qapp) -> None:
    """Test extracting uncompressed image data."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    provider = NTNDAProvider()

    # Create mock raw NTNDArray value
    data = np.array([1, 2, 3, 4, 5, 6], dtype=np.uint8)
    raw = mocker.MagicMock()
    raw.__getitem__ = mocker.MagicMock(
        side_effect=lambda k: {
            "value": data,
            "dimension": [mocker.MagicMock(size=2), mocker.MagicMock(size=3)],
        }.get(k)
    )
    raw.__contains__ = mocker.MagicMock(return_value=True)
    raw["codec.name"] = None
    raw["value"] = data
    raw["dimension"] = [MagicMock(size=2), MagicMock(size=3)]

    # Test extraction
    result = provider._extract_uncompressed_ntndarray(raw)
    assert result.shape == (3, 2)
    assert result.dtype == np.uint8


def test_ntnda_provider_shape_from_dimension(mocker: MockerFixture, qapp) -> None:
    """Test converting dimension to shape."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    provider = NTNDAProvider()

    # Create mock dimension
    dimension = [
        mocker.MagicMock(size=640),
        mocker.MagicMock(size=480),
        mocker.MagicMock(size=3),
    ]

    shape = provider._shape_from_dimension(dimension)
    assert shape == (3, 480, 640)


def test_ntnda_provider_dtype_from_codec_parameters(qapp) -> None:
    """Test getting dtype from codec parameters."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    provider = NTNDAProvider()

    # Test int8 (code 1)
    dtype = provider._dtype_from_codec_parameters(1)
    assert dtype == np.dtype(np.int8)

    # Test uint8 (code 5)
    dtype = provider._dtype_from_codec_parameters(5)
    assert dtype == np.dtype(np.uint8)

    # Test float32 (code 9)
    dtype = provider._dtype_from_codec_parameters(9)
    assert dtype == np.dtype(np.float32)


def test_ntnda_provider_invalid_codec_parameter(qapp) -> None:
    """Test handling invalid codec parameters."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    provider = NTNDAProvider()

    with pytest.raises(ValueError):
        provider._dtype_from_codec_parameters(999)


def test_ntnda_provider_extract_image_fallback(qapp) -> None:
    """Test extract_image fallback for non-NTNDArray values."""
    from ntnda_qt_viewer._p4p import NTNDAProvider

    provider = NTNDAProvider()

    # Simple array value
    value = np.array([1, 2, 3, 4], dtype=np.uint8)
    result = provider._extract_image(value)

    assert isinstance(result, np.ndarray)
    assert result.size > 0
