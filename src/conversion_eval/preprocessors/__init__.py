"""Description: preprocessor名から実際の前処理部品を生成します。"""

from conversion_eval.preprocessors.base import Preprocessor
from conversion_eval.preprocessors.none_preprocessor import NonePreprocessor


def create_preprocessor(name: str) -> Preprocessor:
    if name == "none":
        return NonePreprocessor()
    if name == "libreoffice":
        from conversion_eval.preprocessors.unimplemented import UnimplementedPreprocessor

        return UnimplementedPreprocessor("libreoffice")
    if name == "com":
        from conversion_eval.preprocessors.com import ComPreprocessor

        return ComPreprocessor()
    raise ValueError(f"Unknown preprocessor: {name}")
