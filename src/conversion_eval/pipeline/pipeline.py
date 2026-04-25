"""Description: 1ファイル×1パターンの変換処理を実行し、評価レコードを作成します。"""

from __future__ import annotations

from pathlib import Path

from conversion_eval.converters import create_converter
from conversion_eval.detection import detect_encoding, detect_pdf_type
from conversion_eval.metrics import compute_all_metrics
from conversion_eval.metrics.failure import classify_failure
from conversion_eval.models import Pattern, RunRecord
from conversion_eval.noise.normalizer import normalize
from conversion_eval.preprocessors import create_preprocessor


def run_one(
    pattern: Pattern,
    input_path: Path,
    root_input_dir: Path,
    intermediate_root: Path,
    output_root: Path,
    noise_config: dict,
) -> RunRecord:
    relative_input = _safe_relative(input_path, root_input_dir)
    record = RunRecord(
        pattern_id=pattern.id,
        pattern_name=pattern.name,
        input_file=relative_input.as_posix(),
        input_size_bytes=input_path.stat().st_size,
        input_extension=input_path.suffix.lower(),
        uses_llm=pattern.uses_llm,
        llm_provider=pattern.llm_provider,
        uses_internal_models=pattern.uses_internal_models,
        allow_network_download=pattern.allow_network_download,
        input_pdf_type=detect_pdf_type(input_path),
        input_encoding_detected=detect_encoding(input_path),
    )

    preprocessor = create_preprocessor(pattern.preprocessor)
    converter = create_converter(pattern.converter, pattern=pattern)

    intermediate_dir = intermediate_root / pattern.preprocessor / relative_input.parent
    output_dir = output_root / pattern.id / relative_input.parent
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    preprocess = preprocessor.run(input_path, intermediate_dir)
    record.preprocess_time_sec = preprocess.elapsed_sec
    record.preprocess_success = preprocess.success
    record.preprocess_error = preprocess.error
    record.preprocess_timeout = preprocess.timeout
    if preprocess.path and preprocess.path.exists():
        record.intermediate_size_bytes = preprocess.path.stat().st_size
    if not preprocess.success or preprocess.path is None:
        record.total_time_sec = record.preprocess_time_sec
        record.output_failure_reason = "timeout" if preprocess.timeout else "preprocess_error"
        return record

    converted = converter.convert(preprocess.path, output_dir)
    record.convert_time_sec = converted.elapsed_sec
    record.convert_success = converted.success
    record.convert_error = converted.error
    record.convert_timeout = converted.timeout
    record.tool_version = _join_versions(preprocess.tool_version, converted.tool_version)
    record.total_time_sec = record.preprocess_time_sec + record.convert_time_sec

    text = converted.text if converted.success else ""
    text = normalize(text, noise_config)
    record.metrics = compute_all_metrics(text)
    record.output_char_count = len(text)
    record.output_size_bytes = len(text.encode("utf-8"))
    record.output_failure_reason = classify_failure(converted.success, converted.timeout, text, record.metrics)

    if converted.success:
        output_path = output_dir / f"{input_path.stem}.md"
        output_path.write_text(text, encoding="utf-8", newline="\n")

    return record


def _safe_relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(path.name)


def _join_versions(*versions: str) -> str:
    return ";".join(version for version in versions if version)
