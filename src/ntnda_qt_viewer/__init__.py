"""Lightweight Qt live image viewer for EPICS NTNDArray PVs (and plain waveform PVs).

Built on pyqtgraph and p4p.

Author: Jakub Wlodek
"""

from ._p4p import NTNDAProvider
from ._version import __version__
from ._widget import NTNDAViewerWidget

__all__ = ["__version__", "NTNDAViewerWidget", "NTNDAProvider"]
