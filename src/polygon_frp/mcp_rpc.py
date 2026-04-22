"""Stdio MCP server exposing Polygon RPC tools.

Mirrors the three live-network tools from
polygon-chatbot/mcp-server/src/polygon_mcp/server.py (minus the docs search
tool — that's an `answer-faq` skill concern now):

- get_chain_status
- get_recent_blocks(count)
- get_gas_usage(block_count)

Run: ``uv run python -m polygon_frp.mcp_rpc`` (stdio transport).
Configure: ``POLYGON_RPC_URL`` env var.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from polygon_frp.rpc import get_chain_status as _rpc_chain_status
from polygon_frp.rpc import get_recent_blocks as _rpc_recent_blocks

_RPC_URL = os.environ.get("POLYGON_RPC_URL", "https://polygon.drpc.org")

mcp = FastMCP(
    "polygon-rpc",
    instructions=(
        "Polygon PoS live-network tools. Use get_chain_status for a quick "
        "health snapshot, get_recent_blocks for per-block gas detail, and "
        "get_gas_usage for an aggregated utilization report."
    ),
)


@mcp.tool(name="get_chain_status")
async def get_chain_status() -> str:
    """Get the current status of the Polygon PoS network.

    Returns the latest block number, chain ID, gas price, sync status,
    and peer count from the configured Polygon RPC endpoint.
    """
    status = await _rpc_chain_status(rpc_url=_RPC_URL)
    if not status:
        return "Error: Could not reach Polygon RPC endpoint."

    sync_val = status["syncing"]
    syncing = "Unknown" if sync_val is None else ("Syncing..." if sync_val else "Synced")
    peers = str(status["peer_count"]) if status["peer_count"] is not None else "N/A"

    return (
        f"Polygon PoS Network Status:\n"
        f"- Latest block: {status['latest_block']:,}\n"
        f"- Chain ID: {status['chain_id']}\n"
        f"- Gas price: {status['gas_price_gwei']:.2f} Gwei\n"
        f"- Sync status: {syncing}\n"
        f"- Peers: {peers}"
    )


@mcp.tool(name="get_recent_blocks")
async def get_recent_blocks(count: int = 10) -> str:
    """Get a concise summary of the most recent N Polygon blocks.

    Args:
        count: Number of recent blocks to fetch (default 10, max 50).
    """
    count = min(max(count, 1), 50)
    blocks = await _rpc_recent_blocks(count=count, rpc_url=_RPC_URL)
    if not blocks:
        return "Could not fetch block data from Polygon RPC."

    lines = [
        f"- Block {b['number']:,}: {b['tx_count']} txs, "
        f"{b['gas_used']:,}/{b['gas_limit']:,} gas "
        f"(base_fee={b['base_fee_gwei']:.2f} Gwei)"
        for b in blocks
    ]
    return f"Recent {len(blocks)} Polygon blocks:\n" + "\n".join(lines)


@mcp.tool(name="get_gas_usage")
async def get_gas_usage(block_count: int = 10) -> str:
    """Get gas utilization for recent Polygon PoS blocks.

    Shows gas used vs gas limit for each block and the average utilization.

    Args:
        block_count: Number of recent blocks to analyze (default 10, max 50).
    """
    block_count = min(max(block_count, 1), 50)
    blocks = await _rpc_recent_blocks(count=block_count, rpc_url=_RPC_URL)

    if not blocks:
        return "Could not fetch block data from Polygon RPC."

    rows: list[str] = []
    total_used = 0
    total_limit = 0
    for b in blocks:
        gas_used = b["gas_used"]
        gas_limit = b["gas_limit"]
        pct = (gas_used / gas_limit * 100) if gas_limit else 0
        total_used += gas_used
        total_limit += gas_limit
        rows.append(f"| {b['number']} | {gas_used:,} | {gas_limit:,} | {pct:.1f}% |")

    avg_pct = (total_used / total_limit * 100) if total_limit else 0

    table = (
        "| Block | Gas Used | Gas Limit | Utilization |\n"
        "|-------|----------|-----------|-------------|\n" + "\n".join(rows)
    )

    return f"Gas Utilization — Last {len(blocks)} Blocks\n\n{table}\n\nAverage: {avg_pct:.1f}%"


def main() -> None:
    """Run the MCP server (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
