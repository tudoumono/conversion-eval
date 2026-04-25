"""Description: Markdown変換部品が満たす共通インターフェースを定義します。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from conversion_eval.models import ConversionOutput


class Converter(ABC):
    @abstractmethod
    def convert(self, input_path: Path, output_dir: Path) -> ConversionOutput:
        """入力ファイルをMarkdown文字列へ変換します。"""
