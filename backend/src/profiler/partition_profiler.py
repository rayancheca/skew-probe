"""
Partition profiler: ingests Arrow record batches, maintains CMS + HLL per
column, and computes skew metrics as each batch arrives.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pyarrow as pa

from src.algorithms.count_min_sketch import CountMinSketch
from src.algorithms.hyperloglog import HyperLogLog

_CMS_EPSILON: float = 0.005
_CMS_DELTA: float = 0.01
_HLL_B: int = 14
_TOP_K: int = 20


@dataclass
class PartitionStats:
    """Point-in-time snapshot of one column's partition distribution."""

    column: str
    total_rows: int
    cardinality_estimate: float
    null_count: int
    null_fraction: float
    skew_ratio: float
    top_keys: list[tuple[str, int]]
    partition_counts: list[int]
    batch_count: int
    hll_error: float


@dataclass
class ColumnProfiler:
    """Maintains CMS + HLL state for a single partition key column."""

    column: str
    cms: CountMinSketch = field(default_factory=lambda: CountMinSketch(_CMS_EPSILON, _CMS_DELTA))
    hll: HyperLogLog = field(default_factory=lambda: HyperLogLog(_HLL_B))
    null_count: int = 0
    batch_count: int = 0
    _seen_keys: dict[str, int] = field(default_factory=dict)

    def ingest_batch(self, column_array: pa.Array) -> None:
        """Process one Arrow array column. Updates CMS, HLL, null count."""
        self.batch_count += 1
        for scalar in column_array:
            if scalar is None or scalar.as_py() is None:
                self.null_count += 1
                continue
            key = str(scalar.as_py())
            self.cms.add(key)
            self.hll.add(key)
            self._seen_keys[key] = self._seen_keys.get(key, 0) + 1

    def stats(self) -> PartitionStats:
        """Compute and return the current PartitionStats snapshot."""
        total_rows = self.cms.total_count + self.null_count
        cardinality = self.hll.cardinality()
        null_fraction = self.null_count / total_rows if total_rows > 0 else 0.0

        # Top-K heavy hitters — use CMS estimates on tracked keys
        # (We keep exact counts for keys seen; CMS is the provable bound)
        top_keys = sorted(
            self._seen_keys.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )[:_TOP_K]

        partition_counts = [count for _, count in top_keys]
        skew_ratio = _compute_skew_ratio(partition_counts)

        return PartitionStats(
            column=self.column,
            total_rows=total_rows,
            cardinality_estimate=cardinality,
            null_count=self.null_count,
            null_fraction=null_fraction,
            skew_ratio=skew_ratio,
            top_keys=top_keys,
            partition_counts=partition_counts,
            batch_count=self.batch_count,
            hll_error=self.hll.standard_error,
        )


def _compute_skew_ratio(counts: list[int]) -> float:
    """Max / mean — skew ratio of 1.0 is perfectly uniform, higher is worse."""
    if not counts:
        return 1.0
    mean = sum(counts) / len(counts)
    if mean == 0:
        return 1.0
    return max(counts) / mean


class PartitionProfiler:
    """
    Streaming partition profiler.

    Maintains one ColumnProfiler per candidate partition key. Accepts
    Arrow RecordBatches and emits updated PartitionStats after each batch.
    """

    def __init__(self, partition_columns: list[str]) -> None:
        if not partition_columns:
            raise ValueError("At least one partition column must be specified")
        self._profilers: dict[str, ColumnProfiler] = {
            col: ColumnProfiler(column=col) for col in partition_columns
        }

    @property
    def columns(self) -> list[str]:
        return list(self._profilers.keys())

    def ingest_batch(self, batch: pa.RecordBatch) -> list[PartitionStats]:
        """
        Process one RecordBatch. Returns updated stats for all profiled columns.
        Columns missing from the batch are skipped.
        """
        results: list[PartitionStats] = []
        schema_names = set(batch.schema.names)

        for col, profiler in self._profilers.items():
            if col not in schema_names:
                continue
            column_array = batch.column(col)
            profiler.ingest_batch(column_array)
            results.append(profiler.stats())

        return results

    def ingest_table(self, table: pa.Table) -> list[PartitionStats]:
        """Convenience: ingest a full Table by splitting into RecordBatches."""
        batches = table.to_batches(max_chunksize=50_000)
        stats: list[PartitionStats] = []
        for batch in batches:
            stats = self.ingest_batch(batch)
        return stats

    def current_stats(self) -> list[PartitionStats]:
        """Return current stats without ingesting new data."""
        return [p.stats() for p in self._profilers.values()]

    def column_stats(self, column: str) -> PartitionStats:
        if column not in self._profilers:
            raise KeyError(f"Column '{column}' is not being profiled")
        return self._profilers[column].stats()


def entropy(counts: list[int]) -> float:
    """Shannon entropy of a frequency distribution (nats)."""
    total = sum(counts)
    if total == 0:
        return 0.0
    return -sum(
        (c / total) * math.log(c / total)
        for c in counts
        if c > 0
    )
