"""Interface for ``python -m napari_ntnd``."""

import sys
from argparse import ArgumentParser

from qtpy.QtWidgets import QApplication

from . import __version__
from ._widget import NTNDAViewerWidget

__all__ = ["main"]


def main() -> None:
    parser = ArgumentParser(description="Qt NTNDArray viewer")
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument(
        "prefix",
        help="Top-level PV prefix, or the full array PV with --raw-waveform",
    )
    parser.add_argument(
        "--pva-suffix",
        default="Pva1:",
        help="PVA plugin suffix used to form image PV as <prefix><pva-suffix>Image",
    )
    parser.add_argument(
        "--num-rois",
        type=int,
        default=4,
        help="Number of ROIs (default: %(default)s)",
    )
    parser.add_argument(
        "--roi-suffix-pattern",
        default="ROI{}:",
        help="Format string for ROI suffixes, given 1..N (default: %(default)s)",
    )
    parser.add_argument(
        "--raw-waveform",
        action="store_true",
        help="Target is a flat array instead of an NTNDArray; prefix is the full "
        "PV and --image-shape is required",
    )
    parser.add_argument(
        "--image-shape",
        nargs=2,
        type=int,
        metavar=("ROWS", "COLS"),
        help="Image size for --raw-waveform",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        help="Flat array is interleaved RGB (--raw-waveform only)",
    )
    args = parser.parse_args()
    if args.raw_waveform and args.image_shape is None:
        parser.error("--image-shape is required with --raw-waveform")
    if not args.raw_waveform and (args.image_shape or args.color):
        parser.error("--image-shape and --color require --raw-waveform")

    app = QApplication.instance() or QApplication(sys.argv)
    widget = NTNDAViewerWidget(
        prefix=args.prefix,
        pva_suffix=args.pva_suffix,
        num_rois=args.num_rois,
        roi_suffix_pattern=args.roi_suffix_pattern,
        auto_resize_on_first_image=True,
        raw_waveform=args.raw_waveform,
        image_shape=tuple(args.image_shape) if args.image_shape else None,
        color=args.color,
    )
    widget.resize(1024, 768)
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
