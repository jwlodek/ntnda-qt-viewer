"""Tests for the command-line entry point."""

from __future__ import annotations

import pytest
from pytest_mock import MockerFixture
from qtpy.QtCore import QCoreApplication


@pytest.mark.parametrize(
    ("cli_args", "expected"),
    [([], False), (["--preserve-aspect-ratio"], True)],
)
def test_main_preserve_aspect_ratio(
    mocker: MockerFixture,
    qapp: QCoreApplication,
    cli_args: list[str],
    expected: bool,
) -> None:
    from ntnda_qt_viewer import __main__ as cli

    # Abort via the ValueError -> parser.error path before the event loop runs.
    widget_cls = mocker.patch.object(
        cli, "NTNDAViewerWidget", side_effect=ValueError("stop")
    )
    mocker.patch("sys.argv", ["ntnda-qt-viewer", "DEV:", *cli_args])

    with pytest.raises(SystemExit):
        cli.main()

    assert widget_cls.call_args.kwargs["preserve_aspect_ratio"] is expected
