"""Interface for ``python -m napari_ntnd``."""

import sys
from argparse import ArgumentParser, BooleanOptionalAction

from qtpy.QtWidgets import QApplication

from . import __version__
from ._widget import NTNDAViewerWidget

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
    parser.add_argument(
        "--ntndarray",
        action=BooleanOptionalAction,
        default=True,
        help="Target is an NTNDArray (default). With --no-ntndarray, prefix is "
        "the full PV of a flat array and --image-shape is required",
    )
    parser.add_argument(
        "--image-shape",
        nargs=2,
        type=int,
        metavar=("ROWS", "COLS"),
        help="Image size for --no-ntndarray",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        help="Flat array is interleaved RGB (--no-ntndarray only)",
    )
    args = parser.parse_args()
    if not args.ntndarray and args.image_shape is None:
        parser.error("--image-shape is required with --no-ntndarray")
    if args.ntndarray and (args.image_shape or args.color):
        parser.error("--image-shape and --color require --no-ntndarray")

    app = QApplication.instance() or QApplication(sys.argv)
    widget = NTNDAViewerWidget(
        prefix=args.prefix,
        pva_suffix=args.pva_suffix,
        roi_suffixes=args.roi_suffixes,
        auto_resize_on_first_image=True,
        ntndarray=args.ntndarray,
        image_shape=tuple(args.image_shape) if args.image_shape else None,
        color=args.color,
    )
    widget.resize(1024, 768)
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
