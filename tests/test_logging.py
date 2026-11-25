"""The library logs; whether its records are shown is the application's choice."""

import os
import subprocess
import sys


# Before the NullHandler, Python's lastResort handler printed every warning
# (e.g. "Channel ... disconnected") to stderr in apps that configure no logging.
def test_warnings_are_not_printed_when_the_app_configures_no_logging():
    code = (
        "import logging, ntnda_qt_viewer\n"
        "logging.getLogger('ntnda_qt_viewer._p4p').warning('Channel X disconnected')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stderr == ""


def _run_standalone(*cli_args: str) -> str:
    """Run main() with a fake widget that logs at each level; return stderr."""
    # The fake widget aborts startup via the ValueError -> parser.error path so
    # no Qt event loop is entered.
    code = (
        "import logging, sys\n"
        "import ntnda_qt_viewer.__main__ as m\n"
        "def fake_widget(**kwargs):\n"
        "    log = logging.getLogger('ntnda_qt_viewer._p4p')\n"
        "    log.debug('debug message')\n"
        "    log.info('info message')\n"
        "    log.warning('Channel X disconnected')\n"
        "    raise ValueError('stop')\n"
        "m.NTNDAViewerWidget = fake_widget\n"
        f"sys.argv = ['ntnda-qt-viewer', 'DEV:', *{list(cli_args)!r}]\n"
        "m.main()\n"
    )
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    return result.stderr


def test_standalone_viewer_prints_warnings_by_default():
    stderr = _run_standalone()
    assert "WARNING ntnda_qt_viewer._p4p: Channel X disconnected" in stderr
    assert "info message" not in stderr
    assert "debug message" not in stderr


def test_standalone_viewer_log_level_argument():
    stderr = _run_standalone("--log-level", "debug")
    assert "DEBUG ntnda_qt_viewer._p4p: debug message" in stderr
    assert "INFO ntnda_qt_viewer._p4p: info message" in stderr
