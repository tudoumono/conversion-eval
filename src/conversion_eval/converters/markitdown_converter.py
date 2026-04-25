"""Description: MarkItDownを使って入力ファイルをMarkdownへ変換します。"""

from __future__ import annotations

import importlib.metadata
import time
from pathlib import Path

from conversion_eval.models import ConversionOutput
from conversion_eval.converters.base import Converter


class MarkItDownConverter(Converter):
    def convert(self, input_path: Path, output_dir: Path) -> ConversionOutput:
        start = time.perf_counter()
        try:
            text, version = self._convert_with_markitdown(input_path)
            return ConversionOutput(
                success=True,
                text=text,
                elapsed_sec=time.perf_counter() - start,
                tool_version=f"markitdown:{version}",
            )
        except ImportError:
            if input_path.suffix.lower() in {".txt", ".md"}:
                text = input_path.read_text(encoding="utf-8", errors="replace")
                return ConversionOutput(
                    success=True,
                    text=text,
                    elapsed_sec=time.perf_counter() - start,
                    tool_version="markitdown:missing;text_fallback",
                )
            return ConversionOutput(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error="MarkItDown is not installed. Install the markitdown wheel to enable this converter.",
                tool_version="markitdown:missing",
            )
        except Exception as exc:
            return ConversionOutput(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error=f"{type(exc).__name__}: {exc}",
                tool_version=self._version(),
            )

    def _convert_with_markitdown(self, input_path: Path) -> tuple[str, str]:
        from markitdown import MarkItDown  # type: ignore

        result = MarkItDown().convert(str(input_path))
        text = getattr(result, "text_content", None)
        if text is None:
            text = str(result)
        return text, self._version()

    def _version(self) -> str:
        try:
            return importlib.metadata.version("markitdown")
        except importlib.metadata.PackageNotFoundError:
            return "unknown"
