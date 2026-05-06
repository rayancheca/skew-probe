# SkewProbe — Partition Health Profiler

**Profile your partition key distributions in real time. Catch data skew before it stalls your Spark jobs.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178c6?style=flat-square)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-00d4aa?style=flat-square)](LICENSE)

---

## What it is

Skewed partition keys silently kill Spark and Flink jobs. A single hot key can force one worker to process 100× more data than its peers while the rest sit idle — and the Spark UI shows you row counts but never tells you *why* or *what to fix*.

SkewProbe ingests columnar data (Parquet, CSV), profiles key distributions using **Count-Min Sketch** and **HyperLogLog** implemented from scratch, simulates straggler wall-clock impact across a configurable worker pool, and generates concrete **salting SQL and repartition hints** for DuckDB and PySpark — before you ever run the job.

---

## Architecture

```
                    ┌─────────────────────────────────┐
                    │         FastAPI Backend           │
  Parquet / CSV ───▶│  ┌────────────┐ ┌────────────┐  │
                    │  │  CMS + HLL  │ │  DuckDB    │  │◀── WebSocket
                    │  │  Profiler   │ │  Ingestion │  │
                    │  └─────┬──────┘ └────────────┘  │
                    │        │                          │
                    │  ┌─────▼──────┐ ┌────────────┐  │
                    │  │ Straggler  │ │ Partition  │  │
                    │  │ Simulator  │ │ Advisor    │  │
                    │  └────────────┘ └────────────┘  │
                    └──────────────────────────────────┘
                                    ▲
                                    │ REST / JSON
                    ┌───────────────┴──────────────────┐
                    │      React + D3 Frontend          │
                    │  File Upload → Distribution Chart │
                    │  Straggler Timeline → SQL Advisor │
                    └──────────────────────────────────┘
```

**Data flow:**
1. User uploads Parquet/CSV with partition column names
2. Backend reads via PyArrow, streams `RecordBatch`es to the profiler
3. Each batch updates the Count-Min Sketch (frequency) and HyperLogLog (cardinality) for each column
4. Profiler returns top-K heavy hitters, skew ratio, null fraction
5. Straggler simulator runs greedy LPT assignment across N workers, returns per-worker wall-clock timelines
6. Partition advisor scores each column and emits ready-to-paste SQL
7. Frontend renders interactive D3 distribution charts, animated straggler timeline, copy-paste SQL panel

---

## Technical Deep-Dive

### Count-Min Sketch (custom implementation)

The CMS uses `d` independent hash functions over a `w`-wide counter table. Frequency estimate for item `x` is `min(table[i][h_i(x)])` across all `d` rows — guaranteed to never underestimate, with error bound `ε·N` at probability `≥ 1-δ` where `w = ⌈e/ε⌉`, `d = ⌈ln(1/δ)⌉`. At ε=0.5%, δ=1%: 544 × 5 counters = 2.7 KB vs a 500K-row dictionary.

The hash function uses FNV-1a with per-row seeds derived deterministically, ensuring independent hash families without the overhead of MurmurHash3's full 128-bit pipeline.

### HyperLogLog (custom implementation)

Uses `2^b` registers (b=14 → 16,384 registers, 16 KB). Each item's 64-bit SHA-256-derived hash splits into: high `b` bits → register index, remaining bits → leftmost-1-bit position (rho). Cardinality estimate applies the HLL formula with small-range and large-range corrections. At b=14: ≈0.81% standard error on 100K–10M distinct keys.

The decision to implement both from scratch rather than using `datasketches` was intentional — it makes the error bounds and implementation tradeoffs discussable in an interview, and the implementations are testable against known bounds.

### Straggler Simulation

Uses the **Longest Processing Time (LPT)** greedy algorithm — provably within 4/3 of optimal makespan — to assign observed partition sizes to workers. The simulation quantifies: ideal completion time (perfect uniform distribution), actual completion time (straggler finishes last), slowdown factor, and idle fraction (wasted CPU). This gives data engineers a concrete cost model before committing to a job configuration.

### Why DuckDB for ingestion?

DuckDB's `read_csv_auto` handles heterogeneous real-world CSV reliably (auto-detected types, encoding, delimiters) and outputs Apache Arrow natively — zero copy into PyArrow. For Parquet, PyArrow's `ParquetFile.iter_batches()` streams without loading the full file into memory.

---

## Install & Run

### Requirements

- Python 3.11+ (tested on 3.11.15)
- Node.js 20+

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Generate sample data

```bash
cd backend
source .venv/bin/activate
python ../sample_data/generate_sample.py
```

This creates `sample_data/sample.parquet` — 500K rows with a Zipf-distributed `user_id` where `user_0` holds 38% of all events.

---

## Usage

1. Upload `sample_data/sample.parquet` (or your own Parquet/CSV)
2. Enter `user_id, region` in the partition columns field
3. Set worker count (e.g. 8)
4. Click **Profile Partitions**

The UI shows:
- **Distribution chart**: top-20 key bar chart with cold→warm severity color scale
- **Skew metrics**: skew ratio, cardinality estimate (HLL), null rate, advisor score
- **Straggler timeline**: animated per-worker bar chart showing who finishes and who stalls
- **Advisor panel**: per-column score breakdown + ready-to-paste DuckDB and PySpark SQL

---

## Sample Output

With the included sample data, `user_id` produces:

```
Skew ratio:    9.2×  (user_0 holds 38% of rows)
Cardinality:   ~5,060 distinct keys (HLL estimate, ±0.81%)
Null rate:     5.0%
Advisor score: 79/100 (good)
Slowdown:      3.69× with 8 workers
Idle fraction: 72.9%
```

Salting hint (DuckDB):
```sql
CREATE OR REPLACE VIEW user_id_salted_view AS
SELECT
  *,
  CONCAT(user_id, '_', (HASH(user_id) % 8)::VARCHAR) AS user_id_salted
FROM source_table;
```

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v --tb=short
```

All 35 tests pass, including probabilistic bounds tests for CMS and HLL.

---

## Project Structure

```
skew-probe/
├── backend/
│   ├── src/
│   │   ├── algorithms/
│   │   │   ├── count_min_sketch.py   # CMS from scratch
│   │   │   └── hyperloglog.py        # HLL from scratch
│   │   ├── profiler/
│   │   │   ├── partition_profiler.py # Core streaming profiler
│   │   │   └── batch_processor.py   # Arrow/Parquet/CSV ingestion
│   │   ├── simulator/
│   │   │   └── straggler_sim.py     # LPT straggler model
│   │   ├── advisor/
│   │   │   └── partition_advisor.py # Scoring + SQL generation
│   │   ├── api/
│   │   │   ├── routes.py            # FastAPI endpoints
│   │   │   ├── models.py            # Pydantic request/response types
│   │   │   └── websocket.py         # Streaming WebSocket handler
│   │   └── main.py                  # FastAPI app entry
│   └── tests/
│       ├── test_cms.py              # 9 CMS tests
│       ├── test_hll.py              # 8 HLL tests
│       ├── test_profiler.py         # 11 profiler tests
│       └── test_simulator.py        # 8 simulator tests
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── upload/              # File drop zone + config
│       │   ├── profiler/            # D3 bar chart + metric tiles
│       │   ├── simulator/           # Animated straggler timeline
│       │   ├── advisor/             # Score breakdown + SQL panel
│       │   └── ui/                  # Column selector tabs
│       ├── lib/
│       │   ├── types.ts             # TypeScript API types
│       │   └── utils.ts             # Formatting + color helpers
│       └── styles/tokens.css        # Design system tokens
└── sample_data/
    └── generate_sample.py           # Generates 500K-row Zipf dataset
```

---

## License

MIT
