"""The library logs; whether its records are shown is the application's choice."""

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
