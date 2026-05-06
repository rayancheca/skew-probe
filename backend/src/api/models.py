"""Pydantic request/response models for the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TopKey(BaseModel):
    key: str
    count: int


class ColumnStatsResponse(BaseModel):
    column: str
    total_rows: int
    cardinality_estimate: float
    null_count: int
    null_fraction: float
    skew_ratio: float
    top_keys: list[TopKey]
    batch_count: int
    hll_error: float


class WorkerTimelineResponse(BaseModel):
    worker_id: int
    assigned_rows: int
    finish_time_sec: float
    is_straggler: bool


class SimulationResponse(BaseModel):
    num_workers: int
    total_rows: int
    rows_per_sec: float
    ideal_finish_sec: float
    actual_finish_sec: float
    slowdown_factor: float
    worker_timelines: list[WorkerTimelineResponse]
    straggler_worker_id: int
    idle_fraction: float


class ColumnScoreResponse(BaseModel):
    column: str
    composite_score: float
    entropy_score: float
    null_penalty: float
    skew_penalty: float
    recommendation: str
    severity: Literal["good", "info", "warning", "danger", "critical"]


class PartitionHintsResponse(BaseModel):
    column: str
    duckdb_repartition: str
    duckdb_salting: str
    pyspark_repartition: str
    pyspark_salting: str
    explanation: str


class ProfileResponse(BaseModel):
    column_stats: list[ColumnStatsResponse]
    scores: list[ColumnScoreResponse]
    simulation: SimulationResponse | None
    hints: list[PartitionHintsResponse]
    schema_info: dict[str, str]


class WebSocketMessage(BaseModel):
    event: str
    data: dict


class SimulateRequest(BaseModel):
    column: str
    num_workers: int = Field(default=8, ge=1, le=256)
    rows_per_sec: float = Field(default=1_000_000, gt=0)
