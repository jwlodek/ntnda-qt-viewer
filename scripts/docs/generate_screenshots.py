"""Render annotated documentation screenshots of the viewer without a live IOC.

Run from the repository root:

    QT_QPA_PLATFORM=offscreen uv run python scripts/docs/generate_screenshots.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from qtpy.QtCore import QPoint, QPointF, QRect, Qt
from qtpy.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from qtpy.QtWidgets import QApplication, QDialog, QWidget

from ntnda_qt_viewer import NTNDAViewerWidget

IMAGES = Path(__file__).resolve().parents[2] / "docs" / "images"
ROWS, COLS = 480, 640


def synthetic_image() -> np.ndarray:
    """Gaussian spots on a noisy background, as uint16."""
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[0:ROWS, 0:COLS]
    image = rng.normal(200.0, 20.0, (ROWS, COLS))
    for cy, cx, sigma, amp in (
        (180, 260, 40.0, 3000.0),
        (320, 450, 25.0, 1800.0),
        (120, 520, 15.0, 1200.0),
    ):
        image += amp * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * sigma**2))
    return np.clip(image, 0, 65535).astype(np.uint16)


def build_viewer(**kwargs: object) -> NTNDAViewerWidget:
    viewer = NTNDAViewerWidget(
        "DEV:XSPD1:",
        show_profile_lines=True,
        **kwargs,  # type: ignore
    )
    viewer.resize(1100, 820)
    viewer.show()
    viewer._pending_image = synthetic_image()
    viewer._refresh_display()
    viewer._indicator.set_connected(True)
    viewer._h_image_line.setValue(ROWS - 180)
    viewer._v_image_line.setValue(COLS - 260)
    viewer._hover_x, viewer._hover_y = 380, 300
    viewer._update_hover_value()
    viewer._refresh_status_bar()
    show_roi(viewer)
    QApplication.processEvents()
    return viewer


def show_roi(viewer: NTNDAViewerWidget) -> None:
    viewer._show_roi_labels_action.setChecked(True)
    model = viewer._roi_models[0]
    model.rect.setPos((330, 220), update=False, finish=False)
    model.rect.setSize((140, 120), update=False, finish=False)
    model.visible = True
    model.rect.setVisible(True)
    if model.label is not None:
        model.label.setVisible(True)
    viewer._update_roi_label_position(0)
    viewer._set_roi_checkbox(0, True, block_signal=True)


def widget_rect(viewer: NTNDAViewerWidget, child: QWidget) -> QRect:
    return QRect(child.mapTo(viewer, QPoint(0, 0)), child.size())


def plot_rect(viewer: NTNDAViewerWidget, item: object) -> QRect:
    scene_rect = item.sceneBoundingRect()  # type: ignore
    view_rect = viewer._glw.mapFromScene(scene_rect).boundingRect()
    return view_rect.translated(viewer._glw.mapTo(viewer, QPoint(0, 0)))


def annotate(pixmap: QPixmap, marks: list[tuple[int, QRect, bool]]) -> QPixmap:
    """Outline each rect and add a numbered badge outside a left corner.

    Each mark is ``(number, rect, below)``; ``below`` puts the badge at the
    bottom-left corner instead of the top-left one.
    """
    pad = 32
    canvas = QPixmap(pixmap.width() + 2 * pad, pixmap.height() + 2 * pad)
    canvas.fill(QColor("white"))
    painter = QPainter(canvas)
    painter.drawPixmap(pad, pad, pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setBold(True)
    font.setPointSize(11)
    painter.setFont(font)
    accent = QColor("#ff2d55")
    for number, rect, below in marks:
        rect = rect.translated(pad, pad)
        painter.setPen(QPen(accent, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), 6, 6)
        corner_y = rect.bottom() + 14 if below else rect.top() - 14
        center = QPointF(rect.left() - 14, corner_y)
        painter.setBrush(accent)
        painter.setPen(QPen(QColor("white"), 2))
        painter.drawEllipse(center, 13, 13)
        painter.drawText(
            QRect(int(center.x()) - 13, int(center.y()) - 13, 26, 26),
            Qt.AlignmentFlag.AlignCenter,
            str(number),
        )
    painter.end()
    return canvas


def save(pixmap: QPixmap, name: str) -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    path = IMAGES / name
    pixmap.save(str(path))
    print(f"wrote {path}")


def main_window_screenshot() -> None:
    viewer = build_viewer()
    start_stop = widget_rect(viewer, viewer._start_btn).united(
        widget_rect(viewer, viewer._stop_btn)
    )
    marks = [
        (1, widget_rect(viewer, viewer._indicator), False),
        (2, widget_rect(viewer, viewer._prefix_edit), False),
        (3, widget_rect(viewer, viewer._settings_btn), False),
        (4, start_stop, False),
        (5, plot_rect(viewer, viewer._image_plot), False),
        (6, plot_rect(viewer, viewer._v_profile_plot), True),
        (7, plot_rect(viewer, viewer._h_profile_plot), False),
        (8, widget_rect(viewer, viewer._roi_controls_widget), False),
        (9, widget_rect(viewer, viewer._status_label), True),
    ]
    save(annotate(viewer.grab(), marks), "main_window.png")
    viewer.close()


def alternate_layout_screenshot() -> None:
    viewer = build_viewer(
        colormap="JET", v_profile_position="right", h_profile_position="top"
    )
    save(viewer.grab(), "alternate_layout.png")
    viewer.close()


def settings_menu_screenshot() -> None:
    viewer = build_viewer()
    menu = viewer._settings_btn.menu()
    if menu is not None:
        menu.adjustSize()
        menu.show()
        QApplication.processEvents()
        save(menu.grab(), "settings_menu.png")
        menu.hide()
    viewer.close()


def dialog_screenshots() -> None:
    """Open each dialog with exec() patched to grab instead of blocking."""
    viewer = build_viewer()
    pending: list[str] = []

    def grab_instead_of_exec(dialog: QDialog) -> int:
        dialog.adjustSize()
        dialog.show()
        QApplication.processEvents()
        save(dialog.grab(), pending.pop(0))
        dialog.hide()
        return int(QDialog.DialogCode.Rejected)

    original_exec = QDialog.exec
    QDialog.exec = grab_instead_of_exec  # type: ignore
    try:
        pending.append("scaling_dialog.png")
        viewer._open_scaling_dialog()
        pending.append("roi_management_dialog.png")
        viewer._open_roi_management_dialog()
    finally:
        QDialog.exec = original_exec
    viewer.close()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    main_window_screenshot()
    alternate_layout_screenshot()
    settings_menu_screenshot()
    dialog_screenshots()
    app.processEvents()


if __name__ == "__main__":
    main()
