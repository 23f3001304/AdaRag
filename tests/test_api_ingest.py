"""Unit test for the /ingest route: it routes an upload through the registry into ingest."""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

from fastapi import UploadFile

from api.ingest import ingest
from ingestion.base import ProcessedDoc


class _FakeRegistry:
    """Stands in for the preprocessor registry; echoes the persisted file back as a text doc."""

    def __init__(self) -> None:
        self.seen: Path | None = None

    async def preprocess(self, path: Path) -> ProcessedDoc:
        self.seen = path
        return ProcessedDoc("ignored", "text", path.read_text(encoding="utf-8"), str(path))


class _FakeIngest:
    """Captures the IngestService.ingest arguments."""

    def __init__(self) -> None:
        self.call: tuple | None = None

    async def ingest(self, source, text, modality, original_path) -> dict:
        self.call = (source, text, modality, original_path)
        return {"document_id": "doc1", "chunks": 1, "source": source}


async def test_ingest_routes_upload_through_registry():
    registry, svc = _FakeRegistry(), _FakeIngest()
    state = SimpleNamespace(registry=registry, ingest=svc)
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    upload = UploadFile(filename="note.txt", file=io.BytesIO(b"hello world"))

    result = await ingest(request, upload)

    assert result["document_id"] == "doc1"
    assert svc.call == ("note.txt", "hello world", "text", str(registry.seen))
    assert registry.seen is not None and registry.seen.exists()  # written under data/uploads
    registry.seen.unlink(missing_ok=True)  # cleanup the persisted upload
