"""FastAPI REST routes for file upload and analysis."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path
from typing import Annotated

import pyarrow.parquet as pq
import pyarrow as pa
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.advisor.partition_advisor import generate_hints, score_columns
from src.api.models import (
    ColumnScoreResponse,
    ColumnStatsResponse,
    PartitionHintsResponse,
    ProfileResponse,
    SimulateRequest,
    SimulationResponse,
    TopKey,
    WorkerTimelineResponse,
)
from src.profiler.batch_processor import read_csv_bytes, read_parquet_bytes, infer_schema
from src.profiler.partition_profiler import PartitionProfiler, PartitionStats
from src.simulator.straggler_sim import SimulationResult, simulate_straggler

router = APIRouter()


def _stats_to_response(stats: PartitionStats) -> ColumnStatsResponse:
    return ColumnStatsResponse(
        column=stats.column,
        total_rows=stats.total_rows,
        cardinality_estimate=stats.cardinality_estimate,
        null_count=stats.null_count,
        null_fraction=stats.null_fraction,
        skew_ratio=stats.skew_ratio,
        top_keys=[TopKey(key=k, count=c) for k, c in stats.top_keys],
        batch_count=stats.batch_count,
        hll_error=stats.hll_error,
    )


def _sim_to_response(sim: SimulationResult) -> SimulationResponse:
    return SimulationResponse(
        num_workers=sim.num_workers,
        total_rows=sim.total_rows,
        rows_per_sec=sim.rows_per_sec,
        ideal_finish_sec=sim.ideal_finish_sec,
        actual_finish_sec=sim.actual_finish_sec,
        slowdown_factor=sim.slowdown_factor,
        worker_timelines=[
            WorkerTimelineResponse(
                worker_id=t.worker_id,
                assigned_rows=t.assigned_rows,
                finish_time_sec=t.finish_time_sec,
                is_straggler=t.is_straggler,
            )
            for t in sim.worker_timelines
        ],
        straggler_worker_id=sim.straggler_worker_id,
        idle_fraction=sim.idle_fraction,
    )


async def _profile_table(
    table: pa.Table,
    partition_columns: list[str],
    num_workers: int,
    rows_per_sec: float,
) -> ProfileResponse:
    schema_info = infer_schema(table)

    missing = [c for c in partition_columns if c not in schema_info]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Columns not found in file: {missing}. Available: {list(schema_info.keys())}",
        )

    profiler = PartitionProfiler(partition_columns)
    stats_list = await asyncio.to_thread(profiler.ingest_table, table)

    scores = score_columns(stats_list)
    hints = [generate_hints(s, num_partitions=200) for s in stats_list]

    # Run simulation on best column's top-k partition counts
    sim_result = None
    if stats_list:
        best_stats = stats_list[0]
        counts = best_stats.partition_counts
        if counts:
            sim_raw = simulate_straggler(counts, num_workers, rows_per_sec)
            sim_result = _sim_to_response(sim_raw)

    return ProfileResponse(
        column_stats=[_stats_to_response(s) for s in stats_list],
        scores=[
            ColumnScoreResponse(
                column=sc.column,
                composite_score=sc.composite_score,
                entropy_score=sc.entropy_score,
                null_penalty=sc.null_penalty,
                skew_penalty=sc.skew_penalty,
                recommendation=sc.recommendation,
                severity=sc.severity,  # type: ignore[arg-type]
            )
            for sc in scores
        ],
        simulation=sim_result,
        hints=[
            PartitionHintsResponse(
                column=h.column,
                duckdb_repartition=h.duckdb_repartition,
                duckdb_salting=h.duckdb_salting,
                pyspark_repartition=h.pyspark_repartition,
                pyspark_salting=h.pyspark_salting,
                explanation=h.explanation,
            )
            for h in hints
        ],
        schema_info=schema_info,
    )


@router.post("/analyze", response_model=ProfileResponse)
async def analyze_file(
    file: Annotated[UploadFile, File()],
    partition_columns: Annotated[str, Form()],
    num_workers: Annotated[int, Form(ge=1, le=1024)] = 8,
    rows_per_sec: Annotated[float, Form(gt=0)] = 1_000_000,
) -> ProfileResponse:
    """
    Upload a Parquet or CSV file and receive partition health analysis.

    Args:
        file: The data file (.parquet or .csv).
        partition_columns: Comma-separated column names to profile.
        num_workers: Number of workers for straggler simulation.
        rows_per_sec: Worker throughput for simulation.
    """
    content = await file.read()
    columns = [c.strip() for c in partition_columns.split(",") if c.strip()]

    if not columns:
        raise HTTPException(status_code=422, detail="partition_columns must not be empty")

    filename = (file.filename or "").lower()
    try:
        if filename.endswith(".parquet"):
            table = await asyncio.to_thread(read_parquet_bytes, content)
        elif filename.endswith(".csv"):
            table = await asyncio.to_thread(read_csv_bytes, content)
        else:
            # Try Parquet first, then CSV; preserve the first error for diagnostics
            try:
                table = await asyncio.to_thread(read_parquet_bytes, content)
            except Exception as parquet_exc:
                try:
                    table = await asyncio.to_thread(read_csv_bytes, content)
                except Exception as csv_exc:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Could not read as Parquet ({parquet_exc}) or CSV ({csv_exc})",
                    ) from csv_exc
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Failed to read file: {exc}"
        ) from exc

    return await _profile_table(table, columns, num_workers, rows_per_sec)


@router.post("/simulate", response_model=SimulationResponse)
async def run_simulation(body: SimulateRequest) -> SimulationResponse:
    """Re-run straggler simulation on last profiling result (by column name)."""
    raise HTTPException(
        status_code=501,
        detail="Use /analyze to profile a file — simulation is bundled with analysis.",
    )


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sample-columns")
async def sample_columns() -> dict[str, list[str]]:
    """Return column names from the bundled sample dataset."""
    sample_path = Path(__file__).parent.parent.parent.parent / "sample_data" / "sample.parquet"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample data not found. Run sample_data/generate_sample.py")
    table = pq.read_table(sample_path)
    return {"columns": table.schema.names}
