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
    parser.add_argument(
        "--ca",
        action="store_true",
        help="Connect to the array PV over Channel Access (--raw-waveform only)",
    )
    parser.add_argument(
        "--scale",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Start with manual scaling over this range (default: auto)",
    )
    parser.add_argument(
        "--log-scale",
        action="store_true",
        help="Start with log intensity scaling enabled",
    )
    parser.add_argument(
        "--auto-scale",
        choices=("percentile", "sigma", "minmax"),
        default="percentile",
        help="Auto scaling method (default: %(default)s)",
    )
    parser.add_argument(
        "--percentiles",
        nargs=2,
        type=float,
        default=(0.1, 99.9),
        metavar=("LOW", "HIGH"),
        help="Clip percentiles for --auto-scale percentile (default: 0.1 99.9)",
    )
    parser.add_argument(
        "--n-sigma",
        type=float,
        default=3.0,
        help="N for --auto-scale sigma, median +/- N robust sigma "
        "(default: %(default)s)",
    )
    args = parser.parse_args()
    if args.raw_waveform and args.image_shape is None:
        parser.error("--image-shape is required with --raw-waveform")
    if not args.raw_waveform and (args.image_shape or args.color or args.ca):
        parser.error("--image-shape, --color and --ca require --raw-waveform")
    if args.scale and args.scale[0] >= args.scale[1]:
        parser.error("--scale MIN must be less than MAX")

    app = QApplication.instance() or QApplication(sys.argv)
    try:
        widget = NTNDAViewerWidget(
            prefix=args.prefix,
            pva_suffix=args.pva_suffix,
            num_rois=args.num_rois,
            roi_suffix_pattern=args.roi_suffix_pattern,
            auto_resize_on_first_image=True,
            raw_waveform=args.raw_waveform,
            image_shape=tuple(args.image_shape) if args.image_shape else None,
            color=args.color,
            scale_min=args.scale[0] if args.scale else None,
            scale_max=args.scale[1] if args.scale else None,
            use_ca=args.ca,
            log_scale=args.log_scale,
            auto_scale_method=args.auto_scale,
            auto_scale_percentiles=tuple(args.percentiles),
            auto_scale_n_sigma=args.n_sigma,
        )
    except ValueError as exc:
        parser.error(str(exc))
    widget.resize(1024, 768)
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
