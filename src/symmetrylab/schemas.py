"""Shared data and deterministic serialization. No provider dependency."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Protocol

CONVENTION = "F(k)=s*R*k+s*q; k_new=k+theta"


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")


@dataclass(frozen=True)
class SolverBudget:
    max_combinations: int = 100_000
    seconds: float = 10.0

    def __post_init__(self):
        import math
        if type(self.max_combinations) is not int or self.max_combinations < 0:
            raise ValueError("max_combinations must be a nonnegative integer")
        if not math.isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("seconds must be finite and nonnegative")


class ModelClient(Protocol):
    def complete(self, messages: list[dict], max_tokens: int) -> dict: ...
