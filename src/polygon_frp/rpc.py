"""Polygon JSON-RPC client for chain data queries.

Ported from polygon-chatbot/slackbot/src/polygon_bot/integrations/polygon_rpc.py.

Changes from the original:
- No `polygon_bot.config.settings` dependency. `rpc_url` is passed in as a
  function argument everywhere.
- New helper `get_blocks_in_range(start, end, concurrency=20)` for bounded
  concurrent block fetches used by investigation skills.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15.0


async def _rpc_call(
    method: str,
    params: list[Any] | None = None,
    *,
    rpc_url: str,
    client: httpx.AsyncClient | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    """Make a JSON-RPC call to a Polygon PoS node.

    If a shared `client` is supplied it is reused (important when batching many
    calls); otherwise a short-lived client is created per call.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or [],
        "id": 1,
    }

    async def _do(c: httpx.AsyncClient) -> Any:
        resp = await c.post(rpc_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.error("RPC error for %s: %s", method, data["error"])
            return None
        return data.get("result")

    try:
        if client is not None:
            return await _do(client)
        async with httpx.AsyncClient(timeout=timeout) as c:
            return await _do(c)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.error("RPC call failed for %s: %s", method, exc)
        return None


async def get_chain_status(*, rpc_url: str, client: httpx.AsyncClient | None = None) -> dict | None:
    """Get a snapshot of the chain's current state."""
    latest_block, gas_price, syncing, chain_id, peer_count = await asyncio.gather(
        _rpc_call("eth_blockNumber", rpc_url=rpc_url, client=client),
        _rpc_call("eth_gasPrice", rpc_url=rpc_url, client=client),
        _rpc_call("eth_syncing", rpc_url=rpc_url, client=client),
        _rpc_call("eth_chainId", rpc_url=rpc_url, client=client),
        _rpc_call("net_peerCount", rpc_url=rpc_url, client=client),
    )

    if latest_block is None:
        return None

    if syncing is None:
        sync_status: bool | None = None
    else:
        sync_status = syncing is not False

    return {
        "latest_block": int(latest_block, 16),
        "chain_id": int(chain_id, 16) if chain_id else None,
        "gas_price_gwei": int(gas_price, 16) / 1e9 if gas_price else 0,
        "syncing": sync_status,
        "peer_count": int(peer_count, 16) if peer_count else None,
    }


def _parse_block(num: int, data: dict) -> dict:
    """Normalize an eth_getBlockByNumber result into a summary dict."""
    gas_price_hex = data.get("baseFeePerGas") or "0x0"
    try:
        base_fee_gwei = int(gas_price_hex, 16) / 1e9
    except (ValueError, TypeError):
        base_fee_gwei = 0.0
    return {
        "number": num,
        "gas_used": int(data.get("gasUsed", "0x0"), 16),
        "gas_limit": int(data.get("gasLimit", "0x0"), 16),
        "timestamp": int(data.get("timestamp", "0x0"), 16),
        "tx_count": len(data.get("transactions", [])),
        "base_fee_gwei": base_fee_gwei,
    }


async def get_recent_blocks(
    count: int = 10,
    *,
    rpc_url: str,
    client: httpx.AsyncClient | None = None,
) -> list[dict]:
    """Fetch the most recent N blocks with gas data (concurrent)."""
    latest = await _rpc_call("eth_blockNumber", rpc_url=rpc_url, client=client)
    if latest is None:
        return []

    latest_num = int(latest, 16)

    async def _fetch(num: int) -> dict | None:
        data = await _rpc_call(
            "eth_getBlockByNumber", [hex(num), False], rpc_url=rpc_url, client=client
        )
        if not data:
            return None
        return _parse_block(num, data)

    results = await asyncio.gather(*(_fetch(latest_num - i) for i in range(count)))
    return [b for b in results if b is not None]


async def get_blocks_in_range(
    start: int,
    end: int,
    *,
    rpc_url: str,
    concurrency: int = 20,
    client: httpx.AsyncClient | None = None,
) -> list[dict]:
    """Fetch block summaries for every block in [start, end] inclusive.

    Uses an ``asyncio.Semaphore`` to bound in-flight requests. Returned list is
    ordered by block number ascending. Failed fetches are silently dropped.
    """
    if end < start:
        return []
    if concurrency < 1:
        concurrency = 1

    sem = asyncio.Semaphore(concurrency)

    async def _fetch(num: int) -> dict | None:
        async with sem:
            data = await _rpc_call(
                "eth_getBlockByNumber",
                [hex(num), False],
                rpc_url=rpc_url,
                client=client,
            )
        if not data:
            return None
        return _parse_block(num, data)

    # If caller did not provide a shared client, create one for the batch so we
    # don't open+close a TCP connection per block.
    if client is None:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as c:

            async def _fetch_with(num: int) -> dict | None:
                async with sem:
                    data = await _rpc_call(
                        "eth_getBlockByNumber",
                        [hex(num), False],
                        rpc_url=rpc_url,
                        client=c,
                    )
                if not data:
                    return None
                return _parse_block(num, data)

            results = await asyncio.gather(*(_fetch_with(n) for n in range(start, end + 1)))
    else:
        results = await asyncio.gather(*(_fetch(n) for n in range(start, end + 1)))

    return [b for b in results if b is not None]
