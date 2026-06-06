"""Ingest endpoint: route an uploaded file through the preprocessor registry, then index it."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile

router = APIRouter(tags=["ingest"])

_UPLOADS = Path("data/uploads")


@router.post("/ingest")
async def ingest(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    bucket: str = Form("default"),
    context: str = Form(""),
) -> dict:
    """Ingest one file of any supported modality (text/markdown, PDF, image, audio, video).

    The registry turns it into a text surrogate — image -> vision caption + OCR, audio/video ->
    transcript, PDF/text -> its text. Optional `context` (any free text the user added) is prepended
    so the model has more to work with. The original is preserved under data/uploads so a hit can
    cite it. Disambiguation questions are filed in the background so the upload returns promptly.
    """
    state = request.app.state
    name = file.filename or "upload"
    dest = _UPLOADS / f"{uuid.uuid4().hex}{Path(name).suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(await file.read())
    try:
        doc = await state.registry.preprocess(dest)
        text = f"{context.strip()}\n\n{doc.text}" if context.strip() else doc.text
        ingest_service = state.buckets.services(bucket).ingest
        result = await ingest_service.ingest(name, text, doc.modality, doc.original_path)
        background.add_task(
            ingest_service.flag_ambiguity, result["document_id"], name, text, doc.modality
        )
        return result
    except Exception:
        dest.unlink(missing_ok=True)  # don't leave an orphan upload if preprocessing/indexing fails
        raise
