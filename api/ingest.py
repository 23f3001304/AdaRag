"""Ingest endpoint: route an uploaded file through the preprocessor registry, then index it."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile

router = APIRouter(tags=["ingest"])

_UPLOADS = Path("data/uploads")


@router.post("/ingest")
async def ingest(request: Request, file: UploadFile = File(...)) -> dict:
    """Ingest one file of any supported modality (text/markdown, PDF, image, audio, video).

    The registry turns it into a text surrogate — image -> vision caption + OCR, audio/video ->
    transcript, PDF/text -> its text — which is chunked, embedded, and stored. The uploaded original
    is preserved under data/uploads (referenced by the payload) so a hit can cite the artifact.
    """
    state = request.app.state
    name = file.filename or "upload"
    dest = _UPLOADS / f"{uuid.uuid4().hex}{Path(name).suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(await file.read())
    try:
        doc = await state.registry.preprocess(dest)
        return await state.ingest.ingest(name, doc.text, doc.modality, doc.original_path)
    except Exception:
        dest.unlink(missing_ok=True)  # don't leave an orphan upload if preprocessing/indexing fails
        raise
