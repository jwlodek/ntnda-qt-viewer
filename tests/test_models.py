"""Tests for data models."""

from __future__ import annotations

import pytest
from dataclasses import is_dataclass
from pytest_mock import MockerFixture


def test_roi_model_is_dataclass():
    """Test that _ROIModel is a proper dataclass."""
    from ntnda_qt_viewer._widget import _ROIModel
    
    assert is_dataclass(_ROIModel)


def test_roi_model_creation(mocker: MockerFixture) -> None:
    """Test creating a _ROIModel instance."""
    from ntnda_qt_viewer._widget import _ROIModel
    
    mock_rect_roi = mocker.MagicMock()
    mock_text_item = mocker.MagicMock()
    
    model = _ROIModel(
        suffix="ROI1:",
        rect=mock_rect_roi,
        label=mock_text_item,
        visible=False,
    )
    
    assert model.suffix == "ROI1:"
    assert model.rect == mock_rect_roi
    assert model.label == mock_text_item
    assert model.visible is False


def test_roi_model_default_label_is_none(mocker: MockerFixture) -> None:
    """Test that label defaults to None."""
    from ntnda_qt_viewer._widget import _ROIModel
    
    mock_rect_roi = mocker.MagicMock()
    
    model = _ROIModel(
        suffix="ROI2:",
        rect=mock_rect_roi,
    )
    
    assert model.label is None
    assert model.visible is False


def test_roi_model_visibility_toggle(mocker: MockerFixture) -> None:
    """Test toggling ROI visibility."""
    from ntnda_qt_viewer._widget import _ROIModel
    
    mock_rect_roi = mocker.MagicMock()
    mock_text_item = mocker.MagicMock()
    
    model = _ROIModel(
        suffix="ROI1:",
        rect=mock_rect_roi,
        label=mock_text_item,
        visible=False,
    )
    
    assert model.visible is False
    model.visible = True
    assert model.visible is True


def test_roi_model_suffix_modification(mocker: MockerFixture) -> None:
    """Test modifying ROI suffix."""
    from ntnda_qt_viewer._widget import _ROIModel
    
    mock_rect_roi = mocker.MagicMock()
    
    model = _ROIModel(
        suffix="ROI1:",
        rect=mock_rect_roi,
    )
    
    assert model.suffix == "ROI1:"
    model.suffix = "ROI2:"
    assert model.suffix == "ROI2:"
