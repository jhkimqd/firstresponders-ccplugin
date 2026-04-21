"""Skill entry point: poll a Polygon block range and render a scatter plot.

Invoked by the `investigate-blocks` skill. Prints the PNG path on stdout on
success. On failure, prints a JSON error on stderr and exits non-zero.

Usage:
    python scripts/poll_and_plot.py --metric gas_price_gwei --last 500
    python scripts/poll_and_plot.py --metric tx_count --start 55000000 --end 55001000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Make the in-repo `src/` importable without relying on an editable install.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from polygon_frp.plot import SUPPORTED_METRICS, render_block_chart  # noqa: E402
from polygon_frp.rpc import get_blocks_in_range, get_chain_status  # noqa: E402


def _fail(message: str, code: int = 1, **extra: object) -> int:
    payload = {"error": message, **extra}
    print(json.dumps(payload), file=sys.stderr)
    return code


async def _resolve_range(rpc_url: str, args: argparse.Namespace) -> tuple[int, int]:
    if args.last is not None:
        status = await get_chain_status(rpc_url=rpc_url)
        if not status or "latest_block" not in status:
            raise RuntimeError(f"could not resolve latest block (status={status!r})")
        end = int(status["latest_block"])
        start = max(0, end - int(args.last) + 1)
        return start, end

    if args.start is None or args.end is None:
        raise ValueError("must supply either --last N or both --start and --end")
    if args.end < args.start:
        raise ValueError("--end must be ≥ --start")
    return int(args.start), int(args.end)


async def _run(args: argparse.Namespace) -> int:
    rpc_url = os.environ.get("POLYGON_RPC_URL", "https://polygon-rpc.com")

    try:
        start, end = await _resolve_range(rpc_url, args)
    except Exception as exc:
        return _fail(f"range resolution failed: {exc}", code=2, rpc_url=rpc_url)

    try:
        blocks = await get_blocks_in_range(
            start,
            end,
            rpc_url=rpc_url,
            concurrency=args.concurrency,
        )
    except Exception as exc:
        return _fail(f"RPC fetch failed: {exc}", code=4, rpc_url=rpc_url)

    if not blocks:
        return _fail("no blocks returned from RPC", code=5, rpc_url=rpc_url, start=start, end=end)

    ts = int(time.time())
    out_path = Path(f"/tmp/polygon-frp-{ts}.png")  # noqa: S108 — SPEC §5.1 dictates this path
    render_block_chart(blocks, args.metric, out_path)

    # stdout: just the path, so the skill/wrapper can grep it cleanly.
    print(str(out_path))
    # stderr: human-oriented metadata (skill can surface if useful).
    print(
        json.dumps(
            {
                "png_path": str(out_path),
                "metric": args.metric,
                "start_block": start,
                "end_block": end,
                "blocks_fetched": len(blocks),
                "rpc_url": rpc_url,
            }
        ),
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Poll a Polygon block range and render a metric chart."
    )
    parser.add_argument(
        "--metric",
        choices=SUPPORTED_METRICS,
        default="gas_price_gwei",
        help="Per-block metric to plot (default: gas_price_gwei).",
    )
    parser.add_argument("--start", type=int, help="Starting block number (inclusive).")
    parser.add_argument("--end", type=int, help="Ending block number (inclusive).")
    parser.add_argument(
        "--last",
        type=int,
        help="Plot the most recent N blocks (uses latest block from RPC).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Max concurrent RPC requests (default: 20).",
    )
    args = parser.parse_args(argv)

    if args.last is None and (args.start is None or args.end is None):
        parser.error("supply either --last N or both --start and --end")

    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        return _fail("interrupted", code=130)


if __name__ == "__main__":
    sys.exit(main())
