# ntnda_qt_viewer
Lightweight Qt live image viewer for EPICS NTNDArray PVs (and plain waveform PVs), built on pyqtgraph and p4p.
## Classes
Classe | Description
--- | ---
[NTNDAProvider](#NTNDAProvider) | Subscribes to an image PV and emits frames as numpy arrays.
[NTNDAViewerWidget](#NTNDAViewerWidget) | Live image viewer for EPICS NTNDArray (or flat waveform) PVs.

## NTNDAProvider
```Python
class NTNDAProvider(QObject)
```
Subscribes to an image PV and emits frames as numpy arrays.

The monitor callback runs in a worker thread; frames are forwarded to the
Qt main thread through the ``new_frame`` signal.
### Attributes
Attribute | Type | Optional | Default | Description
--- | --- | --- | --- | ---
channel_name | str | True | None | Full name of the PV to monitor.
raw_waveform | bool | True | None | Treat the PV as a flat array instead of an NTNDArray. Requires ``image_shape``. Default ``False``.
image_shape | tuple of int or None | True | None | ``(rows, cols)`` used to reshape flat arrays.
color | bool | True | None | Flat arrays are interleaved RGB. Default ``False``.
use_ca | bool | True | None | Monitor over Channel Access instead of PVAccess. Only valid with ``raw_waveform=True``. Default ``False``.
### Raises
Error | Description
--- | ---
ValueError | If ``raw_waveform`` is set without ``image_shape``, or ``use_ca`` is set without ``raw_waveform``.
### Methods
Method | Description
--- | ---
[__init__](#__init__) | Description for __init__()
[start](#start) | Start monitoring the NTNDArray PV.
[stop](#stop) | Stop monitoring and clean up.

### __init__
```Python
def __init__(self, channel_name: 'str' = 'DEV:XSPD1:Pva1:Image', *, raw_waveform: 'bool' = False, image_shape: 'tuple[int, int] | None' = None, color: 'bool' = False, use_ca: 'bool' = False) -> 'None'
```
Description for __init__()

### start
```Python
def start(self) -> 'None'
```
Start monitoring the NTNDArray PV.

### stop
```Python
def stop(self) -> 'None'
```
Stop monitoring and clean up.

## NTNDAViewerWidget
```Python
class NTNDAViewerWidget(QWidget)
```
Live image viewer for EPICS NTNDArray (or flat waveform) PVs.

Shows the image with draggable crosshair lines, linked horizontal and
vertical pixel profile plots, ROI overlays backed by areaDetector ROI
plugin PVs, and a settings menu for scaling, colormap and layout.
### Attributes
Attribute | Type | Optional | Default | Description
--- | --- | --- | --- | ---
prefix | str | False | N/A | Top-level PV prefix, e.g. ``"DEV:XSPD1:"``. With ``raw_waveform=True`` this is the full array PV name. ROI PVs are always ``<prefix><roi suffix>{MinX,MinY,SizeX,SizeY}``.
pva_suffix | str | True | None | PVA plugin suffix; the image PV is ``<prefix><pva_suffix>Image``. Ignored when ``raw_waveform=True``. Default ``"Pva1:"``.
auto_resize_on_first_image | bool | True | None | Resize the widget to fit the first received frame. Useful for stand-alone windows, usually off when embedded. Default ``False``.
parent | QWidget or None | True | None | Qt parent widget.
colormap | {"Grayscale", "JET"} or None | True | None | Initial colormap for mono images. ``None`` means Grayscale. Ignored (with a logged warning if set) for color images.
show_profile_lines | bool | True | None | Show the crosshair lines on the image. Default ``False``.
show_roi_controls | bool | True | None | Show the ROI controls bar under the image. Default ``True``.
v_profile_position | {"left", "right"} | True | None | Side of the image for the vertical profile plot. Default ``"left"``.
h_profile_position | {"top", "bottom"} | True | None | Side of the image for the horizontal profile plot. Default ``"bottom"``.
use_opengl | bool | True | None | Render the plots with an OpenGL viewport. On some Linux setups this stops popup menus from painting. Default ``False``.
raw_waveform | bool | True | None | Treat the PV as a flat array instead of an NTNDArray. Requires ``image_shape``. Default ``False``.
image_shape | tuple of int or None | True | None | ``(rows, cols)`` used to reshape the flat array. Only valid with ``raw_waveform=True``.
color | bool | True | None | The flat array is interleaved RGB. Only valid with ``raw_waveform=True``. Default ``False``.
use_ca | bool | True | None | Connect over Channel Access instead of PVAccess. Only valid with ``raw_waveform=True``. Default ``False``.
num_rois | int | True | None | Number of ROIs. Default ``4``.
roi_suffix_pattern | str | True | None | Format string producing ROI suffixes for ``1..num_rois``. Default ``"ROI{}:"``.
scale_min, scale_max | float or None | True | None | Start in manual scaling over this range. Must be passed together.
log_scale | bool | True | None | Start with log intensity scaling. Default ``False``.
auto_scale_method | {"percentile", "sigma", "minmax"} | True | None | How levels are chosen in auto scaling. Default ``"percentile"``.
auto_scale_percentiles | tuple of float | True | None | Low and high clip percentiles for ``"percentile"``. Default ``(0.1, 99.9)``.
auto_scale_n_sigma | float | True | None | N for ``"sigma"``: median +/- N robust standard deviations. Default ``3.0``.
### Raises
Error | Description
--- | ---
ValueError | If an option is out of range or options are combined invalidly.
### Methods
Method | Description
--- | ---
[__init__](#__init__) | Description for __init__()
[start](#start) | Subscribe to the image PV and start updating the display.
[stop](#stop) | Unsubscribe from the image PV and stop updating the display.
[closeEvent](#closeEvent) | Stop the image monitor and close the ROI PV context.

### __init__
```Python
def __init__(self, prefix: 'str', pva_suffix: 'str' = 'Pva1:', auto_resize_on_first_image: 'bool' = False, parent: 'QWidget | None' = None, *, colormap: 'str | None' = None, show_profile_lines: 'bool' = False, show_roi_controls: 'bool' = True, v_profile_position: 'str' = 'left', h_profile_position: 'str' = 'bottom', use_opengl: 'bool' = False, raw_waveform: 'bool' = False, image_shape: 'tuple[int, int] | None' = None, color: 'bool' = False, use_ca: 'bool' = False, num_rois: 'int' = 4, roi_suffix_pattern: 'str' = 'ROI{}:', scale_min: 'float | None' = None, scale_max: 'float | None' = None, log_scale: 'bool' = False, auto_scale_method: 'str' = 'percentile', auto_scale_percentiles: 'tuple[float, float]' = (0.1, 99.9), auto_scale_n_sigma: 'float' = 3.0) -> 'None'
```
Description for __init__()

### start
```Python
def start(self) -> 'None'
```
Subscribe to the image PV and start updating the display.

Uses the prefix currently in the prefix field. Does nothing if the
prefix (or, for NTNDArrays, the PVA suffix) is empty. Equivalent to
pressing **Start**.

### stop
```Python
def stop(self) -> 'None'
```
Unsubscribe from the image PV and stop updating the display.

Safe to call when not running. Equivalent to pressing **Stop**.

### closeEvent
```Python
def closeEvent(self, event: 'QCloseEvent') -> 'None'
```
Stop the image monitor and close the ROI PV context.
