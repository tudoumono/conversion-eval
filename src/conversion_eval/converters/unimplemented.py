"""Description: 未実装converterをレポート上の失敗として扱うための部品です。"""

from __future__ import annotations

import time
from pathlib import Path

from conversion_eval.models import ConversionOutput
from conversion_eval.converters.base import Converter


class UnimplementedConverter(Converter):
    def __init__(self, name: str) -> None:
        self.name = name

    def convert(self, input_path: Path, output_dir: Path) -> ConversionOutput:
        start = time.perf_counter()
        return ConversionOutput(
            success=False,
            elapsed_sec=time.perf_counter() - start,
            error=f"Converter '{self.name}' is not implemented yet.",
            tool_version=f"{self.name}:not_implemented",
        )
