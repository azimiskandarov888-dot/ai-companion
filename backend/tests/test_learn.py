"""Learning: the extraction captures everything important, distilled short."""

from __future__ import annotations

from app import learn


def test_extraction_covers_key_memory_categories():
    p = learn._EXTRACTION_SYSTEM
    # Everything the family asked Bob to remember about the elder.
    for word in ("семью", "здоровье", "планы", "даты", "истории", "переживает"):
        assert word in p


def test_extraction_distills_not_verbatim():
    p = learn._EXTRACTION_SYSTEM
    # It must store the MEANING short, in its own words — never word-for-word.
    assert "своими словами" in p
    assert "НЕ слово в слово" in p
