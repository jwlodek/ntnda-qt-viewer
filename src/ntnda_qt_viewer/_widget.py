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

# Use OpenGL for smooth bilinear texture filtering (reduces aliasing)
pg.setConfigOptions(useOpenGL=True)


class _ImageViewBox(pg.ViewBox):
    """ViewBox with right-drag zoom-to-rect and double-click reset."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._full_range: tuple[int, int] | None = None  # (cols, rows)

    def set_full_range(self, cols: int, rows: int) -> None:
        self._full_range = (cols, rows)

    def mouseDoubleClickEvent(self, ev):
        if self._full_range is not None:
            cols, rows = self._full_range
            self.setRange(xRange=(0, cols), yRange=(0, rows), padding=0)
        ev.accept()

    def mouseDragEvent(self, ev, axis=None):
        if ev.button() == Qt.MouseButton.RightButton:
            ev.accept()
            if ev.isFinish():
                p1 = self.mapToView(ev.buttonDownPos())
                p2 = self.mapToView(ev.pos())
                x0, x1 = sorted([p1.x(), p2.x()])
                y0, y1 = sorted([p1.y(), p2.y()])
                self.setRange(xRange=(x0, x1), yRange=(y0, y1), padding=0)
                self.rbScaleBox.hide()
            else:
                self.updateScaleBox(ev.buttonDownPos(), ev.pos())
        else:
            super().mouseDragEvent(ev, axis)


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
            f"background-color: {colour.name()};border-radius: {self._DIAMETER // 2}px;"
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
        self._hover_pos: str = ""
        self._hover_x: int = -1
        self._hover_y: int = -1

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
        vb = _ImageViewBox()
        self._image_plot = self._glw.addPlot(row=0, col=1, viewBox=vb)
        self._image_plot.setMouseEnabled(x=True, y=True)
        self._image_plot.setMenuEnabled(False)
        self._image_plot.hideAxis("left")
        self._image_plot.hideAxis("bottom")
        self._image_item = pg.ImageItem(autoDownsample=True)
        self._image_plot.addItem(self._image_item)

        # Mouse hover tracking
        self._proxy = pg.SignalProxy(
            self._image_plot.scene().sigMouseMoved,
            rateLimit=30,
            slot=self._on_mouse_moved,
        )

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
        self._h_image_line.sigPositionChanged.connect(self._on_image_h_line_moved)
        self._v_image_line.sigPositionChanged.connect(self._on_image_v_line_moved)

    # ------------------------------------------------------------------
    # Crosshair interaction — image lines
    # ------------------------------------------------------------------

    def _on_image_h_line_moved(self) -> None:
        if self._updating_crosshair or self._current_image is None:
            return
        rows = self._current_image.shape[0]
        self._cross_row = int(np.clip(round(self._h_image_line.value()), 0, rows - 1))
        self._updating_crosshair = True
        self._h_image_line.setValue(self._cross_row)
        self._updating_crosshair = False
        self._sync_crosshairs_from_image()

    def _on_image_v_line_moved(self) -> None:
        if self._updating_crosshair or self._current_image is None:
            return
        cols = self._current_image.shape[1]
        self._cross_col = int(np.clip(round(self._v_image_line.value()), 0, cols - 1))
        self._updating_crosshair = True
        self._v_image_line.setValue(self._cross_col)
        self._updating_crosshair = False
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
        self._fps = 0.0
        self._fps_frame_count = 0
        self._update_hover_value()
        self._refresh_status_bar()

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

        # Set image data on the ImageItem.
        # pyqtgraph doesn't natively handle all dtypes (e.g. int64, uint64),
        # so convert to float32 and provide explicit levels.
        # Mirror horizontally: pyqtgraph transposes the image internally.
        if image.dtype != np.float32:
            display = image[:, ::-1].astype(np.float32)
        else:
            display = image[:, ::-1].copy()
        levels = (float(np.min(display)), float(np.max(display)))
        if levels[0] == levels[1]:
            levels = (levels[0], levels[0] + 1.0)
        self._image_item.setImage(display, levels=levels)

        rows, cols = image.shape[:2]

        if first_image:
            # Lock all views to [0, dim] with no padding
            self._image_plot.setXRange(0, cols, padding=0)
            self._image_plot.setYRange(0, rows, padding=0)
            self._h_profile_plot.setXRange(0, cols, padding=0)
            self._v_profile_plot.setYRange(0, rows, padding=0)

            # Resize window to match image aspect ratio (no black borders)
            self._image_plot.setLimits(
                xMin=0,
                xMax=cols,
                yMin=0,
                yMax=rows,
            )
            self._image_plot.getViewBox().set_full_range(cols, rows)
            self._h_profile_plot.setLimits(xMin=0, xMax=cols)
            self._v_profile_plot.setLimits(yMin=0, yMax=rows)
            self._v_profile_plot.invertY(True)

            # Compute window size: try 1:1 pixels, then 75%, 50%, 25%
            # Profile plots use 1/6 of each axis (stretch 5:1), so scale up
            # to ensure the image area itself is the target pixel size.
            screen = self.screen().availableGeometry()
            max_w = screen.width()
            max_h = screen.height()
            overhead_h = 80  # controls bar + status bar
            for scale in (1.0, 0.75, 0.5, 0.25):
                img_w = int(cols * scale)
                img_h = int(rows * scale)
                # image gets 5/6 of total due to stretch factors
                win_w = int(img_w * 6 / 5)
                win_h = int(img_h * 6 / 5) + overhead_h
                if win_w <= max_w and win_h <= max_h:
                    break
            self.resize(win_w, win_h)

            self._cross_row = 0
            self._cross_col = 0
            self._updating_crosshair = True
            self._h_image_line.setBounds((0, rows - 1))
            self._v_image_line.setBounds((0, cols - 1))
            self._h_image_line.setValue(0)
            self._v_image_line.setValue(0)
            self._updating_crosshair = False

        self._update_profiles()
        self._update_hover_value()

        now = time.monotonic()
        elapsed = now - self._fps_last_time
        if elapsed >= 1.0:
            self._fps = self._fps_frame_count / elapsed
            self._fps_frame_count = 0
            self._fps_last_time = now
        self._refresh_status_bar()

    def _on_disconnected(self) -> None:
        self._connected = False
        self._indicator.set_connected(False)
        self._status_label.setText("Disconnected")

    def _on_mouse_moved(self, args: tuple) -> None:
        pos = args[0]
        if not self._image_plot.sceneBoundingRect().contains(pos):
            self._hover_x = -1
            self._hover_y = -1
            self._hover_pos = ""
            self._refresh_status_bar()
            return
        vb = self._image_plot.getViewBox()
        mouse_point = vb.mapSceneToView(pos)
        self._hover_x = int(mouse_point.x())
        self._hover_y = int(mouse_point.y())
        self._update_hover_value()
        self._refresh_status_bar()

    def _update_hover_value(self) -> None:
        if self._current_image is None or self._hover_x < 0:
            self._hover_pos = ""
            return
        rows, cols = self._current_image.shape[:2]
        x, y = self._hover_x, self._hover_y
        if 0 <= x < cols and 0 <= y < rows:
            val = self._current_image[y, x]
            self._hover_pos = f" | x={x} y={y} val={val}"
        else:
            self._hover_pos = ""

    def _refresh_status_bar(self) -> None:
        if self._current_image is None:
            return
        img = self._current_image
        self._status_label.setText(
            f"{self._fps:.1f} FPS | {img.shape} {img.dtype}{self._hover_pos}"
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        self._display_timer.stop()
        self._provider.stop()
        super().closeEvent(event)
