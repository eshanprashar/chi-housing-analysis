"""Guardrail: a column must not live in two blocks (keeps partial-F honest)."""

from chicago_housing.config import BLOCKS


def test_blocks_do_not_overlap():
    seen: set[str] = set()
    for cols in BLOCKS.values():
        overlap = seen & set(cols)
        assert not overlap, f"columns in multiple blocks: {overlap}"
        seen |= set(cols)
