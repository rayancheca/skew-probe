export interface TopKey {
  key: string;
  count: number;
}

export interface ColumnStats {
  column: string;
  total_rows: number;
  cardinality_estimate: number;
  null_count: number;
  null_fraction: number;
  skew_ratio: number;
  top_keys: TopKey[];
  batch_count: number;
  hll_error: number;
}

export interface WorkerTimeline {
  worker_id: number;
  assigned_rows: number;
  finish_time_sec: number;
  is_straggler: boolean;
}

export interface SimulationResult {
  num_workers: number;
  total_rows: number;
  rows_per_sec: number;
  ideal_finish_sec: number;
  actual_finish_sec: number;
  slowdown_factor: number;
  worker_timelines: WorkerTimeline[];
  straggler_worker_id: number;
  idle_fraction: number;
}

export type Severity = 'good' | 'info' | 'warning' | 'danger' | 'critical';

export interface ColumnScore {
  column: string;
  composite_score: number;
  entropy_score: number;
  null_penalty: number;
  skew_penalty: number;
  recommendation: string;
  severity: Severity;
}

export interface PartitionHints {
  column: string;
  duckdb_repartition: string;
  duckdb_salting: string;
  pyspark_repartition: string;
  pyspark_salting: string;
  explanation: string;
}

export interface ProfileResponse {
  column_stats: ColumnStats[];
  scores: ColumnScore[];
  simulation: SimulationResult | null;
  hints: PartitionHints[];
  schema_info: Record<string, string>;
}
