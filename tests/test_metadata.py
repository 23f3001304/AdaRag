"""Unit tests for metadata enrichment value objects (the pure, LLM-free parts)."""

from __future__ import annotations

from enrichment.metadata import ChunkMetadata, _str_list


def test_sparse_terms_joins_keyphrases_then_entities():
    m = ChunkMetadata(entities=["Qdrant", "RRF"], keyphrases=["hybrid search"])
    assert m.sparse_terms() == "hybrid search Qdrant RRF"


def test_empty_metadata_is_empty_with_blank_terms():
    m = ChunkMetadata()
    assert m.is_empty
    assert m.sparse_terms() == ""


def test_str_list_coerces_trims_and_drops_blanks_and_none():
    assert _str_list(["a", " b ", "", 3, None]) == ["a", "b", "3"]


def test_str_list_rejects_non_list():
    assert _str_list("not a list") == []
    assert _str_list(None) == []
