"""Description: 前処理を行わず、入力ファイルをそのまま次工程へ渡します。"""

from __future__ import annotations

import time
from pathlib import Path

from conversion_eval.models import StepResult
from conversion_eval.preprocessors.base import Preprocessor


class NonePreprocessor(Preprocessor):
    def run(self, input_path: Path, intermediate_dir: Path) -> StepResult:
        start = time.perf_counter()
        return StepResult(success=True, path=input_path, elapsed_sec=time.perf_counter() - start)
