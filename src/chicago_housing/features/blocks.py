"""Assemble the block-structured modeling table from constants.BLOCKS."""

from chicago_housing.constants import BLOCKS


def block_columns(*block_names: str) -> list[str]:
    """Flatten one or more named blocks into a column list (for partial-F)."""
    cols: list[str] = []
    for name in block_names:
        cols.extend(BLOCKS[name])
    return cols
