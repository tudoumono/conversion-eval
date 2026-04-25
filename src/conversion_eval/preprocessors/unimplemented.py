"""Description: 未実装preprocessorをレポート上の失敗として扱うための部品です。"""

from __future__ import annotations

import time
from pathlib import Path

from conversion_eval.models import StepResult
from conversion_eval.preprocessors.base import Preprocessor


class UnimplementedPreprocessor(Preprocessor):
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, input_path: Path, intermediate_dir: Path) -> StepResult:
        start = time.perf_counter()
        return StepResult(
            success=False,
            path=None,
            elapsed_sec=time.perf_counter() - start,
            error=f"Preprocessor '{self.name}' is not implemented yet.",
        )
