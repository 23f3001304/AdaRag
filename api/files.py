"""Files endpoint: serve a bucket's preserved original (image/audio/video/pdf) for view + download.

Access is restricted to files under data/uploads so an arbitrary path can't be read off disk.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(tags=["files"])

_UPLOADS = Path("data/uploads")


@router.get("/files/raw")
async def raw(path: str = Query(...), name: str | None = None) -> FileResponse:
    """Serve a preserved original by its stored path; `name` sets the download filename."""
    try:
        resolved = Path(path).resolve()
        if _UPLOADS.resolve() not in resolved.parents or not resolved.is_file():
            raise HTTPException(status_code=404, detail="file not found")
    except OSError as exc:
        raise HTTPException(status_code=404, detail="file not found") from exc
    media = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
    return FileResponse(resolved, media_type=media, filename=name or resolved.name)
