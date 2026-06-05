"""Unit tests for bucket naming helpers (pure, no Qdrant)."""

from __future__ import annotations

import pytest

from core.buckets import bucket_slug, collection_name


def test_default_bucket_uses_base_collection():
    assert collection_name("adarag_chunks", "default") == "adarag_chunks"


def test_named_bucket_is_suffixed_and_slugged():
    assert collection_name("adarag_chunks", "My Project!") == "adarag_chunks_my_project"


def test_bucket_slug_normalizes():
    assert bucket_slug("  Legal Docs 2026 ") == "legal_docs_2026"


def test_bucket_slug_rejects_empty():
    with pytest.raises(ValueError, match="invalid bucket name"):
        bucket_slug("!!!")
