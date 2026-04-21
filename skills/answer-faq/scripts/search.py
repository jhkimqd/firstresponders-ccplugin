#!/usr/bin/env python3
"""Entry point for the `answer-faq` skill.

Usage:
    uv run python skills/answer-faq/scripts/search.py "<query>" [--k N] [--docs-dir PATH]

Prints a JSON array of hits to stdout. Each hit is:
    {"source": "<relative path under data/docs/>", "text": "...", "score": 0.42}

The heavy lifting lives in ``polygon_frp.docs_index`` (owned by Agent A). This script
is a thin CLI wrapper so Claude Code skills stay language-agnostic and cite a stable
public entry point.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the repo's src/ layout importable without requiring `uv pip install -e .` to have
# run first (helpful during development and CI bootstrap).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from polygon_frp import docs_index  # noqa: E402


def _default_docs_dir() -> Path:
    return _REPO_ROOT / "data" / "docs"


def _build_index(docs_dir: Path):
    """Build a searchable index using whichever public API docs_index exposes.

    The module's final shape is coordinated with Agent A (see SPEC §5.7). We accept
    both plausible signatures so this script stays robust across small API tweaks:

    - ``docs_index.build_index(docs_dir)`` returning a DocsIndex-like object, or
    - ``docs_index.DocsIndex(docs_dir=...)`` with a ``build()`` or eager constructor.
    """
    builder = getattr(docs_index, "build_index", None)
    if callable(builder):
        return builder(docs_dir)

    cls = getattr(docs_index, "DocsIndex", None)
    if cls is None:
        raise RuntimeError("polygon_frp.docs_index exposes neither build_index() nor DocsIndex")

    # Try a docs_dir keyword first; fall back to positional.
    try:
        idx = cls(docs_dir=docs_dir)  # type: ignore[call-arg]
    except TypeError:
        idx = cls(docs_dir)  # type: ignore[call-arg]

    # If the class uses a lazy build() step, call it.
    build = getattr(idx, "build", None)
    if callable(build):
        try:
            build()
        except TypeError:
            # build() takes chunks — assume the constructor already indexed the dir.
            pass
    return idx


def _search(index, query: str, k: int) -> list[dict]:
    method = getattr(index, "search", None)
    if method is None:
        raise RuntimeError("DocsIndex has no .search() method")

    # Try common parameter names: top_k, k.
    try:
        hits = method(query, top_k=k)
    except TypeError:
        try:
            hits = method(query, k=k)
        except TypeError:
            hits = method(query, k)

    return [_normalize_hit(h) for h in hits]


def _normalize_hit(h) -> dict:
    """Coerce a hit (dataclass, dict, or tuple) into a plain {source, text, score}."""
    if isinstance(h, dict):
        return {
            "source": h.get("source", ""),
            "text": h.get("text", ""),
            "score": float(h.get("score", 0.0)),
        }
    return {
        "source": getattr(h, "source", ""),
        "text": getattr(h, "text", ""),
        "score": float(getattr(h, "score", 0.0)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve cited passages for a FAQ query.")
    parser.add_argument("query", help="Natural-language question")
    parser.add_argument("--k", type=int, default=5, help="Number of hits to return (default: 5)")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=_default_docs_dir(),
        help="Override path to the bundled docs directory.",
    )
    args = parser.parse_args()

    if not args.docs_dir.is_dir():
        print(
            json.dumps({"error": f"docs dir not found: {args.docs_dir}"}),
            file=sys.stderr,
        )
        return 2

    index = _build_index(args.docs_dir)
    hits = _search(index, args.query, args.k)

    # Rewrite `source` into a repo-relative citation path when possible.
    for hit in hits:
        src = hit["source"]
        if src and not src.endswith(".md"):
            hit["source"] = f"data/docs/{src}.md"

    json.dump(hits, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
