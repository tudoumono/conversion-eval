"""Description: 人の目評価用CSVテンプレートを生成します。"""

from __future__ import annotations

import csv
from pathlib import Path

from conversion_eval.folder_markers import write_report_folder_markers
from conversion_eval.models import Pattern
from conversion_eval.pipeline.runner import collect_input_files


FIELDS = [
    "pattern_id",
    "sample_file",
    "score_readability",
    "score_structure",
    "score_table_quality",
    "score_image_handling",
    "score_noise_level",
    "score_information_loss",
    "score_overall",
    "score_rag_readiness",
    "comment",
]

FIELD_LABELS = {
    "pattern_id": "パターンID",
    "sample_file": "サンプルファイル",
    "score_readability": "読みやすさ",
    "score_structure": "構造再現性",
    "score_table_quality": "表品質",
    "score_image_handling": "画像扱い",
    "score_noise_level": "ノイズ少なさ",
    "score_information_loss": "情報欠落少なさ",
    "score_overall": "総合評価",
    "score_rag_readiness": "RAG適性",
    "comment": "コメント",
}


def write_human_eval_template(path: Path, sample_dir: Path, patterns: list[Pattern]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_report_folder_markers(path.parent, "human_eval")
    sample_files = collect_input_files(sample_dir)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[FIELD_LABELS[field] for field in FIELDS])
        writer.writeheader()
        for sample_file in sample_files:
            rel = sample_file.relative_to(sample_dir).as_posix()
            for pattern in patterns:
                if not pattern.applies_to(sample_file):
                    continue
                row = {"pattern_id": pattern.id, "sample_file": rel}
                writer.writerow(_label_row(row))


def _label_row(row: dict[str, object]) -> dict[str, object]:
    return {FIELD_LABELS[field]: row.get(field, "") for field in FIELDS}
