"""Description: Markdown出力の見出し・表・箇条書きなどの構造指標を計測します。"""

from __future__ import annotations

import re


HEADING_RE = re.compile(r"^(#{1,6})\s+\S", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]*\)")
CODE_BLOCK_RE = re.compile(r"```")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S", re.MULTILINE)


def compute_structural_metrics(text: str) -> dict[str, object]:
    heading_depths = [len(match.group(1)) for match in HEADING_RE.finditer(text)]
    return {
        "heading_count": len(heading_depths),
        "heading_max_depth": max(heading_depths, default=0),
        "heading_hierarchy_valid": _heading_hierarchy_valid(heading_depths),
        "table_count": _count_tables(text),
        "table_row_count": _count_table_rows(text),
        "image_ref_count": len(IMAGE_RE.findall(text)),
        "list_count": _count_list_blocks(text),
        "code_block_count": len(CODE_BLOCK_RE.findall(text)) // 2,
        "paragraph_count": _count_paragraphs(text),
    }


def _heading_hierarchy_valid(depths: list[int]) -> bool:
    if not depths:
        return True
    previous = depths[0]
    for depth in depths[1:]:
        if depth - previous > 1:
            return False
        previous = depth
    return True


def _table_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip().startswith("|") and line.strip().endswith("|")]


def _count_tables(text: str) -> int:
    count = 0
    in_table = False
    for line in text.splitlines():
        is_table_line = line.strip().startswith("|") and line.strip().endswith("|")
        if is_table_line and not in_table:
            count += 1
            in_table = True
        elif not is_table_line:
            in_table = False
    return count


def _count_table_rows(text: str) -> int:
    return len(_table_lines(text))


def _count_list_blocks(text: str) -> int:
    count = 0
    in_list = False
    for line in text.splitlines():
        is_item = bool(LIST_ITEM_RE.match(line))
        if is_item and not in_list:
            count += 1
            in_list = True
        elif not is_item:
            in_list = False
    return count


def _count_paragraphs(text: str) -> int:
    paragraphs = 0
    for block in re.split(r"\n\s*\n", text.strip()):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("```"):
            continue
        if LIST_ITEM_RE.match(stripped):
            continue
        paragraphs += 1
    return paragraphs
