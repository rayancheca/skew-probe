"""
WebSocket handler for streaming batch-by-batch profiling updates.

Protocol:
  Client → Server: { "action": "start", "columns": ["col1", "col2"], "num_workers": 8 }
  Server → Client: { "event": "batch_complete", "data": { ... PartitionStats ... } }
  Server → Client: { "event": "done", "data": { ... final ProfileResponse ... } }
  Server → Client: { "event": "error", "data": { "message": "..." } }
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from fastapi import WebSocket, WebSocketDisconnect

from src.advisor.partition_advisor import generate_hints, score_columns
from src.profiler.partition_profiler import PartitionProfiler, PartitionStats
from src.simulator.straggler_sim import simulate_straggler


def _stats_to_dict(stats: PartitionStats) -> dict:
    return {
        "column": stats.column,
        "total_rows": stats.total_rows,
        "cardinality_estimate": stats.cardinality_estimate,
        "null_count": stats.null_count,
        "null_fraction": stats.null_fraction,
        "skew_ratio": stats.skew_ratio,
        "top_keys": [{"key": k, "count": c} for k, c in stats.top_keys],
        "batch_count": stats.batch_count,
        "hll_error": stats.hll_error,
    }


async def handle_parquet_stream(
    websocket: WebSocket,
    parquet_path: Path,
    columns: list[str],
    num_workers: int,
    rows_per_sec: float,
) -> None:
    """Stream a Parquet file batch by batch, sending updates after each batch."""
    profiler = PartitionProfiler(columns)
    pf = await asyncio.to_thread(pq.ParquetFile, parquet_path)

    batch_num = 0
    async for batch in _iter_parquet_async(pf):
        stats_list = await asyncio.to_thread(profiler.ingest_batch, batch)
        batch_num += 1

        payload = {
            "event": "batch_complete",
            "data": {
                "batch": batch_num,
                "column_stats": [_stats_to_dict(s) for s in stats_list],
            },
        }
        await websocket.send_text(json.dumps(payload))
        await asyncio.sleep(0)  # yield to event loop

    # Final summary
    final_stats = profiler.current_stats()
    scores = score_columns(final_stats)
    hints = [generate_hints(s) for s in final_stats]

    sim_data = None
    if final_stats and final_stats[0].partition_counts:
        sim = simulate_straggler(final_stats[0].partition_counts, num_workers, rows_per_sec)
        sim_data = {
            "num_workers": sim.num_workers,
            "total_rows": sim.total_rows,
            "ideal_finish_sec": sim.ideal_finish_sec,
            "actual_finish_sec": sim.actual_finish_sec,
            "slowdown_factor": sim.slowdown_factor,
            "idle_fraction": sim.idle_fraction,
            "worker_timelines": [
                {
                    "worker_id": t.worker_id,
                    "assigned_rows": t.assigned_rows,
                    "finish_time_sec": t.finish_time_sec,
                    "is_straggler": t.is_straggler,
                }
                for t in sim.worker_timelines
            ],
        }

    await websocket.send_text(
        json.dumps(
            {
                "event": "done",
                "data": {
                    "column_stats": [_stats_to_dict(s) for s in final_stats],
                    "scores": [
                        {
                            "column": sc.column,
                            "composite_score": sc.composite_score,
                            "entropy_score": sc.entropy_score,
                            "null_penalty": sc.null_penalty,
                            "skew_penalty": sc.skew_penalty,
                            "recommendation": sc.recommendation,
                            "severity": sc.severity,
                        }
                        for sc in scores
                    ],
                    "hints": [
                        {
                            "column": h.column,
                            "duckdb_repartition": h.duckdb_repartition,
                            "duckdb_salting": h.duckdb_salting,
                            "pyspark_repartition": h.pyspark_repartition,
                            "pyspark_salting": h.pyspark_salting,
                            "explanation": h.explanation,
                        }
                        for h in hints
                    ],
                    "simulation": sim_data,
                },
            }
        )
    )


async def _iter_parquet_async(pf: pq.ParquetFile):
    """
    Async wrapper that reads Parquet batches off the event loop thread.
    Each batch is fetched in a thread pool executor to avoid blocking the loop.
    """
    loop = asyncio.get_running_loop()
    iterator = pf.iter_batches(batch_size=50_000)

    def _next_batch() -> pa.RecordBatch | None:
        try:
            return next(iterator)
        except StopIteration:
            return None

    while True:
        batch = await loop.run_in_executor(None, _next_batch)
        if batch is None:
            break
        yield batch
