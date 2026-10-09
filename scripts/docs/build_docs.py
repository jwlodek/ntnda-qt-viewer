"""Build the documentation site.

Regenerates the API reference with npdoc2md, then builds (or serves) the site
with Zensical. Run from anywhere:

    uv run --group docs python scripts/docs/build_docs.py            # build site/
    uv run --group docs python scripts/docs/build_docs.py --serve    # live preview
    uv run --group docs python scripts/docs/build_docs.py --screenshots
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
API_DIR = DOCS / "api"
# The public classes live in these private modules, so whitelist them.
API_MODULES = ("_widget.py", "_p4p.py")
_ANCHOR = re.compile(r"\]\(#([^)]+)\)")


def _run(*args: str) -> None:
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    subprocess.run([sys.executable, *args], cwd=ROOT, env=env, check=True)


def generate_api_docs() -> None:
    shutil.rmtree(API_DIR, ignore_errors=True)
    _run(
        "-m",
        "npdoc2md",
        "--quiet",
        str(ROOT / "src" / "ntnda_qt_viewer"),
        str(API_DIR),
        "--private-whitelist",
        *API_MODULES,
    )
    # npdoc2md links keep the heading case, but Zensical and GitHub lowercase ids.
    for page in API_DIR.glob("*.md"):
        text = page.read_text()
        page.write_text(_ANCHOR.sub(lambda m: f"](#{m.group(1).lower()})", text))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the documentation site.")
    parser.add_argument(
        "--serve", action="store_true", help="Serve with live reload instead"
    )
    parser.add_argument(
        "--screenshots", action="store_true", help="Regenerate the screenshots first"
    )
    args = parser.parse_args()

    if args.screenshots:
        _run(str(ROOT / "scripts" / "docs" / "generate_screenshots.py"))
    generate_api_docs()
    if args.serve:
        _run("-m", "zensical", "serve")
    else:
        _run("-m", "zensical", "build", "--clean", "--strict")


if __name__ == "__main__":
    main()
