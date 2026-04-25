"""Description: 1変換1行のraw CSVレポートを書き出します。"""

from __future__ import annotations

import csv
from pathlib import Path

from conversion_eval.models import RunRecord


BASE_FIELDS = [
    "pattern_id",
    "pattern_name",
    "input_file",
    "input_size_bytes",
    "input_extension",
    "uses_llm",
    "llm_provider",
    "uses_internal_models",
    "allow_network_download",
    "input_pdf_type",
    "input_encoding_detected",
    "preprocess_time_sec",
    "preprocess_success",
    "preprocess_error",
    "preprocess_timeout",
    "intermediate_size_bytes",
    "convert_time_sec",
    "convert_success",
    "convert_error",
    "convert_timeout",
    "total_time_sec",
    "output_size_bytes",
    "output_char_count",
    "output_failure_reason",
    "tool_version",
]

METRIC_FIELDS = [
    "heading_count",
    "heading_max_depth",
    "heading_hierarchy_valid",
    "table_count",
    "table_row_count",
    "image_ref_count",
    "list_count",
    "code_block_count",
    "paragraph_count",
    "noise_nan_count",
    "noise_empty_line_ratio",
    "noise_control_char_count",
    "noise_zero_width_char_count",
    "noise_replacement_char_count",
]

FIELD_LABELS = {
    "pattern_id": "パターンID",
    "pattern_name": "パターン名",
    "input_file": "入力ファイル",
    "input_size_bytes": "入力サイズ_バイト",
    "input_extension": "入力拡張子",
    "uses_llm": "LLM使用",
    "llm_provider": "LLMプロバイダ",
    "uses_internal_models": "内部モデル使用",
    "allow_network_download": "ネットワーク取得許可",
    "input_pdf_type": "PDF種別",
    "input_encoding_detected": "検出文字コード",
    "preprocess_time_sec": "前処理時間_秒",
    "preprocess_success": "前処理成功",
    "preprocess_error": "前処理エラー",
    "preprocess_timeout": "前処理タイムアウト",
    "intermediate_size_bytes": "中間ファイルサイズ_バイト",
    "convert_time_sec": "変換時間_秒",
    "convert_success": "変換成功",
    "convert_error": "変換エラー",
    "convert_timeout": "変換タイムアウト",
    "total_time_sec": "合計時間_秒",
    "output_size_bytes": "出力サイズ_バイト",
    "output_char_count": "出力文字数",
    "output_failure_reason": "出力失敗理由",
    "tool_version": "ツールバージョン",
    "heading_count": "見出し数",
    "heading_max_depth": "見出し最大深さ",
    "heading_hierarchy_valid": "見出し階層妥当",
    "table_count": "表数",
    "table_row_count": "表行数",
    "image_ref_count": "画像参照数",
    "list_count": "リスト数",
    "code_block_count": "コードブロック数",
    "paragraph_count": "段落数",
    "noise_nan_count": "ノイズ_NaN数",
    "noise_empty_line_ratio": "ノイズ_空行率",
    "noise_control_char_count": "ノイズ_制御文字数",
    "noise_zero_width_char_count": "ノイズ_ゼロ幅文字数",
    "noise_replacement_char_count": "ノイズ_置換文字数",
}


def write_raw_report(path: Path, records: list[RunRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = BASE_FIELDS + METRIC_FIELDS
    labeled_fields = [FIELD_LABELS[field] for field in fields]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=labeled_fields)
        writer.writeheader()
        for record in records:
            writer.writerow(_label_row(record.to_row(), fields))


def _label_row(row: dict[str, object], fields: list[str]) -> dict[str, object]:
    return {FIELD_LABELS[field]: row.get(field, "") for field in fields}
