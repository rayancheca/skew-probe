"""
HyperLogLog — probabilistic cardinality estimation.

Uses 2^b registers of size 5 bits (packed as bytes). Each hash h is split into:
  - high b bits → register index j
  - remaining bits → position of leftmost 1-bit (rho)
The cardinality estimate is alpha * m^2 * harmonic_mean(2^-reg[j]).

Error bound: standard error ≈ 1.04 / sqrt(m), where m = 2^b.
For b=14 (m=16384): ~0.81% relative error.
"""

import hashlib
import math
import struct
from dataclasses import dataclass, field

_ALPHA: dict[int, float] = {
    4: 0.673,
    5: 0.697,
    6: 0.709,
}


def _alpha(m: int) -> float:
    if m in _ALPHA:
        return _ALPHA[m]
    return 0.7213 / (1 + 1.079 / m)


def _hash64(item: object) -> int:
    """MurmurHash3-inspired 64-bit hash via SHA-256 truncation."""
    if isinstance(item, str):
        data = item.encode("utf-8")
    elif isinstance(item, int):
        data = struct.pack(">q", item)
    elif isinstance(item, float):
        data = struct.pack(">d", item)
    else:
        data = str(item).encode("utf-8")
    digest = hashlib.sha256(data).digest()
    return struct.unpack(">Q", digest[:8])[0]


def _rho(w: int, max_bits: int) -> int:
    """Position of the leftmost 1-bit in the lower max_bits bits of w (1-indexed)."""
    if w == 0:
        return max_bits + 1
    count = 1
    mask = 1 << (max_bits - 1)
    while count <= max_bits and not (w & mask):
        count += 1
        mask >>= 1
    return count


@dataclass
class HyperLogLog:
    """
    HyperLogLog cardinality estimator.

    Attributes:
        b: Register width exponent. m = 2^b registers. Range [4, 16].
        m: Number of registers (2^b).
        registers: Array of m byte registers.
    """

    b: int
    m: int = field(init=False)
    registers: bytearray = field(init=False)

    def __post_init__(self) -> None:
        if not (4 <= self.b <= 16):
            raise ValueError(f"b must be in [4, 16], got {self.b}")
        self.m = 1 << self.b
        self.registers = bytearray(self.m)

    def add(self, item: object) -> None:
        """Process one item and update the appropriate register."""
        h = _hash64(item)
        j = h >> (64 - self.b)
        w = h & ((1 << (64 - self.b)) - 1)
        rho = _rho(w, 64 - self.b)
        if rho > self.registers[j]:
            self.registers[j] = rho

    def cardinality(self) -> float:
        """Estimate distinct cardinality using the HyperLogLog formula."""
        alpha = _alpha(self.m)
        z = sum(2.0 ** -r for r in self.registers)
        raw = alpha * self.m * self.m / z

        # Small range correction
        zeros = self.registers.count(0)
        if raw <= 2.5 * self.m and zeros > 0:
            return self.m * math.log(self.m / zeros)

        # Large range correction (> 1/30 * 2^32)
        two32 = 1 << 32
        if raw > two32 / 30:
            return -two32 * math.log(1 - raw / two32)

        return raw

    def merge(self, other: "HyperLogLog") -> "HyperLogLog":
        """Return a new HLL that is the union of self and other."""
        if self.b != other.b:
            raise ValueError("HyperLogLog instances must have the same b to merge")
        merged = HyperLogLog(b=self.b)
        for i in range(self.m):
            merged.registers[i] = max(self.registers[i], other.registers[i])
        return merged

    @property
    def standard_error(self) -> float:
        """Expected relative standard error (≈ 1.04 / sqrt(m))."""
        return 1.04 / math.sqrt(self.m)

    @property
    def memory_bytes(self) -> int:
        """Memory footprint in bytes."""
        return self.m
