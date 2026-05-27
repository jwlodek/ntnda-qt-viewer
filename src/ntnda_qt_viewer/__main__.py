"""Interface for ``python -m napari_ntnd``."""

import sys
from argparse import ArgumentParser

from qtpy.QtWidgets import QApplication

from . import __version__
from ._widget import NTNDViewerWidget

__all__ = ["main"]


def main() -> None:
    parser = ArgumentParser(description="Qt NTNDArray viewer")
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "prefix",
        nargs="?",
        default="DEV:XSPD1:",
        help="Top-level PV prefix (default: %(default)s)",
    )
    parser.add_argument(
        "--pva-suffix",
        default="Pva1:",
        help="PVA plugin suffix used to form image PV as <prefix><pva-suffix>Image",
    )
    parser.add_argument(
        "--roi-suffixes",
        nargs="*",
        default=["ROI1:", "ROI2:", "ROI3:", "ROI4:"],
        help="ROI plugin suffixes (default: %(default)s)",
    )
    args = parser.parse_args()

    app = QApplication.instance() or QApplication(sys.argv)
    widget = NTNDViewerWidget(
        prefix=args.prefix,
        pva_suffix=args.pva_suffix,
        roi_suffixes=args.roi_suffixes,
    )
    widget.resize(1024, 768)
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
