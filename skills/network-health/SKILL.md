---
name: network-health
description: Answer "is Polygon Chain okay right now?"-style questions by composing live Datadog monitors/incidents with Polygon chain status. Use when the user asks "is the network okay?", "is Polygon down?", "any active Polygon incidents?", "are there ongoing issues on Bor/Heimdall?", or similar live-health queries.
---

# network-health

A **prompt-only** skill (no script). It orchestrates live data from two MCP servers:

1. **Datadog MCP** — Claude's managed Datadog integration (authenticated per responder through Claude settings). Provides monitors, incidents, active alerts, and recent metric anomalies. Tool namespace varies by integration version; discover available tools via `/mcp` or by inspection. Typical names include `list_monitors`, `search_monitors`, `list_incidents`, `query_metrics`.
2. **`polygon-frp-rpc`** MCP — bundled stdio server in this plugin. Provides chain-level liveness (`get_chain_status`, `get_recent_blocks`, `get_gas_usage`).

## When to trigger

- "Is the network okay?" / "Is Polygon down?"
- "Any active Polygon incidents?"
- "What's the current state of Bor / Heimdall?"
- "Are validators healthy right now?"
- "Is there an ongoing outage?"

Do **not** use this skill for:
- Historical "what changed" questions — use `summarize-upgrades`.
- Static FAQ about how the network works — use `answer-faq`.
- Block-range plots or investigation charts — use `investigate-blocks`.

## Workflow

1. **Start chain-level checks in parallel with Datadog checks:**
   - Call `polygon-frp-rpc.get_chain_status` → latest block number, chain id, gas price, syncing flag, peer count.
   - Call `polygon-frp-rpc.get_recent_blocks(count=10)` → spot-check that blocks are advancing (timestamps increasing, non-zero tx_count is healthy).
   - Query `datadog` MCP tools for:
     - Active monitors in a triggered / alert state (prefer any `list_monitors` / `search_monitors` tool the MCP exposes, filtered to alerting states).
     - Open incidents (any `list_incidents` / `search_incidents` tool, filtered to `active` / `stable` / `resolved=false`).
     - Optionally: recent metric queries for critical dashboards (block production rate, validator set size, bridge health).

2. **Synthesize a concise status report** with the following structure:
   - **Verdict** (one line): "🟢 Healthy", "🟡 Degraded — <brief cause>", or "🔴 Incident in progress — <brief cause>".
   - **Chain liveness**: latest block, gas price gwei, peer count, syncing status.
   - **Active alerts / incidents**: bulleted list; include incident URL/ID and severity if available. If none, say "No active monitors or incidents."
   - **Recent block health**: block timestamps advancing? gas-used ratios normal? mention anomalies.
   - **Sources**: list the MCP tools called (e.g., `datadog.list_monitors`, `polygon-frp-rpc.get_chain_status`).

3. **Do not fabricate data.** If a Datadog tool isn't available or errors out, say so explicitly rather than inventing a monitor list.

## Output contract

- Responder will paste the synthesized report directly into Slack/Telegram/Discord, so keep it crisp, use bullet points, and avoid speculation beyond what the data supports.
- If the chain is advancing but Datadog is unreachable, still answer — flag the missing signal and return the RPC-only view.
- If Datadog shows an incident, always include the incident's URL/ID so responders can follow up.
