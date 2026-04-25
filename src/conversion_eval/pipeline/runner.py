"""Description: 入力ファイル一覧を集め、複数パターンの実行を制御します。"""

from __future__ import annotations

from pathlib import Path

from conversion_eval.models import Pattern, RunRecord
from conversion_eval.pipeline.pipeline import run_one


SUPPORTED_EXTENSIONS = {
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".pdf",
    ".pptx",
    ".rtf",
    ".bik",
    ".bpg",
    ".bca",
    ".bci",
}


def collect_input_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def run_patterns(
    patterns: list[Pattern],
    input_dir: Path,
    intermediate_root: Path,
    output_root: Path,
    noise_config: dict,
) -> list[RunRecord]:
    records: list[RunRecord] = []
    files = collect_input_files(input_dir)
    for pattern in patterns:
        for input_path in files:
            if not pattern.applies_to(input_path):
                continue
            records.append(
                run_one(
                    pattern=pattern,
                    input_path=input_path,
                    root_input_dir=input_dir,
                    intermediate_root=intermediate_root,
                    output_root=output_root,
                    noise_config=noise_config,
                )
            )
    return records
