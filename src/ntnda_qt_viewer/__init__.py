"""Lightweight Qt live image viewer for EPICS NTNDArray PVs (and plain waveform PVs), built on pyqtgraph and p4p.
"""

from ._version import __version__
from ._widget import NTNDAViewerWidget
from ._p4p import NTNDAProvider

__all__ = ["__version__", "NTNDAViewerWidget", "NTNDAProvider"]
