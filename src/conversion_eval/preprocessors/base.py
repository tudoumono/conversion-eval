"""Description: 形式変換部品が満たす共通インターフェースを定義します。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from conversion_eval.models import StepResult


class Preprocessor(ABC):
    @abstractmethod
    def run(self, input_path: Path, intermediate_dir: Path) -> StepResult:
        """必要に応じて入力ファイルを中間ファイルへ変換します。"""
