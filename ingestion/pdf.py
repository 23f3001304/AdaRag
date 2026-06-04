"""PDF preprocessor: pypdf extracts the text layer as the surrogate; the original is preserved."""

from __future__ import annotations

from pathlib import Path

from ingestion.base import ProcessedDoc


class PdfPreprocessor:
    """Extracts a PDF's text layer (pypdf); the original is kept for figure/vision answers later."""

    extensions = (".pdf",)

    async def process(self, path: Path) -> ProcessedDoc:
        from pypdf import PdfReader  # deferred: only needed when a PDF is ingested

        reader = PdfReader(str(path))
        text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
        return ProcessedDoc(path.name, "pdf", text.strip(), str(path))
