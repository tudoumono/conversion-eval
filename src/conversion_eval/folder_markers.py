"""Description: 生成フォルダの用途が分かるように説明用ファイルを配置します。"""

from __future__ import annotations

from pathlib import Path

from conversion_eval.models import Pattern


PREPROCESSOR_MARKER_NAMES = {
    "none": "形式変換なし",
    "com": "Office_COM形式変換",
    "com_pdf": "Office_COM_PDF化",
    "libreoffice": "LibreOffice形式変換",
    "libreoffice_pdf": "LibreOffice_PDF化",
}

# 旧バージョンで作成した説明ファイルだけを掃除するための名前です。
LEGACY_PREPROCESSOR_MARKER_NAMES = {
    "none": ("前処理なし",),
    "com": ("Office_COM前処理",),
    "libreoffice": ("LibreOffice前処理",),
}

LEGACY_PATTERN_MARKER_NAMES = {
    "pattern_b": ("変換結果_COM + Docling",),
    "pattern_d": ("変換結果_LibreOffice + Docling",),
    "pattern_f": ("変換結果_Direct + Docling",),
    "pattern_h": ("変換結果_Direct + Docling OCR",),
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
    intermediate_marker_name = "この実行の中間ファイル" if _is_run_dir(intermediate_root) else "中間ファイル置き場"
    output_marker_name = "この実行のMarkdown変換結果" if _is_run_dir(output_root) else "Markdown変換結果置き場"
    _write_marker(
        intermediate_root,
        intermediate_marker_name,
        "Markdown変換の前に行う形式変換で作成したファイルや、元ファイルをそのまま渡すための中間ファイルを置くフォルダです。",
    )
    _write_marker(
        intermediate_root / pattern.preprocessor,
        PREPROCESSOR_MARKER_NAMES.get(pattern.preprocessor, f"{pattern.preprocessor}形式変換"),
        f"{pattern.preprocessor} 形式変換を通した中間ファイルを置くフォルダです。",
        legacy_filenames=LEGACY_PREPROCESSOR_MARKER_NAMES.get(pattern.preprocessor, ()),
    )
    _write_marker(
        intermediate_dir,
        "入力フォルダ構造を保持した中間ファイル",
        "入力フォルダの階層を保ったまま、変換に渡す中間ファイルを置くフォルダです。",
    )
    _write_marker(
        output_root,
        output_marker_name,
        "各変換パターンで作成したMarkdown出力を置くフォルダです。",
    )
    _write_marker(
        output_root / pattern.id,
        f"Markdown変換結果_{_safe_filename(pattern.name)}",
        f"{pattern.name} パターンで作成したMarkdown出力を置くフォルダです。",
        legacy_filenames=_legacy_pattern_marker_names(pattern),
    )
    _write_marker(
        output_dir,
        "ノイズ正規化後Markdown",
        "Markdown変換後にノイズ正規化を行ったMarkdownファイルを置くフォルダです。",
        legacy_filenames=("ノイズ除去後Markdown",),
    )


def write_report_folder_markers(report_dir: Path, report_kind: str) -> None:
    marker_name, description = REPORT_MARKERS.get(
        report_kind,
        (f"{report_kind}レポート", f"{report_kind} レポートを置くフォルダです。"),
    )
    if _is_run_dir(report_dir):
        reports_root = report_dir.parent.parent
        report_kind_dir = report_dir.parent
        _write_marker(
            reports_root,
            "評価レポート置き場",
            "変換評価で作成したraw、summary、目視評価テンプレートをまとめて置くフォルダです。",
        )
        _write_marker(report_kind_dir, marker_name, description)
        _write_marker(report_dir, f"実行別_{marker_name}", f"{report_dir.name} の{description}")
        return

    _write_marker(
        report_dir.parent,
        "評価レポート置き場",
        "変換評価で作成したraw、summary、目視評価テンプレートをまとめて置くフォルダです。",
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
            "Markdown変換の前に行う形式変換で作成したファイルや、元ファイルをそのまま渡すための中間ファイルを置くフォルダです。",
        )
        for preprocessor in sorted({pattern.preprocessor for pattern in patterns}):
            _write_existing_intermediate_markers(intermediate_root, preprocessor)
        for run_dir in _run_dirs(intermediate_root):
            _write_marker(
                run_dir,
                "この実行の中間ファイル",
                "Markdown変換の前に行う形式変換で作成したファイルや、元ファイルをそのまま渡すための中間ファイルを置くフォルダです。",
            )
            for preprocessor in sorted({pattern.preprocessor for pattern in patterns}):
                _write_existing_intermediate_markers(run_dir, preprocessor)

    if output_root.exists():
        _write_marker(
            output_root,
            "Markdown変換結果置き場",
            "各変換パターンで作成したMarkdown出力を置くフォルダです。",
        )
        for pattern in patterns:
            _write_existing_output_markers(output_root, pattern)
        for run_dir in _run_dirs(output_root):
            _write_marker(
                run_dir,
                "この実行のMarkdown変換結果",
                "各変換パターンで作成したMarkdown出力を置くフォルダです。",
            )
            for pattern in patterns:
                _write_existing_output_markers(run_dir, pattern)

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
                for run_dir in _run_dirs(report_dir):
                    _write_marker(run_dir, f"実行別_{marker_name}", f"{run_dir.name} の{description}")


def _write_existing_intermediate_markers(intermediate_root: Path, preprocessor: str) -> None:
    preprocessor_dir = intermediate_root / preprocessor
    if not preprocessor_dir.exists():
        return
    _write_marker(
        preprocessor_dir,
        PREPROCESSOR_MARKER_NAMES.get(preprocessor, f"{preprocessor}形式変換"),
        f"{preprocessor} 形式変換を通した中間ファイルを置くフォルダです。",
        legacy_filenames=LEGACY_PREPROCESSOR_MARKER_NAMES.get(preprocessor, ()),
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
        f"Markdown変換結果_{_safe_filename(pattern.name)}",
        f"{pattern.name} パターンで作成したMarkdown出力を置くフォルダです。",
        legacy_filenames=_legacy_pattern_marker_names(pattern),
    )
    _write_marker(
        pattern_dir,
        "ノイズ正規化後Markdown",
        "Markdown変換後にノイズ正規化を行ったMarkdownファイルを置くフォルダです。",
        legacy_filenames=("ノイズ除去後Markdown",),
    )
    for directory in _child_dirs(pattern_dir):
        _write_marker(
            directory,
            "ノイズ正規化後Markdown",
            "Markdown変換後にノイズ正規化を行ったMarkdownファイルを置くフォルダです。",
            legacy_filenames=("ノイズ除去後Markdown",),
        )


def _child_dirs(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_dir())


def _run_dirs(root: Path) -> list[Path]:
    return sorted(path for path in root.iterdir() if path.is_dir() and _is_run_dir(path))


def _is_run_dir(path: Path) -> bool:
    return path.name.startswith("run_")


def _legacy_pattern_marker_names(pattern: Pattern) -> tuple[str, ...]:
    return (f"変換結果_{pattern.name}", *LEGACY_PATTERN_MARKER_NAMES.get(pattern.id, ()))


def _write_marker(
    directory: Path,
    filename: str,
    description: str,
    legacy_filenames: tuple[str, ...] = (),
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _safe_filename(filename)
    path.write_text(f"{description}\n", encoding="utf-8", newline="\n")
    for legacy_filename in legacy_filenames:
        legacy_path = directory / _safe_filename(legacy_filename)
        if legacy_path != path and legacy_path.is_file():
            legacy_path.unlink(missing_ok=True)


def _safe_filename(filename: str) -> str:
    value = filename
    for char in INVALID_FILENAME_CHARS:
        value = value.replace(char, "_")
    return value.strip(" .") or "説明"
