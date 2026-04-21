#!/usr/bin/env python3
"""Entry point for the ``refresh-knowledge`` skill.

Thin wrapper around :mod:`polygon_frp.github_ingest` so Claude Code can invoke
it without knowing the internal module path. Forwards all CLI args unchanged
and exits with the library's exit code.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src/ tree is importable when run directly (outside ``uv run``).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from polygon_frp.github_ingest import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
