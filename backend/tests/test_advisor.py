"""Tests for partition advisor."""

import pytest

from src.advisor.partition_advisor import generate_hints, score_columns, ColumnScore
from src.profiler.partition_profiler import PartitionStats


def _make_stats(
    column: str,
    skew_ratio: float = 1.0,
    null_fraction: float = 0.0,
    cardinality: float = 1000.0,
    counts: list[int] | None = None,
) -> PartitionStats:
    if counts is None:
        counts = [100, 100, 100, 100, 100]
    return PartitionStats(
        column=column,
        total_rows=sum(counts) + int(null_fraction * sum(counts)),
        cardinality_estimate=cardinality,
        null_count=int(null_fraction * sum(counts)),
        null_fraction=null_fraction,
        skew_ratio=skew_ratio,
        top_keys=[(f"key_{i}", c) for i, c in enumerate(counts)],
        partition_counts=counts,
        batch_count=1,
        hll_error=0.0081,
    )


def test_score_good_column() -> None:
    stats = _make_stats("region", skew_ratio=1.1, counts=[100, 95, 102, 98])
    scores = score_columns([stats])
    assert scores[0].severity == "good"
    assert scores[0].composite_score >= 75


def test_score_severe_skew() -> None:
    stats = _make_stats("user_id", skew_ratio=45.0, counts=[9000, 100, 50, 30])
    scores = score_columns([stats])
    assert scores[0].severity in {"danger", "critical"}
    assert scores[0].composite_score < 50


def test_score_high_nulls() -> None:
    stats = _make_stats("nullable_col", null_fraction=0.4, counts=[100, 100])
    scores = score_columns([stats])
    assert scores[0].null_penalty > 30


def test_scores_sorted_descending() -> None:
    good = _make_stats("region", skew_ratio=1.1, counts=[100, 100, 100])
    bad = _make_stats("user_id", skew_ratio=40.0, counts=[5000, 10, 5])
    scores = score_columns([bad, good])
    assert scores[0].column == "region"
    assert scores[1].column == "user_id"


def test_generate_hints_returns_all_snippets() -> None:
    stats = _make_stats("user_id", skew_ratio=12.0, counts=[1000, 50, 30])
    hints = generate_hints(stats, num_partitions=100)
    assert hints.column == "user_id"
    assert "CONCAT" in hints.duckdb_salting
    assert "HASH" in hints.duckdb_salting
    assert "F.hash" in hints.pyspark_salting
    assert "repartition" in hints.pyspark_repartition
    assert "COPY" in hints.duckdb_repartition


def test_generate_hints_explanation_mentions_skew() -> None:
    stats = _make_stats("user_id", skew_ratio=20.0, counts=[2000, 100])
    hints = generate_hints(stats)
    assert "20." in hints.explanation or "skew" in hints.explanation.lower()


def test_all_severity_labels_valid() -> None:
    from src.advisor.partition_advisor import ColumnScore
    valid = {"good", "info", "warning", "danger", "critical"}
    for ratio, null in [(1.1, 0), (3.0, 0.05), (9.0, 0.1), (25.0, 0.2), (50.0, 0.5)]:
        stats = _make_stats("col", skew_ratio=ratio, null_fraction=null)
        score = score_columns([stats])[0]
        assert score.severity in valid
