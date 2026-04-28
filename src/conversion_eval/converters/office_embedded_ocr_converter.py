"""Description: Officeファイル本文をMarkdown化し、埋め込み画像のOCR結果を追記します。"""

from __future__ import annotations

import importlib.metadata
import logging
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

from conversion_eval.converters.base import Converter
from conversion_eval.converters.markitdown_converter import MarkItDownConverter
from conversion_eval.models import ConversionOutput


MEDIA_ROOTS = {
    ".docx": "word/media/",
    ".pptx": "ppt/media/",
    ".xlsx": "xl/media/",
}

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class EmbeddedImageOcrResult:
    path: str
    text: str
    skipped_reason: str = ""


class OfficeEmbeddedOcrConverter(Converter):
    def convert(self, input_path: Path, output_dir: Path) -> ConversionOutput:
        start = time.perf_counter()
        base = MarkItDownConverter().convert(input_path, output_dir)
        if not base.success:
            return base

        try:
            ocr_results = _ocr_embedded_images(input_path)
            text = _append_ocr_section(base.text, ocr_results)
            return ConversionOutput(
                success=True,
                text=text,
                elapsed_sec=time.perf_counter() - start,
                tool_version=f"{base.tool_version};rapidocr:{_rapidocr_version()}",
            )
        except ImportError:
            return ConversionOutput(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error="RapidOCR is not installed. Install rapidocr to enable embedded image OCR.",
                tool_version=f"{base.tool_version};rapidocr:missing",
            )
        except Exception as exc:
            return ConversionOutput(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error=f"{type(exc).__name__}: {exc}",
                tool_version=f"{base.tool_version};rapidocr:{_rapidocr_version()}",
            )


def _ocr_embedded_images(input_path: Path) -> list[EmbeddedImageOcrResult]:
    media_root = MEDIA_ROOTS.get(input_path.suffix.lower())
    if media_root is None:
        return []

    _suppress_rapidocr_info_logs()
    from rapidocr import RapidOCR  # type: ignore

    ocr = RapidOCR()
    results: list[EmbeddedImageOcrResult] = []
    with zipfile.ZipFile(input_path) as archive:
        media_paths = [
            name
            for name in archive.namelist()
            if name.startswith(media_root) and not name.endswith("/")
        ]
        for name in sorted(media_paths):
            extension = Path(name).suffix.lower()
            if extension not in SUPPORTED_IMAGE_EXTENSIONS:
                results.append(
                    EmbeddedImageOcrResult(
                        path=name,
                        text="",
                        skipped_reason=f"非対応画像形式のためOCR対象外です: {extension or '拡張子なし'}",
                    )
                )
                continue
            output = ocr(archive.read(name))
            texts = getattr(output, "txts", None) or ()
            text = "\n".join(str(item).strip() for item in texts if str(item).strip())
            results.append(EmbeddedImageOcrResult(path=name, text=text))
    return results


def _append_ocr_section(base_text: str, results: list[EmbeddedImageOcrResult]) -> str:
    section = ["## 埋め込み画像OCR"]
    if not results:
        section.append("埋め込み画像は見つかりませんでした。")
    for result in results:
        section.append(f"### {result.path}")
        if result.skipped_reason:
            section.append(result.skipped_reason)
        elif result.text:
            section.append(result.text)
        else:
            section.append("OCRで読み取れるテキストはありませんでした。")
    return "\n\n".join(part for part in [base_text.strip(), "\n\n".join(section)] if part)


def _suppress_rapidocr_info_logs() -> None:
    logger = logging.getLogger("RapidOCR")
    logger.setLevel(logging.ERROR)
    for handler in logger.handlers:
        handler.setLevel(logging.ERROR)
    try:
        from rapidocr.utils.log import logger as rapidocr_logger  # type: ignore
    except ImportError:
        return
    rapidocr_logger.setLevel(logging.ERROR)
    for handler in rapidocr_logger.handlers:
        handler.setLevel(logging.ERROR)


def _rapidocr_version() -> str:
    try:
        return importlib.metadata.version("rapidocr")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"
