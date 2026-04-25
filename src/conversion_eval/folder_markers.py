"""Description: 生成フォルダの用途が分かるように説明用ファイルを配置します。"""

from __future__ import annotations

from pathlib import Path

from conversion_eval.models import Pattern


PREPROCESSOR_MARKER_NAMES = {
    "none": "前処理なし",
    "com": "Office_COM前処理",
    "libreoffice": "LibreOffice前処理",
}

REPORT_MARKERS = {
    "raw": (
        "変換結果の生レポート",
        "1ファイル×1パターンの実行結果をそのまま記録したCSVを置くフォルダです。",
    ),
    "summary": (
        "集計レポート",
        "パターン別、拡張子別、処理時間外挿などの集計CSVを置くフォルダです。",
    ),
    "human_eval": (
        "目視評価テンプレート",
        "人が変換品質を評価するためのCSVテンプレートを置くフォルダです。",
    ),
}

INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def write_conversion_folder_markers(
    pattern: Pattern,
    intermediate_root: Path,
    intermediate_dir: Path,
    output_root: Path,
    output_dir: Path,
) -> None:
    _write_marker(
        intermediate_root,
        "中間ファイル置き場",
        "変換前処理で作成した一時ファイルや、元ファイルをそのまま渡すための中間ファイルを置くフォルダです。",
    )
    _write_marker(
        intermediate_root / pattern.preprocessor,
        PREPROCESSOR_MARKER_NAMES.get(pattern.preprocessor, f"{pattern.preprocessor}前処理"),
        f"{pattern.preprocessor} 前処理を通した中間ファイルを置くフォルダです。",
    )
    _write_marker(
        intermediate_dir,
        "入力フォルダ構造を保持した中間ファイル",
        "入力フォルダの階層を保ったまま、変換に渡す中間ファイルを置くフォルダです。",
    )
    _write_marker(
        output_root,
        "Markdown変換結果置き場",
        "各変換パターンで作成したMarkdown出力を置くフォルダです。",
    )
    _write_marker(
        output_root / pattern.id,
        f"変換結果_{_safe_filename(pattern.name)}",
        f"{pattern.name} パターンで作成したMarkdown出力を置くフォルダです。",
    )
    _write_marker(
        output_dir,
        "ノイズ除去後Markdown",
        "変換後にノイズ正規化を行ったMarkdownファイルを置くフォルダです。",
    )


def write_report_folder_markers(report_dir: Path, report_kind: str) -> None:
    _write_marker(
        report_dir.parent,
        "評価レポート置き場",
        "変換評価で作成したraw、summary、目視評価テンプレートをまとめて置くフォルダです。",
    )
    marker_name, description = REPORT_MARKERS.get(
        report_kind,
        (f"{report_kind}レポート", f"{report_kind} レポートを置くフォルダです。"),
    )
    _write_marker(report_dir, marker_name, description)


def write_existing_generated_folder_markers(
    patterns: list[Pattern],
    intermediate_root: Path,
    output_root: Path,
    reports_root: Path,
) -> None:
    if intermediate_root.exists():
        _write_marker(
            intermediate_root,
            "中間ファイル置き場",
            "変換前処理で作成した一時ファイルや、元ファイルをそのまま渡すための中間ファイルを置くフォルダです。",
        )
        for preprocessor in sorted({pattern.preprocessor for pattern in patterns}):
            _write_existing_intermediate_markers(intermediate_root, preprocessor)

    if output_root.exists():
        _write_marker(
            output_root,
            "Markdown変換結果置き場",
            "各変換パターンで作成したMarkdown出力を置くフォルダです。",
        )
        for pattern in patterns:
            _write_existing_output_markers(output_root, pattern)

    if reports_root.exists():
        _write_marker(
            reports_root,
            "評価レポート置き場",
            "変換評価で作成したraw、summary、目視評価テンプレートをまとめて置くフォルダです。",
        )
        for report_kind in REPORT_MARKERS:
            report_dir = reports_root / report_kind
            if report_dir.exists():
                marker_name, description = REPORT_MARKERS[report_kind]
                _write_marker(report_dir, marker_name, description)


def _write_existing_intermediate_markers(intermediate_root: Path, preprocessor: str) -> None:
    preprocessor_dir = intermediate_root / preprocessor
    if not preprocessor_dir.exists():
        return
    _write_marker(
        preprocessor_dir,
        PREPROCESSOR_MARKER_NAMES.get(preprocessor, f"{preprocessor}前処理"),
        f"{preprocessor} 前処理を通した中間ファイルを置くフォルダです。",
    )
    for directory in _child_dirs(preprocessor_dir):
        _write_marker(
            directory,
            "入力フォルダ構造を保持した中間ファイル",
            "入力フォルダの階層を保ったまま、変換に渡す中間ファイルを置くフォルダです。",
        )


def _write_existing_output_markers(output_root: Path, pattern: Pattern) -> None:
    pattern_dir = output_root / pattern.id
    if not pattern_dir.exists():
        return
    _write_marker(
        pattern_dir,
        f"変換結果_{_safe_filename(pattern.name)}",
        f"{pattern.name} パターンで作成したMarkdown出力を置くフォルダです。",
    )
    for directory in _child_dirs(pattern_dir):
        _write_marker(
            directory,
            "ノイズ除去後Markdown",
            "変換後にノイズ正規化を行ったMarkdownファイルを置くフォルダです。",
        )


def _child_dirs(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_dir())


def _write_marker(directory: Path, filename: str, description: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _safe_filename(filename)
    path.write_text(f"{description}\n", encoding="utf-8", newline="\n")


def _safe_filename(filename: str) -> str:
    value = filename
    for char in INVALID_FILENAME_CHARS:
        value = value.replace(char, "_")
    return value.strip(" .") or "説明"
