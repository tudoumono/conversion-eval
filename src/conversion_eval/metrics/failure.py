"""Description: 変換結果を実質成功・準失敗・失敗に分類します。"""

from __future__ import annotations


def classify_failure(convert_success: bool, convert_timeout: bool, text: str, metrics: dict[str, object]) -> str:
    if convert_timeout:
        return "timeout"
    if not convert_success:
        return "convert_error"
    char_count = len(text)
    if char_count < 10:
        return "empty_output"
    replacement_count = int(metrics.get("noise_replacement_char_count", 0))
    if char_count > 0 and replacement_count / char_count > 0.5:
        return "mojibake_majority"
    if (
        int(metrics.get("heading_count", 0)) == 0
        and int(metrics.get("table_count", 0)) == 0
        and int(metrics.get("paragraph_count", 0)) < 1
    ):
        return "structure_collapsed"
    return ""
