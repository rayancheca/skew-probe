"""Tests for PartitionProfiler."""

import pyarrow as pa
import pytest

from src.profiler.partition_profiler import PartitionProfiler, entropy


def _make_batch(user_ids: list[str | None], product_ids: list[str]) -> pa.RecordBatch:
    return pa.record_batch(
        {
            "user_id": pa.array(user_ids, type=pa.string()),
            "product_id": pa.array(product_ids, type=pa.string()),
        }
    )


def test_ingest_single_batch() -> None:
    profiler = PartitionProfiler(["user_id"])
    batch = _make_batch(["a", "b", "a", "c"], ["p1", "p2", "p3", "p4"])
    stats = profiler.ingest_batch(batch)
    assert len(stats) == 1
    assert stats[0].total_rows == 4


def test_skew_ratio_uniform() -> None:
    profiler = PartitionProfiler(["user_id"])
    # 4 unique keys, 1 each — perfect uniform → skew ratio should be 1
    batch = _make_batch(["a", "b", "c", "d"], ["p1", "p2", "p3", "p4"])
    stats = profiler.ingest_batch(batch)
    assert stats[0].skew_ratio == pytest.approx(1.0, abs=0.01)


def test_skew_ratio_hot_key() -> None:
    profiler = PartitionProfiler(["user_id"])
    # a appears 100 times, b once — extreme skew
    keys = ["a"] * 100 + ["b"]
    batch = _make_batch(keys, [f"p{i}" for i in range(101)])
    stats = profiler.ingest_batch(batch)
    # Top key count = 100, mean = (100 + 1) / 2 = 50.5
    assert stats[0].skew_ratio > 1.0


def test_null_counting() -> None:
    profiler = PartitionProfiler(["user_id"])
    batch = _make_batch(["a", None, "b", None], ["p1", "p2", "p3", "p4"])
    stats = profiler.ingest_batch(batch)
    assert stats[0].null_count == 2
    assert stats[0].null_fraction == pytest.approx(0.5, abs=0.01)


def test_missing_column_skipped() -> None:
    profiler = PartitionProfiler(["missing_col"])
    batch = _make_batch(["a", "b"], ["p1", "p2"])
    stats = profiler.ingest_batch(batch)
    # column not in batch → empty results
    assert len(stats) == 0


def test_multi_column_profiling() -> None:
    profiler = PartitionProfiler(["user_id", "product_id"])
    batch = _make_batch(["a", "a", "b"], ["p1", "p2", "p1"])
    stats = profiler.ingest_batch(batch)
    assert len(stats) == 2
    columns = {s.column for s in stats}
    assert columns == {"user_id", "product_id"}


def test_accumulates_across_batches() -> None:
    profiler = PartitionProfiler(["user_id"])
    batch1 = _make_batch(["a", "b"], ["p1", "p2"])
    batch2 = _make_batch(["a", "c"], ["p3", "p4"])
    profiler.ingest_batch(batch1)
    stats = profiler.ingest_batch(batch2)
    assert stats[0].total_rows == 4


def test_entropy_uniform() -> None:
    import math
    counts = [100, 100, 100, 100]
    ent = entropy(counts)
    assert ent == pytest.approx(math.log(4), rel=0.01)


def test_entropy_single_key() -> None:
    counts = [1000]
    ent = entropy(counts)
    assert ent == pytest.approx(0.0, abs=1e-9)


def test_no_partition_columns_raises() -> None:
    with pytest.raises(ValueError):
        PartitionProfiler([])
