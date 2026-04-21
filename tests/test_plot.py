"""Smoke tests for polygon_frp.plot."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from polygon_frp.plot import (
    SUPPORTED_METRICS,
    render_block_chart,
    render_timeseries,
)


def _fixture_blocks(n: int = 60, start: int = 60_000_000) -> list[dict]:
    blocks: list[dict] = []
    for i in range(n):
        blocks.append(
            {
                "number": start + i,
                "gas_price_gwei": 30.0 + 0.1 * i,
                "gas_used_ratio": 0.5 + 0.001 * i,
                "tx_count": 80 + (i % 7),
                "gas_used": int((0.5 + 0.001 * i) * 30_000_000),
                "gas_limit": 30_000_000,
            }
        )
    return blocks


def test_render_block_chart_produces_png_over_1kb(tmp_path: Path) -> None:
    out = tmp_path / "chart.png"
    result = render_block_chart(_fixture_blocks(), "gas_price_gwei", out)

    assert result == out
    assert out.exists()
    size = out.stat().st_size
    assert size > 1024, f"expected PNG >1KB, got {size} bytes"

    # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
    with out.open("rb") as fh:
        header = fh.read(8)
    assert header == b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize("metric", list(SUPPORTED_METRICS))
def test_render_block_chart_all_metrics(tmp_path: Path, metric: str) -> None:
    out = tmp_path / f"chart-{metric}.png"
    render_block_chart(_fixture_blocks(), metric, out)
    assert out.stat().st_size > 1024


def test_render_block_chart_derives_gas_used_ratio(tmp_path: Path) -> None:
    blocks = [
        {"number": 1, "gas_used": 15_000_000, "gas_limit": 30_000_000},
        {"number": 2, "gas_used": 20_000_000, "gas_limit": 30_000_000},
        {"number": 3, "gas_used": 25_000_000, "gas_limit": 30_000_000},
    ]
    out = tmp_path / "derived.png"
    render_block_chart(blocks, "gas_used_ratio", out)
    assert out.stat().st_size > 1024


def test_render_block_chart_rejects_bad_metric(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        render_block_chart(_fixture_blocks(), "not_a_metric", tmp_path / "x.png")


def test_render_block_chart_rejects_empty(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        render_block_chart([], "tx_count", tmp_path / "x.png")


def test_render_timeseries_produces_png(tmp_path: Path) -> None:
    now = datetime(2024, 1, 1, 12, 0, 0)
    points = [(now + timedelta(minutes=i), 10.0 + i * 0.3) for i in range(30)]

    out = tmp_path / "ts.png"
    result = render_timeseries(points, "Datadog metric X", out)

    assert result == out
    assert out.stat().st_size > 1024
