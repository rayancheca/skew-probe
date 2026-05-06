"""
Straggler simulator: models wall-clock task completion time for
skewed vs. ideal partition assignments across a configurable worker pool.

The model assumes:
  - Each worker processes rows at a constant throughput (rows/sec).
  - Ideal: partition sizes are uniform (total_rows / num_workers each).
  - Actual: partition sizes follow the observed top-K distribution.
  - Job completes when the slowest worker finishes (straggler effect).
"""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_ROWS_PER_SEC: float = 1_000_000


@dataclass(frozen=True)
class WorkerTimeline:
    """Wall-clock completion for one worker."""

    worker_id: int
    assigned_rows: int
    finish_time_sec: float
    is_straggler: bool


@dataclass(frozen=True)
class SimulationResult:
    """Full simulation outcome for one scenario."""

    num_workers: int
    total_rows: int
    rows_per_sec: float
    ideal_finish_sec: float
    actual_finish_sec: float
    slowdown_factor: float
    worker_timelines: list[WorkerTimeline]
    straggler_worker_id: int
    idle_fraction: float


def simulate_straggler(
    partition_counts: list[int],
    num_workers: int,
    rows_per_sec: float = _DEFAULT_ROWS_PER_SEC,
) -> SimulationResult:
    """
    Simulate job completion under observed partition distribution.

    Args:
        partition_counts: Row counts per observed partition key (desc sorted).
        num_workers: Number of workers in the pool.
        rows_per_sec: Throughput per worker.

    Returns:
        SimulationResult with per-worker timelines and slowdown factor.
    """
    if num_workers < 1:
        raise ValueError("num_workers must be >= 1")
    if rows_per_sec <= 0:
        raise ValueError("rows_per_sec must be > 0")
    if not partition_counts:
        raise ValueError("partition_counts cannot be empty")

    total_rows = sum(partition_counts)
    if total_rows == 0:
        raise ValueError("total_rows must be > 0")

    worker_loads = _assign_partitions_greedy(partition_counts, num_workers)

    timelines: list[WorkerTimeline] = [
        WorkerTimeline(
            worker_id=i,
            assigned_rows=worker_loads[i],
            finish_time_sec=worker_loads[i] / rows_per_sec,
            is_straggler=False,
        )
        for i in range(num_workers)
    ]

    actual_finish = max(t.finish_time_sec for t in timelines)
    straggler_id = max(range(num_workers), key=lambda i: timelines[i].finish_time_sec)

    # Mark the straggler
    timelines[straggler_id] = WorkerTimeline(
        worker_id=straggler_id,
        assigned_rows=timelines[straggler_id].assigned_rows,
        finish_time_sec=timelines[straggler_id].finish_time_sec,
        is_straggler=True,
    )

    ideal_finish = (total_rows / num_workers) / rows_per_sec
    slowdown = actual_finish / ideal_finish if ideal_finish > 0 else 1.0

    # Idle fraction: wasted worker-time as fraction of total available time
    total_available = actual_finish * num_workers
    total_used = sum(t.finish_time_sec for t in timelines)
    idle_fraction = max(0.0, (total_available - total_used) / total_available)

    return SimulationResult(
        num_workers=num_workers,
        total_rows=total_rows,
        rows_per_sec=rows_per_sec,
        ideal_finish_sec=ideal_finish,
        actual_finish_sec=actual_finish,
        slowdown_factor=slowdown,
        worker_timelines=timelines,
        straggler_worker_id=straggler_id,
        idle_fraction=idle_fraction,
    )


def _assign_partitions_greedy(counts: list[int], num_workers: int) -> list[int]:
    """
    Greedy longest-processing-time (LPT) assignment.
    Assigns each partition (largest first) to the currently least-loaded worker.
    This is the standard approximation for makespan minimization.
    """
    loads = [0] * num_workers
    for count in sorted(counts, reverse=True):
        min_worker = min(range(num_workers), key=lambda i: loads[i])
        loads[min_worker] += count
    return loads
