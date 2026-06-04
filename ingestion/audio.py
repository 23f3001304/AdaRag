"""Audio/video preprocessor: faster-whisper transcribes speech to a text surrogate (original kept).

Video is handled too — faster-whisper decodes via `av` (ffmpeg), so it transcribes a video's audio
track without a separate dependency. Scene detection / diarization are intentionally out of scope.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ingestion.base import ProcessedDoc

_VIDEO = frozenset({".mp4", ".mov", ".mkv", ".webm", ".avi"})


class AudioPreprocessor:
    """Transcribes audio (and video audio tracks) with faster-whisper into a text surrogate."""

    extensions = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".mp4", ".mov", ".mkv", ".webm")

    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size
        self._model: Any | None = None

    def _load(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel  # deferred: heavy native lib + model download

            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
        return self._model

    def _transcribe(self, path: str) -> str:
        segments, _ = self._load().transcribe(path)
        return " ".join(seg.text.strip() for seg in segments).strip()

    async def process(self, path: Path) -> ProcessedDoc:
        text = await asyncio.to_thread(self._transcribe, str(path))
        modality = "video" if path.suffix.lower() in _VIDEO else "audio"
        return ProcessedDoc(path.name, modality, text, str(path))
