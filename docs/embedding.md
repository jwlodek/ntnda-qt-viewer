# Embedding the viewer

`NTNDAViewerWidget` is a regular `QWidget`, so it can go anywhere a widget
can: a layout, a tab, a dock or a splitter. Your application owns the
`QApplication`; the viewer never creates one.

## Minimal example

```python
import sys

from qtpy.QtWidgets import QApplication

from ntnda_qt_viewer import NTNDAViewerWidget

app = QApplication(sys.argv)
viewer = NTNDAViewerWidget("DEV:XSPD1:", pva_suffix="Pva1:")
viewer.resize(1000, 800)
viewer.show()
viewer.start()
sys.exit(app.exec())
```

`viewer.start()` and `viewer.stop()` do the same as the **Start** and
**Stop** buttons, so your application can control streaming directly.

## In a layout next to other widgets

```python
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget

from ntnda_qt_viewer import NTNDAViewerWidget


class BeamlinePanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Motor controls go here"))
        self.viewer = NTNDAViewerWidget(
            "DEV:XSPD1:",
            parent=self,
            show_roi_controls=False,
            v_profile_position="right",
        )
        layout.addWidget(self.viewer, stretch=1)
```

## In a dock or tab of a main window

```python
from qtpy.QtCore import Qt
from qtpy.QtGui import QCloseEvent
from qtpy.QtWidgets import QDockWidget, QMainWindow, QTabWidget

from ntnda_qt_viewer import NTNDAViewerWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        tabs = QTabWidget()
        self.camera_a = NTNDAViewerWidget("DEV:CAM1:", colormap="JET")
        self.camera_b = NTNDAViewerWidget("DEV:CAM2:", num_rois=2)
        tabs.addTab(self.camera_a, "Camera 1")
        tabs.addTab(self.camera_b, "Camera 2")
        self.setCentralWidget(tabs)

        dock = QDockWidget("Waveform", self)
        self.waveform = NTNDAViewerWidget(
            "DEV:SCOPE:Trace",
            raw_waveform=True,
            image_shape=(256, 1024),
            num_rois=0,
            show_roi_controls=False,
        )
        dock.setWidget(self.waveform)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def closeEvent(self, event: QCloseEvent) -> None:
        # Child widgets don't get closeEvent when the window closes.
        for viewer in (self.camera_a, self.camera_b, self.waveform):
            viewer.close()
        super().closeEvent(event)
```

## Things to know when embedding

- **Start and stop from code.** `start()` subscribes using the prefix in the
  prefix field and does nothing if it is empty; `stop()` is safe to call
  when not running.
- **Shut down cleanly.** Closing the viewer stops its PV monitor and closes
  its ROI PV context. Qt only sends `closeEvent` to top-level windows, so
  call `viewer.close()` from your own window's `closeEvent` as above.
- **Sizing.** `auto_resize_on_first_image` is off by default, which suits
  embedding: the viewer fills whatever space the layout gives it. Turn it on
  only for stand-alone windows.
- **No global pyqtgraph settings.** The viewer configures its own plots and
  does not call `pyqtgraph.setConfigOptions`, so it won't change other
  pyqtgraph widgets in your application.
- **OpenGL is off by default.** `use_opengl=True` can stop popup menus from
  painting on some Linux setups; leave it off unless you need it.
- **Hide what you don't need.** `show_roi_controls=False` and `num_rois=0`
  give a plain image and profile viewer; `show_profile_lines=False` (the
  default) hides the crosshair.
- **Invalid options raise `ValueError`** at construction, for example
  `image_shape` without `raw_waveform=True`, or only one of `scale_min` and
  `scale_max`.

## Constructor options

| Argument | Default | Description |
| --- | --- | --- |
| `prefix` | required | PV prefix, or the full array PV with `raw_waveform=True`. |
| `pva_suffix` | `"Pva1:"` | PVA plugin suffix for the image PV. |
| `auto_resize_on_first_image` | `False` | Resize to fit the first frame. |
| `parent` | `None` | Qt parent widget. |
| `colormap` | `None` | `"Grayscale"` or `"JET"`; `None` means Grayscale. |
| `show_profile_lines` | `False` | Show the crosshair lines. |
| `show_roi_controls` | `True` | Show the ROI controls bar. |
| `v_profile_position` | `"left"` | `"left"` or `"right"`. |
| `h_profile_position` | `"bottom"` | `"top"` or `"bottom"`. |
| `use_opengl` | `False` | Use an OpenGL viewport for the plots. |
| `raw_waveform` | `False` | Treat the PV as a flat array. |
| `image_shape` | `None` | `(rows, cols)` for raw waveforms. |
| `color` | `False` | Raw waveform is interleaved RGB. |
| `use_ca` | `False` | Use Channel Access for the raw waveform. |
| `num_rois` | `4` | Number of ROIs. |
| `roi_suffix_pattern` | `"ROI{}:"` | Format string for ROI suffixes. |
| `scale_min`, `scale_max` | `None` | Start in manual scaling over this range. |
| `log_scale` | `False` | Start with log scaling. |
| `auto_scale_method` | `"percentile"` | `"percentile"`, `"sigma"` or `"minmax"`. |
| `auto_scale_percentiles` | `(0.1, 99.9)` | Clip percentiles for percentile scaling. |
| `auto_scale_n_sigma` | `3.0` | N for sigma scaling. |

Arguments after `parent` are keyword-only. See the
[API reference](api/ntnda_qt_viewer.md#ntndaviewerwidget) for full descriptions.
