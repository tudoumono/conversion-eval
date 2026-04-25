"""Description: Doclingを使って入力ファイルをMarkdownへ変換します。"""

from __future__ import annotations

import importlib.metadata
import logging
import os
import shutil
import time
import uuid
from pathlib import Path

from conversion_eval.converters.base import Converter
from conversion_eval.models import ConversionOutput


RAPIDOCR_REQUIRED_MODEL_FILES = (
    "ch_PP-OCRv4_det_mobile.onnx",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "ch_PP-OCRv4_rec_mobile.onnx",
)

DOCLING_REQUIRED_HF_CACHE_DIRS = (
    "models--docling-project--docling-layout-heron",
    "models--docling-project--docling-models",
)


class DoclingConverter(Converter):
    def __init__(
        self,
        allow_network_download: bool = False,
        uses_ocr: bool = True,
        force_full_page_ocr: bool = False,
    ) -> None:
        self.allow_network_download = allow_network_download
        self.uses_ocr = uses_ocr
        self.force_full_page_ocr = force_full_page_ocr

    def convert(self, input_path: Path, output_dir: Path) -> ConversionOutput:
        start = time.perf_counter()
        temp_input: Path | None = None
        try:
            self._configure_network_policy()
            self._check_required_models(input_path)

            conversion_input = self._ascii_input_path(input_path)
            if conversion_input != input_path:
                temp_input = conversion_input
            result = self._document_converter(input_path).convert(conversion_input)
            text = result.document.export_to_markdown()
            return ConversionOutput(
                success=True,
                text=text,
                elapsed_sec=time.perf_counter() - start,
                tool_version=f"docling:{self._version()}",
            )
        except ImportError:
            return ConversionOutput(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error="Docling is not installed. Install the docling wheel to enable this converter.",
                tool_version="docling:missing",
            )
        except Exception as exc:
            return ConversionOutput(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error=f"{type(exc).__name__}: {exc}",
                tool_version=f"docling:{self._version()}",
            )
        finally:
            if temp_input is not None:
                try:
                    temp_input.unlink()
                except OSError:
                    pass

    def _ascii_input_path(self, input_path: Path) -> Path:
        if _is_ascii_path(input_path):
            return input_path
        temp_root = Path(os.environ.get("CONVERSION_EVAL_ASCII_TMP", ".tmp/docling"))
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_path = temp_root / f"docling_{uuid.uuid4().hex}{input_path.suffix.lower()}"
        shutil.copy2(input_path, temp_path)
        return temp_path

    def _configure_network_policy(self) -> None:
        _suppress_rapidocr_info_logs()
        if self.allow_network_download:
            return
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

    def _check_required_models(self, input_path: Path) -> None:
        if self.allow_network_download or input_path.suffix.lower() != ".pdf":
            return
        missing = _missing_docling_pdf_assets()
        if missing:
            joined = "; ".join(missing)
            raise RuntimeError(
                "Docling PDF変換に必要なローカルモデルが見つかりません。"
                "allow_network_download=true にするか、事前にモデルを配置してください。"
                f" missing={joined}"
            )

    def _document_converter(self, input_path: Path):
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend  # type: ignore
        from docling.datamodel.base_models import InputFormat  # type: ignore
        from docling.datamodel.pipeline_options import PdfPipelineOptions  # type: ignore
        from docling.document_converter import DocumentConverter, PdfFormatOption  # type: ignore

        if input_path.suffix.lower() == ".pdf":
            pipeline_options = PdfPipelineOptions()
            pipeline_options.enable_remote_services = False
            pipeline_options.do_picture_description = False
            pipeline_options.do_picture_classification = False
            pipeline_options.do_code_enrichment = False
            pipeline_options.do_formula_enrichment = False
            pipeline_options.do_ocr = self.uses_ocr
            pipeline_options.ocr_options.force_full_page_ocr = self.force_full_page_ocr
            pipeline_options.do_table_structure = True
            return DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        backend=PyPdfiumDocumentBackend,
                        pipeline_options=pipeline_options,
                    )
                }
            )
        return DocumentConverter()

    def _version(self) -> str:
        try:
            return importlib.metadata.version("docling")
        except importlib.metadata.PackageNotFoundError:
            return "unknown"


def _is_ascii_path(path: Path) -> bool:
    try:
        str(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _missing_docling_pdf_assets() -> list[str]:
    missing: list[str] = []
    missing.extend(_missing_rapidocr_assets())
    missing.extend(_missing_huggingface_assets())
    return missing


def _missing_rapidocr_assets() -> list[str]:
    try:
        import rapidocr  # type: ignore
    except ImportError:
        return ["rapidocr package"]

    package_dir = Path(rapidocr.__file__).parent
    model_dir = package_dir / "models"
    missing: list[str] = []
    for filename in RAPIDOCR_REQUIRED_MODEL_FILES:
        path = model_dir / filename
        if not path.exists() or path.stat().st_size == 0:
            missing.append(str(path))
    return missing


def _missing_huggingface_assets() -> list[str]:
    cache_root = Path(os.environ.get("HF_HUB_CACHE", ".tmp/huggingface_nosymlink/hub"))
    missing: list[str] = []
    for dirname in DOCLING_REQUIRED_HF_CACHE_DIRS:
        path = cache_root / dirname
        if not path.exists() or not any(path.rglob("*")):
            missing.append(str(path))
    return missing


def _suppress_rapidocr_info_logs() -> None:
    logger = logging.getLogger("RapidOCR")
    logger.setLevel(logging.WARNING)
    for handler in logger.handlers:
        handler.setLevel(logging.WARNING)
    try:
        from rapidocr.utils.log import logger as rapidocr_logger  # type: ignore
    except ImportError:
        return
    rapidocr_logger.setLevel(logging.WARNING)
    for handler in rapidocr_logger.handlers:
        handler.setLevel(logging.WARNING)
