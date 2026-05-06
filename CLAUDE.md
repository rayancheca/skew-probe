# Agent Instructions — Read Before Every Action

Read in this order, every session:

1. `~/daily-builder/prompts/rules/session_protocol.md`
2. `~/daily-builder/prompts/rules/quality_bar.md`
3. `~/daily-builder/prompts/rules/code_rules.md`
4. `state.md` in this directory
5. This file

---

# Project: Skew Probe — Partition Health Profiler

**Tagline:** Profile your partition key distributions in real time and catch data skew before it stalls your distributed jobs.

**Domain:** Big Data, Data Engineering and Analytics Pipelines

**Tech stack:** Python, PyArrow, DuckDB, FastAPI, WebSockets, TypeScript, React, D3.js, Vite

**Problem:** Skewed partition keys silently kill Spark and Flink jobs — a single hot key can force one worker to process 100x more data than its peers while the rest sit idle, and the Spark UI shows you counts but never tells you why or what to fix. Skew Probe ingests columnar data batches, profiles key distributions using Count-Min Sketch and HyperLogLog, simulates straggler wall-clock impact across a configurable worker pool, and generates concrete salting or repartition recommendations before the job ever runs.

**Why it stands out:** It implements two canonical probabilistic data structures from scratch, models real distributed-systems straggler behavior with a quantitative cost model, and produces output data engineers can act on immediately — not just a visualization, but a diagnostic instrument with concrete recommendations.

---

# Core features

    • Real-time partition key profiler built on Count-Min Sketch and HyperLogLog — estimates cardinality and top-K heavy hitters across streaming Parquet/Arrow IPC batches without materializing full histograms, surfacing skew ratio (max-partition / mean-partition) as each batch lands
    • Straggler simulator: given a live partition distribution and a configurable worker count, models wall-clock completion time under ideal vs. skewed assignment and renders an animated timeline showing which workers finish and which ones stall
    • Partition advisor that scores candidate keys by cardinality entropy, null concentration, and estimated join selectivity — then emits ready-to-paste salting SQL and repartition hints for both DuckDB and PySpark

---

# Full Implementation Plan

Read `~/daily-builder/prompts/new_project.md` for the complete instructions.
Start at STEP 3 — the idea is already chosen and approved. Details are above.
Do not regenerate ideas.

Estimated sessions: 3
