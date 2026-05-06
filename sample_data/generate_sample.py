"""
Generates a realistic skewed e-commerce dataset as Parquet.
- user_id: heavily skewed (Zipf distribution — top 1% of users generate ~50% of events)
- product_id: moderately skewed (some hot products)
- region: low skew (6 regions roughly uniform)
- event_type: very low cardinality (6 types)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

N_ROWS = 500_000
N_USERS = 10_000
N_PRODUCTS = 5_000
REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1", "sa-east-1"]
EVENT_TYPES = ["purchase", "view", "add_to_cart", "search", "wishlist", "review"]
SEED = 42


def zipf_sample(n: int, size: int, exponent: float = 1.5, rng: np.random.Generator | None = None) -> np.ndarray:
    """Sample from Zipf distribution with rejection sampling for exact range."""
    if rng is None:
        rng = np.random.default_rng(SEED)
    ranks = np.arange(1, n + 1)
    weights = 1.0 / (ranks ** exponent)
    weights /= weights.sum()
    return rng.choice(n, size=size, p=weights)


def generate() -> None:
    out_dir = Path(__file__).parent
    out_path = out_dir / "sample.parquet"

    rng = np.random.default_rng(SEED)

    user_ids = zipf_sample(N_USERS, N_ROWS, exponent=1.5, rng=rng)
    product_ids = zipf_sample(N_PRODUCTS, N_ROWS, exponent=1.1, rng=rng)
    region_ids = rng.choice(len(REGIONS), size=N_ROWS, p=[0.35, 0.25, 0.2, 0.1, 0.07, 0.03])
    event_type_ids = rng.choice(len(EVENT_TYPES), size=N_ROWS, p=[0.15, 0.40, 0.20, 0.15, 0.07, 0.03])
    timestamps = rng.integers(1_700_000_000, 1_720_000_000, size=N_ROWS)

    # Introduce ~5% nulls in user_id to test null handling
    null_mask = rng.random(N_ROWS) < 0.05
    user_id_col = pa.array(
        [f"user_{uid}" if not null_mask[i] else None for i, uid in enumerate(user_ids)],
        type=pa.string(),
    )

    table = pa.table(
        {
            "user_id": user_id_col,
            "product_id": pa.array([f"prod_{pid}" for pid in product_ids], type=pa.string()),
            "region": pa.array([REGIONS[r] for r in region_ids], type=pa.string()),
            "event_type": pa.array([EVENT_TYPES[e] for e in event_type_ids], type=pa.string()),
            "session_id": pa.array([f"sess_{rng.integers(1, 50000)}" for _ in range(N_ROWS)], type=pa.string()),
            "timestamp": pa.array(timestamps, type=pa.int64()),
        }
    )

    pq.write_table(table, out_path)
    print(f"Generated {N_ROWS:,} rows → {out_path}")
    print(f"Schema: {table.schema}")

    top_users = sorted(
        {f"user_{uid}": 0 for uid in user_ids}.keys()
    )
    # Show skew stats
    from collections import Counter
    user_counts = Counter(f"user_{uid}" for uid in user_ids)
    top10 = user_counts.most_common(10)
    total = sum(user_counts.values())
    print(f"\nTop-10 user_ids contribute {sum(c for _, c in top10) / total:.1%} of rows:")
    for uid, cnt in top10:
        print(f"  {uid}: {cnt:,} rows ({cnt/total:.2%})")


if __name__ == "__main__":
    generate()
