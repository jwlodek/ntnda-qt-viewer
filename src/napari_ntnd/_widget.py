"""pyqtgraph-based NTNDArray image viewer widget."""

from __future__ import annotations

import logging
import time

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ._p4p import NTNDProvider

__all__ = ["NTNDViewerWidget"]

logger = logging.getLogger(__name__)

_DISPLAY_INTERVAL_MS = 33  # ~30 FPS


class _StatusIndicator(QLabel):
    """A small coloured circle that indicates connection status."""

    _DIAMETER = 14

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self._DIAMETER, self._DIAMETER)
        self.set_connected(False)

    def set_connected(self, connected: bool) -> None:
        colour = QColor("#22c55e") if connected else QColor("#ef4444")
        self.setStyleSheet(
            f"background-color: {colour.name()};"
            f"border-radius: {self._DIAMETER // 2}px;"
        )


class NTNDViewerWidget(QWidget):
    """A Qt widget using pyqtgraph ImageView to display NTNDArray images.

    Includes draggable crosshair lines on the image and synchronised
    horizontal/vertical pixel profile plots.
    """

    def __init__(
        self,
        channel_name: str = "13SIM1:Pva1:Image",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("napari-ntnd")

        self._provider = NTNDProvider(channel_name)
        self._current_image: np.ndarray | None = None
        self._pending_image: np.ndarray | None = None
        self._connected = False
        self._updating_crosshair = False
        self._fps_last_time = time.monotonic()
        self._fps_frame_count = 0
        self._fps = 0.0

        self._cross_row = 0
        self._cross_col = 0

        self._init_ui()
        self._connect_signals()

        self._display_timer = QTimer(self)
        self._display_timer.setInterval(_DISPLAY_INTERVAL_MS)
        self._display_timer.timeout.connect(self._refresh_display)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)

        # --- controls bar ---
        controls = QHBoxLayout()
        controls.setContentsMargins(4, 2, 4, 2)

        self._indicator = _StatusIndicator()
        controls.addWidget(self._indicator)

        controls.addWidget(QLabel("Channel:"))
        self._channel_edit = QLineEdit(self._provider.channel_name)
        controls.addWidget(self._channel_edit)

        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        controls.addWidget(self._start_btn)
        controls.addWidget(self._stop_btn)
        root.addLayout(controls)

        # --- graphics layout: aligned image + profile plots ---
        self._glw = pg.GraphicsLayoutWidget()
        root.addWidget(self._glw, stretch=1)

        # Row 0, Col 0: vertical profile plot (left)
        self._v_profile_plot = self._glw.addPlot(row=0, col=0)
        self._v_profile_plot.setMouseEnabled(x=False, y=False)
        self._v_profile_plot.setMenuEnabled(False)
        self._v_profile_plot.hideAxis("bottom")
        self._v_profile_curve = self._v_profile_plot.plot(pen="c")

        # Row 0, Col 1: image view
        self._image_plot = self._glw.addPlot(row=0, col=1)
        self._image_plot.setMouseEnabled(x=False, y=False)
        self._image_plot.setMenuEnabled(False)
        self._image_plot.hideAxis("left")
        self._image_plot.hideAxis("bottom")
        self._image_item = pg.ImageItem()
        self._image_plot.addItem(self._image_item)

        # Link vertical profile Y axis to image Y axis
        self._v_profile_plot.setYLink(self._image_plot)

        # Crosshair lines on the image
        self._h_image_line = pg.InfiniteLine(
            pos=0, angle=0, movable=True, pen=pg.mkPen("y", width=2)
        )
        self._v_image_line = pg.InfiniteLine(
            pos=0, angle=90, movable=True, pen=pg.mkPen("y", width=2)
        )
        self._image_plot.addItem(self._h_image_line)
        self._image_plot.addItem(self._v_image_line)

        # Row 1, Col 1: horizontal profile plot (bottom, under image only)
        self._h_profile_plot = self._glw.addPlot(row=1, col=1)
        self._h_profile_plot.setMouseEnabled(x=False, y=False)
        self._h_profile_plot.setMenuEnabled(False)
        self._h_profile_plot.hideAxis("left")
        self._h_profile_curve = self._h_profile_plot.plot(pen="c")

        # Link horizontal profile X axis to image X axis
        self._h_profile_plot.setXLink(self._image_plot)

        # Sizing: image row/col gets most space
        self._glw.ci.layout.setRowStretchFactor(0, 5)
        self._glw.ci.layout.setRowStretchFactor(1, 1)
        self._glw.ci.layout.setColumnStretchFactor(0, 1)
        self._glw.ci.layout.setColumnStretchFactor(1, 5)

        # --- status bar ---
        self._status_label = QLabel("Idle")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self._status_label)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn.clicked.connect(self._on_stop)
        self._provider.new_frame.connect(self._on_new_frame)
        self._provider.disconnected.connect(self._on_disconnected)

        # Draggable crosshair lines on the image
        self._h_image_line.sigPositionChanged.connect(
            self._on_image_h_line_moved
        )
        self._v_image_line.sigPositionChanged.connect(
            self._on_image_v_line_moved
        )



    # ------------------------------------------------------------------
    # Crosshair interaction — image lines
    # ------------------------------------------------------------------

    def _on_image_h_line_moved(self) -> None:
        if self._updating_crosshair or self._current_image is None:
            return
        rows = self._current_image.shape[0]
        self._cross_row = int(
            np.clip(round(self._h_image_line.value()), 0, rows - 1)
        )
        self._sync_crosshairs_from_image()

    def _on_image_v_line_moved(self) -> None:
        if self._updating_crosshair or self._current_image is None:
            return
        cols = self._current_image.shape[1]
        self._cross_col = int(
            np.clip(round(self._v_image_line.value()), 0, cols - 1)
        )
        self._sync_crosshairs_from_image()

    def _sync_crosshairs_from_image(self) -> None:
        self._update_profiles()

    # ------------------------------------------------------------------
    # Profile updates
    # ------------------------------------------------------------------

    def _update_profiles(self) -> None:
        if self._current_image is None:
            return
        img = self._current_image
        if img.ndim == 3:
            img = img[..., 0]
        rows, cols = img.shape

        row = np.clip(self._cross_row, 0, rows - 1)
        col = np.clip(self._cross_col, 0, cols - 1)

        self._h_profile_curve.setData(np.arange(cols), img[row, :])

        self._v_profile_curve.setData(img[:, col], np.arange(rows))

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        channel = self._channel_edit.text().strip()
        if not channel:
            return
        self._provider.channel_name = channel
        self._provider.start()
        self._fps_last_time = time.monotonic()
        self._fps_frame_count = 0
        self._fps = 0.0
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._channel_edit.setEnabled(False)
        self._display_timer.start()
        self._status_label.setText(f"Subscribed to {channel}")

    def _on_stop(self) -> None:
        self._provider.stop()
        self._display_timer.stop()
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._channel_edit.setEnabled(True)
        self._connected = False
        self._indicator.set_connected(False)
        self._status_label.setText("Stopped")

    # ------------------------------------------------------------------
    # Frame / disconnect handling
    # ------------------------------------------------------------------

    def _on_new_frame(self, image: np.ndarray) -> None:
        self._fps_frame_count += 1
        self._pending_image = image
        if not self._connected:
            self._connected = True
            self._indicator.set_connected(True)

    def _refresh_display(self) -> None:
        image = self._pending_image
        if image is None:
            return
        self._pending_image = None
        first_image = self._current_image is None
        self._current_image = image

        # Set image data on the ImageItem
        self._image_item.setImage(image)

        rows, cols = image.shape[:2]

        # Lock all views to [0, dim] with no padding
        self._image_plot.setXRange(0, cols, padding=0)
        self._image_plot.setYRange(0, rows, padding=0)
        self._h_profile_plot.setXRange(0, cols, padding=0)
        self._v_profile_plot.setYRange(0, rows, padding=0)

        if first_image:
            # Resize window to match image aspect ratio (no black borders)
            self._image_plot.setLimits(
                xMin=0, xMax=cols, yMin=0, yMax=rows,
            )
            self._h_profile_plot.setLimits(xMin=0, xMax=cols)
            self._v_profile_plot.setLimits(yMin=0, yMax=rows)
            self._v_profile_plot.invertY(True)

            # Compute window size preserving image aspect ratio
            screen = self.screen().availableGeometry()
            max_w = int(screen.width() * 0.8)
            max_h = int(screen.height() * 0.8)
            aspect = cols / rows
            if max_w / max_h > aspect:
                win_h = max_h
                win_w = int(win_h * aspect)
            else:
                win_w = max_w
                win_h = int(win_w / aspect)
            self.resize(win_w, win_h)

            self._cross_row = image.shape[0] // 2
            self._cross_col = image.shape[1] // 2
            self._updating_crosshair = True
            self._h_image_line.setValue(self._cross_row)
            self._v_image_line.setValue(self._cross_col)
            self._updating_crosshair = False

        self._update_profiles()

        now = time.monotonic()
        elapsed = now - self._fps_last_time
        if elapsed >= 1.0:
            self._fps = self._fps_frame_count / elapsed
            self._fps_frame_count = 0
            self._fps_last_time = now
        self._status_label.setText(
            f"{self._fps:.1f} FPS | {image.shape} {image.dtype}"
        )

    def _on_disconnected(self) -> None:
        self._connected = False
        self._indicator.set_connected(False)
        self._status_label.setText("Disconnected")

    def closeEvent(self, event) -> None:  # noqa: N802
        self._display_timer.stop()
        self._provider.stop()
        super().closeEvent(event)
