"""Unit tests for src/polygon_frp/rpc.py with mocked httpx.AsyncClient."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polygon_frp.rpc import (
    _rpc_call,
    get_blocks_in_range,
    get_chain_status,
    get_recent_blocks,
)

TEST_RPC_URL = "https://rpc.test.invalid"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _mk_response(json_payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_payload
    resp.raise_for_status = MagicMock()
    return resp


class _FakeClient:
    """Minimal async client fake driven by a (method, params) -> result dict."""

    def __init__(self, routes: dict[tuple[str, tuple], Any]):
        self.routes = routes
        self.calls: list[dict] = []

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def post(self, url: str, json: dict) -> MagicMock:  # noqa: A002
        self.calls.append({"url": url, "payload": json})
        method = json["method"]
        params = tuple(json.get("params") or [])
        if (method, params) in self.routes:
            result = self.routes[(method, params)]
        elif (method, ()) in self.routes and not params:
            result = self.routes[(method, ())]
        else:
            # Match by method only as fallback
            result = next(
                (v for (m, _p), v in self.routes.items() if m == method),
                None,
            )
        if isinstance(result, Exception):
            raise result
        return _mk_response({"jsonrpc": "2.0", "id": 1, "result": result})


def _patched_client(routes: dict) -> _FakeClient:
    """Return a FakeClient usable as `httpx.AsyncClient(...)` replacement."""
    fake = _FakeClient(routes)

    def _factory(*a, **kw) -> _FakeClient:
        return fake

    _factory._fake = fake  # type: ignore[attr-defined]
    return _factory  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# _rpc_call
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_rpc_call_returns_result():
    factory = _patched_client({("eth_blockNumber", ()): "0x10"})
    with patch("polygon_frp.rpc.httpx.AsyncClient", factory):
        result = await _rpc_call("eth_blockNumber", rpc_url=TEST_RPC_URL)
    assert result == "0x10"


@pytest.mark.asyncio
async def test_rpc_call_handles_rpc_error():
    """An `error` key in the JSON-RPC response returns None."""
    fake_client = _FakeClient({})

    async def _post(*a, **kw):
        return _mk_response({"jsonrpc": "2.0", "id": 1, "error": {"code": -32000}})

    fake_client.post = _post  # type: ignore[assignment]

    def _factory(*a, **kw):
        return fake_client

    with patch("polygon_frp.rpc.httpx.AsyncClient", _factory):
        result = await _rpc_call("eth_blockNumber", rpc_url=TEST_RPC_URL)
    assert result is None


@pytest.mark.asyncio
async def test_rpc_call_handles_http_error():
    import httpx

    fake_client = _FakeClient({})

    async def _post(*a, **kw):
        raise httpx.ConnectError("boom")

    fake_client.post = _post  # type: ignore[assignment]

    def _factory(*a, **kw):
        return fake_client

    with patch("polygon_frp.rpc.httpx.AsyncClient", _factory):
        result = await _rpc_call("eth_blockNumber", rpc_url=TEST_RPC_URL)
    assert result is None


# --------------------------------------------------------------------------- #
# get_chain_status
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_chain_status_happy_path():
    routes = {
        ("eth_blockNumber", ()): "0x64",
        ("eth_gasPrice", ()): "0x3B9ACA00",  # 1 Gwei
        ("eth_syncing", ()): False,
        ("eth_chainId", ()): "0x89",  # Polygon = 137
        ("net_peerCount", ()): "0x8",
    }
    factory = _patched_client(routes)
    with patch("polygon_frp.rpc.httpx.AsyncClient", factory):
        status = await get_chain_status(rpc_url=TEST_RPC_URL)

    assert status is not None
    assert status["latest_block"] == 100
    assert status["chain_id"] == 137
    assert status["gas_price_gwei"] == pytest.approx(1.0)
    assert status["syncing"] is False
    assert status["peer_count"] == 8


@pytest.mark.asyncio
async def test_get_chain_status_returns_none_when_block_fetch_fails():
    fake_client = _FakeClient({})

    async def _post(*a, **kw):
        return _mk_response({"jsonrpc": "2.0", "id": 1, "error": {"code": -1}})

    fake_client.post = _post  # type: ignore[assignment]

    def _factory(*a, **kw):
        return fake_client

    with patch("polygon_frp.rpc.httpx.AsyncClient", _factory):
        status = await get_chain_status(rpc_url=TEST_RPC_URL)
    assert status is None


@pytest.mark.asyncio
async def test_get_chain_status_syncing_object_detected():
    """When eth_syncing returns an object (not false), it means syncing=True."""
    routes = {
        ("eth_blockNumber", ()): "0x1",
        ("eth_gasPrice", ()): "0x0",
        ("eth_syncing", ()): {"currentBlock": "0x1", "highestBlock": "0x9"},
        ("eth_chainId", ()): "0x89",
        ("net_peerCount", ()): "0x1",
    }
    factory = _patched_client(routes)
    with patch("polygon_frp.rpc.httpx.AsyncClient", factory):
        status = await get_chain_status(rpc_url=TEST_RPC_URL)
    assert status is not None
    assert status["syncing"] is True


# --------------------------------------------------------------------------- #
# get_recent_blocks
# --------------------------------------------------------------------------- #


def _mock_block(num: int) -> dict:
    return {
        "number": hex(num),
        "gasUsed": hex(21000 * (num % 10 + 1)),
        "gasLimit": hex(30_000_000),
        "timestamp": hex(1_700_000_000 + num),
        "transactions": ["0x" + "a" * 64] * (num % 5),
        "baseFeePerGas": hex(1_000_000_000),  # 1 gwei
    }


class _BlockFakeClient:
    """Async-client fake that returns mock blocks from eth_getBlockByNumber."""

    def __init__(self, latest: int, missing: set[int] | None = None):
        self.latest = latest
        self.missing = missing or set()
        self.calls: list[dict] = []

    async def __aenter__(self) -> _BlockFakeClient:
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def post(self, url: str, json: dict) -> MagicMock:  # noqa: A002
        self.calls.append({"url": url, "payload": json})
        method = json["method"]
        params = json.get("params") or []
        if method == "eth_blockNumber":
            return _mk_response({"jsonrpc": "2.0", "id": 1, "result": hex(self.latest)})
        if method == "eth_getBlockByNumber":
            block_hex = params[0]
            num = int(block_hex, 16)
            if num in self.missing:
                return _mk_response({"jsonrpc": "2.0", "id": 1, "result": None})
            return _mk_response({"jsonrpc": "2.0", "id": 1, "result": _mock_block(num)})
        return _mk_response({"jsonrpc": "2.0", "id": 1, "result": None})


@pytest.mark.asyncio
async def test_get_recent_blocks_returns_count_blocks():
    fake = _BlockFakeClient(latest=500)

    def _factory(*a, **kw):
        return fake

    with patch("polygon_frp.rpc.httpx.AsyncClient", _factory):
        blocks = await get_recent_blocks(count=5, rpc_url=TEST_RPC_URL)

    assert len(blocks) == 5
    numbers = [b["number"] for b in blocks]
    assert set(numbers) == {500, 499, 498, 497, 496}
    assert all("gas_used" in b and "gas_limit" in b for b in blocks)
    assert all(b["base_fee_gwei"] == pytest.approx(1.0) for b in blocks)


@pytest.mark.asyncio
async def test_get_recent_blocks_skips_failed_fetches():
    fake = _BlockFakeClient(latest=100, missing={99, 98})

    def _factory(*a, **kw):
        return fake

    with patch("polygon_frp.rpc.httpx.AsyncClient", _factory):
        blocks = await get_recent_blocks(count=5, rpc_url=TEST_RPC_URL)
    # 5 requested, 2 missing -> 3 returned
    assert len(blocks) == 3


@pytest.mark.asyncio
async def test_get_recent_blocks_empty_when_latest_unavailable():
    fake = _FakeClient({})

    async def _post(*a, **kw):
        return _mk_response({"jsonrpc": "2.0", "id": 1, "error": {"code": -1}})

    fake.post = _post  # type: ignore[assignment]

    def _factory(*a, **kw):
        return fake

    with patch("polygon_frp.rpc.httpx.AsyncClient", _factory):
        blocks = await get_recent_blocks(count=5, rpc_url=TEST_RPC_URL)
    assert blocks == []


# --------------------------------------------------------------------------- #
# get_blocks_in_range
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_blocks_in_range_inclusive():
    fake = _BlockFakeClient(latest=10_000)

    def _factory(*a, **kw):
        return fake

    with patch("polygon_frp.rpc.httpx.AsyncClient", _factory):
        blocks = await get_blocks_in_range(100, 110, rpc_url=TEST_RPC_URL, concurrency=5)

    assert len(blocks) == 11  # inclusive
    numbers = sorted(b["number"] for b in blocks)
    assert numbers == list(range(100, 111))


@pytest.mark.asyncio
async def test_get_blocks_in_range_respects_semaphore_bound():
    """Verify concurrency limit is enforced."""
    import asyncio

    in_flight = 0
    peak = 0
    lock = asyncio.Lock()

    class _SlowClient:
        def __init__(self):
            self.calls: list[dict] = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

        async def post(self, url, json):  # noqa: A002
            nonlocal in_flight, peak
            async with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            async with lock:
                in_flight -= 1
            method = json["method"]
            params = json.get("params") or []
            if method == "eth_blockNumber":
                return _mk_response({"jsonrpc": "2.0", "id": 1, "result": "0x64"})
            num = int(params[0], 16)
            return _mk_response({"jsonrpc": "2.0", "id": 1, "result": _mock_block(num)})

    fake = _SlowClient()

    def _factory(*a, **kw):
        return fake

    with patch("polygon_frp.rpc.httpx.AsyncClient", _factory):
        blocks = await get_blocks_in_range(1, 30, rpc_url=TEST_RPC_URL, concurrency=4)

    assert len(blocks) == 30
    # Peak should never exceed the configured concurrency
    assert peak <= 4


@pytest.mark.asyncio
async def test_get_blocks_in_range_empty_when_end_before_start():
    blocks = await get_blocks_in_range(10, 5, rpc_url=TEST_RPC_URL)
    assert blocks == []


@pytest.mark.asyncio
async def test_rpc_call_reuses_provided_client():
    """When a shared client is passed, no new AsyncClient is opened."""
    import httpx

    shared = AsyncMock(spec=httpx.AsyncClient)
    shared.post.return_value = _mk_response({"jsonrpc": "2.0", "id": 1, "result": "0xaa"})

    result = await _rpc_call("eth_blockNumber", rpc_url=TEST_RPC_URL, client=shared)
    assert result == "0xaa"
    shared.post.assert_awaited_once()
