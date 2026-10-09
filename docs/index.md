# ntnda-qt-viewer documentation

A lightweight Qt live image viewer for EPICS
[NTNDArray](https://docs.epics-controls.org/en/latest/specs/ntndarray.html)
PVs (and plain waveform PVs), built on pyqtgraph and p4p.

![Viewer overview](images/main_window.png)

## Contents

- [Usage](usage.md): launching the viewer, the window layout, mouse controls,
  ROIs, scaling and the settings menu.
- [Embedding](embedding.md): using `NTNDAViewerWidget` inside your own Qt
  application.
- API reference (generated with npdoc2md):
  - [`NTNDAViewerWidget`](api/ntnda_qt_viewer.md#ntndaviewerwidget)
  - [`NTNDAProvider`](api/ntnda_qt_viewer.md#ntndaprovider)

The site is published to GitHub Pages from `main` by the `Docs` workflow.

## Building the docs locally

```bash
uv run npdoc2md src/ntnda_qt_viewer docs/api
uv run zensical build
uv run zensical serve
```

The build regenerates the API reference from the numpydoc docstrings with
[npdoc2md](https://github.com/jwlodek/npdoc2md) (main branch), then runs
[Zensical](https://zensical.org/). Add `--screenshots` to also re-render the screenshots, which are drawn
offscreen from a synthetic image, so no IOC is needed.
