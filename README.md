# polygon-firstresponders

A Claude Code plugin for Polygon first responders. Answer FAQ-class questions with cited
sources, summarize recent Bor / Heimdall-v2 upgrades from locally-ingested GitHub data,
investigate live network state (block polling + charts, Datadog monitors), and optionally
spin up test networks via `kurtosis-pos`.

No server, no shared infra, no per-org token cost — each responder runs this against their
own Claude Code subscription.

---

## Why a plugin (and not a Slack bot)?

- **Zero org token cost** — Claude Code is the harness; no BYO-key plumbing.
- **Surface-agnostic** — responders copy/paste from the terminal into Slack / Telegram /
  Discord / tickets, matching how they already work.
- **Native composition** — bundles a `polygon-frp-rpc` MCP, uses Claude's managed Datadog MCP,
  and can vendor additional skills (e.g. `kurtosis-pos`) under `skills/` as needed.
- **Code execution is first-class** — skills call Python scripts (matplotlib plots,
  concurrent RPC polling, GitHub ingestion) without a server-side agent loop.

See `SPEC.md` for the full architecture rationale.

---

## Prerequisites

- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and logged in.
- Python 3.10+.
- [`uv`](https://docs.astral.sh/uv/) for dependency management:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Optional but recommended:
  - `GITHUB_TOKEN` — personal access token with `public_repo` scope. Without it,
    `refresh-knowledge` falls back to 60 req/hr unauthenticated GitHub access.
  - A Claude-managed **Datadog** integration connected to your Claude account, required
    for `network-health` to query monitors, metrics, and incidents (see
    [Connecting the Datadog MCP](#connecting-the-datadog-mcp) below).

---

## Install

### Recommended — via the bundled marketplace (no clone needed)

The repo ships `.claude-plugin/marketplace.json` so Claude Code can install the plugin
directly from GitHub — no manual clone, no `uv sync` to bootstrap. Run from any shell:

```bash
# Add this repo as a marketplace (one-time per machine)
claude plugin marketplace add 0xPolygon/firstresponders-ccplugin

# Install the plugin (pins to the tagged version; re-run to pick up updates)
claude plugin install polygon-firstresponders@polygon-firstresponders

# Later: update to the latest tag
claude plugin marketplace update polygon-firstresponders
claude plugin update polygon-firstresponders
```

Then provision local secrets + knowledge base (the plugin can run read-only FAQ without
these, but `refresh-knowledge`, `investigate-blocks`, and `network-health` need them):

```bash
export GITHUB_TOKEN=ghp_...                           # optional, raises GitHub rate limits
export POLYGON_RPC_URL=https://polygon.drpc.org       # override default if desired

# Populate the GitHub knowledge base — run once, then whenever you want fresh PR data
claude /polygon-firstresponders:refresh-knowledge     # or ask Claude: "refresh the github data"
```

Restart your Claude Code session after install so skills and the bundled
`polygon-frp-rpc` MCP register.

### Alternative — clone + load locally (iterative plugin development)

Use this flow if you're editing the plugin itself, not just using it:

```bash
# 1. Clone
git clone https://github.com/0xPolygon/firstresponders-ccplugin.git ~/firstresponders-ccplugin
cd ~/firstresponders-ccplugin

# 2. Install Python deps
uv sync

# 3. Set up environment
cp .env.example .env
$EDITOR .env

# 4. Load ephemeral (no install — overrides anything installed):
claude --plugin-dir ~/firstresponders-ccplugin
# or install from the local path:
claude plugin marketplace add ~/firstresponders-ccplugin --scope local
claude plugin install polygon-firstresponders@polygon-firstresponders --scope local
```

The bundled `polygon-frp-rpc` MCP auto-starts when Claude Code launches the plugin — no
separate install step.

### Connecting the Datadog MCP

The `network-health` skill queries Datadog through **Claude's managed Datadog
integration**, which is authenticated per-user through Claude (not through this plugin's
`.mcp.json`). Each responder connects it once:

1. In Claude Code, run `/mcp` (or visit your Claude account settings → Integrations).
2. Locate the Datadog integration and click **Connect**.
3. Authenticate with your Polygon Datadog account (OAuth or API keys, per your org's
   policy).
4. Confirm the Datadog tools appear by running `/mcp` again — you should see tools like
   `list_monitors`, `list_incidents`, etc. under the Datadog MCP.

`network-health` discovers these tools at runtime; it does not require a specific tool
namespace. If a responder has not connected Datadog, the skill falls back to an RPC-only
view and flags the missing signal explicitly.

> This plugin's `.mcp.json` only declares `polygon-frp-rpc` (bundled with the repo). The
> Datadog MCP is intentionally **not** declared here — it is a per-user Claude integration,
> not a plugin-local stdio server.

### Updating the plugin

If you installed via the marketplace:

```bash
claude plugin marketplace update polygon-firstresponders
claude plugin update polygon-firstresponders
# Restart your Claude Code session.
```

If you're running a local clone:

```bash
cd ~/firstresponders-ccplugin
git pull
uv sync                # pick up any dep changes
# Restart your Claude Code session.
```

### Publishing a new version (maintainers)

1. Bump `version` in **both** `.claude-plugin/plugin.json` and
   `.claude-plugin/marketplace.json` (keep them in sync — marketplace consumers compare
   against the marketplace entry).
2. `claude plugin validate .` — must pass.
3. `uv run pytest` — must pass.
4. Tag and push:
   ```bash
   git tag v0.2.0
   git push origin main --tags
   ```
5. Responders get the update with `claude plugin marketplace update polygon-firstresponders`
   then `claude plugin update polygon-firstresponders`.

---

## Usage

Just ask Claude Code questions. The plugin auto-routes to the right skill:

| You ask | Skill invoked | What it does |
|---|---|---|
| "What's the minimum stake to become a Polygon validator?" | `answer-faq` | TF-IDF search over `data/docs/*.md`, cites file paths. |
| "What changed in Bor this week?" | `summarize-upgrades` | Reads `data/github/bor/prs.jsonl`, groups merged PRs, cites URLs. |
| "Plot gas prices for the last 500 blocks." | `investigate-blocks` | Concurrent RPC poll + matplotlib scatter + line-of-best-fit → PNG path. |
| "Is Polygon healthy right now?" | `network-health` | Composes Claude's Datadog MCP + the bundled `polygon-frp-rpc` MCP. |
| "Refresh the GitHub data." | `refresh-knowledge` | Incremental pull of Bor + Heimdall-v2 commits/PRs. |

See `FAQ_COVERAGE.md` for the full catalogue of questions the FAQ skill is tuned for.

### Freshness policy

Every answer produced by this plugin is bound by the **≤ 30-day freshness rule** documented
in `FRESHNESS_POLICY.md`:

- Static FAQ answers must be grounded in bundled docs whose upstream repos have been pushed
  within the last 30 days, **or** the skill must explicitly disclose that the answer cannot
  be freshness-verified.
- PR / commit summaries must flag windows where the corpus is older than 30 days and prompt
  a `refresh-knowledge` run.
- When information is unavailable at the required freshness, the skills **refuse to guess**
  — they surface the uncertainty to the responder instead of fabricating a confident-looking
  but potentially stale answer.

If you edit `data/docs/*.md` or add a new doc, update its **Authoritative sources** callout
with currently-maintained repos (`pushed_at` ≤ 30 days). Before tagging a plugin release,
audit every repo URL in the corpus for staleness — `FRESHNESS_POLICY.md` lists the canonical
and explicitly-deprecated references.

---

## Developer workflow

```bash
uv sync                                       # install deps
uv run pytest                                 # run all tests
uv run pytest tests/test_docs_index.py -v     # focused retrieval tests
uv run ruff check .                           # lint
uv run ruff format .                          # format
uv run python -m polygon_frp.plot --demo      # plot smoke test → /tmp/polygon-frp-demo.png
```

### Refreshing the knowledge base

Just ask Claude Code: *"refresh the GitHub data"* or *"pull the latest bor PRs"* — the
`refresh-knowledge` skill runs the incremental ingest and advances the cursor, so
subsequent refreshes only pull new PRs/commits. Do it at the start of a shift or whenever
you suspect a question depends on recent upgrades.

### Adding more skills

Skills live in `skills/<skill-name>/` and are auto-registered by entries in
`plugin.json`'s `skills` array. To add one:

1. Create `skills/my-skill/SKILL.md` with frontmatter (`name`, `description`) + workflow.
2. Optionally add `skills/my-skill/scripts/*.py` for deterministic work.
3. Append `"skills/my-skill"` to the `skills` array in `plugin.json`.
4. Reload Claude Code.

To **vendor** an external skill (e.g. `kurtosis-pos`), drop its directory under
`skills/` and reference it from `plugin.json` the same way. This repo is the single
source of truth — no cross-repo skill dependencies needed.

---

## Layout

```
firstresponders-ccplugin/
├── SPEC.md                       # canonical spec — read first
├── README.md                     # this file
├── FAQ_COVERAGE.md               # catalogue of questions the FAQ skill covers
├── plugin.json                   # Claude Code plugin manifest
├── .mcp.json                     # polygon-frp-rpc MCP wiring (Datadog is per-user, not here)
├── pyproject.toml                # uv-managed deps
├── skills/
│   ├── answer-faq/
│   ├── summarize-upgrades/
│   ├── investigate-blocks/
│   ├── network-health/
│   └── refresh-knowledge/
├── src/polygon_frp/
│   ├── rpc.py                    # JSON-RPC client (concurrent)
│   ├── docs_index.py             # TF-IDF index over docs + GitHub JSONL
│   ├── github_ingest.py          # incremental Bor/Heimdall-v2 pull
│   ├── mcp_rpc.py                # stdio MCP exposing RPC tools
│   └── plot.py                   # matplotlib (Agg) charting
├── data/
│   ├── docs/                     # 9 bundled public markdown files
│   └── github/                   # gitignored; populated by refresh-knowledge
└── tests/
```

---

## Boundaries

- **Never commit** `data/github/` or `.env` — both are per-responder local state.
- **Cite sources** in every answer: file path for doc hits, URL for PRs/commits, PNG
  path for plots.
- **No LLM SDK** ships inside this plugin; Claude Code owns the LLM.
- **No server** — no FastAPI, no Slack Socket Mode, no webhooks.

Full boundary list in `SPEC.md §9`.

---

## License

MIT.
