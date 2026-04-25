"""Description: rawレコードを集計し、パターン別・拡張子別サマリーを出力します。"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from conversion_eval.models import RunRecord


FIELD_LABELS = {
    "pattern_id": "パターンID",
    "input_extension": "入力拡張子",
    "record_count": "レコード数",
    "effective_success_count": "有効成功数",
    "effective_success_rate": "有効成功率",
    "avg_total_time_sec": "平均合計時間_秒",
    "avg_noise_count": "平均ノイズ数",
    "avg_output_char_count": "平均出力文字数",
    "single_process_hours": "逐次処理時間_時間",
    "parallel_4_hours": "4並列処理時間_時間",
    "parallel_8_hours": "8並列処理時間_時間",
    "failure_estimate": "推定失敗件数",
}


def write_summaries(summary_dir: Path, records: list[RunRecord], production_file_count: int = 120_000) -> None:
    summary_dir.mkdir(parents=True, exist_ok=True)
    _write_group_summary(summary_dir / "by_pattern.csv", records, "pattern_id")
    _write_group_summary(summary_dir / "by_extension.csv", records, "input_extension")
    _write_extrapolation(summary_dir / "extrapolation.csv", records, production_file_count)


def _write_group_summary(path: Path, records: list[RunRecord], key: str) -> None:
    groups: dict[str, list[RunRecord]] = defaultdict(list)
    for record in records:
        groups[str(getattr(record, key))].append(record)

    fields = [
        key,
        "record_count",
        "effective_success_count",
        "effective_success_rate",
        "avg_total_time_sec",
        "avg_noise_count",
        "avg_output_char_count",
    ]
    labeled_fields = [FIELD_LABELS[field] for field in fields]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=labeled_fields)
        writer.writeheader()
        for group_key, group_records in sorted(groups.items()):
            count = len(group_records)
            effective = [r for r in group_records if r.convert_success and not r.output_failure_reason]
            avg_time = sum(r.total_time_sec for r in group_records) / count if count else 0
            avg_noise = sum(_noise_count(r) for r in group_records) / count if count else 0
            avg_chars = sum(r.output_char_count for r in group_records) / count if count else 0
            row = {
                key: group_key,
                "record_count": count,
                "effective_success_count": len(effective),
                "effective_success_rate": f"{(len(effective) / count if count else 0):.6f}",
                "avg_total_time_sec": f"{avg_time:.6f}",
                "avg_noise_count": f"{avg_noise:.6f}",
                "avg_output_char_count": f"{avg_chars:.2f}",
            }
            writer.writerow(_label_row(row, fields))


def _write_extrapolation(path: Path, records: list[RunRecord], production_file_count: int) -> None:
    groups: dict[str, list[RunRecord]] = defaultdict(list)
    for record in records:
        groups[record.pattern_id].append(record)

    fields = ["pattern_id", "avg_total_time_sec", "single_process_hours", "parallel_4_hours", "parallel_8_hours", "failure_estimate"]
    labeled_fields = [FIELD_LABELS[field] for field in fields]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=labeled_fields)
        writer.writeheader()
        for pattern_id, group_records in sorted(groups.items()):
            count = len(group_records)
            avg_time = sum(r.total_time_sec for r in group_records) / count if count else 0
            failed = [r for r in group_records if not (r.convert_success and not r.output_failure_reason)]
            failure_rate = len(failed) / count if count else 0
            single_hours = avg_time * production_file_count / 3600
            row = {
                "pattern_id": pattern_id,
                "avg_total_time_sec": f"{avg_time:.6f}",
                "single_process_hours": f"{single_hours:.2f}",
                "parallel_4_hours": f"{single_hours / 4:.2f}",
                "parallel_8_hours": f"{single_hours / 8:.2f}",
                "failure_estimate": int(round(failure_rate * production_file_count)),
            }
            writer.writerow(_label_row(row, fields))


def _noise_count(record: RunRecord) -> int:
    return sum(
        int(record.metrics.get(name, 0))
        for name in (
            "noise_nan_count",
            "noise_control_char_count",
            "noise_zero_width_char_count",
            "noise_replacement_char_count",
        )
    )


def _label_row(row: dict[str, object], fields: list[str]) -> dict[str, object]:
    return {FIELD_LABELS[field]: row.get(field, "") for field in fields}
