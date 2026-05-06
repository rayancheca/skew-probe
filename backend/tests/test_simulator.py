"""Tests for straggler simulator."""

import pytest

from src.simulator.straggler_sim import simulate_straggler


def test_uniform_distribution_no_slowdown() -> None:
    counts = [100, 100, 100, 100]
    result = simulate_straggler(counts, num_workers=4)
    assert result.slowdown_factor == pytest.approx(1.0, abs=0.01)


def test_skewed_has_slowdown() -> None:
    counts = [1000] + [10] * 9
    result = simulate_straggler(counts, num_workers=4)
    assert result.slowdown_factor > 1.0


def test_single_worker_no_idle() -> None:
    counts = [100, 200, 300]
    result = simulate_straggler(counts, num_workers=1)
    assert result.num_workers == 1
    assert result.actual_finish_sec == pytest.approx(600 / 1_000_000, rel=0.01)


def test_straggler_marked_correctly() -> None:
    counts = [10_000, 100, 100]
    result = simulate_straggler(counts, num_workers=3)
    straggler = result.worker_timelines[result.straggler_worker_id]
    assert straggler.is_straggler is True
    assert straggler.finish_time_sec == max(
        t.finish_time_sec for t in result.worker_timelines
    )


def test_invalid_workers_raises() -> None:
    with pytest.raises(ValueError):
        simulate_straggler([100], num_workers=0)


def test_idle_fraction_nonnegative() -> None:
    counts = [1000, 1, 1]
    result = simulate_straggler(counts, num_workers=3)
    assert 0.0 <= result.idle_fraction <= 1.0


def test_total_rows_preserved() -> None:
    counts = [50, 100, 150, 200]
    result = simulate_straggler(counts, num_workers=2)
    assert result.total_rows == 500


def test_rows_per_sec_scaling() -> None:
    counts = [1_000_000]
    slow = simulate_straggler(counts, num_workers=1, rows_per_sec=1_000)
    fast = simulate_straggler(counts, num_workers=1, rows_per_sec=1_000_000)
    assert slow.actual_finish_sec == pytest.approx(fast.actual_finish_sec * 1000, rel=0.01)
