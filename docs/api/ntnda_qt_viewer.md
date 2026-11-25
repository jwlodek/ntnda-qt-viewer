# ntnda_qt_viewer
Lightweight Qt live image viewer for EPICS NTNDArray PVs (and plain waveform PVs).

Built on pyqtgraph and p4p.

Author: Jakub Wlodek
## Classes
Classe | Description
--- | ---
[NTNDAProvider](#ntndaprovider) | Subscribes to an image PV and emits frames as numpy arrays.
[NTNDAViewerWidget](#ntndaviewerwidget) | Live image viewer for EPICS NTNDArray (or flat waveform) PVs.
[ViewerColors](#viewercolors) | Colors of the viewer's plot elements.

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
[start](#start) | Start monitoring the NTNDArray PV.
[stop](#stop) | Stop monitoring and clean up.

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
preserve_aspect_ratio | bool | True | None | Keep square image pixels on resize, filling leftover space with the background color. The profile plots stay attached to the image edges. Default ``False``.
colors | ViewerColors or None | True | None | Colors of the background, profile plots, profile lines and ROIs. ``None`` uses the :class:`ViewerColors` defaults. Can be changed later with :meth:`set_colors` or from the Settings menu.
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
push_frame | callable or None | True | None | Registration function called once with :meth:`push_frame`, e.g. ``camera.subscribe``. When given (callback mode) the viewer never talks to CA/PVA: frames come only from the hook and ROIs are kept in memory. Default ``None`` reads frames and ROIs from PVs.
### Raises
Error | Description
--- | ---
ValueError | If an option is out of range or options are combined invalidly.
### Methods
Method | Description
--- | ---
[set_colors](#set_colors) | Recolor the background, profile plots, profile lines and ROIs.
[start](#start) | Subscribe to the image PV and start updating the display.
[stop](#stop) | Unsubscribe from the image PV and stop updating the display.
[push_frame](#push_frame) | Display ``image`` directly, bypassing CA and PVA.
[add_click_hook](#add_click_hook) | Call ``hook(x, y)`` whenever the image is left-clicked.
[remove_click_hook](#remove_click_hook) | Remove a hook added with :meth:`add_click_hook`.
[closeEvent](#closeevent) | Stop the image monitor and close the ROI PV context.

### set_colors
```Python
def set_colors(self, colors: 'ViewerColors') -> 'None'
```
Recolor the background, profile plots, profile lines and ROIs.

#### Parameters
Parameter | Type | Optional | Default | Description
--- | --- | --- | --- | ---
colors | ViewerColors | False | N/A | The new colors. Equivalent to accepting the **Colors...** dialog.

### start
```Python
def start(self) -> 'None'
```
Subscribe to the image PV and start updating the display.

Uses the prefix currently in the prefix field. Does nothing if the
prefix (or, for NTNDArrays, the PVA suffix) is empty. In callback
mode (``push_frame`` given) only frames from :meth:`push_frame` are
accepted. Equivalent to pressing **Start**.

### stop
```Python
def stop(self) -> 'None'
```
Unsubscribe from the image PV and stop updating the display.

Safe to call when not running. Equivalent to pressing **Stop**.

### push_frame
```Python
def push_frame(self, image: 'np.ndarray') -> 'None'
```
Display ``image`` directly, bypassing CA and PVA.

Intended to be registered as a hook/callback with an in-process data
source. Safe to call from any thread; the frame is copied and shown
on the Qt main thread, subject to the max framerate. Frames are
dropped while the viewer is stopped.
#### Parameters
Parameter | Type | Optional | Default | Description
--- | --- | --- | --- | ---
image | numpy.ndarray | False | N/A | ``(rows, cols)`` mono or ``(rows, cols, 3)`` RGB image.
#### Raises
Error | Description
--- | ---
ValueError | If ``image`` does not have a supported shape.

### add_click_hook
```Python
def add_click_hook(self, hook: 'Callable[[int, int], object]') -> 'None'
```
Call ``hook(x, y)`` whenever the image is left-clicked.

``x`` and ``y`` are the integer pixel column and row of the click,
with (0, 0) at the top-left pixel. Clicks outside the image, on ROIs
or crosshair lines, or before the first frame are ignored. Hooks run
on the Qt main thread.

### remove_click_hook
```Python
def remove_click_hook(self, hook: 'Callable[[int, int], object]') -> 'None'
```
Remove a hook added with :meth:`add_click_hook`.

### closeEvent
```Python
def closeEvent(self, event: 'QCloseEvent') -> 'None'
```
Stop the image monitor and close the ROI PV context.

## ViewerColors
```Python
class ViewerColors(object)
```
Colors of the viewer's plot elements.

Each color is any name :class:`QColor` accepts, such as ``"#1e1e1e"`` or
``"white"``.
### Attributes
Attribute | Type | Optional | Default | Description
--- | --- | --- | --- | ---
background | str | True | None | Background of the image and profile plot area. Default ``"#000000"``.
axes | str | True | None | Profile plot axis lines, ticks, tick labels and titles. Default ``"#969696"``.
profile_curves | str | True | None | Horizontal and vertical profile curves. Default ``"#00ffff"``.
profile_lines | str | True | None | Crosshair (profile) lines drawn on the image. Default ``"#ffff00"``.
roi | sequence of str | True | green | Colors of the first ROIs' outlines and labels, in order. ROIs beyond these get generated colors with hues as far as possible from those already in use; generation is deterministic, so a given ROI always gets the same color. An empty sequence generates every ROI's color. Hovered outlines use a lighter shade. Default green, yellow, cyan and pink.
### Raises
Error | Description
--- | ---
ValueError | If a color name is invalid.
### Methods
Method | Description
--- | ---
[roi_color](#roi_color) | Return the color for the ROI at zero-based index ``idx``.

### roi_color
```Python
def roi_color(self, idx: 'int') -> 'str'
```
Return the color for the ROI at zero-based index ``idx``.
