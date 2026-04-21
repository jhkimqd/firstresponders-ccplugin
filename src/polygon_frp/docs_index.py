"""TF-IDF-like document index over Polygon markdown docs + GitHub JSONL.

Ported verbatim from polygon-chatbot/mcp-server/src/polygon_mcp/docs.py with
these additions:

- `index_github_jsonl(path, source_prefix)` — index PR / commit JSONL records
  alongside markdown chunks. Each record becomes one chunk; its `source` is
  the PR/commit URL so answers can cite it directly.
- `build_index` default for the new repo looks up `data/docs/` at repo root
  (no package-bundled docs path).
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


def _resolve_docs_dir() -> Path:
    """Find docs directory: env var > repo data/docs/ fallback."""
    env_dir = os.environ.get("POLYGON_DOCS_DIR", "")
    if env_dir:
        return Path(env_dir)

    # Repo checkout: data/docs/ at repo root (this file lives at
    # <repo>/src/polygon_frp/docs_index.py so repo root is parents[2]).
    repo_docs = Path(__file__).resolve().parents[2] / "data" / "docs"
    return repo_docs


_DOCS_DIR = _resolve_docs_dir()

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


@dataclass
class DocChunk:
    text: str
    source: str
    score: float = 0.0
    # Optional metadata to support filtered queries (date window etc.) on
    # GitHub-derived chunks. Markdown chunks leave this empty.
    metadata: dict = field(default_factory=dict)


@dataclass
class DocsIndex:
    """Simple TF-IDF-like index over document chunks — no external dependencies."""

    chunks: list[DocChunk] = field(default_factory=list)
    _idf: dict[str, float] = field(default_factory=dict)
    _tf_cache: list[dict[str, float]] = field(default_factory=list)

    def build(self, chunks: list[DocChunk]) -> None:
        self.chunks = chunks
        n = len(chunks)
        df: dict[str, int] = {}
        self._tf_cache = []

        for chunk in chunks:
            tokens = _tokenize(chunk.text)
            tf: dict[str, float] = {}
            total = len(tokens) or 1
            for tok in tokens:
                tf[tok] = tf.get(tok, 0) + 1
            for tok in tf:
                tf[tok] /= total
                df[tok] = df.get(tok, 0) + 1
            self._tf_cache.append(tf)

        self._idf = {tok: math.log((n + 1) / (count + 1)) + 1 for tok, count in df.items()}

    def search(self, query: str, top_k: int = 5) -> list[DocChunk]:
        if not self.chunks:
            return []

        query_tokens = set(_tokenize(query))
        scored: list[tuple[float, int]] = []

        for i, tf in enumerate(self._tf_cache):
            score = sum(tf.get(tok, 0) * self._idf.get(tok, 0) for tok in query_tokens)
            if score > 0:
                scored.append((score, i))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, idx in scored[:top_k]:
            chunk = self.chunks[idx]
            results.append(
                DocChunk(
                    text=chunk.text,
                    source=chunk.source,
                    score=score,
                    metadata=dict(chunk.metadata),
                )
            )
        return results

    def index_github_jsonl(self, path: Path, source_prefix: str = "") -> int:
        """Extend the index with PR/commit records from a JSONL file.

        Each record becomes one chunk whose `source` is the record's
        ``html_url`` (falling back to ``source_prefix:<sha>/#<number>`` if the
        URL is absent). Chunk text is ``title + body`` for PRs or the commit
        message for commits. Records missing usable text are skipped.

        After loading, the index is rebuilt so TF-IDF statistics include the
        new chunks. Returns the number of chunks actually added.
        """
        path = Path(path)
        if not path.exists():
            return 0

        new_chunks: list[DocChunk] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                text = _github_record_to_text(rec)
                if not text:
                    continue

                source = rec.get("html_url") or rec.get("url")
                if not source:
                    ident = rec.get("sha") or rec.get("number") or "unknown"
                    source = f"{source_prefix}:{ident}" if source_prefix else str(ident)

                # Canonical schema (from github_ingest.py) is flat with a
                # `type` discriminator: "pr" or "commit". We fall back to
                # heuristics only if `type` is absent (legacy fixtures).
                kind = rec.get("type") or ("pr" if "number" in rec else "commit")
                metadata: dict = {
                    "kind": kind,
                    "source_prefix": source_prefix,
                }
                for key in (
                    "repo",
                    "author",
                    "merged_at",
                    "authored_at",
                    "number",
                    "sha",
                    "files",
                ):
                    if key in rec:
                        metadata[key] = rec[key]

                # Canonical timestamp (flat): `merged_at` for PRs,
                # `authored_at` for commits. Keep legacy fallbacks so tests
                # that construct nested GitHub-API-shaped records still work.
                date = _record_date(rec)
                if date:
                    metadata["date"] = date

                new_chunks.append(DocChunk(text=text, source=str(source), metadata=metadata))

        if not new_chunks:
            return 0

        self.build(self.chunks + new_chunks)
        return len(new_chunks)


def _github_record_to_text(rec: dict) -> str:
    """Flatten a PR/commit record into searchable text.

    Target schema is flat (from `github_ingest.py`):
    - PRs carry `title` + `body`.
    - Commits carry `message` at the top level.

    Legacy nested shapes (``commit.message``) are still accepted so older
    fixtures or ad-hoc JSONL files keep working.
    """
    title = rec.get("title") or ""
    body = rec.get("body") or ""
    if title or body:
        return (title + "\n\n" + body).strip()

    message = rec.get("message") or ""
    if message:
        return message.strip()

    # Legacy GitHub-API nested shape fallback.
    commit = rec.get("commit") or {}
    return (commit.get("message") or "").strip()


def _record_date(rec: dict) -> str | None:
    """Best-effort extraction of a record's primary timestamp (ISO string).

    Canonical fields (flat): ``merged_at`` (PRs), ``authored_at`` (commits).
    Legacy fallbacks: ``created_at``, ``date``, ``commit.author.date``.
    """
    for key in ("merged_at", "authored_at", "created_at", "date"):
        val = rec.get(key)
        if isinstance(val, str) and val:
            return val
    commit = rec.get("commit") or {}
    author = commit.get("author") or {}
    if isinstance(author, dict):
        date = author.get("date")
        if isinstance(date, str) and date:
            return date
    return None


def _tokenize(text: str) -> list[str]:
    """Lowercase split on non-alphanumeric, drop short tokens."""
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1]


def load_docs(docs_dir: Path | None = None) -> list[dict]:
    """Load all .md files from the docs directory."""
    docs_dir = docs_dir or _DOCS_DIR
    documents = []
    if not docs_dir.is_dir():
        return documents
    for md_file in sorted(docs_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8").strip()
        if text:
            documents.append({"source": md_file.stem, "text": text})
    return documents


def chunk_document(doc: dict) -> list[DocChunk]:
    """Split a document into overlapping chunks respecting section boundaries."""
    text = doc["text"]
    source = doc["source"]
    sections = re.split(r"\n(?=#{1,4}\s)", text)
    chunks: list[DocChunk] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= CHUNK_SIZE:
            chunks.append(DocChunk(text=section, source=source))
            continue

        paragraphs = section.split("\n\n")
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 2 > CHUNK_SIZE and current:
                chunks.append(DocChunk(text=current.strip(), source=source))
                overlap = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else current
                current = overlap + "\n\n" + para
            else:
                current = current + "\n\n" + para if current else para

        if current.strip():
            chunks.append(DocChunk(text=current.strip(), source=source))

    return chunks


def build_index(docs_dir: Path | None = None) -> DocsIndex:
    """Load docs, chunk them, and build a searchable index."""
    documents = load_docs(docs_dir)
    all_chunks: list[DocChunk] = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc))

    index = DocsIndex()
    index.build(all_chunks)
    return index
