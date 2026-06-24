"""Assemble the block-structured modeling table from config.BLOCKS."""

from chicago_housing.config import BLOCKS


def block_columns(*block_names: str) -> list[str]:
    """Flatten one or more named blocks into a column list (for partial-F)."""
    cols: list[str] = []
    for name in block_names:
        cols.extend(BLOCKS[name])
    return cols
