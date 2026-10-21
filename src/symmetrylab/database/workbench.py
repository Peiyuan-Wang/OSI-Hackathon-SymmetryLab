"""Local run storage: generated identifiers, atomic snapshots, no automatic resume."""
from pathlib import Path
import re
from symmetrylab.schemas import read_json


class RunStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def folder(self, identifier):
        if not re.fullmatch(r"[0-9a-f]{32}", identifier):
            raise ValueError("invalid run identifier")
        folder = self.root / identifier
        if folder.is_symlink():
            raise ValueError("symlink run directories are not supported")
        return folder

    def read(self, identifier):
        return read_json(self.folder(identifier) / "state.json")

    def list(self):
        rows = []
        for path in self.root.glob("*/state.json"):
            try:
                state = self.read(path.parent.name)
                rows.append({k: state[k] for k in ("run_id", "goal", "status", "mode", "created_at")})
            except (ValueError, OSError, KeyError):
                continue
        return sorted(rows, key=lambda row: row["created_at"], reverse=True)[:100]
