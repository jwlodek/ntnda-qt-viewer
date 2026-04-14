"""Interface for ``python -m napari_ntnd``."""

import sys
from argparse import ArgumentParser

from qtpy.QtWidgets import QApplication

from . import __version__
from ._widget import NTNDViewerWidget

__all__ = ["main"]


def main() -> None:
    parser = ArgumentParser(description="napari NTNDArray viewer")
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "channel",
        nargs="?",
        default="13SIM1:Pva1:Image",
        help="NTNDArray PV channel name (default: %(default)s)",
    )
    args = parser.parse_args()

    app = QApplication.instance() or QApplication(sys.argv)
    widget = NTNDViewerWidget(channel_name=args.channel)
    widget.resize(1024, 768)
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
