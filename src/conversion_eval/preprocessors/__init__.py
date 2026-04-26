"""Description: preprocessor名から実際の形式変換部品を生成します。"""

from conversion_eval.preprocessors.base import Preprocessor
from conversion_eval.preprocessors.none_preprocessor import NonePreprocessor


def create_preprocessor(name: str) -> Preprocessor:
    if name == "none":
        return NonePreprocessor()
    if name == "libreoffice":
        from conversion_eval.preprocessors.libreoffice import LibreOfficePreprocessor

        return LibreOfficePreprocessor()
    if name == "libreoffice_pdf":
        from conversion_eval.preprocessors.libreoffice import LibreOfficePdfPreprocessor

        return LibreOfficePdfPreprocessor()
    if name == "com":
        from conversion_eval.preprocessors.com import ComPreprocessor

        return ComPreprocessor()
    if name == "com_pdf":
        from conversion_eval.preprocessors.com_pdf import ComPdfPreprocessor

        return ComPdfPreprocessor()
    raise ValueError(f"Unknown format conversion preprocessor: {name}")
