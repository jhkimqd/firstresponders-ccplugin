"""Tests for :mod:`polygon_frp.github_ingest`.

The GitHub SDK is fully stubbed via lightweight fake objects — no network.
Covers:
  * JSONL append semantics (records are newline-delimited JSON with the agreed schema)
  * Idempotency (running twice does NOT duplicate rows)
  * Cursor advance (``data/github/.cursor.json`` picks up the latest timestamps)
  * ``--since`` CLI parsing
  * Exit-code classification for rate-limit / auth / network
  * summarize.py filtering + grouping
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SUMMARIZE_SCRIPT = REPO_ROOT / "skills" / "summarize-upgrades" / "scripts"
if str(SUMMARIZE_SCRIPT) not in sys.path:
    sys.path.insert(0, str(SUMMARIZE_SCRIPT))

import summarize  # type: ignore[import-not-found]  # noqa: E402

from polygon_frp import github_ingest  # noqa: E402
from polygon_frp.github_ingest import (  # noqa: E402
    Cursor,
    _parse_since,
    append_records,
    ingest,
)

# ---------------------------------------------------------------------------
# PyGithub fakes
# ---------------------------------------------------------------------------


class _FakeUser:
    def __init__(self, login: str) -> None:
        self.login = login


class _FakeFile:
    def __init__(self, filename: str) -> None:
        self.filename = filename


class _FakePR:
    def __init__(
        self,
        *,
        number: int,
        title: str,
        body: str,
        merged_at: datetime | None,
        updated_at: datetime | None = None,
        author: str = "octocat",
        files: list[str] | None = None,
        html_url: str | None = None,
    ) -> None:
        self.number = number
        self.title = title
        self.body = body
        self.merged_at = merged_at
        self.updated_at = updated_at or merged_at
        self.user = _FakeUser(author) if author else None
        self._files = [_FakeFile(f) for f in (files or [])]
        self.html_url = html_url or f"https://github.com/0xPolygon/bor/pull/{number}"

    def get_files(self) -> list[_FakeFile]:
        return list(self._files)


class _FakeCommitAuthor:
    def __init__(self, name: str, date: datetime) -> None:
        self.name = name
        self.date = date


class _FakeInnerCommit:
    def __init__(self, message: str, author: _FakeCommitAuthor) -> None:
        self.message = message
        self.author = author


class _FakeCommit:
    def __init__(
        self,
        *,
        sha: str,
        message: str,
        authored_at: datetime,
        author: str = "dev",
        files: list[str] | None = None,
        html_url: str | None = None,
    ) -> None:
        self.sha = sha
        self.commit = _FakeInnerCommit(message, _FakeCommitAuthor(author, authored_at))
        self.files = [_FakeFile(f) for f in (files or [])]
        self.html_url = html_url or f"https://github.com/0xPolygon/bor/commit/{sha}"


class _FakeRepo:
    def __init__(self, prs: list[_FakePR], commits: list[_FakeCommit]) -> None:
        self._prs = prs
        self._commits = commits

    def get_pulls(self, state: str, sort: str, direction: str) -> list[_FakePR]:  # noqa: ARG002
        assert state == "closed"
        # Sort by updated_at desc to mimic GitHub's API ordering.
        return sorted(
            self._prs,
            key=lambda p: p.updated_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

    def get_commits(self, since: datetime) -> list[_FakeCommit]:
        return [c for c in self._commits if c.commit.author.date >= since]


class _FakeClient:
    def __init__(self, repos: dict[str, _FakeRepo]) -> None:
        self._repos = repos
        self.get_repo_calls: list[str] = []

    def get_repo(self, full: str) -> _FakeRepo:
        self.get_repo_calls.append(full)
        short = full.split("/", 1)[1]
        return self._repos[short]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_client() -> _FakeClient:
    t0 = datetime(2026, 4, 18, 10, 0, tzinfo=timezone.utc)
    bor_prs = [
        _FakePR(
            number=101,
            title="Add milestone batching",
            body="Batches milestones to reduce heimdall load.",
            merged_at=t0,
            updated_at=t0,
            author="alice",
            files=["consensus/bor/milestone.go"],
        ),
        _FakePR(
            number=102,
            title="Fix gas price calculator",
            body="Off-by-one for EIP-1559 base fee adjustment.",
            merged_at=t0 + timedelta(days=1),
            updated_at=t0 + timedelta(days=1),
            author="bob",
            files=["core/vm/gas.go"],
        ),
        # Closed-but-not-merged — must be filtered out
        _FakePR(
            number=103,
            title="Draft only",
            body="",
            merged_at=None,
            updated_at=t0 + timedelta(days=2),
            author="bob",
        ),
    ]
    bor_commits = [
        _FakeCommit(
            sha="aaa111",
            message="consensus: tighten milestone validation",
            authored_at=t0,
            author="alice",
            files=["consensus/bor/milestone.go"],
        ),
        _FakeCommit(
            sha="bbb222",
            message="core/vm: correct gas accounting",
            authored_at=t0 + timedelta(days=1),
            author="bob",
            files=["core/vm/gas.go"],
        ),
    ]
    heimdall_prs = [
        _FakePR(
            number=55,
            title="New checkpoint verifier",
            body="Rewrites checkpoint verifier with BLS.",
            merged_at=t0 + timedelta(hours=6),
            updated_at=t0 + timedelta(hours=6),
            author="carol",
            files=["checkpoint/keeper.go"],
            html_url="https://github.com/0xPolygon/heimdall-v2/pull/55",
        ),
    ]
    heimdall_commits: list[_FakeCommit] = []
    return _FakeClient(
        repos={
            "bor": _FakeRepo(bor_prs, bor_commits),
            "heimdall-v2": _FakeRepo(heimdall_prs, heimdall_commits),
        }
    )


# ---------------------------------------------------------------------------
# _parse_since / Cursor
# ---------------------------------------------------------------------------


def test_parse_since_relative() -> None:
    dt = _parse_since("30d")
    now = datetime.now(timezone.utc)
    assert timedelta(days=29, hours=23) < (now - dt) < timedelta(days=30, hours=1)


def test_parse_since_iso_date() -> None:
    dt = _parse_since("2026-04-01")
    assert dt == datetime(2026, 4, 1, tzinfo=timezone.utc)


def test_parse_since_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        _parse_since("banana")


def test_cursor_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / ".cursor.json"
    c = Cursor.load(p)
    when = datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc)
    c.advance("bor", "prs_since", when)
    c.save()

    c2 = Cursor.load(p)
    assert c2.data["bor"]["prs_since"].startswith("2026-04-15")
    # ``since_for`` picks the max of cursor vs fallback
    fallback = datetime(2026, 3, 1, tzinfo=timezone.utc)
    assert c2.since_for("bor", "prs_since", fallback) == when


# ---------------------------------------------------------------------------
# append_records idempotency
# ---------------------------------------------------------------------------


def test_append_records_dedups(tmp_path: Path) -> None:
    path = tmp_path / "prs.jsonl"
    recs = [
        {"number": 1, "title": "a"},
        {"number": 2, "title": "b"},
        {"number": 1, "title": "a-dup"},
    ]
    written = append_records(path, recs, dedup_key="number")
    assert written == 2

    # Running again with overlapping records must not duplicate
    again = append_records(
        path,
        [{"number": 2, "title": "b-again"}, {"number": 3, "title": "c"}],
        dedup_key="number",
    )
    assert again == 1

    with path.open() as fh:
        lines = [json.loads(line) for line in fh if line.strip()]
    numbers = [r["number"] for r in lines]
    assert sorted(numbers) == [1, 2, 3]


# ---------------------------------------------------------------------------
# ingest() end-to-end (with fake client)
# ---------------------------------------------------------------------------


def test_ingest_writes_schema(tmp_path: Path, fake_client: _FakeClient) -> None:
    since = datetime(2026, 4, 1, tzinfo=timezone.utc)
    report = ingest(
        ["bor", "heimdall-v2"],
        since,
        data_dir=tmp_path,
        github_client=fake_client,
    )
    assert fake_client.get_repo_calls == ["0xPolygon/bor", "0xPolygon/heimdall-v2"]
    assert report.prs_written == {"bor": 2, "heimdall-v2": 1}
    assert report.commits_written == {"bor": 2, "heimdall-v2": 0}

    bor_prs = [
        json.loads(line) for line in (tmp_path / "bor" / "prs.jsonl").read_text().splitlines()
    ]
    numbers = sorted(r["number"] for r in bor_prs)
    assert numbers == [101, 102]

    # Required fields present with correct shape
    pr101 = next(r for r in bor_prs if r["number"] == 101)
    assert pr101["type"] == "pr"
    assert pr101["repo"] == "bor"
    assert pr101["author"] == "alice"
    assert pr101["html_url"].endswith("/pull/101")
    assert pr101["files"] == ["consensus/bor/milestone.go"]
    assert pr101["merged_at"].startswith("2026-04-18")

    # Commits file present and keyed by sha
    bor_commits = [
        json.loads(line) for line in (tmp_path / "bor" / "commits.jsonl").read_text().splitlines()
    ]
    shas = sorted(r["sha"] for r in bor_commits)
    assert shas == ["aaa111", "bbb222"]
    c = next(r for r in bor_commits if r["sha"] == "bbb222")
    assert c["type"] == "commit"
    assert c["author"] == "bob"
    assert c["authored_at"].startswith("2026-04-19")


def test_ingest_idempotent(tmp_path: Path, fake_client: _FakeClient) -> None:
    """Running twice back-to-back must not duplicate rows (SPEC §8)."""
    since = datetime(2026, 4, 1, tzinfo=timezone.utc)
    ingest(["bor", "heimdall-v2"], since, data_dir=tmp_path, github_client=fake_client)
    report2 = ingest(["bor", "heimdall-v2"], since, data_dir=tmp_path, github_client=fake_client)
    # Second run sees every record as a dup → zero new rows
    assert report2.total == 0

    # File-on-disk unchanged in record count
    bor_pr_lines = (tmp_path / "bor" / "prs.jsonl").read_text().splitlines()
    assert len(bor_pr_lines) == 2
    bor_commit_lines = (tmp_path / "bor" / "commits.jsonl").read_text().splitlines()
    assert len(bor_commit_lines) == 2


def test_ingest_advances_cursor(tmp_path: Path, fake_client: _FakeClient) -> None:
    since = datetime(2026, 4, 1, tzinfo=timezone.utc)
    ingest(["bor", "heimdall-v2"], since, data_dir=tmp_path, github_client=fake_client)
    cursor_path = tmp_path / ".cursor.json"
    data = json.loads(cursor_path.read_text())
    assert "bor" in data and "heimdall-v2" in data
    # Latest merged PR for bor is #102 at 2026-04-19
    assert data["bor"]["prs_since"].startswith("2026-04-19")
    # Latest commit is bbb222 at 2026-04-19
    assert data["bor"]["commits_since"].startswith("2026-04-19")
    # Heimdall has only a PR, no commits → commits_since absent
    assert data["heimdall-v2"]["prs_since"].startswith("2026-04-18")
    assert "commits_since" not in data["heimdall-v2"]


# ---------------------------------------------------------------------------
# Exit-code classification
# ---------------------------------------------------------------------------


def test_classify_network_error() -> None:
    code = github_ingest._classify_github_exception(TimeoutError("slow"))
    assert code == github_ingest.EXIT_NETWORK


def test_classify_rate_limit() -> None:
    # Simulate PyGithub RateLimitExceededException if it imports; otherwise fallback
    try:
        from github import RateLimitExceededException
    except Exception:
        pytest.skip("PyGithub not installed in test env")
    exc = RateLimitExceededException(403, {"message": "API rate limit exceeded"}, {})
    assert github_ingest._classify_github_exception(exc) == github_ingest.EXIT_RATE_LIMIT


def test_classify_bad_credentials() -> None:
    try:
        from github import BadCredentialsException
    except Exception:
        pytest.skip("PyGithub not installed in test env")
    exc = BadCredentialsException(401, {"message": "Bad credentials"}, {})
    assert github_ingest._classify_github_exception(exc) == github_ingest.EXIT_AUTH


# ---------------------------------------------------------------------------
# summarize.py
# ---------------------------------------------------------------------------


def test_summarize_filter_and_group(tmp_path: Path) -> None:
    # Seed a minimal prs.jsonl for bor
    repo_dir = tmp_path / "bor"
    repo_dir.mkdir(parents=True)
    records = [
        {
            "type": "pr",
            "repo": "bor",
            "number": 101,
            "title": "Add milestone batching",
            "body": "checkpoint-adjacent work",
            "merged_at": "2026-04-15T10:00:00+00:00",
            "author": "alice",
            "files": ["consensus/bor/milestone.go"],
            "html_url": "https://github.com/0xPolygon/bor/pull/101",
        },
        {
            "type": "pr",
            "repo": "bor",
            "number": 102,
            "title": "Tune gas calc",
            "body": "gas price adjustments",
            "merged_at": "2026-04-17T11:00:00+00:00",
            "author": "bob",
            "files": ["core/vm/gas.go"],
            "html_url": "https://github.com/0xPolygon/bor/pull/102",
        },
        {
            "type": "pr",
            "repo": "bor",
            "number": 80,
            "title": "Old thing",
            "body": "",
            "merged_at": "2026-01-01T00:00:00+00:00",
            "author": "ghost",
            "files": [],
            "html_url": "https://github.com/0xPolygon/bor/pull/80",
        },
    ]
    with (repo_dir / "prs.jsonl").open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")

    since = datetime(2026, 4, 10, tzinfo=timezone.utc)
    matched = summarize.filter_prs(records, since=since, until=None, keywords=["milestone"])
    assert [r["number"] for r in matched] == [101]

    # Grouping
    all_recent = summarize.filter_prs(records, since=since, until=None, keywords=[])
    groups = summarize.group_by_week(all_recent)
    # Two merges in April 2026 → week 16 (April 13–19 ISO) covers both
    flat_numbers = [pr["number"] for _, prs in groups for pr in prs]
    assert set(flat_numbers) == {101, 102}


def test_summarize_markdown_contains_urls() -> None:
    records = [
        {
            "type": "pr",
            "repo": "bor",
            "number": 101,
            "title": "Add milestone batching",
            "body": "",
            "merged_at": "2026-04-15T10:00:00+00:00",
            "author": "alice",
            "files": [],
            "html_url": "https://github.com/0xPolygon/bor/pull/101",
        }
    ]
    groups = summarize.group_by_week(records)
    out = summarize.render_markdown(
        groups,
        since=datetime(2026, 4, 1, tzinfo=timezone.utc),
        until=None,
        repos=["bor"],
        keywords=[],
        limit=10,
    )
    assert "https://github.com/0xPolygon/bor/pull/101" in out
    assert "[bor#101]" in out
    assert "## Week 2026-W16" in out


def test_summarize_empty_reports_no_matches() -> None:
    out = summarize.render_markdown(
        [], since=None, until=None, repos=["bor"], keywords=[], limit=10
    )
    assert "No matching merged PRs" in out
