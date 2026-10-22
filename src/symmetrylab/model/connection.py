"""Saved model connection: Base URL, model ID, protocol and API key on this computer.

The key is stored in a file readable only by the current user (mode 0600) and is
never returned to the interface, written to run records or included in reports.
It is not encrypted; anyone who can read your account's files can read it.
"""
import json
import os
from pathlib import Path
import re
import threading

FIELDS = ("base_url", "model", "protocol")
DEFAULT = {"base_url": "", "model": "", "protocol": "chat_completions"}


class ConnectionStore:
    def __init__(self, path, defaults=None):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.defaults = {**DEFAULT, **{k: v for k, v in (defaults or {}).items() if k in FIELDS and isinstance(v, str)}}

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        result = dict(self.defaults)
        result.update({k: data[k] for k in FIELDS if isinstance(data.get(k), str)})
        if isinstance(data.get("api_key"), str):
            result["api_key"] = data["api_key"]
        return result

    def public(self):
        data = self.load()
        key = data.get("api_key", "")
        env = bool(os.environ.get("SYMMETRYLAB_API_KEY"))
        ready = bool(data["base_url"] and data["model"] and (key or env))
        return {**{k: data[k] for k in FIELDS}, "key_saved": bool(key), "key_hint": key[-4:] if len(key) >= 12 else "",
                "key_source": "saved" if key else ("environment" if env else "none"), "ready": ready}

    def client_config(self, override=None):
        """Config for OpenAICompatibleClient. override may carry unsaved form values for a test."""
        data = self.load()
        for k, v in (override or {}).items():
            if k in FIELDS + ("api_key",) and isinstance(v, str) and v.strip():
                data[k] = v.strip()
        return data

    def save(self, values, forget_key=False):
        if not isinstance(values, dict) or set(values) - set(FIELDS + ("api_key",)):
            raise ValueError("unknown connection fields")
        candidate = self.client_config(values)
        if forget_key:
            candidate.pop("api_key", None)
        key = candidate.get("api_key", "")
        if key and (len(key) > 500 or re.search(r"\s", key)):
            raise ValueError("API key must be one line without spaces")
        if any(len(candidate.get(k, "")) > 500 for k in FIELDS):
            raise ValueError("connection fields are too long")
        # Validate URL/protocol/model with the real client, using a dummy key if none is set.
        from symmetrylab.model.client import OpenAICompatibleClient
        OpenAICompatibleClient({**candidate, "api_key": key or "validation-only"})
        record = {k: candidate[k] for k in FIELDS}
        if key:
            record["api_key"] = key
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
            os.chmod(temp, 0o600)
            temp.replace(self.path)
        return self.public()
