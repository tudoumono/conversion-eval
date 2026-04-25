"""Description: パターン定義、処理結果、レポート行のデータ構造を定義します。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Pattern:
    id: str
    name: str
    preprocessor: str
    converter: str
    applicable_extensions: tuple[str, ...]
    uses_llm: bool = False
    llm_provider: str = "none"
    uses_ocr: bool = False
    force_full_page_ocr: bool = False
    uses_internal_models: bool = False
    allow_network_download: bool = False

    def applies_to(self, path: Path) -> bool:
        return path.suffix.lower() in self.applicable_extensions


@dataclass
class StepResult:
    success: bool
    path: Path | None = None
    elapsed_sec: float = 0.0
    error: str = ""
    timeout: bool = False
    tool_version: str = ""


@dataclass
class ConversionOutput:
    success: bool
    text: str = ""
    elapsed_sec: float = 0.0
    error: str = ""
    timeout: bool = False
    tool_version: str = ""


@dataclass
class RunRecord:
    pattern_id: str
    pattern_name: str
    input_file: str
    input_size_bytes: int
    input_extension: str
    uses_llm: bool = False
    llm_provider: str = "none"
    uses_ocr: bool = False
    force_full_page_ocr: bool = False
    uses_internal_models: bool = False
    allow_network_download: bool = False
    input_pdf_type: str = ""
    input_encoding_detected: str = "unknown"
    preprocess_time_sec: float = 0.0
    preprocess_success: bool = False
    preprocess_error: str = ""
    preprocess_timeout: bool = False
    intermediate_size_bytes: int = 0
    convert_time_sec: float = 0.0
    convert_success: bool = False
    convert_error: str = ""
    convert_timeout: bool = False
    total_time_sec: float = 0.0
    output_size_bytes: int = 0
    output_char_count: int = 0
    output_failure_reason: str = ""
    tool_version: str = ""
    metrics: dict[str, object] = field(default_factory=dict)

    def to_row(self) -> dict[str, object]:
        base = {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "input_file": self.input_file,
            "input_size_bytes": self.input_size_bytes,
            "input_extension": self.input_extension,
            "uses_llm": self.uses_llm,
            "llm_provider": self.llm_provider,
            "uses_ocr": self.uses_ocr,
            "force_full_page_ocr": self.force_full_page_ocr,
            "uses_internal_models": self.uses_internal_models,
            "allow_network_download": self.allow_network_download,
            "input_pdf_type": self.input_pdf_type,
            "input_encoding_detected": self.input_encoding_detected,
            "preprocess_time_sec": f"{self.preprocess_time_sec:.6f}",
            "preprocess_success": self.preprocess_success,
            "preprocess_error": self.preprocess_error,
            "preprocess_timeout": self.preprocess_timeout,
            "intermediate_size_bytes": self.intermediate_size_bytes,
            "convert_time_sec": f"{self.convert_time_sec:.6f}",
            "convert_success": self.convert_success,
            "convert_error": self.convert_error,
            "convert_timeout": self.convert_timeout,
            "total_time_sec": f"{self.total_time_sec:.6f}",
            "output_size_bytes": self.output_size_bytes,
            "output_char_count": self.output_char_count,
            "output_failure_reason": self.output_failure_reason,
            "tool_version": self.tool_version,
        }
        base.update(self.metrics)
        return base
