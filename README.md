# ntnda-qt-viewer

A lightweight Qt-based live image viewer for EPICS
[NTNDArray](https://docs.epics-controls.org/en/latest/specs/ntndarray.html)
PVs, built on [pyqtgraph](https://pyqtgraph.readthedocs.io/) and
[p4p](https://mdavidsaver.github.io/p4p/).

## Features

- Live streaming from any NTNDArray PVAccess channel
- Supports 8–64 bit signed/unsigned integers and 32/64-bit floats
- Draggable crosshair lines with linked horizontal and vertical pixel profile plots
- Scroll-wheel zoom, right-drag zoom-to-rectangle, double-click to reset
- Live pixel readout (x, y, value) under the cursor
- Connection status indicator and framerate display

## Installation

```bash
pip install ntnda-qt-viewer
```

A Qt backend is also required. Install one via the `gui` dependency group or
separately:

```bash
pip install PySide6
```

## Usage

Launch from the command line with an optional channel name:

```bash
ntnda-qt-viewer            # defaults to 13SIM1:Pva1:Image
ntnda-qt-viewer MY:PV:Name
```

Or embed the widget in your own Qt application:

```python
from ntnda_qt_viewer import NTNDViewerWidget

widget = NTNDViewerWidget(channel_name="MY:PV:Name")
widget.show()
```

## Development

This project uses [pixi](https://pixi.sh/) for environment management:

```bash
pixi install
pixi run lint
pixi run test
```

Environments for Python 3.11–3.14 are available (`py311`, `py312`, `py313`,
`py314`).

## License

BSD 3-Clause. See [LICENSE](LICENSE) for details.
