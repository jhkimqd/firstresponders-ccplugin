---
name: answer-faq
description: |
  Answer static Polygon PoS / CDK questions from bundled public docs. Use when the user
  asks anything covered by FAQ_COVERAGE.md — node operations (Bor/Heimdall setup, sync,
  peers, RPC methods, snapshots, pruning), developer topics (chain IDs, deployment, gas
  estimation, bridging, WebSockets, ERC standards, tooling like Hardhat/Foundry/ethers/viem),
  validator topics (staking, slashing, rewards, checkpointing, jailing, governance),
  RPC provider operations (load balancing, failover, caching, rate limiting, Bor tuning
  flags, `debug_*`/`trace_*`/`bor_*` namespaces), gas & fees (EIP-1559 on Polygon, stuck
  tx handling), POL/MATIC migration, and audits/bounty. Prefer this skill over ad-hoc
  web search for any Polygon question that isn't about live network state.
---

# answer-faq

Answer FAQ-class Polygon questions by retrieving cited passages from the bundled public
doc corpus at `data/docs/`.

## When to use

Use this skill when the question is **static knowledge** — the answer does not depend on
the current block, current validator set, active incidents, or recently-merged code. If
the question is about live state ("is the network healthy right now?", "plot gas prices
for the last 500 blocks", "what changed in Bor this week?"), defer to `network-health`,
`investigate-blocks`, or `summarize-upgrades` instead.

A concrete trigger list lives in `FAQ_COVERAGE.md`. Representative prompts:

- "What's the minimum stake to become a Polygon validator?"
- "How do I enable the `debug` namespace on Bor?"
- "Does Polygon CDK support `CREATE2`?"
- "What is the withdrawal time from Polygon PoS to Ethereum?"
- "How does EIP-1559 work on Polygon?"
- "Has MATIC been replaced by POL?"

## Freshness policy (non-negotiable)

This plugin follows the **≤ 30-day freshness rule** documented in `FRESHNESS_POLICY.md` at
the repo root. Before producing any answer from this skill:

1. **Every answer must be grounded in a source whose upstream reference is ≤ 30 days old**
   (repo `pushed_at`, PR/commit date, or blog post date), OR must explicitly disclose that
   freshness cannot be verified.
2. **Never fabricate currency.** If the retrieved chunk names a specific version, address,
   fee, APY, minimum stake, parameter, or API shape, and the chunk does not itself cite a
   fresh upstream, flag the uncertainty in your answer rather than relaying it cleanly.
3. **Prefer "I don't know, check <X>" over a plausible-sounding guess.** First responders
   relay these answers to real users across Slack / Telegram / Discord. A confident wrong
   answer propagates; a hedge prompts verification.

Read `FRESHNESS_POLICY.md` for the full rule, the list of currently-authoritative repos,
and the list of deprecated references that must not be cited as authoritative.

## Workflow

1. **Retrieve** top matches from the doc corpus:
   ```bash
   uv run python skills/answer-faq/scripts/search.py "<user question>" --k 5
   ```
   The script prints a JSON array. Each element has `source` (relative path under
   `data/docs/`), `text` (the chunk), and `score` (TF-IDF cosine similarity).

2. **Check freshness signals in the retrieved chunks**:
   - The doc's opening **Authoritative sources** callout (if present) names the upstream
     repos. If a chunk quotes specifics (addresses, parameters, minimum-stake values) that
     are not traceable to one of those authoritative repos, downgrade confidence.
   - If the chunk references `maticnetwork/polygon-edge`, legacy `maticnetwork/heimdall`,
     `0xPolygon/agglayer` (archived), or any repo called out as deprecated in
     `FRESHNESS_POLICY.md`, **do not cite it as authoritative** — use the citation only to
     warn the user that the tooling is deprecated.
   - For time-sensitive facts (versions, addresses, fees, APY, minimum stakes, parameter
     values, API shapes): if the chunk is not dated and its upstream repo's recency is not
     verifiable from what you have, say so in the answer.

3. **Compose the answer**. Use only content from the retrieved chunks. If the chunks
   don't actually answer the question, say so explicitly — do not fall back to training
   knowledge and present it as if it came from the docs.

4. **Cite**. Every factual claim must be followed by the `data/docs/<file>.md` path it
   came from. When responders copy/paste into Slack/Telegram/Discord, the citation travels
   with the answer.

5. **Tune `--k` when needed**. For narrow questions (single-doc answer) `k=3` is enough.
   For cross-cutting questions that span multiple docs (e.g. bridging + gas + POL), try
   `k=5` or `k=8`.

## Output shape

```
<concise answer in plain prose, 1–4 short paragraphs>

Sources:
- data/docs/<file>.md
- data/docs/<other>.md
```

If nothing relevant is retrieved, respond:

> "I couldn't find this in the bundled docs (`data/docs/`). This might be a live-state
> question — try `network-health` or `investigate-blocks` — or it may need a
> `refresh-knowledge` run if it's about a recent upgrade."

## Never do

- Don't invoke an external web search unless the user explicitly asks — the whole point
  of the corpus is vetted offline answers.
- Don't cite `FAQ_COVERAGE.md`; that's a trigger catalogue, not a source of truth.
- Don't wrap the bash command in extra orchestration — one `search.py` call, then compose.
