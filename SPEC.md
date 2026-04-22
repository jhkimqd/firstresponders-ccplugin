# `polygon-firstresponders` — Claude Code Plugin Spec

> Self-contained specification for building a Claude Code plugin that Polygon first responders use to answer user inquiries across Slack / Telegram / Discord / etc. Start any fresh Claude Code session in this directory with this spec as the entry point — no prior conversation context required.

---

## 1. Context & Motivation

Polygon's first responders handle incoming user questions about the Polygon PoS stack. Questions arrive across many channels (Slack, Telegram, Discord, support tickets) and responders copy/paste answers regardless of where the bot lives. Scope of questions spans:

- **Static FAQ** — node ops, dev questions, validator ops, RPC provider tuning, bridging, gas/fees, POL migration. See `FAQ_COVERAGE.md` (ported from `polygon-chatbot/LIKELY_QUESTIONS.md`) for the full catalogue.
- **Cutting-edge state beyond public docs** — recent commits and merged PRs in [`0xPolygon/bor`](https://github.com/0xPolygon/bor) and [`0xPolygon/heimdall-v2`](https://github.com/0xPolygon/heimdall-v2). Needed because upgrades ship faster than public docs.
- **Live investigation** — poll block ranges, render charts (e.g., gas-price scatter + line-of-best-fit over a block range), query Datadog metrics/monitors/incidents, optionally spin up test networks via `kurtosis-pos`.

### Why a Claude Code plugin (not a Slack bot, not an MCP server)

A prior architecture (see `/home/jihwankim/polygon-chatbot/ARCHITECTURE.md`) split this into an MCP server + a Slack bot. Both have problems:

- **External MCP server** is hard to maintain and can be unreliable; public exposure multiplies abuse and token-cost surface.
- **Slack bot with a centralized key** means Polygon pays per-token for every query. A per-user BYO-key registry in Slack is awkward UX.
- **Slack bot with `LLM_BACKEND=ollama`** can't do tool-calling, so investigation tasks (plotting, RPC polling via tools) don't work.

A **Claude Code plugin** solves all three:

- **Zero org token cost** — each responder runs the plugin against their own Claude Code subscription. No "bring your own key" plumbing needed; Claude Code itself is the harness.
- **Composes natively with existing assets** — imports the `kurtosis-pos` skill ([PR #528](https://github.com/0xPolygon/kurtosis-pos/pull/528)) and wires the internal Datadog MCP server via `.mcp.json`. Neither needs to be re-implemented.
- **Code execution is first-class** — skills can call Python scripts (matplotlib plots, concurrent RPC polling, GitHub ingestion) without a server-side agent loop.
- **Simple distribution** — `git pull` to update. No deployed service, no cron infra required (responders run ingestion locally when they want fresh data).
- **Surface-agnostic** — responders copy/paste from the Claude Code terminal into whatever medium (Slack/Telegram/Discord) the original question came from. Matches how they already work.

---

## 2. Objective

Ship `polygon-firstresponders`, a Claude Code plugin at this repo (`/home/jihwankim/firstresponders-ccplugin`), that lets any Polygon first responder:

1. Answer FAQ-class questions with citations to bundled public docs.
2. Summarize recent Bor / Heimdall-v2 upgrades from locally-ingested GitHub commit+PR data.
3. Investigate live network state — block polling + charting, Datadog monitors/incidents, optional Kurtosis test network spin-up.
4. Refresh the GitHub knowledge base on demand (per-responder local state).

**Non-goals for v1:**
- No server deployment, no Slack/Discord bot, no shared infra.
- No LLM SDK code in the plugin — Claude Code owns the LLM.
- No vector DB — TF-IDF is enough for the corpus size.
- No public-facing surface; plugin is for internal responder use only.

---

## 3. Source repos to reuse

The prior repo at `/home/jihwankim/polygon-chatbot/` contains working pieces we should port rather than rewrite.

| New file | Source file | What to take |
|---|---|---|
| `src/polygon_frp/rpc.py` | `polygon-chatbot/slackbot/src/polygon_bot/integrations/polygon_rpc.py:15-81` | Keep `_rpc_call`, `get_chain_status`, `get_recent_blocks`. Drop dependency on `polygon_bot.config.settings`; accept `rpc_url` as a constructor/function argument instead. |
| `src/polygon_frp/docs_index.py` | `polygon-chatbot/mcp-server/src/polygon_mcp/docs.py:12-150` | The entire TF-IDF `DocsIndex` class and chunking logic. Extend to index GitHub JSONL records alongside markdown (one chunk per PR/commit). |
| `data/docs/*.md` | `polygon-chatbot/data/docs/` | Copy all 9 markdown files verbatim: `agglayer.md`, `bridging.md`, `deploy-contract-pos.md`, `gas-fees.md`, `nodes-and-validators.md`, `polygon-cdk.md`, `polygon-pos-overview.md`, `rpc-endpoints.md`, `smart-contracts.md`. |
| `FAQ_COVERAGE.md` | `polygon-chatbot/LIKELY_QUESTIONS.md` | Copy verbatim; use as the acceptance-test fixture for FAQ retrieval. |
| `tests/test_docs_index.py` | Adapt from `polygon-chatbot/slackbot/tests/test_synthesis.py` retrieval checks | Extend with ≥20 questions sampled from `FAQ_COVERAGE.md`; assert correct source doc in top-3 hits. |

**Do NOT port**: the Anthropic tool-calling loop (`slackbot/src/polygon_bot/ops/agent.py`), the Ollama client (`slackbot/src/polygon_bot/ollama_client.py`), the LLM factory (`slackbot/src/polygon_bot/llm.py`), the Slack-Bolt glue (`slackbot/src/polygon_bot/main.py`), or the MCP server package (`mcp-server/src/polygon_mcp/server.py`). Those belong to the retired architectures.

---

## 4. Target repo layout

```
firstresponders-ccplugin/
├── SPEC.md                              # this file
├── README.md                            # install + usage for responders
├── FAQ_COVERAGE.md                      # ported from LIKELY_QUESTIONS.md
├── plugin.json                          # Claude Code plugin manifest
├── .mcp.json                            # Datadog MCP + local polygon-frp-rpc MCP
├── .gitignore                           # excludes data/github/, /tmp plots, venv
├── pyproject.toml                       # uv-managed, Python 3.10+
├── skills/
│   ├── answer-faq/
│   │   ├── SKILL.md                     # trigger rules + workflow
│   │   └── scripts/search.py            # calls src/polygon_frp/docs_index.py
│   ├── summarize-upgrades/
│   │   ├── SKILL.md
│   │   └── scripts/summarize.py         # reads data/github/*/prs.jsonl
│   ├── investigate-blocks/
│   │   ├── SKILL.md
│   │   └── scripts/poll_and_plot.py     # uses rpc.py + plot.py
│   ├── network-health/
│   │   └── SKILL.md                     # composes Datadog MCP + polygon-frp-rpc MCP (prompt-only; no script)
│   └── refresh-knowledge/
│       ├── SKILL.md
│       └── scripts/ingest.py            # entry point to src/polygon_frp/github_ingest.py
├── src/polygon_frp/
│   ├── __init__.py
│   ├── rpc.py                           # ported (see reuse map)
│   ├── docs_index.py                    # ported (see reuse map)
│   ├── github_ingest.py                 # new
│   └── plot.py                          # new
├── data/
│   ├── docs/                            # 9 public markdown files (committed)
│   └── github/                          # gitignored; populated by ingest.py
│       ├── .cursor.json
│       ├── bor/
│       │   ├── prs.jsonl
│       │   └── commits.jsonl
│       └── heimdall-v2/
│           ├── prs.jsonl
│           └── commits.jsonl
├── systemd/
│   ├── firstresponders-ingest.service   # optional template
│   └── firstresponders-ingest.timer     # optional template
└── tests/
    ├── test_docs_index.py               # ported + extended
    ├── test_github_ingest.py            # new
    ├── test_plot.py                     # new
    └── test_rpc.py                      # new (mock httpx)
```

---

## 5. Components

### 5.1 Skills

Each skill is a Markdown file (`SKILL.md`) in a dedicated directory. Claude Code auto-discovers them via `plugin.json`. Skill authoring rules:

- **Frontmatter**: `name`, `description` (concrete triggers — "Use when the user asks about X, Y, Z"), and the skill type.
- **Workflow body**: how Claude should chain tools/scripts. Prefer scripts for deterministic work (polling, plotting, ingestion); prefer MCP tools for live queries (Datadog); prefer retrieval + generation for Q&A.
- **Output shape**: every FAQ answer must cite `data/docs/<file>.md` paths; every upgrade summary must cite PR URLs; every chart skill must return the saved PNG path.

| Skill | Trigger summary | Calls |
|---|---|---|
| `answer-faq` | Any static question covered in `FAQ_COVERAGE.md` (node ops, dev, validator, RPC provider, bridging, gas, POL migration). | `scripts/search.py` → `docs_index.py` TF-IDF; Claude composes cited answer. |
| `summarize-upgrades` | "What changed in Bor / Heimdall recently?", "Any new checkpoint logic since <date>?" | `scripts/summarize.py` reads `data/github/*/prs.jsonl`, filters by date/keywords. |
| `investigate-blocks` | "Plot gas prices for blocks X to Y", "Show tx count trend for last 500 blocks". | `scripts/poll_and_plot.py` → `rpc.py` + `plot.py` → returns PNG path at `/tmp/polygon-frp-<timestamp>.png`. |
| `network-health` | "Is the network okay?", "Any active Polygon incidents?" | Pure prompt skill — composes Datadog MCP tools + polygon-frp-rpc MCP tools (`get_chain_status`). |
| `refresh-knowledge` | "Refresh the GitHub data", "Pull latest bor PRs". | `scripts/ingest.py` → `github_ingest.py`. |

### 5.2 MCP wiring (`.mcp.json`)

Register two MCPs. Exact URLs/env for the internal Datadog MCP must be filled by the installer:

```json
{
  "mcpServers": {
    "polygon-datadog": {
      "command": "<FILL: internal Datadog MCP command or URL>",
      "env": {
        "DATADOG_API_KEY": "${DATADOG_API_KEY}",
        "DATADOG_APP_KEY": "${DATADOG_APP_KEY}",
        "DATADOG_SITE": "${DATADOG_SITE:-datadoghq.com}"
      }
    },
    "polygon-frp-rpc": {
      "command": "uv",
      "args": ["run", "python", "-m", "polygon_frp.mcp_rpc"],
      "env": {
        "POLYGON_RPC_URL": "${POLYGON_RPC_URL:-https://polygon.drpc.org}"
      }
    }
  }
}
```

Implement `src/polygon_frp/mcp_rpc.py` as a thin stdio MCP exposing three tools: `get_chain_status`, `get_recent_blocks(count)`, `get_gas_usage(block_count)`. Mirror the tools in `polygon-chatbot/mcp-server/src/polygon_mcp/server.py` but without the `search_polygon_docs` tool (that's a skill-level concern now).

### 5.3 `plugin.json`

Manifest Claude Code reads on install. Must declare:

- Plugin name, version, description.
- Skill directories (`skills/*`).
- MCP config path (`.mcp.json`).
- Optional dependency on the `kurtosis-pos` skill so Claude can invoke it for test-network investigations.
- Required Python version and the `uv` lockfile location.

### 5.4 `github_ingest.py` (new)

Incremental GitHub pull:

- Target repos: `0xPolygon/bor`, `0xPolygon/heimdall-v2`.
- Uses `PyGithub` (or raw httpx — prefer `PyGithub` for its pagination helpers).
- Reads cursor from `data/github/.cursor.json`: `{"bor": {"prs_since": "...", "commits_since": "..."}, "heimdall-v2": {...}}`.
- Fetches **merged** PRs (not drafts, not closed-unmerged) with `title`, `body`, `merged_at`, `user.login`, `files[].filename`, `html_url`.
- Fetches commits on the default branch with `sha`, `commit.message`, `commit.author.date`, `commit.author.name`, `files[].filename`, `html_url`.
- Writes newline-delimited JSON to `data/github/{repo}/prs.jsonl` and `commits.jsonl` (append, deduped by `sha` / PR number).
- Advances the cursor after a successful write.
- Auth: reads `GITHUB_TOKEN` from env. If unset, logs a warning and proceeds unauthenticated (60 req/hr limit).
- Exit codes: `0` success, `1` rate-limit hit, `2` network error, `3` auth failure.

### 5.5 `plot.py` (new)

- `render_block_chart(blocks: list[dict], metric: str, out_path: Path) -> Path` — scatter of `metric` (`gas_price_gwei`, `gas_used_ratio`, `tx_count`) vs. block number; overlays a `numpy.polyfit` line of best fit; saves PNG.
- `render_timeseries(points: list[tuple[datetime, float]], title: str, out_path: Path) -> Path` — for Datadog-derived data.
- Uses `matplotlib` with the `Agg` backend (no X display needed).

### 5.6 `rpc.py` (ported)

- Lift `_rpc_call`, `get_chain_status`, `get_recent_blocks` from `polygon-chatbot/slackbot/src/polygon_bot/integrations/polygon_rpc.py`.
- Add `get_blocks_in_range(start: int, end: int, concurrency: int = 20) -> list[dict]` — bounded concurrent fetch for investigation skills. Use an `asyncio.Semaphore`.
- Parameter, not global: `rpc_url` passed in, no dependency on a `settings` singleton.

### 5.7 `docs_index.py` (ported + extended)

- Port `DocsIndex` class verbatim.
- Add `index_github_jsonl(path: Path, source_prefix: str)` so PRs/commits participate in the same TF-IDF corpus. Each PR body becomes a chunk; `source` field carries the PR URL.
- `answer-faq` searches over markdown only; `summarize-upgrades` can optionally search over the GitHub-indexed chunks filtered by date window.

---

## 6. Commands / developer workflow

Project uses `uv` (already the convention in the old repo's Python tooling).

```bash
# Setup
uv sync                                       # install deps from pyproject.toml + uv.lock
cp .env.example .env                          # fill GITHUB_TOKEN, DATADOG_*, POLYGON_RPC_URL

# Populate knowledge base (first run)
uv run python -m polygon_frp.github_ingest --repos bor,heimdall-v2 --since 30d

# Tests
uv run pytest
uv run pytest tests/test_docs_index.py -v     # focused retrieval tests

# Lint / format
uv run ruff check .
uv run ruff format .

# Plot smoke test
uv run python -m polygon_frp.plot --demo      # writes /tmp/polygon-frp-demo.png

# Install plugin into Claude Code
# (documented in README.md; typically a `claude plugins install <path>` invocation)
```

---

## 7. Code style & conventions

- **Python 3.10+**, type hints throughout, `from __future__ import annotations`.
- **`uv` for dependency management**, `ruff` for lint + format (mirror `polygon-chatbot/slackbot/pyproject.toml` settings).
- **Async for I/O**: all RPC and GitHub calls via `httpx.AsyncClient` with explicit timeouts.
- **No globals for config** — functions accept URL/token args; CLI entry points read env and pass down.
- **Small functions, no LLM glue** — every module should be testable without a Claude Code session running.
- **Deterministic scripts**: skill-invoked scripts print structured JSON or a file path on stdout so Claude can parse cleanly.

---

## 8. Testing strategy

- **Unit**: mock `httpx.AsyncClient` for RPC tests; mock `PyGithub` for ingestion tests; test TF-IDF retrieval with fixture corpus.
- **FAQ acceptance**: sample ≥20 questions from `FAQ_COVERAGE.md` across all four personas (node op / dev / validator / RPC provider) and assert the correct source doc is in top-3 hits from `docs_index.py`. Keep this as a living regression test.
- **Ingestion idempotency**: running `github_ingest` twice on the same range must not duplicate rows.
- **Plot smoke**: `render_block_chart` produces a PNG > 1KB with matplotlib's `Agg` backend.
- **MCP smoke**: start `polygon-frp-rpc` MCP, call `get_chain_status` via an MCP test client, verify shape.
- **End-to-end in Claude Code** (manual):
  1. "What's the minimum stake to become a Polygon validator?" → `answer-faq` cites `data/docs/nodes-and-validators.md`.
  2. "What changed in Bor this week?" → `summarize-upgrades` lists merged PRs with URLs.
  3. "Plot gas prices for the last 500 blocks." → `investigate-blocks` returns PNG path + trend description.
  4. "Is the network healthy right now?" → `network-health` composes Datadog monitors + `get_chain_status`.

---

## 9. Boundaries

### Always do
- Cite sources in every FAQ answer (file path for docs, URL for PRs/commits).
- Treat `data/github/` as per-responder state (gitignored, never committed).
- Pass RPC / API URLs as function arguments; never hardcode production endpoints.
- Surface the PNG path to the user whenever a plot is generated.
- Log structured errors and exit with distinct codes from scripts so Claude can react.

### Ask first
- Any change to `.mcp.json` that would require new env vars from the responder.
- Adding a new external dependency that needs a paid API key.
- Any "cleanup" that touches `data/docs/` — the old repo's doc corpus is the baseline; edits need explicit review.
- Publishing this plugin to the official Polygon GitHub org (currently staged locally at `/home/jihwankim/firstresponders-ccplugin/`).

### Never do
- Ship an LLM SDK (Anthropic, OpenAI, Ollama) inside this plugin — Claude Code owns the LLM.
- Deploy a long-lived server (no FastAPI, no Slack Socket Mode, no webhook endpoint).
- Commit `data/github/` contents or any secrets.
- Embed production keys (Datadog, Incident.io, GitHub) in git or in skill prompts.
- Re-introduce a vector DB (Qdrant/Chroma) — TF-IDF is the design decision for v1.
- Build a generic "LLM provider" abstraction — it's out of scope; Claude Code is the only LLM harness.

---

## 10. Build order (smallest verifiable slices)

Recommended as a parallel-agent team workstream sequence. Each slice ships something testable.

1. **Scaffold**: `pyproject.toml`, `plugin.json`, `.mcp.json` (stubs), `.gitignore`, `README.md`, `FAQ_COVERAGE.md` (ported). Verify `uv sync` runs clean.
2. **Port `rpc.py` + `docs_index.py`**: copy from source files (see §3), drop `settings` dependency, add tests. Land `tests/test_docs_index.py` with ≥20 questions from `FAQ_COVERAGE.md`.
3. **`answer-faq` skill**: `SKILL.md` + `scripts/search.py`. Manual smoke: 5 questions from `FAQ_COVERAGE.md`.
4. **`github_ingest.py` + `refresh-knowledge` skill**: incremental pull with cursor, JSONL output, mocked tests.
5. **`summarize-upgrades` skill**: reads JSONL, groups by week, cites PR URLs.
6. **`plot.py` + `investigate-blocks` skill**: block-range concurrency in `rpc.py`, matplotlib Agg backend.
7. **`mcp_rpc.py` + `.mcp.json` polygon-frp-rpc entry**: stdio MCP exposing three tools.
8. **`network-health` skill + Datadog MCP wiring**: prompt-only skill; plug the internal Datadog MCP command into `.mcp.json`.
9. **kurtosis-pos dependency**: link in `plugin.json` so Claude can invoke it.
10. **`systemd/` templates**: optional nightly timer for responders who want it.
11. **README**: install instructions (Claude Code prerequisites, `uv`, optional `GITHUB_TOKEN`, Datadog MCP env).

## 11. File ownership for parallel agents

If spawning a team, split ownership along these axes to avoid conflicts:

| Agent | Owns |
|---|---|
| Agent A (core lib) | `src/polygon_frp/rpc.py`, `src/polygon_frp/docs_index.py`, `src/polygon_frp/mcp_rpc.py`, `tests/test_rpc.py`, `tests/test_docs_index.py` |
| Agent B (ingestion) | `src/polygon_frp/github_ingest.py`, `skills/refresh-knowledge/*`, `skills/summarize-upgrades/*`, `tests/test_github_ingest.py` |
| Agent C (investigation) | `src/polygon_frp/plot.py`, `skills/investigate-blocks/*`, `skills/network-health/*`, `tests/test_plot.py` |
| Agent D (FAQ + scaffolding) | `skills/answer-faq/*`, `pyproject.toml`, `plugin.json`, `.mcp.json`, `.gitignore`, `README.md`, `FAQ_COVERAGE.md`, `data/docs/*` (copy task) |

Integration points (coordinated via messaging, not shared file writes): `docs_index.py` API (A → D), `rpc.py` API (A → C), JSONL schema (B → A for `index_github_jsonl`).

---

## 12. Open items for the next session to confirm

1. **Datadog MCP command/URL**: need the exact internal MCP server entry (command, env vars) to finalize `.mcp.json`.
2. **Publish target**: stays in `~/firstresponders-ccplugin` for now, or push to `0xPolygon/firstresponders-ccplugin` (or personal fork) once v1 passes acceptance tests?
3. **Investigation scope confirmation**: in the prior planning round you selected both the three specific investigation skills **and** "defer investigation — Q&A only in v1". This spec assumes **all three investigation skills ship in v1** (`investigate-blocks`, `network-health`, `summarize-upgrades`). If you meant Q&A-only, collapse skills to `answer-faq` + `summarize-upgrades` + `refresh-knowledge` and drop `investigate-blocks` + `network-health` + `plot.py` + the `mcp_rpc.py` investigation wiring.
4. **kurtosis-pos import mechanism**: confirm whether the skill is installable via plugin dependency (needs the skill published somewhere Claude Code can reach) or whether we vendor a copy under `skills/kurtosis-pos/`.

---

## 13. Reference paths

- **Old repo (read-only reference for porting)**: `/home/jihwankim/polygon-chatbot/`
  - Architecture doc: `/home/jihwankim/polygon-chatbot/ARCHITECTURE.md`
  - FAQ source: `/home/jihwankim/polygon-chatbot/LIKELY_QUESTIONS.md`
  - RPC client: `/home/jihwankim/polygon-chatbot/slackbot/src/polygon_bot/integrations/polygon_rpc.py`
  - TF-IDF indexer: `/home/jihwankim/polygon-chatbot/mcp-server/src/polygon_mcp/docs.py`
  - MCP tools reference: `/home/jihwankim/polygon-chatbot/mcp-server/src/polygon_mcp/server.py`
  - Public docs: `/home/jihwankim/polygon-chatbot/data/docs/*.md`
- **New repo (this directory)**: `/home/jihwankim/firstresponders-ccplugin/`
- **External**:
  - kurtosis-pos PR: https://github.com/0xPolygon/kurtosis-pos/pull/528
  - Bor repo: https://github.com/0xPolygon/bor
  - Heimdall-v2 repo: https://github.com/0xPolygon/heimdall-v2
