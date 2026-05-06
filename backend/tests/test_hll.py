"""Tests for HyperLogLog."""

import pytest
from src.algorithms.hyperloglog import HyperLogLog


def test_empty_cardinality_is_zero() -> None:
    hll = HyperLogLog(b=10)
    assert hll.cardinality() == 0


def test_single_item_cardinality() -> None:
    hll = HyperLogLog(b=10)
    hll.add("only_item")
    card = hll.cardinality()
    assert 0.5 <= card <= 2.0


def test_large_cardinality_within_error_bounds() -> None:
    hll = HyperLogLog(b=14)
    n = 100_000
    for i in range(n):
        hll.add(f"user_{i}")
    estimate = hll.cardinality()
    error = abs(estimate - n) / n
    # b=14 gives ~0.81% standard error; allow 3x for safety
    assert error < 0.03, f"Error {error:.3%} exceeded 3% for n={n}"


def test_duplicate_items_not_double_counted() -> None:
    hll = HyperLogLog(b=12)
    for _ in range(1000):
        hll.add("same_key")
    estimate = hll.cardinality()
    assert estimate < 10


def test_merge_union_cardinality() -> None:
    a = HyperLogLog(b=12)
    b = HyperLogLog(b=12)
    for i in range(500):
        a.add(f"set_a_{i}")
    for i in range(500):
        b.add(f"set_b_{i}")
    merged = a.merge(b)
    estimate = merged.cardinality()
    # Should be ~1000 distinct items
    assert 800 < estimate < 1200


def test_merge_different_b_raises() -> None:
    a = HyperLogLog(b=10)
    b = HyperLogLog(b=12)
    with pytest.raises(ValueError):
        a.merge(b)


def test_invalid_b_raises() -> None:
    with pytest.raises(ValueError):
        HyperLogLog(b=3)


def test_standard_error_decreases_with_b() -> None:
    hll_low = HyperLogLog(b=8)
    hll_high = HyperLogLog(b=14)
    assert hll_high.standard_error < hll_low.standard_error
