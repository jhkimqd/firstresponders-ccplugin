#!/usr/bin/env python3
"""Summarize recent merged PRs from ``data/github/*/prs.jsonl``.

Reads the NDJSON files produced by :mod:`polygon_frp.github_ingest`, filters by
date window + optional keywords, and emits a Markdown (or JSON) digest grouped
by ISO-week. Every bullet carries the PR URL so Claude can cite it.

CLI::

    python scripts/summarize.py --repo both --since 14d --keywords checkpoint,milestone
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "github"
DEFAULT_REPOS = ("bor", "heimdall-v2")


def _parse_window(value: str | None) -> datetime | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    m = re.fullmatch(r"(\d+)([dhw])", value)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        delta = {
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
            "w": timedelta(weeks=amount),
        }[unit]
        return datetime.now(timezone.utc) - delta
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid date/window: {value!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _iter_prs(data_dir: Path, repos: Iterable[str]) -> Iterable[dict[str, Any]]:
    for repo in repos:
        path = data_dir / repo / "prs.jsonl"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def _matches_keywords(pr: dict[str, Any], keywords: list[str]) -> bool:
    if not keywords:
        return True
    haystack_parts = [pr.get("title", ""), pr.get("body", "")]
    files = pr.get("files") or []
    haystack_parts.extend(files)
    haystack = "\n".join(haystack_parts).lower()
    return any(kw in haystack for kw in keywords)


def _merged_at(pr: dict[str, Any]) -> datetime | None:
    raw = pr.get("merged_at")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def filter_prs(
    records: Iterable[dict[str, Any]],
    *,
    since: datetime | None,
    until: datetime | None,
    keywords: list[str],
) -> list[dict[str, Any]]:
    keywords = [k.strip().lower() for k in keywords if k.strip()]
    out: list[dict[str, Any]] = []
    for pr in records:
        dt = _merged_at(pr)
        if dt is None:
            continue
        if since and dt < since:
            continue
        if until and dt > until:
            continue
        if not _matches_keywords(pr, keywords):
            continue
        out.append(pr)
    # Newest first
    out.sort(key=lambda r: _merged_at(r) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return out


def group_by_week(prs: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pr in prs:
        dt = _merged_at(pr)
        if dt is None:
            continue
        iso = dt.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        buckets[key].append(pr)
    # Sort week keys descending (newest first)
    return sorted(buckets.items(), reverse=True)


def render_markdown(
    groups: list[tuple[str, list[dict[str, Any]]]],
    *,
    since: datetime | None,
    until: datetime | None,
    repos: list[str],
    keywords: list[str],
    limit: int,
) -> str:
    total_listed = sum(len(prs) for _, prs in groups)
    lines: list[str] = []
    header_parts = [f"repos={','.join(repos)}"]
    if since:
        header_parts.append(f"since={since.date().isoformat()}")
    if until:
        header_parts.append(f"until={until.date().isoformat()}")
    if keywords:
        header_parts.append(f"keywords={','.join(keywords)}")

    lines.append(f"# Upgrade digest ({'; '.join(header_parts)})")
    lines.append("")
    if total_listed == 0:
        lines.append("_No matching merged PRs. Try widening `--since` or dropping `--keywords`._")
        return "\n".join(lines) + "\n"

    remaining = limit
    for week, prs in groups:
        if remaining <= 0:
            break
        lines.append(f"## Week {week}")
        lines.append("")
        for pr in prs:
            if remaining <= 0:
                break
            repo = pr.get("repo", "?")
            number = pr.get("number", "?")
            title = (pr.get("title") or "").strip() or "(no title)"
            author = pr.get("author") or "unknown"
            url = pr.get("html_url", "")
            lines.append(f"- **[{repo}#{number}]({url})** — {title} _(by {author})_")
            remaining -= 1
        lines.append("")

    if total_listed > limit:
        lines.append(
            f"_Showing {limit} of {total_listed} matches. Re-run with a higher `--limit`._"
        )
    return "\n".join(lines).rstrip() + "\n"


def render_json(prs: list[dict[str, Any]]) -> str:
    # Emit a slimmed-down view to keep stdout compact.
    slim = [
        {
            "repo": pr.get("repo"),
            "number": pr.get("number"),
            "title": pr.get("title"),
            "author": pr.get("author"),
            "merged_at": pr.get("merged_at"),
            "html_url": pr.get("html_url"),
        }
        for pr in prs
    ]
    return json.dumps(slim, indent=2, ensure_ascii=False)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Summarize recent Polygon upgrade PRs.")
    p.add_argument("--repo", default="both", choices=["bor", "heimdall-v2", "both"])
    p.add_argument("--since", default="14d")
    p.add_argument("--until", default=None)
    p.add_argument("--keywords", default="")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--format", default="markdown", choices=["markdown", "json"])
    p.add_argument("--data-dir", type=Path, default=DATA_DIR)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    repos: list[str]
    if args.repo == "both":
        repos = list(DEFAULT_REPOS)
    else:
        repos = [str(args.repo)]

    try:
        since = _parse_window(args.since)
        until = _parse_window(args.until)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    keywords = [k for k in (args.keywords or "").split(",") if k.strip()]
    records = list(_iter_prs(args.data_dir, repos))
    matched = filter_prs(records, since=since, until=until, keywords=keywords)

    if args.format == "json":
        print(render_json(matched[: args.limit]))
    else:
        groups = group_by_week(matched)
        print(
            render_markdown(
                groups,
                since=since,
                until=until,
                repos=repos,
                keywords=keywords,
                limit=args.limit,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
