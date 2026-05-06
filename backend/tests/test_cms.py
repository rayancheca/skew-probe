"""Tests for Count-Min Sketch."""

import pytest
from src.algorithms.count_min_sketch import CountMinSketch


def test_single_item_frequency() -> None:
    cms = CountMinSketch(epsilon=0.01, delta=0.01)
    cms.add("user_id_42", count=100)
    assert cms.estimate("user_id_42") == 100


def test_unknown_item_returns_zero() -> None:
    cms = CountMinSketch(epsilon=0.01, delta=0.01)
    cms.add("a", count=5)
    assert cms.estimate("never_seen") == 0


def test_frequency_monotonically_increases() -> None:
    cms = CountMinSketch(epsilon=0.01, delta=0.01)
    for i in range(50):
        cms.add("hot_key")
    before = cms.estimate("hot_key")
    cms.add("hot_key", count=10)
    after = cms.estimate("hot_key")
    assert after == before + 10


def test_total_count() -> None:
    cms = CountMinSketch(epsilon=0.05, delta=0.05)
    for i in range(100):
        cms.add(f"key_{i}")
    assert cms.total_count == 100


def test_merge_combines_counts() -> None:
    a = CountMinSketch(epsilon=0.05, delta=0.05)
    b = CountMinSketch(epsilon=0.05, delta=0.05)
    a.add("shared", count=3)
    b.add("shared", count=7)
    merged = a.merge(b)
    assert merged.estimate("shared") == 10
    assert merged.total_count == 10


def test_estimate_never_underestimates() -> None:
    cms = CountMinSketch(epsilon=0.01, delta=0.01)
    true_counts: dict[str, int] = {}
    for i in range(200):
        key = f"key_{i % 20}"
        count = (i % 5) + 1
        cms.add(key, count=count)
        true_counts[key] = true_counts.get(key, 0) + count

    for key, true_count in true_counts.items():
        assert cms.estimate(key) >= true_count


def test_integer_key() -> None:
    cms = CountMinSketch(epsilon=0.05, delta=0.05)
    cms.add(42, count=5)
    assert cms.estimate(42) == 5


def test_invalid_epsilon_raises() -> None:
    with pytest.raises(ValueError):
        CountMinSketch(epsilon=0, delta=0.05)


def test_invalid_count_raises() -> None:
    cms = CountMinSketch(epsilon=0.05, delta=0.05)
    with pytest.raises(ValueError):
        cms.add("x", count=0)
