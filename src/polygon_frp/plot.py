"""Matplotlib-based plotting helpers for the investigation skills.

Uses the non-interactive `Agg` backend so plots render in headless
environments (Claude Code, CI, servers without X).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # noqa: E402  — must precede pyplot import

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SUPPORTED_METRICS = ("gas_price_gwei", "gas_used_ratio", "tx_count")

_METRIC_LABELS = {
    "gas_price_gwei": "Gas price (gwei)",
    "gas_used_ratio": "Gas used / gas limit",
    "tx_count": "Transactions per block",
}


def _extract_metric(block: dict, metric: str) -> float:
    """Pull a metric out of a block dict, with fall-back computation.

    If the block doesn't carry a pre-computed metric, derive it from
    the raw RPC fields when possible so this module is resilient to
    small changes in the upstream `rpc.get_blocks_in_range` schema.
    """
    if metric in block:
        return float(block[metric])

    if metric == "gas_used_ratio":
        gas_used = block.get("gas_used")
        gas_limit = block.get("gas_limit")
        if gas_used is None or gas_limit in (None, 0):
            raise KeyError(
                "block missing 'gas_used_ratio' and cannot derive from gas_used/gas_limit"
            )
        return float(gas_used) / float(gas_limit)

    if metric == "gas_price_gwei":
        # polygon_frp.rpc.get_blocks_in_range ships `base_fee_gwei` per block (already in gwei).
        base_fee_gwei = block.get("base_fee_gwei")
        if base_fee_gwei is not None:
            return float(base_fee_gwei)
        base_fee_wei = block.get("base_fee_per_gas")
        if base_fee_wei is not None:
            return float(base_fee_wei) / 1e9
        raise KeyError("block missing 'gas_price_gwei' / 'base_fee_gwei' / 'base_fee_per_gas'")

    raise KeyError(f"block missing metric '{metric}'")


def render_block_chart(blocks: list[dict], metric: str, out_path: Path) -> Path:
    """Scatter a per-block metric with a line of best fit.

    Args:
        blocks: list of block dicts; each must have a "number" key and either
            the metric key itself or the raw fields needed to derive it
            (e.g. "gas_used" + "gas_limit" for "gas_used_ratio").
        metric: one of "gas_price_gwei", "gas_used_ratio", or "tx_count".
        out_path: destination PNG path (parent dirs must exist or will be created).

    Returns:
        The `out_path` Path, for chaining.
    """
    if metric not in SUPPORTED_METRICS:
        raise ValueError(f"metric must be one of {SUPPORTED_METRICS}, got {metric!r}")
    if not blocks:
        raise ValueError("blocks must be non-empty")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    numbers = np.array([int(b["number"]) for b in blocks], dtype=float)
    values = np.array([_extract_metric(b, metric) for b in blocks], dtype=float)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(numbers, values, s=18, alpha=0.6, color="#1f77b4", label=_METRIC_LABELS[metric])

    # Line of best fit (degree 1). Requires ≥2 distinct x values and finite values.
    finite_mask = np.isfinite(numbers) & np.isfinite(values)
    if finite_mask.sum() >= 2 and len(np.unique(numbers[finite_mask])) >= 2:
        coeffs = np.polyfit(numbers[finite_mask], values[finite_mask], 1)
        fit_line = np.poly1d(coeffs)
        xs_sorted = np.sort(numbers[finite_mask])
        slope, intercept = coeffs
        ax.plot(
            xs_sorted,
            fit_line(xs_sorted),
            color="#d62728",
            linewidth=2,
            label=f"best fit (slope={slope:.3g})",
        )
        subtitle = f"slope={slope:.4g}, intercept={intercept:.4g}"
    else:
        subtitle = "(insufficient distinct x values for regression)"

    ax.set_xlabel("Block number")
    ax.set_ylabel(_METRIC_LABELS[metric])
    ax.set_title(f"{_METRIC_LABELS[metric]} vs. block number\n{subtitle}", fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, format="png")
    plt.close(fig)

    return out_path


def render_timeseries(
    points: Iterable[tuple[datetime, float]],
    title: str,
    out_path: Path,
) -> Path:
    """Line plot of (timestamp, value) points — used for Datadog-derived data.

    Args:
        points: iterable of (datetime, float) tuples. Will be sorted by timestamp.
        title: plot title.
        out_path: destination PNG path.

    Returns:
        The `out_path` Path.
    """
    pts = sorted(points, key=lambda p: p[0])
    if not pts:
        raise ValueError("points must be non-empty")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    xs = [p[0] for p in pts]
    ys = [float(p[1]) for p in pts]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(xs, ys, color="#2ca02c", linewidth=1.6, marker="o", markersize=3, alpha=0.8)
    ax.set_xlabel("Time")
    ax.set_ylabel("Value")
    ax.set_title(title)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, format="png")
    plt.close(fig)

    return out_path


def _build_demo_blocks(n: int = 120, start: int = 55_000_000) -> list[dict]:
    """Synthetic blocks for the `--demo` smoke test."""
    rng = np.random.default_rng(42)
    blocks: list[dict] = []
    for i in range(n):
        num = start + i
        # Gas price drifting upward with noise.
        gwei = 30.0 + 0.05 * i + rng.normal(0, 3.0)
        ratio = float(np.clip(0.4 + 0.002 * i + rng.normal(0, 0.05), 0, 1))
        tx = int(max(0, 80 + rng.normal(0, 15)))
        blocks.append(
            {
                "number": num,
                "gas_price_gwei": max(1.0, gwei),
                "gas_used_ratio": ratio,
                "tx_count": tx,
                "gas_used": int(ratio * 30_000_000),
                "gas_limit": 30_000_000,
            }
        )
    return blocks


def _demo(out_path: Path) -> Path:
    blocks = _build_demo_blocks()
    return render_block_chart(blocks, "gas_price_gwei", out_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m polygon_frp.plot")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Render a synthetic demo chart to /tmp/polygon-frp-demo.png",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/polygon-frp-demo.png"),  # noqa: S108 — SPEC §5.5 dictates this path
        help="Output path for --demo (default: /tmp/polygon-frp-demo.png)",
    )
    args = parser.parse_args(argv)

    if args.demo:
        path = _demo(args.out)
        print(str(path))
        return 0

    # No action requested.
    parser.print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
