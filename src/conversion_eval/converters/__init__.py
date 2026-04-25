"""Description: converter名から実際のMarkdown変換部品を生成します。"""

from conversion_eval.converters.base import Converter
from conversion_eval.models import Pattern


def create_converter(name: str, pattern: Pattern | None = None) -> Converter:
    if name == "markitdown":
        from conversion_eval.converters.markitdown_converter import MarkItDownConverter

        return MarkItDownConverter()
    if name == "docling":
        from conversion_eval.converters.docling_converter import DoclingConverter

        return DoclingConverter(
            allow_network_download=pattern.allow_network_download if pattern else False
        )
    if name == "com_direct":
        from conversion_eval.converters.com_direct import ComDirectConverter

        return ComDirectConverter()
    if name in {}:
        from conversion_eval.converters.unimplemented import UnimplementedConverter

        return UnimplementedConverter(name)
    raise ValueError(f"Unknown converter: {name}")
