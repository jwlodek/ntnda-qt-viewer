"""Lightweight Qt live image viewer for EPICS NTNDArray PVs (and plain waveform PVs).

Built on pyqtgraph and p4p.

Author: Jakub Wlodek
"""

import logging

from ._p4p import NTNDAProvider
from ._version import __version__
from ._widget import NTNDAViewerWidget

# The application decides where these records go; without a handler here,
# Python's lastResort printer writes every warning to stderr.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ["__version__", "NTNDAViewerWidget", "NTNDAProvider"]
