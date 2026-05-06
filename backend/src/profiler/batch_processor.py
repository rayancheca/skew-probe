"""
Batch processor: reads Parquet / CSV / Arrow IPC files using DuckDB and
PyArrow, yielding RecordBatches for streaming ingestion into the profiler.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterator

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.ipc as ipc

_BATCH_SIZE: int = 50_000


def iter_parquet_batches(path: Path) -> Iterator[pa.RecordBatch]:
    """Yield RecordBatches from a Parquet file using PyArrow."""
    reader = pq.ParquetFile(path)
    for batch in reader.iter_batches(batch_size=_BATCH_SIZE):
        yield batch


def iter_csv_batches(path: Path) -> Iterator[pa.RecordBatch]:
    """
    Read a CSV file via DuckDB (handles auto-detection), convert to Arrow.
    DuckDB is used here because it handles messy real-world CSV reliably.
    Uses read_csv() with a validated path to avoid string-interpolation injection.
    """
    con = duckdb.connect()
    # read_csv accepts a file path directly — no SQL string interpolation
    arrow_table = con.read_csv(str(path)).arrow()
    for batch in arrow_table.to_batches(max_chunksize=_BATCH_SIZE):
        yield batch


def iter_arrow_ipc_batches(data: bytes) -> Iterator[pa.RecordBatch]:
    """Yield RecordBatches from Arrow IPC bytes (file or stream format)."""
    buf = io.BytesIO(data)
    try:
        reader = ipc.open_file(buf)
        for i in range(reader.num_record_batches):
            yield reader.get_batch(i)
    except pa.lib.ArrowInvalid:
        buf.seek(0)
        reader = ipc.open_stream(buf)
        for batch in reader:
            yield batch


def read_parquet_bytes(data: bytes) -> pa.Table:
    """Read Parquet from raw bytes (for uploaded file handling)."""
    buf = io.BytesIO(data)
    return pq.read_table(buf)


def read_csv_bytes(data: bytes) -> pa.Table:
    """Read CSV from raw bytes via DuckDB."""
    con = duckdb.connect()
    buf = io.BytesIO(data)
    rel = con.read_csv(buf)  # type: ignore[arg-type]
    return rel.arrow()


def infer_schema(table: pa.Table) -> dict[str, str]:
    """Return {column_name: arrow_type_string} for schema inspection."""
    return {field.name: str(field.type) for field in table.schema}
