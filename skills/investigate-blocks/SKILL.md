---
name: investigate-blocks
description: Poll a range of Polygon Chain blocks over JSON-RPC and render a scatter plot with a line of best fit. Use when the user asks to "plot gas prices for blocks X to Y", "show tx count trend for the last N blocks", "chart gas usage over recent blocks", or any other request that maps a per-block numeric metric (gas price, gas-used ratio, tx count) to block number.
---

# investigate-blocks

Generates a per-block scatter plot (with a `numpy.polyfit` line of best fit) from live Polygon Chain RPC data.

## When to trigger

Use this skill when the user asks a question that fits the pattern "plot / chart / graph / show the trend of `<metric>` over blocks `<X..Y>` or the last N blocks". Example phrasings:

- "Plot gas prices for blocks 55000000 to 55001000."
- "Show the tx count trend for the last 500 blocks."
- "Chart gas-used ratio across the last 200 blocks."
- "Visualize how gas fees moved over the last 1000 blocks."

Do **not** use this skill for:
- General questions ("why are gas prices high?") — use `answer-faq`.
- Questions about incidents or network-level health — use `network-health`.
- Questions about Bor/Heimdall code changes — use `summarize-upgrades`.

## Inputs

Parse from the user's request:

- `metric`: one of `gas_price_gwei`, `gas_used_ratio`, `tx_count`. Default to `gas_price_gwei` if the user says "gas prices"; map "tx count" / "transactions per block" → `tx_count`; map "gas usage" / "gas used ratio" / "utilization" → `gas_used_ratio`.
- Either:
  - `--start N --end M` (explicit range), or
  - `--last N` (most recent N blocks; script derives the range from `eth_blockNumber`).
- Optional `--concurrency` (default 20).

## Workflow

1. Call the script:
   ```bash
   uv run python skills/investigate-blocks/scripts/poll_and_plot.py \
     --metric <metric> [--start N --end M | --last N] [--concurrency 20]
   ```
2. The script fetches the blocks via `polygon_frp.rpc.get_blocks_in_range`, renders the chart via `polygon_frp.plot.render_block_chart`, writes a PNG to `/tmp/polygon-frp-<unix-ts>.png`, and prints that path on stdout.
3. Surface the PNG path back to the user verbatim, plus a one-sentence trend summary derived from the slope reported in the chart title (e.g. "Gas prices are trending up ~0.05 gwei/block over this range."). The user will paste the image into Slack/Telegram/Discord.

## Output contract

- Always print the PNG path (absolute) to the user.
- Always include a short natural-language summary of the direction + magnitude of the trend.
- Cite the block range queried and the RPC endpoint used (read from `POLYGON_RPC_URL` env).

## Failure modes

- If the RPC is unreachable, the script exits non-zero and prints a JSON error on stderr — relay the failure to the user with the endpoint that failed.
- If `--last N` with N > 5000, warn the user about concurrency/latency before proceeding.
