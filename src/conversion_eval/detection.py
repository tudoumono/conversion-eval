"""Description: 入力ファイルのエンコーディングやPDF種別を簡易判定します。"""

from __future__ import annotations

import logging
from pathlib import Path


PDF_WARNING_LOGGERS = ("pdfminer", "pdfplumber", "pypdf", "pypdfium2")


def detect_encoding(path: Path) -> str:
    if path.suffix.lower() not in {".txt", ".md", ".csv", ".rtf"}:
        return "unknown"
    sample = path.read_bytes()[:65536]
    try:
        from charset_normalizer import from_bytes  # type: ignore
    except ImportError:
        return _detect_encoding_fallback(sample)
    best = from_bytes(sample).best()
    if best is None or best.encoding is None:
        return "unknown"
    return best.encoding


def _detect_encoding_fallback(sample: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            sample.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "unknown"


def detect_pdf_type(path: Path) -> str:
    if path.suffix.lower() != ".pdf":
        return ""
    _suppress_pdf_parser_warnings()
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return "unknown"
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = pdf.pages[:2]
            text_chars = sum(len(page.extract_text() or "") for page in pages)
        if text_chars > 200:
            return "text"
        if text_chars == 0:
            return "scan"
        return "mixed"
    except Exception:
        return "unknown"


def _suppress_pdf_parser_warnings() -> None:
    for logger_name in PDF_WARNING_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
