"""Retrieval regression tests for docs_index.py.

Samples ≥20 questions from FAQ_COVERAGE.md spanning the four personas
(node-op / dev / validator / RPC provider) plus the cross-persona sections.
Each question is mapped to the source doc (filename stem) that *should* be in
the top-3 TF-IDF hits. Keep this list living — add more questions as they
surface from responders in the field.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polygon_frp.docs_index import (
    DocChunk,
    DocsIndex,
    build_index,
    chunk_document,
    load_docs,
)

# Pytest discovers this at import time; the index is reused across tests.
_INDEX = build_index()


# Each entry: (persona, question, expected_source_stem)
# Source stems match filenames in data/docs/ without the .md suffix.
FAQ_CASES: list[tuple[str, str, str]] = [
    # --- Node Operators ---
    ("node-op", "How do I run a Polygon PoS full node?", "nodes-and-validators"),
    (
        "node-op",
        "What are the minimum hardware requirements for a Polygon PoS node?",
        "nodes-and-validators",
    ),
    (
        "node-op",
        "What is the difference between Bor and Heimdall?",
        "nodes-and-validators",
    ),
    (
        "node-op",
        "How do I set up an archive node on Polygon PoS?",
        "nodes-and-validators",
    ),
    (
        "node-op",
        "What public RPC endpoints are available for Polygon PoS?",
        "rpc-endpoints",
    ),
    # --- Developers ---
    (
        "dev",
        "How do I add Polygon PoS to MetaMask?",
        "polygon-pos-overview",
    ),
    (
        "dev",
        "What is the chain ID for Polygon PoS mainnet?",
        "polygon-pos-overview",
    ),
    (
        "dev",
        "How do I deploy a smart contract on Polygon PoS using Hardhat?",
        "deploy-contract-pos",
    ),
    (
        "dev",
        "How do I verify a smart contract on PolygonScan?",
        "deploy-contract-pos",
    ),
    (
        "dev",
        "What is Polygon CDK and when should I use it?",
        "polygon-cdk",
    ),
    (
        "dev",
        "How does the Polygon PoS bridge work?",
        "bridging",
    ),
    (
        "dev",
        "How does the AggLayer bridge differ from the PoS bridge?",
        "agglayer",
    ),
    (
        "dev",
        "How do I deploy an ERC-721 NFT on Polygon?",
        "smart-contracts",
    ),
    # --- Validators ---
    (
        "validator",
        "What is the minimum stake required to become a validator on Polygon?",
        "nodes-and-validators",
    ),
    (
        "validator",
        "How are validator rewards calculated on Polygon PoS?",
        "nodes-and-validators",
    ),
    (
        "validator",
        "How often does Heimdall submit checkpoints to Ethereum?",
        "polygon-pos-overview",
    ),
    (
        "validator",
        "What is Heimdall's role in Polygon PoS validation?",
        "nodes-and-validators",
    ),
    # --- RPC providers ---
    (
        "rpc-provider",
        "What is the best free RPC endpoint for Polygon PoS?",
        "rpc-endpoints",
    ),
    (
        "rpc-provider",
        "What private RPC providers like Alchemy and QuickNode support Polygon?",
        "rpc-endpoints",
    ),
    (
        "rpc-provider",
        "How do I handle the Polygon PoS-specific bor_ RPC namespace?",
        "rpc-endpoints",
    ),
    # --- Cross-persona (gas / POL migration) ---
    (
        "cross",
        "What is the current base fee on Polygon PoS?",
        "gas-fees",
    ),
    (
        "cross",
        "How does EIP-1559 work on Polygon?",
        "gas-fees",
    ),
    (
        "cross",
        "What is the MATIC to POL migration?",
        "polygon-pos-overview",
    ),
    # --- Liquid staking (sPOL) ---
    (
        "validator",
        "What is sPOL?",
        "staked-pol",
    ),
    (
        "validator",
        "How is sPOL different from native POL staking?",
        "staked-pol",
    ),
    (
        "dev",
        "What is the sPOL contract address on Ethereum?",
        "staked-pol",
    ),
    (
        "validator",
        "Is sPOL available on Polygon PoS?",
        "staked-pol",
    ),
]


def test_at_least_20_faq_cases() -> None:
    """Guardrail: the corpus must have ≥20 regression questions."""
    assert len(FAQ_CASES) >= 20, f"only {len(FAQ_CASES)} cases"


def test_all_four_personas_covered() -> None:
    personas = {p for p, *_ in FAQ_CASES}
    for required in ("node-op", "dev", "validator", "rpc-provider"):
        assert required in personas, f"persona {required} missing from FAQ_CASES"


def test_index_has_expected_doc_sources() -> None:
    """All expected sources referenced by FAQ_CASES exist in data/docs/."""
    sources_in_index = {c.source for c in _INDEX.chunks}
    expected_sources = {src for _, _, src in FAQ_CASES}
    missing = expected_sources - sources_in_index
    assert not missing, f"data/docs/ is missing: {missing}"


@pytest.mark.parametrize(
    ("persona", "question", "expected_source"),
    FAQ_CASES,
    ids=[f"{p}:{q[:50]}" for p, q, _ in FAQ_CASES],
)
def test_faq_retrieval_top3(persona: str, question: str, expected_source: str) -> None:
    hits = _INDEX.search(question, top_k=3)
    assert hits, f"no hits for {question!r}"
    top_sources = [h.source for h in hits]
    assert expected_source in top_sources, (
        f"[{persona}] expected {expected_source!r} in top-3 for {question!r}, got {top_sources}"
    )


# --------------------------------------------------------------------------- #
# Unit tests for the TF-IDF machinery itself
# --------------------------------------------------------------------------- #


def test_empty_index_returns_empty_list() -> None:
    idx = DocsIndex()
    assert idx.search("anything") == []


def test_chunk_document_respects_headings() -> None:
    doc = {
        "source": "fixture",
        "text": "# A\nfirst section\n\n# B\nsecond section\n\n# C\nthird section",
    }
    chunks = chunk_document(doc)
    assert len(chunks) == 3
    assert all(c.source == "fixture" for c in chunks)
    assert chunks[0].text.startswith("# A")
    assert chunks[1].text.startswith("# B")


def test_load_docs_reads_data_dir() -> None:
    docs = load_docs()
    assert len(docs) >= 9, f"expected at least 9 markdown files, got {len(docs)}"
    assert {"nodes-and-validators", "gas-fees", "bridging"} <= {d["source"] for d in docs}


# --------------------------------------------------------------------------- #
# index_github_jsonl
# --------------------------------------------------------------------------- #


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


def test_index_github_jsonl_adds_pr_chunks(tmp_path: Path) -> None:
    idx = DocsIndex()
    idx.build([DocChunk(text="Unrelated markdown content about bridges.", source="bridging")])
    jsonl = tmp_path / "prs.jsonl"
    _write_jsonl(
        jsonl,
        [
            {
                "number": 101,
                "title": "Add new milestone-based checkpoint verification",
                "body": "This PR introduces a milestone subsystem for faster "
                "checkpoint finality on Polygon PoS.",
                "merged_at": "2026-04-01T00:00:00Z",
                "html_url": "https://github.com/0xPolygon/bor/pull/101",
            },
            {
                "number": 102,
                "title": "Fix txpool eviction race",
                "body": "Resolve a race in txpool eviction that caused stuck "
                "transactions under heavy load.",
                "merged_at": "2026-04-02T00:00:00Z",
                "html_url": "https://github.com/0xPolygon/bor/pull/102",
            },
        ],
    )

    added = idx.index_github_jsonl(jsonl, source_prefix="bor")
    assert added == 2
    assert len(idx.chunks) == 3  # 1 original + 2 PRs

    # Retrieval: query for the PR content should surface the PR URL
    hits = idx.search("milestone checkpoint finality", top_k=3)
    top_sources = [h.source for h in hits]
    assert "https://github.com/0xPolygon/bor/pull/101" in top_sources

    # Metadata should carry the merge date & kind
    pr_chunk = next(
        c for c in idx.chunks if c.source == "https://github.com/0xPolygon/bor/pull/101"
    )
    assert pr_chunk.metadata["kind"] == "pr"
    assert pr_chunk.metadata["date"] == "2026-04-01T00:00:00Z"
    assert pr_chunk.metadata["source_prefix"] == "bor"


def test_index_github_jsonl_handles_commits(tmp_path: Path) -> None:
    """Canonical flat commit schema from github_ingest.py."""
    idx = DocsIndex()
    idx.build([])
    jsonl = tmp_path / "commits.jsonl"
    _write_jsonl(
        jsonl,
        [
            {
                "type": "commit",
                "repo": "heimdall-v2",
                "sha": "abc123",
                "message": "consensus: fix validator rotation off-by-one",
                "authored_at": "2026-03-30T10:00:00+00:00",
                "author": "alice",
                "files": ["consensus/rotate.go"],
                "html_url": "https://github.com/0xPolygon/heimdall-v2/commit/abc123",
            }
        ],
    )
    added = idx.index_github_jsonl(jsonl, source_prefix="heimdall-v2")
    assert added == 1
    chunk = idx.chunks[0]
    assert chunk.source.endswith("/commit/abc123")
    assert "validator rotation" in chunk.text
    assert chunk.metadata["kind"] == "commit"
    assert chunk.metadata["date"] == "2026-03-30T10:00:00+00:00"
    assert chunk.metadata["authored_at"] == "2026-03-30T10:00:00+00:00"
    assert chunk.metadata["author"] == "alice"
    assert chunk.metadata["repo"] == "heimdall-v2"


def test_index_github_jsonl_handles_canonical_pr(tmp_path: Path) -> None:
    """Canonical flat PR schema from github_ingest.py (flat `author`, list[str] files)."""
    idx = DocsIndex()
    idx.build([])
    jsonl = tmp_path / "prs.jsonl"
    _write_jsonl(
        jsonl,
        [
            {
                "type": "pr",
                "repo": "bor",
                "number": 1234,
                "title": "Add milestone checkpoint fast-path",
                "body": "Implements a faster checkpoint finality path using milestones.",
                "merged_at": "2026-04-15T10:30:00+00:00",
                "author": "alice",
                "files": ["consensus/bor/milestone.go"],
                "html_url": "https://github.com/0xPolygon/bor/pull/1234",
            }
        ],
    )
    added = idx.index_github_jsonl(jsonl, source_prefix="bor")
    assert added == 1
    chunk = idx.chunks[0]
    assert chunk.source == "https://github.com/0xPolygon/bor/pull/1234"
    assert chunk.metadata["kind"] == "pr"
    assert chunk.metadata["author"] == "alice"
    assert chunk.metadata["repo"] == "bor"
    assert chunk.metadata["number"] == 1234
    assert chunk.metadata["date"] == "2026-04-15T10:30:00+00:00"
    assert chunk.metadata["merged_at"] == "2026-04-15T10:30:00+00:00"


def test_index_github_jsonl_missing_file_returns_zero(tmp_path: Path) -> None:
    idx = DocsIndex()
    idx.build([])
    result = idx.index_github_jsonl(tmp_path / "does-not-exist.jsonl", source_prefix="bor")
    assert result == 0


def test_index_github_jsonl_skips_blank_and_malformed(tmp_path: Path) -> None:
    idx = DocsIndex()
    idx.build([])
    jsonl = tmp_path / "prs.jsonl"
    jsonl.write_text(
        "\n".join(
            [
                "",
                "not-json",
                json.dumps(
                    {
                        "number": 1,
                        "title": "ok",
                        "body": "valid",
                        "html_url": "https://example/pr/1",
                    }
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    added = idx.index_github_jsonl(jsonl, source_prefix="bor")
    assert added == 1
