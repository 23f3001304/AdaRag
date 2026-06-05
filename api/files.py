"""Files endpoint: serve a bucket's preserved original (image/audio/video/pdf) for view + download.

Access is restricted to files under data/uploads so an arbitrary path can't be read off disk.

Two browser-side hazards shape this endpoint:

1. The route is `/files/blob` and the stored path is base64url-encoded. A plain
   `/files/raw?path=data/uploads/<md5>.pdf` URL looks like a tracking beacon, so URL-pattern
   ad/privacy blockers can drop it. A neutral route + opaque param carries no pattern to match.

2. `?download=1` serves the bytes as `application/octet-stream`. Some browser extensions block
   `application/pdf` responses outright - they let the request reach the server, then swap the
   200 response for an empty 204, so the browser saves a 0-byte file. A generic content-type is
   invisible to such filters; the JS caller supplies the real filename, so the user still gets
   `resume.pdf`. Inline previews (image/audio/video, never blocked) keep their true content-type.
"""

from __future__ import annotations

import base64
import binascii
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(tags=["files"])

_UPLOADS = Path("data/uploads")


def _decode_path(raw: str) -> str:
    """Decode a base64url path param; tolerate a plain path so direct/older links still resolve."""
    try:
        return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return raw


@router.get("/files/blob")
async def blob(
    path: str = Query(...),
    name: str | None = None,
    download: bool = False,
) -> FileResponse:
    """Serve a preserved original by its stored path; `name` sets the download filename."""
    try:
        resolved = Path(_decode_path(path)).resolve()
        if _UPLOADS.resolve() not in resolved.parents or not resolved.is_file():
            raise HTTPException(status_code=404, detail="file not found")
    except OSError as exc:
        raise HTTPException(status_code=404, detail="file not found") from exc
    if download:  # no Content-Disposition: some extensions drop attachment downloads of binaries.
        # The JS caller names the saved file via the anchor's `download` attribute instead.
        return FileResponse(resolved, media_type="application/octet-stream")
    media = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
    return FileResponse(
        resolved,
        media_type=media,
        filename=name or resolved.name,
        content_disposition_type="inline",
    )
