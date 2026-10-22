import hashlib
import json
from io import BytesIO
from pathlib import Path

import pytest

from scripts.fetch_ssg_catalog import fetch_catalog


def manifest_at(path: Path, payload: bytes) -> Path:
    manifest = path / "manifest.json"
    manifest.write_text(json.dumps({"files": [{
        "file": "catalog.sqlite",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "download_url": "https://github.com/example/project/releases/download/data/catalog.sqlite",
    }]}), encoding="utf-8")
    return manifest


def test_downloads_catalog_and_checks_checksum(tmp_path, monkeypatch):
    payload = b"verified sqlite payload"
    manifest = manifest_at(tmp_path, payload)
    requests = []

    def open_url(request, timeout):
        requests.append((request.full_url, timeout))
        return BytesIO(payload)

    monkeypatch.setattr("scripts.fetch_ssg_catalog.urlopen", open_url)
    target = fetch_catalog(manifest)

    assert target.read_bytes() == payload
    assert len(requests) == 1 and requests[0][0].endswith("catalog.sqlite")
    assert list(tmp_path.glob(".*.download")) == []


def test_reuses_verified_catalog_without_network(tmp_path, monkeypatch):
    payload = b"already present"
    manifest = manifest_at(tmp_path, payload)
    target = tmp_path / "catalog.sqlite"
    target.write_bytes(payload)

    def fail(*args, **kwargs):
        pytest.fail("a valid local catalog should not be downloaded again")

    monkeypatch.setattr("scripts.fetch_ssg_catalog.urlopen", fail)
    assert fetch_catalog(manifest) == target


def test_rejects_bad_download_and_removes_partial_file(tmp_path, monkeypatch):
    manifest = manifest_at(tmp_path, b"expected")
    monkeypatch.setattr("scripts.fetch_ssg_catalog.urlopen", lambda *a, **k: BytesIO(b"tampered"))

    with pytest.raises(ValueError, match="failed manifest"):
        fetch_catalog(manifest)

    assert not (tmp_path / "catalog.sqlite").exists()
    assert list(tmp_path.glob(".*.download")) == []


def test_rejects_existing_catalog_with_wrong_hash(tmp_path, monkeypatch):
    manifest = manifest_at(tmp_path, b"expected")
    (tmp_path / "catalog.sqlite").write_bytes(b"tampered")
    monkeypatch.setattr("scripts.fetch_ssg_catalog.urlopen", lambda *a, **k: pytest.fail("unexpected download"))

    with pytest.raises(ValueError, match="Existing SSG catalog"):
        fetch_catalog(manifest)
