"""Append-only local event journal. No credentials or hidden reasoning."""

from datetime import datetime, timezone
import json
from pathlib import Path


class Trace:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, state, **data):
        event = {"time": datetime.now(timezone.utc).isoformat(), "state": state, **data}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
