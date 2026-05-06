"""
Partition advisor: scores candidate keys and generates concrete
salting SQL and repartition hints for DuckDB and PySpark.

Scoring criteria (each 0–100):
  1. Cardinality entropy score — prefer high cardinality columns
  2. Null concentration penalty — penalize high null fraction
  3. Skew penalty — penalize high skew ratio
  4. Composite score = 0.4 * entropy + 0.3 * (1 - null) + 0.3 * (1 - skew)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.profiler.partition_profiler import PartitionStats, entropy


_MAX_SKEW_RATIO: float = 50.0
_SALT_BUCKETS: int = 8


@dataclass(frozen=True)
class ColumnScore:
    """Scored recommendation for a single candidate partition key."""

    column: str
    composite_score: float
    entropy_score: float
    null_penalty: float
    skew_penalty: float
    recommendation: str
    severity: str


@dataclass(frozen=True)
class PartitionHints:
    """Concrete SQL/code snippets for the best candidate column."""

    column: str
    duckdb_repartition: str
    duckdb_salting: str
    pyspark_repartition: str
    pyspark_salting: str
    explanation: str


def score_columns(stats_list: list[PartitionStats]) -> list[ColumnScore]:
    """Score and rank all profiled columns."""
    return sorted(
        [_score_column(s) for s in stats_list],
        key=lambda s: s.composite_score,
        reverse=True,
    )


def _score_column(stats: PartitionStats) -> ColumnScore:
    ent = entropy(stats.partition_counts) if stats.partition_counts else 0.0
    max_entropy = math.log(max(len(stats.partition_counts), 1))
    entropy_score = (ent / max_entropy * 100) if max_entropy > 0 else 0.0

    null_penalty = stats.null_fraction * 100
    skew_clamped = min(stats.skew_ratio, _MAX_SKEW_RATIO)
    skew_penalty = (skew_clamped / _MAX_SKEW_RATIO) * 100

    composite = (
        0.4 * entropy_score
        + 0.3 * (100 - null_penalty)
        + 0.3 * (100 - skew_penalty)
    )

    recommendation, severity = _classify(composite, stats.skew_ratio, stats.null_fraction)

    return ColumnScore(
        column=stats.column,
        composite_score=round(composite, 1),
        entropy_score=round(entropy_score, 1),
        null_penalty=round(null_penalty, 1),
        skew_penalty=round(skew_penalty, 1),
        recommendation=recommendation,
        severity=severity,
    )


def _classify(
    score: float,
    skew_ratio: float,
    null_fraction: float,
) -> tuple[str, str]:
    if score >= 75:
        return "Good partition key candidate", "good"
    if score >= 50:
        if skew_ratio > 10:
            return "Moderate skew — consider salting or composite key", "warning"
        if null_fraction > 0.1:
            return "High null rate — add NOT NULL filter or composite key", "warning"
        return "Acceptable partition key", "info"
    if score >= 25:
        return "High skew — salting recommended before production use", "danger"
    return "Severely skewed or sparse — repartition required", "critical"


def generate_hints(stats: PartitionStats, num_partitions: int = 200) -> PartitionHints:
    """Generate ready-to-paste SQL / PySpark snippets for a column."""
    col = stats.column
    salt_col = f"{col}_salted"

    duckdb_repartition = (
        f"-- Repartition to {num_partitions} uniform partitions\n"
        f"COPY (\n"
        f"  SELECT *\n"
        f"  FROM source_table\n"
        f") TO 'output/' (FORMAT PARQUET, PARTITION_BY ({col}), OVERWRITE_OR_IGNORE);"
    )

    duckdb_salting = (
        f"-- Salt hot key '{col}' into {_SALT_BUCKETS} buckets to reduce skew\n"
        f"CREATE OR REPLACE VIEW {salt_col}_view AS\n"
        f"SELECT\n"
        f"  *,\n"
        f"  CONCAT({col}, '_', (HASH({col}) % {_SALT_BUCKETS})::VARCHAR) AS {salt_col}\n"
        f"FROM source_table;\n\n"
        f"-- Then partition on {salt_col} instead of {col}"
    )

    pyspark_repartition = (
        f"# Repartition to {num_partitions} partitions on {col}\n"
        f"df_repartitioned = (\n"
        f"    df\n"
        f"    .repartition({num_partitions}, F.col(\"{col}\"))\n"
        f")\n"
        f"df_repartitioned.write.partitionBy(\"{col}\").parquet(\"output/\")"
    )

    pyspark_salting = (
        f"# Salt '{col}' into {_SALT_BUCKETS} buckets\n"
        f"import pyspark.sql.functions as F\n\n"
        f"df_salted = df.withColumn(\n"
        f"    \"{salt_col}\",\n"
        f"    F.concat(\n"
        f"        F.col(\"{col}\").cast(\"string\"),\n"
        f"        F.lit(\"_\"),\n"
        f"        (F.hash(F.col(\"{col}\")) % {_SALT_BUCKETS}).cast(\"string\")\n"
        f"    )\n"
        f")\n"
        f"df_salted.write.partitionBy(\"{salt_col}\").parquet(\"output/\")"
    )

    skew_pct = round((stats.skew_ratio - 1) * 100, 1)
    explanation = (
        f"Column '{col}' has a skew ratio of {stats.skew_ratio:.1f}x "
        f"(top partition is {stats.skew_ratio:.1f}x the mean). "
        f"Estimated cardinality: {int(stats.cardinality_estimate):,}. "
        f"{'Salting with ' + str(_SALT_BUCKETS) + ' buckets should reduce hot-key concentration by ~' + str(_SALT_BUCKETS) + 'x.' if stats.skew_ratio > 5 else 'Standard repartition should suffice.'}"
    )

    return PartitionHints(
        column=col,
        duckdb_repartition=duckdb_repartition,
        duckdb_salting=duckdb_salting,
        pyspark_repartition=pyspark_repartition,
        pyspark_salting=pyspark_salting,
        explanation=explanation,
    )
