"""pyqtgraph-based NTNDArray image viewer widget."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from p4p.client.thread import Context
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ._p4p import NTNDProvider

__all__ = ["NTNDViewerWidget"]

logger = logging.getLogger(__name__)

_DISPLAY_INTERVAL_MS = 33  # ~30 FPS
_DEFAULT_PVA_SUFFIX = "Pva1:"
_DEFAULT_ROI_SUFFIXES = ["ROI1:", "ROI2:", "ROI3:", "ROI4:"]
_COLORMAPS = ("Grayscale", "JET")

# One-line orientation control.
# Change this to another key in _ORIENTATION_PRESETS as needed.
_ORIENTATION_PRESET = "current"

_ORIENTATION_PRESETS: dict[str, dict[str, str | bool]] = {
    # Preserves the currently correct orientation.
    "current": {"transform": "rotate180", "invert_x": True, "invert_y": False},
    "none": {"transform": "none", "invert_x": False, "invert_y": False},
    "mirror_lr": {"transform": "none", "invert_x": True, "invert_y": False},
    "mirror_ud": {"transform": "none", "invert_x": False, "invert_y": True},
    "rotate180": {"transform": "rotate180", "invert_x": False, "invert_y": False},
}

# Use OpenGL for smooth bilinear texture filtering (reduces aliasing)
pg.setConfigOptions(useOpenGL=True, imageAxisOrder="row-major")


@dataclass
class _ROIModel:
    suffix: str
    rect: pg.RectROI
    visible: bool = False


class _ImageViewBox(pg.ViewBox):
    """ViewBox with right-drag zoom-to-rect and double-click reset."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._full_range: tuple[int, int] | None = None  # (cols, rows)
        self._set_roi_mode = False
        self._roi_drag_callback = None

    def set_roi_drag_mode(self, enabled: bool, callback) -> None:
        self._set_roi_mode = enabled
        self._roi_drag_callback = callback

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
                if self._set_roi_mode and self._roi_drag_callback is not None:
                    self._roi_drag_callback(x0, x1, y0, y1)
                else:
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
        prefix: str = "13SIM1:",
        pva_suffix: str = _DEFAULT_PVA_SUFFIX,
        roi_suffixes: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("ntnda-qt-viewer")

        self._prefix = prefix
        self._pva_suffix = pva_suffix
        self._roi_suffixes = roi_suffixes or _DEFAULT_ROI_SUFFIXES.copy()
        self._provider = NTNDProvider(self._build_image_channel())
        self._current_image: np.ndarray | None = None
        self._pending_image: np.ndarray | None = None
        self._connected = False
        self._updating_crosshair = False
        self._roi_context: Context | None = None
        self._roi_models: list[_ROIModel] = []
        self._roi_enable_checks: list[QCheckBox] = []
        self._roi_set_buttons: list[QPushButton] = []
        self._active_roi_idx = 0
        self._set_roi_mode = False
        self._selected_colormap = "Grayscale"
        self._jet_lut = self._build_jet_lut()
        self._scale_mode = "auto"  # "auto" or "manual"
        self._log_scale = False
        self._manual_min: float | None = None
        self._manual_max: float | None = None
        self._data_dtype: np.dtype | None = None
        self._fps_last_time = time.monotonic()
        self._fps_frame_count = 0
        self._fps = 0.0
        self._orientation = _ORIENTATION_PRESETS.get(
            _ORIENTATION_PRESET,
            _ORIENTATION_PRESETS["current"],
        )

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

        controls.addWidget(QLabel("Prefix:"))
        self._prefix_edit = QLineEdit(self._prefix)
        controls.addWidget(self._prefix_edit)

        controls.addWidget(QLabel("PVA Suffix:"))
        self._pva_suffix_edit = QLineEdit(self._pva_suffix)
        controls.addWidget(self._pva_suffix_edit)

        controls.addWidget(QLabel("Colormap:"))
        self._colormap_combo = QComboBox()
        self._colormap_combo.addItems(list(_COLORMAPS))
        self._colormap_combo.setCurrentText(self._selected_colormap)
        controls.addWidget(self._colormap_combo)

        self._scaling_btn = QPushButton("Scaling...")
        controls.addWidget(self._scaling_btn)

        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        controls.addWidget(self._start_btn)
        controls.addWidget(self._stop_btn)
        root.addLayout(controls)

        # --- graphics layout: aligned image + profile plots ---
        self._glw = pg.GraphicsLayoutWidget()
        root.addWidget(self._glw, stretch=1)

        # --- ROI controls bar ---
        roi_controls = QHBoxLayout()
        roi_controls.setContentsMargins(4, 2, 4, 2)
        roi_controls.addWidget(QLabel("ROIs:"))
        for idx, suffix in enumerate(self._roi_suffixes):
            set_btn = QPushButton(f"Set {suffix}")
            set_btn.setCheckable(True)
            set_btn.clicked.connect(
                lambda checked, roi_idx=idx: self._on_set_roi_button_clicked(
                    roi_idx, checked
                )
            )
            roi_controls.addWidget(set_btn)
            self._roi_set_buttons.append(set_btn)

            enable_check = QCheckBox(f"Enable {suffix}")
            enable_check.setChecked(False)
            enable_check.toggled.connect(
                lambda visible, roi_idx=idx: self._toggle_roi_visibility(roi_idx, visible)
            )
            roi_controls.addWidget(enable_check)
            self._roi_enable_checks.append(enable_check)
        roi_controls.addStretch(1)
        root.addLayout(roi_controls)

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
        self._image_plot.getViewBox().invertX(bool(self._orientation["invert_x"]))
        self._image_plot.getViewBox().invertY(bool(self._orientation["invert_y"]))
        vb.set_roi_drag_mode(False, self._on_set_roi_rectangle)
        self._image_item = pg.ImageItem(autoDownsample=True)
        self._image_plot.addItem(self._image_item)

        self._create_roi_overlays()

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
        self._colormap_combo.currentTextChanged.connect(self._on_colormap_changed)
        self._scaling_btn.clicked.connect(self._open_scaling_dialog)

        # Draggable crosshair lines on the image
        self._h_image_line.sigPositionChanged.connect(self._on_image_h_line_moved)
        self._v_image_line.sigPositionChanged.connect(self._on_image_v_line_moved)

    def _build_image_channel(self) -> str:
        return f"{self._prefix}{self._pva_suffix}Image"

    @staticmethod
    def _dtype_min_max(dtype: np.dtype) -> tuple[float, float]:
        if np.issubdtype(dtype, np.integer):
            info = np.iinfo(dtype)
            return float(info.min), float(info.max)
        if np.issubdtype(dtype, np.floating):
            info = np.finfo(dtype)
            return float(info.min), float(info.max)
        return 0.0, 1.0

    def _update_dtype_defaults(self, dtype: np.dtype) -> None:
        if self._data_dtype == dtype:
            return
        self._data_dtype = dtype
        self._manual_min, self._manual_max = self._dtype_min_max(dtype)

    @staticmethod
    def _build_jet_lut(size: int = 256) -> np.ndarray:
        """Create a classic JET lookup table as uint8 RGB values."""
        x = np.linspace(0.0, 1.0, size, dtype=np.float32)
        r = np.clip(1.5 - np.abs(4.0 * x - 3.0), 0.0, 1.0)
        g = np.clip(1.5 - np.abs(4.0 * x - 2.0), 0.0, 1.0)
        b = np.clip(1.5 - np.abs(4.0 * x - 1.0), 0.0, 1.0)
        lut = np.stack((r, g, b), axis=1)
        return (lut * 255).astype(np.uint8)

    def _apply_colormap(self) -> None:
        if self._selected_colormap == "JET":
            self._image_item.setLookupTable(self._jet_lut)
        else:
            self._image_item.setLookupTable(None)

    def _on_colormap_changed(self, name: str) -> None:
        self._selected_colormap = name
        self._apply_colormap()

    def _open_scaling_dialog(self) -> None:
        dialog = QDialog(None)
        dialog.setWindowTitle("Scaling Options")

        prev_scale_mode = self._scale_mode
        prev_log_scale = self._log_scale
        prev_manual_min = self._manual_min
        prev_manual_max = self._manual_max

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        auto_radio = QRadioButton("Auto scale (frame min/max)")
        manual_radio = QRadioButton("Manual scale")
        auto_radio.setChecked(self._scale_mode == "auto")
        manual_radio.setChecked(self._scale_mode == "manual")

        log_check = QCheckBox("Log scale")
        log_check.setChecked(self._log_scale)

        min_edit = QLineEdit()
        max_edit = QLineEdit()
        min_val = self._manual_min if self._manual_min is not None else 0.0
        max_val = self._manual_max if self._manual_max is not None else 1.0
        min_edit.setText(str(min_val))
        max_edit.setText(str(max_val))
        min_edit.setEnabled(manual_radio.isChecked())
        max_edit.setEnabled(manual_radio.isChecked())

        def _update_manual_enabled() -> None:
            enabled = manual_radio.isChecked()
            min_edit.setEnabled(enabled)
            max_edit.setEnabled(enabled)

        auto_radio.toggled.connect(_update_manual_enabled)
        manual_radio.toggled.connect(_update_manual_enabled)

        def _refresh_preview() -> None:
            if self._current_image is not None:
                self._pending_image = self._current_image
                self._refresh_display()

        def _apply_from_controls(show_error: bool) -> bool:
            next_log_scale = log_check.isChecked()
            next_scale_mode = "manual" if manual_radio.isChecked() else "auto"

            next_manual_min = self._manual_min
            next_manual_max = self._manual_max
            if next_scale_mode == "manual":
                try:
                    next_manual_min = float(min_edit.text().strip())
                    next_manual_max = float(max_edit.text().strip())
                except ValueError:
                    if show_error:
                        QMessageBox.warning(
                            self,
                            "Scaling Options",
                            "Manual min/max must be numeric values.",
                        )
                    return False
                if next_manual_min >= next_manual_max:
                    if show_error:
                        QMessageBox.warning(
                            self,
                            "Scaling Options",
                            "Manual min must be less than manual max.",
                        )
                    return False

            self._log_scale = next_log_scale
            self._scale_mode = next_scale_mode
            if next_scale_mode == "manual":
                self._manual_min = next_manual_min
                self._manual_max = next_manual_max
            _refresh_preview()
            return True

        def _on_preview_change() -> None:
            _apply_from_controls(show_error=False)

        def _on_accept() -> None:
            if _apply_from_controls(show_error=True):
                dialog.accept()

        auto_radio.toggled.connect(_on_preview_change)
        manual_radio.toggled.connect(_on_preview_change)
        log_check.toggled.connect(_on_preview_change)
        min_edit.textChanged.connect(_on_preview_change)
        max_edit.textChanged.connect(_on_preview_change)

        form.addRow(auto_radio)
        form.addRow(manual_radio)
        form.addRow(log_check)
        form.addRow("Manual Min", min_edit)
        form.addRow("Manual Max", max_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(_on_accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._scale_mode = prev_scale_mode
            self._log_scale = prev_log_scale
            self._manual_min = prev_manual_min
            self._manual_max = prev_manual_max
            _refresh_preview()
            return

    def _transform_for_scaling(self, image: np.ndarray) -> np.ndarray:
        if not self._log_scale:
            return image
        return np.log1p(np.clip(image, a_min=0.0, a_max=None))

    def _manual_levels(self) -> tuple[float, float] | None:
        if self._manual_min is None or self._manual_max is None:
            return None
        if not self._log_scale:
            return self._manual_min, self._manual_max
        return float(np.log1p(max(self._manual_min, 0.0))), float(
            np.log1p(max(self._manual_max, 0.0))
        )

    def _roi_field_channel(self, suffix: str, field: str) -> str:
        return f"{self._prefix}{suffix}{field}"

    def _set_active_roi(self, idx: int) -> None:
        self._active_roi_idx = idx

    def _set_roi_mode_enabled(self, enabled: bool) -> None:
        self._set_roi_mode = enabled
        self._image_plot.getViewBox().set_roi_drag_mode(enabled, self._on_set_roi_rectangle)
        if enabled:
            self._status_label.setText(
                f"Set ROI mode: right-drag to define {self._roi_models[self._active_roi_idx].suffix}"
            )
        else:
            self._refresh_status_bar()

    def _on_set_roi_button_clicked(self, idx: int, checked: bool) -> None:
        if checked:
            self._set_active_roi(idx)
            for i, btn in enumerate(self._roi_set_buttons):
                if i != idx:
                    btn.setChecked(False)
            self._set_roi_mode_enabled(True)
            return
        self._set_roi_mode_enabled(False)

    def _exit_set_roi_mode(self) -> None:
        self._set_roi_mode_enabled(False)
        for btn in self._roi_set_buttons:
            btn.setChecked(False)

    def _toggle_roi_visibility(self, idx: int, visible: bool) -> None:
        if not (0 <= idx < len(self._roi_models)):
            return
        if visible:
            can_enable, reason = self._load_roi_from_ioc(idx)
            if not can_enable:
                self._set_roi_checkbox(idx, False)
                self._status_label.setText(reason)
                self._show_roi_warning(reason)
                return
        model = self._roi_models[idx]
        model.visible = visible
        model.rect.setVisible(visible)
        self._set_roi_checkbox(idx, visible)

    def _set_roi_checkbox(self, idx: int, checked: bool) -> None:
        if 0 <= idx < len(self._roi_enable_checks):
            check = self._roi_enable_checks[idx]
            if check.isChecked() != checked:
                check.setChecked(checked)

    def _show_roi_warning(self, message: str) -> None:
        QMessageBox.warning(self, "ROI Warning", message)

    def _source_to_display_roi(
        self,
        min_x: int,
        min_y: int,
        size_x: int,
        size_y: int,
        rows: int,
        cols: int,
    ) -> tuple[int, int, int, int]:
        """Map ROI from source PV coordinates to displayed image coordinates."""
        transform = str(self._orientation["transform"])
        if transform == "rotate180":
            disp_min_x = cols - (min_x + size_x)
            disp_min_y = rows - (min_y + size_y)
            return (
                int(np.clip(disp_min_x, 0, max(cols - size_x, 0))),
                int(np.clip(disp_min_y, 0, max(rows - size_y, 0))),
                size_x,
                size_y,
            )
        return min_x, min_y, size_x, size_y

    def _load_roi_from_ioc(self, idx: int) -> tuple[bool, str]:
        if self._current_image is None:
            suffix = self._roi_models[idx].suffix
            return False, f"Cannot enable {suffix} before first image frame"

        rows, cols = self._current_image.shape[:2]
        suffix = self._roi_models[idx].suffix
        ctxt = self._ensure_roi_context()
        fields = ("MinX", "MinY", "SizeX", "SizeY")
        try:
            values = [int(ctxt.get(self._roi_field_channel(suffix, field))) for field in fields]
        except Exception:
            logger.exception("Failed to read ROI settings for %s", suffix)
            return False, f"Failed to read {suffix} settings from IOC"

        src_min_x, src_min_y, size_x, size_y = values
        if size_x <= 0 or size_y <= 0:
            return (
                False,
                f"Cannot enable {suffix}: ROI size ({size_x}x{size_y}) is invalid. Use Set {suffix}.",
            )
        if size_x > cols or size_y > rows:
            return (
                False,
                f"Cannot enable {suffix}: ROI size ({size_x}x{size_y}) exceeds image ({cols}x{rows}). Use Set {suffix}.",
            )
        if src_min_x < 0 or src_min_y < 0 or src_min_x + size_x > cols or src_min_y + size_y > rows:
            return (
                False,
                f"Cannot enable {suffix}: ROI bounds are outside image ({cols}x{rows}). Use Set {suffix}.",
            )

        x0, y0, size_x, size_y = self._source_to_display_roi(
            src_min_x, src_min_y, size_x, size_y, rows, cols
        )
        rect = self._roi_models[idx].rect
        rect.setPos((x0, y0), update=False, finish=False)
        rect.setSize((size_x, size_y), update=False, finish=False)
        return True, ""

    def _create_roi_overlays(self) -> None:
        pens = [
            pg.mkPen("#00ff66", width=3),
            pg.mkPen("#ffcc00", width=3),
            pg.mkPen("#00d9ff", width=3),
            pg.mkPen("#ff3366", width=3),
        ]
        hover_pens = [
            pg.mkPen("#adff2f", width=4),
            pg.mkPen("#ffd84d", width=4),
            pg.mkPen("#66eaff", width=4),
            pg.mkPen("#ff7fa2", width=4),
        ]
        for idx, suffix in enumerate(self._roi_suffixes):
            rect = pg.RectROI([0, 0], [20, 20], pen=pens[idx % len(pens)], movable=True)
            rect.hoverPen = hover_pens[idx % len(hover_pens)]
            rect.addScaleHandle([0.5, 0.0], [0.5, 1.0])
            rect.addScaleHandle([0.5, 1.0], [0.5, 0.0])
            rect.addScaleHandle([0.0, 0.5], [1.0, 0.5])
            rect.addScaleHandle([1.0, 0.5], [0.0, 0.5])
            rect.sigRegionChangeFinished.connect(
                lambda _=None, roi_idx=idx: self._on_roi_region_changed(roi_idx)
            )
            rect.setVisible(False)
            self._image_plot.addItem(rect)
            self._roi_models.append(_ROIModel(suffix=suffix, rect=rect))

    def _ensure_roi_context(self) -> Context:
        if self._roi_context is None:
            self._roi_context = Context("pva")
        return self._roi_context

    def _display_to_source_roi(
        self,
        min_x: int,
        min_y: int,
        size_x: int,
        size_y: int,
        rows: int,
        cols: int,
    ) -> tuple[int, int, int, int]:
        """Map ROI from displayed image coordinates back to source PV coordinates."""
        transform = str(self._orientation["transform"])
        if transform == "rotate180":
            src_min_x = cols - (min_x + size_x)
            src_min_y = rows - (min_y + size_y)
            return (
                int(np.clip(src_min_x, 0, max(cols - size_x, 0))),
                int(np.clip(src_min_y, 0, max(rows - size_y, 0))),
                size_x,
                size_y,
            )
        return min_x, min_y, size_x, size_y

    def _write_roi(self, idx: int, min_x: int, min_y: int, size_x: int, size_y: int) -> None:
        if not (0 <= idx < len(self._roi_models)):
            return
        if self._current_image is None:
            return
        rows, cols = self._current_image.shape[:2]
        src_min_x, src_min_y, src_size_x, src_size_y = self._display_to_source_roi(
            min_x, min_y, size_x, size_y, rows, cols
        )
        suffix = self._roi_models[idx].suffix
        ctxt = self._ensure_roi_context()
        updates = {
            "MinX": int(src_min_x),
            "MinY": int(src_min_y),
            "SizeX": int(src_size_x),
            "SizeY": int(src_size_y),
        }
        for field, value in updates.items():
            channel = self._roi_field_channel(suffix, field)
            try:
                ctxt.put(channel, value, wait=False)
            except Exception:
                logger.exception("Failed to write %s=%s", channel, value)

    def _on_roi_region_changed(self, idx: int) -> None:
        if self._current_image is None:
            return
        rows, cols = self._current_image.shape[:2]
        rect = self._roi_models[idx].rect
        pos = rect.pos()
        size = rect.size()
        x0 = int(np.clip(round(pos.x()), 0, max(cols - 1, 0)))
        y0 = int(np.clip(round(pos.y()), 0, max(rows - 1, 0)))
        size_x = int(np.clip(round(size.x()), 1, max(cols - x0, 1)))
        size_y = int(np.clip(round(size.y()), 1, max(rows - y0, 1)))
        rect.setPos((x0, y0), update=False, finish=False)
        rect.setSize((size_x, size_y), update=False, finish=False)
        self._write_roi(idx, x0, y0, size_x, size_y)

    def _on_set_roi_rectangle(self, x0: float, x1: float, y0: float, y1: float) -> None:
        if self._current_image is None:
            return
        if not (0 <= self._active_roi_idx < len(self._roi_models)):
            return
        rows, cols = self._current_image.shape[:2]
        left = int(np.clip(round(min(x0, x1)), 0, max(cols - 1, 0)))
        right = int(np.clip(round(max(x0, x1)), 0, max(cols - 1, 0)))
        top = int(np.clip(round(min(y0, y1)), 0, max(rows - 1, 0)))
        bottom = int(np.clip(round(max(y0, y1)), 0, max(rows - 1, 0)))
        size_x = max(1, right - left + 1)
        size_y = max(1, bottom - top + 1)

        model = self._roi_models[self._active_roi_idx]
        model.rect.setPos((left, top), update=False, finish=False)
        model.rect.setSize((size_x, size_y), update=False, finish=False)
        model.rect.setVisible(True)
        if self._active_roi_idx < len(self._roi_enable_checks):
            self._roi_enable_checks[self._active_roi_idx].setChecked(True)
        self._write_roi(self._active_roi_idx, left, top, size_x, size_y)
        self._exit_set_roi_mode()

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
        prefix = self._prefix_edit.text().strip()
        pva_suffix = self._pva_suffix_edit.text().strip()
        if not prefix or not pva_suffix:
            return
        self._prefix = prefix
        self._pva_suffix = pva_suffix
        channel = self._build_image_channel()
        self._provider.channel_name = channel
        self._provider.start()
        self._fps_last_time = time.monotonic()
        self._fps_frame_count = 0
        self._fps = 0.0
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._prefix_edit.setEnabled(False)
        self._pva_suffix_edit.setEnabled(False)
        self._display_timer.start()
        self._status_label.setText(f"Subscribed to {channel}")

    def _on_stop(self) -> None:
        self._provider.stop()
        self._display_timer.stop()
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._prefix_edit.setEnabled(True)
        self._pva_suffix_edit.setEnabled(True)
        self._connected = False
        self._indicator.set_connected(False)
        self._fps = 0.0
        self._fps_frame_count = 0
        self._update_hover_value()
        self._refresh_status_bar()

    # ------------------------------------------------------------------
    # Frame / disconnect handling
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_transform(image: np.ndarray, transform: str) -> np.ndarray:
        if transform == "rotate180":
            return image[::-1, ::-1, ...]
        return image

    def _orient_image(self, image: np.ndarray) -> np.ndarray:
        """Apply the configured data-space orientation transform."""
        transform = str(self._orientation["transform"])
        return self._apply_transform(image, transform)

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
        self._update_dtype_defaults(image.dtype)
        self._current_image = self._orient_image(image)
        image = self._current_image

        # Set image data on the ImageItem.
        # pyqtgraph doesn't natively handle all dtypes (e.g. int64, uint64),
        # so convert to float32 and provide explicit levels.
        if image.dtype != np.float32:
            display = image.astype(np.float32)
        else:
            display = image.copy()
        display = self._transform_for_scaling(display)
        if self._scale_mode == "manual":
            levels = self._manual_levels()
            if levels is None:
                levels = (float(np.min(display)), float(np.max(display)))
        else:
            levels = (float(np.min(display)), float(np.max(display)))
        if levels[0] >= levels[1]:
            levels = (levels[0], levels[0] + 1.0)
        self._image_item.setImage(display, levels=levels)
        self._apply_colormap()

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
        if self._roi_context is not None:
            self._roi_context.close()
            self._roi_context = None
        super().closeEvent(event)
