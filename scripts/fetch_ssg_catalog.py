"""Download the pinned SSG SQLite catalog and verify its manifest checksum."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "ssg" / "manifest.json"
CHUNK_SIZE = 1024 * 1024


def digest_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def read_catalog_entry(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = [
        entry for entry in manifest.get("files", [])
        if isinstance(entry, dict)
        and str(entry.get("file", "")).endswith(".sqlite")
    ]
    if len(entries) != 1:
        raise ValueError("SSG manifest must contain exactly one SQLite catalog")
    entry = entries[0]
    filename = entry.get("file")
    url = entry.get("download_url")
    if not isinstance(filename, str) or not filename or Path(filename).name != filename:
        raise ValueError("SSG catalog filename must be a simple filename")
    if not isinstance(url, str) or urlparse(url).scheme != "https" or urlparse(url).hostname != "github.com":
        raise ValueError("SSG catalog download_url must be an HTTPS GitHub release URL")
    if not isinstance(entry.get("bytes"), int) or entry["bytes"] <= 0:
        raise ValueError("SSG catalog manifest bytes must be a positive integer")
    sha256 = entry.get("sha256")
    if not isinstance(sha256, str) or len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
        raise ValueError("SSG catalog manifest must include a lowercase SHA-256 digest")
    return entry


def fetch_catalog(manifest_path: Path = DEFAULT_MANIFEST, destination: Path | None = None) -> Path:
    entry = read_catalog_entry(manifest_path)
    target = destination or manifest_path.parent / str(entry["file"])
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        size, digest = digest_file(target)
        if size != entry["bytes"] or digest != entry["sha256"]:
            raise ValueError(f"Existing SSG catalog failed manifest validation: {target}")
        print(f"SSG catalog verified: {target}")
        return target

    request = Request(str(entry["download_url"]), headers={"User-Agent": "SymmetryLab-build"})
    fd, temp_name = tempfile.mkstemp(prefix=f".{entry['file']}.", suffix=".download", dir=target.parent)
    temp_path = Path(temp_name)
    digest = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(fd, "wb") as output:
            with urlopen(request, timeout=180) as response:
                while chunk := response.read(CHUNK_SIZE):
                    size += len(chunk)
                    if size > entry["bytes"]:
                        raise ValueError("Downloaded SSG catalog is larger than the manifest size")
                    digest.update(chunk)
                    output.write(chunk)
        if size != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
            raise ValueError("Downloaded SSG catalog failed manifest size or SHA-256 validation")
        temp_path.chmod(0o644)
        os.replace(temp_path, target)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    print(f"Downloaded and verified SSG catalog: {target}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    try:
        fetch_catalog(args.manifest, args.destination)
    except Exception as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
