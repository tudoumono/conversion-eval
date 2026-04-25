"""Description: 設定に応じてMarkdown出力のノイズを正規化します。"""

from __future__ import annotations

import re
from typing import Any


def normalize(text: str, config: dict[str, Any]) -> str:
    if not config.get("enabled", False):
        return text

    for rule in config.get("rules", []):
        if not rule.get("enabled", False):
            continue
        name = rule.get("name")
        if name == "remove_zero_width_chars":
            text = re.sub(r"[\u200b-\u200f\ufeff]", "", text)
        elif name == "remove_bom":
            text = text.lstrip("\ufeff")
        elif name == "collapse_empty_lines":
            text = re.sub(r"\n{3,}", "\n\n", text)
        elif name == "trim_trailing_spaces":
            text = "\n".join(line.rstrip() for line in text.splitlines())
    return text
