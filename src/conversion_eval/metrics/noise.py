"""Description: Markdown出力に含まれるノイズ量を計測します。"""

from __future__ import annotations

import re


CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\ufeff]")


def compute_noise_metrics(text: str) -> dict[str, object]:
    lines = text.splitlines()
    empty_lines = sum(1 for line in lines if not line.strip())
    line_count = len(lines) or 1
    return {
        "noise_nan_count": len(re.findall(r"\bnan\b", text, flags=re.IGNORECASE)),
        "noise_empty_line_ratio": round(empty_lines / line_count, 6),
        "noise_control_char_count": len(CONTROL_RE.findall(text)),
        "noise_zero_width_char_count": len(ZERO_WIDTH_RE.findall(text)),
        "noise_replacement_char_count": text.count("\ufffd"),
    }
