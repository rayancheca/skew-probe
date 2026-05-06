"""
Count-Min Sketch — sub-linear frequency estimation for streaming data.

Uses d independent hash functions over a w-wide table. The frequency estimate
for any item is the minimum cell value across all d rows. Error bound:
    estimate <= true_count + epsilon * total_count
with probability >= 1 - delta, where w = ceil(e/epsilon), d = ceil(ln(1/delta)).
"""

import math
import struct
from dataclasses import dataclass, field
from typing import Final

# FNV-1a basis and prime for fast mixing
_FNV_BASIS_32: Final = 0x811C9DC5
_FNV_PRIME_32: Final = 0x01000193


def _fnv1a_hash(data: bytes, seed: int) -> int:
    """FNV-1a hash with seed mixing via XOR before hashing."""
    h = _FNV_BASIS_32 ^ (seed & 0xFFFFFFFF)
    for byte in data:
        h ^= byte
        h = (h * _FNV_PRIME_32) & 0xFFFFFFFF
    return h


def _to_bytes(item: object) -> bytes:
    if isinstance(item, str):
        return item.encode("utf-8")
    if isinstance(item, int):
        return struct.pack(">q", item)
    if isinstance(item, float):
        return struct.pack(">d", item)
    return str(item).encode("utf-8")


@dataclass
class CountMinSketch:
    """
    Count-Min Sketch with configurable accuracy/memory tradeoff.

    Attributes:
        epsilon: Max relative error (smaller = more accurate = more memory).
        delta: Failure probability (smaller = more reliable = more rows).
        width: Number of counters per row (w = ceil(e / epsilon)).
        depth: Number of hash rows (d = ceil(ln(1 / delta))).
        total_count: Number of items added so far.
    """

    epsilon: float
    delta: float
    width: int = field(init=False)
    depth: int = field(init=False)
    total_count: int = field(init=False, default=0)
    _table: list[list[int]] = field(init=False)
    _seeds: list[int] = field(init=False)

    def __post_init__(self) -> None:
        if not (0 < self.epsilon < 1):
            raise ValueError(f"epsilon must be in (0, 1), got {self.epsilon}")
        if not (0 < self.delta < 1):
            raise ValueError(f"delta must be in (0, 1), got {self.delta}")
        self.width = math.ceil(math.e / self.epsilon)
        self.depth = math.ceil(math.log(1.0 / self.delta))
        self._table = [[0] * self.width for _ in range(self.depth)]
        # Deterministic seeds derived from depth index for reproducibility
        self._seeds = [_fnv1a_hash(str(i).encode(), 0xDEADBEEF) for i in range(self.depth)]

    def add(self, item: object, count: int = 1) -> None:
        """Increment all d counters for item by count."""
        if count < 1:
            raise ValueError("count must be >= 1")
        key = _to_bytes(item)
        for row, seed in enumerate(self._seeds):
            col = _fnv1a_hash(key, seed) % self.width
            self._table[row][col] += count
        self.total_count += count

    def estimate(self, item: object) -> int:
        """Return the minimum-across-rows frequency estimate for item."""
        key = _to_bytes(item)
        return min(
            self._table[row][_fnv1a_hash(key, seed) % self.width]
            for row, seed in enumerate(self._seeds)
        )

    def merge(self, other: "CountMinSketch") -> "CountMinSketch":
        """Return a new sketch that is the union of self and other."""
        if self.width != other.width or self.depth != other.depth:
            raise ValueError("Sketches must have the same dimensions to merge")
        merged = CountMinSketch(epsilon=self.epsilon, delta=self.delta)
        merged.total_count = self.total_count + other.total_count
        for r in range(self.depth):
            for c in range(self.width):
                merged._table[r][c] = self._table[r][c] + other._table[r][c]
        return merged

    @property
    def memory_bytes(self) -> int:
        """Approximate memory footprint in bytes (8 bytes per int64 counter)."""
        return self.depth * self.width * 8
