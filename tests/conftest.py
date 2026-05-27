"""Test fixtures and configuration."""

from __future__ import annotations

from typing import Generator, Any

import pytest
from unittest.mock import MagicMock
from pytest_mock import MockerFixture
import numpy as np
from qtpy.QtCore import Qt, QRect, QSize
from qtpy.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Create a QApplication for testing Qt widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_context(mocker: MockerFixture) -> MagicMock:
    """Create a mock p4p Context."""
    context = mocker.MagicMock()
    context.get = mocker.MagicMock(return_value=0)
    context.put = mocker.MagicMock()
    context.monitor = mocker.MagicMock()
    context.close = mocker.MagicMock()
    return context


@pytest.fixture
def mock_signal(mocker: MockerFixture) -> MagicMock:
    """Create a mock Qt signal."""
    signal = mocker.MagicMock()
    signal.emit = mocker.MagicMock()
    signal.connect = mocker.MagicMock()
    signal.disconnect = mocker.MagicMock()
    signal.toggled = mocker.MagicMock()
    signal.clicked = mocker.MagicMock()
    signal.accepted = mocker.MagicMock()
    signal.rejected = mocker.MagicMock()
    return signal


@pytest.fixture
def sample_image() -> np.ndarray:
    """Create a sample image array for testing."""
    return np.random.randint(0, 256, (480, 640), dtype=np.uint8)


@pytest.fixture
def mock_rect_roi(mocker: MockerFixture) -> MagicMock:
    """Create a mock RectROI."""
    rect = mocker.MagicMock()
    rect.pos = mocker.MagicMock(return_value=mocker.MagicMock(x=mocker.MagicMock(return_value=10), y=mocker.MagicMock(return_value=20)))
    rect.size = mocker.MagicMock(return_value=mocker.MagicMock(x=mocker.MagicMock(return_value=100), y=mocker.MagicMock(return_value=100)))
    rect.setPos = mocker.MagicMock()
    rect.setSize = mocker.MagicMock()
    rect.setVisible = mocker.MagicMock()
    rect.sigRegionChanged = mocker.MagicMock()
    rect.sigRegionChangeFinished = mocker.MagicMock()
    rect.hoverPen = None
    rect.addScaleHandle = mocker.MagicMock()
    return rect


@pytest.fixture
def mock_text_item(mocker: MockerFixture) -> MagicMock:
    """Create a mock TextItem for ROI labels."""
    text = mocker.MagicMock()
    text.setPos = mocker.MagicMock()
    text.setVisible = mocker.MagicMock()
    text.setText = mocker.MagicMock()
    return text


@pytest.fixture
def mock_image_plot(mocker: MockerFixture) -> MagicMock:
    """Create a mock image plot."""
    plot = mocker.MagicMock()
    plot.addItem = mocker.MagicMock()
    plot.removeItem = mocker.MagicMock()
    plot.setImage = mocker.MagicMock()
    plot.clear = mocker.MagicMock()
    return plot


@pytest.fixture
def mock_pyqtgraph(mocker: MockerFixture) -> MagicMock:
    """Mock pyqtgraph module."""
    pg = mocker.MagicMock()
    
    # Mock ViewBox
    pg.ViewBox = mocker.MagicMock()
    
    # Mock RectROI
    def rect_roi_factory(*args, **kwargs):
        rect = mocker.MagicMock()
        rect.pos = mocker.MagicMock(return_value=mocker.MagicMock(x=mocker.MagicMock(return_value=0), y=mocker.MagicMock(return_value=0)))
        rect.size = mocker.MagicMock(return_value=mocker.MagicMock(x=mocker.MagicMock(return_value=20), y=mocker.MagicMock(return_value=20)))
        rect.setPos = mocker.MagicMock()
        rect.setSize = mocker.MagicMock()
        rect.setVisible = mocker.MagicMock()
        rect.sigRegionChanged = mocker.MagicMock()
        rect.sigRegionChangeFinished = mocker.MagicMock()
        rect.hoverPen = None
        rect.addScaleHandle = mocker.MagicMock()
        return rect
    
    pg.RectROI = rect_roi_factory
    
    # Mock TextItem
    def text_item_factory(*args, **kwargs):
        text = mocker.MagicMock()
        text.setPos = mocker.MagicMock()
        text.setVisible = mocker.MagicMock()
        text.setText = mocker.MagicMock()
        return text
    
    pg.TextItem = text_item_factory
    
    # Mock mkPen
    pg.mkPen = mocker.MagicMock(side_effect=lambda *args, **kwargs: mocker.MagicMock())
    
    # Mock QtWidgets
    pg.QtWidgets = mocker.MagicMock()
    pg.QtWidgets.QScrollArea = mocker.MagicMock()
    pg.QtWidgets.QWidget = mocker.MagicMock()
    pg.QtWidgets.QVBoxLayout = mocker.MagicMock()
    pg.QtWidgets.QHBoxLayout = mocker.MagicMock()
    pg.QtWidgets.QLabel = mocker.MagicMock()
    pg.QtWidgets.QLineEdit = mocker.MagicMock()
    pg.QtWidgets.QPushButton = mocker.MagicMock()
    pg.QtWidgets.QCheckBox = mocker.MagicMock()
    pg.QtWidgets.QInputDialog = mocker.MagicMock()
    pg.QtWidgets.QMessageBox = mocker.MagicMock()
    pg.QtWidgets.QDialog = mocker.MagicMock()
    
    return pg
