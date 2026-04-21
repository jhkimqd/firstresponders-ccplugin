"""Incremental GitHub ingestion for 0xPolygon/bor and 0xPolygon/heimdall-v2.

Pulls merged PRs and default-branch commits into newline-delimited JSON files
at ``data/github/{repo}/{prs,commits}.jsonl``. Maintains a per-repo cursor at
``data/github/.cursor.json`` so subsequent runs are incremental.

CLI::

    python -m polygon_frp.github_ingest --repos bor,heimdall-v2 --since 30d

Exit codes (per SPEC §5.4):
    0 — success
    1 — rate-limit exhausted
    2 — network error
    3 — auth failure
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("polygon_frp.github_ingest")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_OWNER = "0xPolygon"
KNOWN_REPOS: tuple[str, ...] = ("bor", "heimdall-v2")

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "github"
CURSOR_FILENAME = ".cursor.json"

# Exit codes
EXIT_OK = 0
EXIT_RATE_LIMIT = 1
EXIT_NETWORK = 2
EXIT_AUTH = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_since(value: str) -> datetime:
    """Parse ``--since`` values: ``30d``, ``12h``, ``2026-04-01``, or ISO-8601."""
    value = value.strip()
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
    # Try ISO-8601 (date or datetime)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"unrecognised --since value: {value!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------


@dataclass
class Cursor:
    """Per-repo high-water marks for incremental ingestion."""

    path: Path
    data: dict[str, dict[str, str]]

    @classmethod
    def load(cls, path: Path) -> Cursor:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if not isinstance(data, dict):
                    data = {}
            except json.JSONDecodeError:
                logger.warning("cursor file %s is malformed; resetting", path)
                data = {}
        else:
            data = {}
        return cls(path=path, data=data)

    def since_for(self, repo: str, key: str, fallback: datetime) -> datetime:
        """Return effective ``since`` for (repo, key), max of cursor and fallback."""
        raw = self.data.get(repo, {}).get(key)
        stored = _parse_iso(raw)
        if stored is None:
            return fallback
        return max(stored, fallback)

    def advance(self, repo: str, key: str, when: datetime) -> None:
        repo_data = self.data.setdefault(repo, {})
        existing = _parse_iso(repo_data.get(key))
        if existing is None or when > existing:
            repo_data[key] = _iso(when) or ""

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True))
        tmp.replace(self.path)


# ---------------------------------------------------------------------------
# NDJSON dedup-append writer
# ---------------------------------------------------------------------------


def _load_existing_ids(path: Path, key: str) -> set[Any]:
    """Return set of dedup identifiers already persisted in ``path``."""
    if not path.exists():
        return set()
    ids: set[Any] = set()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if key in rec:
                ids.add(rec[key])
    return ids


def append_records(path: Path, records: Iterable[dict[str, Any]], dedup_key: str) -> int:
    """Append records as NDJSON, skipping ones whose ``dedup_key`` already exists.

    Returns the number of new records written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = _load_existing_ids(path, dedup_key)
    written = 0
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            ident = rec.get(dedup_key)
            if ident is None or ident in seen:
                continue
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            seen.add(ident)
            written += 1
    return written


# ---------------------------------------------------------------------------
# GitHub client integration (PyGithub)
# ---------------------------------------------------------------------------


def _build_github_client(token: str | None):
    """Construct a :class:`github.Github` client. Lazy import so tests can stub."""
    from github import Auth, Github  # type: ignore[import-not-found]

    if token:
        return Github(auth=Auth.Token(token))
    return Github()


def _pr_record(pr: Any, repo: str) -> dict[str, Any]:
    """Convert a PyGithub ``PullRequest`` to a JSONL-ready dict."""
    files: list[str] = []
    try:
        # ``get_files`` paginates; keep bounded.
        for f in pr.get_files():
            fn = getattr(f, "filename", None)
            if fn:
                files.append(fn)
            if len(files) >= 200:
                break
    except Exception:  # noqa: BLE001 — best-effort; upstream may 404 on huge PRs
        files = []

    author = None
    user = getattr(pr, "user", None)
    if user is not None:
        author = getattr(user, "login", None)

    return {
        "type": "pr",
        "repo": repo,
        "number": int(pr.number),
        "title": pr.title or "",
        "body": pr.body or "",
        "merged_at": _iso(pr.merged_at),
        "author": author,
        "files": files,
        "html_url": pr.html_url,
    }


def _commit_record(commit: Any, repo: str) -> dict[str, Any]:
    """Convert a PyGithub ``Commit`` to a JSONL-ready dict."""
    inner = getattr(commit, "commit", None)

    message = ""
    authored_at: datetime | None = None
    author_name: str | None = None
    if inner is not None:
        message = getattr(inner, "message", "") or ""
        inner_author = getattr(inner, "author", None)
        if inner_author is not None:
            authored_at = getattr(inner_author, "date", None)
            author_name = getattr(inner_author, "name", None)

    files: list[str] = []
    try:
        for f in commit.files or []:
            fn = getattr(f, "filename", None)
            if fn:
                files.append(fn)
            if len(files) >= 200:
                break
    except Exception:  # noqa: BLE001
        files = []

    return {
        "type": "commit",
        "repo": repo,
        "sha": commit.sha,
        "message": message,
        "authored_at": _iso(authored_at),
        "author": author_name,
        "files": files,
        "html_url": commit.html_url,
    }


def fetch_merged_prs(repo_obj: Any, repo_name: str, since: datetime) -> list[dict[str, Any]]:
    """Yield merged PR dicts whose ``merged_at`` >= ``since``."""
    records: list[dict[str, Any]] = []
    # Pull closed PRs, newest first; stop once we pass ``since``.
    prs = repo_obj.get_pulls(state="closed", sort="updated", direction="desc")
    for pr in prs:
        updated = getattr(pr, "updated_at", None)
        if updated is not None:
            u = updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)
            if u < since:
                break
        if not getattr(pr, "merged_at", None):
            continue
        merged = pr.merged_at
        if merged.tzinfo is None:
            merged = merged.replace(tzinfo=timezone.utc)
        if merged < since:
            continue
        records.append(_pr_record(pr, repo_name))
    return records


def fetch_commits(repo_obj: Any, repo_name: str, since: datetime) -> list[dict[str, Any]]:
    """Yield commit dicts authored on or after ``since`` on the default branch."""
    records: list[dict[str, Any]] = []
    commits = repo_obj.get_commits(since=since)
    for commit in commits:
        records.append(_commit_record(commit, repo_name))
    return records


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


@dataclass
class IngestReport:
    prs_written: dict[str, int]
    commits_written: dict[str, int]

    @property
    def total(self) -> int:
        return sum(self.prs_written.values()) + sum(self.commits_written.values())


def ingest(
    repos: list[str],
    since: datetime,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    token: str | None = None,
    github_client: Any | None = None,
) -> IngestReport:
    """Run incremental ingestion for the given repos.

    ``github_client`` is primarily a test hook — if unset we construct a real
    PyGithub client using ``token`` (or ``GITHUB_TOKEN`` in env).
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    cursor = Cursor.load(data_dir / CURSOR_FILENAME)

    if github_client is None:
        if token is None:
            token = os.environ.get("GITHUB_TOKEN")
        if not token:
            logger.warning("GITHUB_TOKEN not set — using unauthenticated GitHub (60 req/hr limit)")
        github_client = _build_github_client(token)
    assert github_client is not None  # for type-checkers

    report = IngestReport(prs_written={}, commits_written={})

    for repo_name in repos:
        full = f"{REPO_OWNER}/{repo_name}"
        logger.info("ingesting %s since %s", full, since.isoformat())
        repo_obj = github_client.get_repo(full)

        prs_since = cursor.since_for(repo_name, "prs_since", since)
        commits_since = cursor.since_for(repo_name, "commits_since", since)

        pr_records = fetch_merged_prs(repo_obj, repo_name, prs_since)
        commit_records = fetch_commits(repo_obj, repo_name, commits_since)

        repo_dir = data_dir / repo_name
        prs_written = append_records(repo_dir / "prs.jsonl", pr_records, dedup_key="number")
        commits_written = append_records(
            repo_dir / "commits.jsonl", commit_records, dedup_key="sha"
        )

        report.prs_written[repo_name] = prs_written
        report.commits_written[repo_name] = commits_written

        # Advance cursor to the latest merged/authored timestamp we persisted.
        pr_times = [dt for r in pr_records if (dt := _parse_iso(r.get("merged_at"))) is not None]
        commit_times = [
            dt for r in commit_records if (dt := _parse_iso(r.get("authored_at"))) is not None
        ]
        if pr_times:
            cursor.advance(repo_name, "prs_since", max(pr_times))
        if commit_times:
            cursor.advance(repo_name, "commits_since", max(commit_times))

    cursor.save()
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _classify_github_exception(exc: BaseException) -> int:
    """Map exceptions into exit codes per SPEC §5.4."""
    # Lazy import so missing PyGithub at test-time doesn't explode here.
    try:
        from github import (  # type: ignore[import-not-found]
            BadCredentialsException,
            GithubException,
            RateLimitExceededException,
        )
    except Exception:  # noqa: BLE001
        github_exception: type = type(None)
        rate_limit_exception: type = type(None)
        bad_credentials_exception: type = type(None)
    else:
        github_exception = GithubException
        rate_limit_exception = RateLimitExceededException
        bad_credentials_exception = BadCredentialsException

    if isinstance(exc, rate_limit_exception):
        return EXIT_RATE_LIMIT
    if isinstance(exc, bad_credentials_exception):
        return EXIT_AUTH
    if isinstance(exc, github_exception):
        status = getattr(exc, "status", None)
        if status in (401, 403):
            # 403 can be either auth or rate-limit; detect by message.
            msg = str(getattr(exc, "data", "")).lower()
            if "rate limit" in msg:
                return EXIT_RATE_LIMIT
            return EXIT_AUTH
        return EXIT_NETWORK

    # httpx/urllib-style network faults
    name = type(exc).__name__.lower()
    if any(tag in name for tag in ("timeout", "connection", "network", "dns")):
        return EXIT_NETWORK
    return EXIT_NETWORK


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m polygon_frp.github_ingest",
        description="Incremental GitHub pull for Polygon repos.",
    )
    p.add_argument(
        "--repos",
        default=",".join(KNOWN_REPOS),
        help="comma-separated short names (default: %(default)s)",
    )
    p.add_argument(
        "--since",
        default="30d",
        help="lookback window (e.g. 30d, 12h, 2w, 2026-04-01) (default: %(default)s)",
    )
    p.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="output directory (default: %(default)s)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    unknown = [r for r in repos if r not in KNOWN_REPOS]
    if unknown:
        logger.warning("ingesting non-default repos: %s", unknown)

    try:
        since = _parse_since(args.since)
    except ValueError as exc:
        logger.error("invalid --since: %s", exc)
        return 2

    try:
        report = ingest(repos, since, data_dir=args.data_dir)
    except Exception as exc:  # noqa: BLE001
        code = _classify_github_exception(exc)
        logger.error("ingest failed (exit %s): %s", code, exc)
        return code

    summary = {
        "prs_written": report.prs_written,
        "commits_written": report.commits_written,
        "total": report.total,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
