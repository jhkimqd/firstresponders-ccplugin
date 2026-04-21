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
- **Native composition** — imports the `kurtosis-pos` skill and wires the internal Datadog
  MCP server via `.mcp.json`. Neither needs re-implementation.
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
  - Datadog API + app keys — required for `network-health` to query monitors, metrics,
    and incidents via the internal `polygon-datadog` MCP.

---

## Install

```bash
# 1. Clone
git clone <this-repo> ~/firstresponders-ccplugin
cd ~/firstresponders-ccplugin

# 2. Install Python deps (creates .venv/ and uv.lock)
uv sync

# 3. Set up environment
cp .env.example .env
$EDITOR .env          # fill GITHUB_TOKEN, DATADOG_*, POLYGON_RPC_URL

# 4. Populate the GitHub knowledge base (first run)
uv run python -m polygon_frp.github_ingest --repos bor,heimdall-v2 --since 30d

# 5. Point Claude Code at the plugin
claude plugins install .
# or if you prefer a symlink for iterative dev:
claude plugins link .
```

Restart your Claude Code session (or run `/plugins` and reload) so the skills register.

### Configuring the Datadog MCP

Open `.mcp.json` and replace the `<FILL: ...>` placeholder on `polygon-datadog.command`
with the command or URL of the Polygon internal Datadog MCP server. The env vars are read
from `.env` automatically when Claude Code launches the plugin.

> Do **not** commit production Datadog keys. `.env` is gitignored; keep it that way.

---

## Usage

Just ask Claude Code questions. The plugin auto-routes to the right skill:

| You ask | Skill invoked | What it does |
|---|---|---|
| "What's the minimum stake to become a Polygon validator?" | `answer-faq` | TF-IDF search over `data/docs/*.md`, cites file paths. |
| "What changed in Bor this week?" | `summarize-upgrades` | Reads `data/github/bor/prs.jsonl`, groups merged PRs, cites URLs. |
| "Plot gas prices for the last 500 blocks." | `investigate-blocks` | Concurrent RPC poll + matplotlib scatter + line-of-best-fit → PNG path. |
| "Is Polygon healthy right now?" | `network-health` | Composes `polygon-datadog` MCP + `polygon-rpc` MCP. |
| "Refresh the GitHub data." | `refresh-knowledge` | Incremental pull of Bor + Heimdall-v2 commits/PRs. |

See `FAQ_COVERAGE.md` for the full catalogue of questions the FAQ skill is tuned for.

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

### Refreshing the knowledge base on a schedule

Optional systemd templates live under `systemd/`. Install them under
`~/.config/systemd/user/` and `systemctl --user enable --now firstresponders-ingest.timer`
to refresh nightly. Not required — you can always run `refresh-knowledge` on demand.

---

## Layout

```
firstresponders-ccplugin/
├── SPEC.md                       # canonical spec — read first
├── README.md                     # this file
├── FAQ_COVERAGE.md               # catalogue of questions the FAQ skill covers
├── plugin.json                   # Claude Code plugin manifest
├── .mcp.json                     # Datadog + polygon-rpc MCP wiring
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
