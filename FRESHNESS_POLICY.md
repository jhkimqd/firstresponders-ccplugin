# Freshness Policy

> **Plugin-wide rule.** First responders relay answers across Slack, Telegram, Discord, and support channels. A wrong-but-confident answer about Polygon state, tooling, or contract addresses can mislead many users. Staleness is the most common failure mode for a static-corpus plugin. This document is the single source of truth for how skills handle recency; every answer-producing skill links here.

## The rule

**1-month cutoff.** Any factual answer this plugin produces must be grounded in a source that is ≤ 30 days old as of the current date, OR must explicitly disclose that it cannot be freshness-verified.

"Source" means any of:

- A GitHub repository whose `pushed_at` is within the last 30 days.
- A PR, commit, issue, release, or blog post dated within the last 30 days.
- A bundled doc (`data/docs/*.md`) whose referenced authoritative repos are all within the 30-day window. Each such doc opens with an **Authoritative sources** callout listing the upstream repos — that's the verifiable ground truth, not the prose.
- A live RPC / Datadog response (always fresh by construction).

## When the information is stale or unverifiable

**Be explicit. Never fabricate recency.** If you cannot verify that the answer is grounded in a ≤ 30-day-old source, say so, in one of these forms (pick the one that fits):

- *"I found this in `data/docs/FILE.md`, but the underlying repo `ORG/REPO` was last updated DATE (more than 30 days ago). This answer may be out of date — verify against the live repo before relaying."*
- *"The bundled docs don't cover this question directly. Run `refresh-knowledge` to pull the latest Bor/Heimdall-v2 state and retry, or check the relevant upstream repo manually."*
- *"I don't have this information with the freshness guarantee required by this plugin. Don't relay a guess — escalate or check the authoritative source directly."*

**Never** quote a specific version number, address, minimum stake, fee, APY, parameter value, or API shape from memory. If it's not in a retrieved chunk that cites a fresh source, flag it.

## What counts as "authoritative" for Polygon

| Domain | Canonical source |
|---|---|
| Bor (PoS execution) | `0xPolygon/bor` |
| Heimdall v2 (PoS consensus) | `0xPolygon/heimdall-v2` |
| PoS devnet / topology | `0xPolygon/kurtosis-pos` |
| CDK devnet / topology | `0xPolygon/kurtosis-cdk` |
| CDK execution clients | `0xPolygon/cdk-erigon`, `0xPolygon/erigon` |
| PoS staking / bridge contracts | `0xPolygon/pos-contracts` |
| PoS bridge SDK | `0xPolygon/matic.js` |
| AggLayer unified bridge SDK | `0xPolygon/lxly.js` |
| zkEVM bridge backend | `0xPolygon/zkevm-bridge-service` |
| AggLayer implementation | `agglayer/agglayer` (note: `0xPolygon/agglayer` is **archived**) |
| Liquid staking (sPOL) | `0xPolygon/sPOL-contracts` |
| Operator tooling | `0xPolygon/matic-cli`, `0xPolygon/polygon-cli`, `0xPolygon/panoptichain` |
| Official docs | https://docs.polygon.technology |

## Explicitly not to cite

Do not cite these as authoritative. If a bundled doc still references them, treat the reference as a warning rather than a recommendation:

- `maticnetwork/polygon-edge` — repository deleted.
- `maticnetwork/heimdall` (v1) — archived; Heimdall v2 is canonical.
- `maticnetwork/node-ansible` — unmaintained.
- `0xPolygon/agglayer` — archived 2024-08; current is `agglayer/agglayer`.
- `maticnetwork/maticjs-ethers` — stale since 2024.

## Operator workflow: keep the corpus fresh

The freshness guarantee is only as good as the corpus. Responders and maintainers share responsibility:

1. **Before each release / tagged version**: run the `scripts/audit_freshness.sh`-style check (or manually curl `api.github.com/repos/<repo>` for every repo URL in `data/docs/*.md`). Flag any repo with `pushed_at` > 30 days or `archived: true`. Update the docs or escalate to remove the reference.
2. **`refresh-knowledge` skill** keeps the PR/commit corpus under `data/github/` current. Run it before any `summarize-upgrades` session — the skill already warns when its data is stale, but responders should proactively refresh at session start.
3. **`FAQ_COVERAGE.md`** acceptance tests (`tests/test_docs_index.py`) catch retrieval drift when docs are edited — keep them green.
4. **When in doubt, add a new doc rather than edit a stale one**: staleness often indicates a tooling migration (e.g., polygon-edge → removed). Adding a fresh doc with an **Authoritative sources** callout is usually clearer than patching an old doc.

## For skills

Each answer-producing skill links to this file in its SKILL.md and must enforce the rule in-flow. See:

- `skills/answer-faq/SKILL.md`
- `skills/summarize-upgrades/SKILL.md`

`investigate-blocks`, `network-health`, and `refresh-knowledge` query live data and are exempt — their output is fresh by construction.
