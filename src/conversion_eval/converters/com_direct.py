"""Description: Office COMで文書を直接読み取り、簡易Markdownを組み立てます。"""

from __future__ import annotations

import importlib.metadata
import time
from pathlib import Path

from conversion_eval.converters.base import Converter
from conversion_eval.models import ConversionOutput


class ComDirectConverter(Converter):
    def convert(self, input_path: Path, output_dir: Path) -> ConversionOutput:
        start = time.perf_counter()
        try:
            if input_path.suffix.lower() in {".doc", ".docx", ".rtf", ".pdf"}:
                text = self._convert_word(input_path)
            elif input_path.suffix.lower() in {".xls", ".xlsx"}:
                text = self._convert_excel(input_path)
            else:
                return ConversionOutput(
                    success=False,
                    elapsed_sec=time.perf_counter() - start,
                    error=f"COM direct does not support extension: {input_path.suffix}",
                    tool_version=self._tool_version(),
                )
            return ConversionOutput(
                success=True,
                text=text,
                elapsed_sec=time.perf_counter() - start,
                tool_version=self._tool_version(),
            )
        except ImportError:
            return ConversionOutput(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error="pywin32 is not installed. Install pywin32 to enable COM direct conversion.",
                tool_version="pywin32:missing",
            )
        except Exception as exc:
            return ConversionOutput(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error=f"{type(exc).__name__}: {exc}",
                tool_version=self._tool_version(),
            )

    def _convert_word(self, input_path: Path) -> str:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore

        pythoncom.CoInitialize()
        word = None
        doc = None
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            try:
                word.AutomationSecurity = 3
            except Exception:
                pass
            doc = word.Documents.Open(
                str(input_path),
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False,
                NoEncodingDialog=True,
            )
            parts: list[str] = []
            paragraph_count = doc.Paragraphs.Count
            for idx in range(1, paragraph_count + 1):
                paragraph = doc.Paragraphs(idx)
                text = str(paragraph.Range.Text).replace("\r", "").replace("\x07", "").strip()
                if not text:
                    continue
                style_name = str(paragraph.Style.NameLocal)
                level = _heading_level(style_name)
                if level:
                    parts.append(f"{'#' * level} {text}")
                else:
                    parts.append(text)

            for table_idx in range(1, doc.Tables.Count + 1):
                table = doc.Tables(table_idx)
                parts.append(_word_table_to_markdown(table))
            return "\n\n".join(part for part in parts if part.strip())
        finally:
            if doc is not None:
                doc.Close(False)
            if word is not None:
                word.Quit()
            pythoncom.CoUninitialize()

    def _convert_excel(self, input_path: Path) -> str:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore

        pythoncom.CoInitialize()
        excel = None
        workbook = None
        try:
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            try:
                excel.AutomationSecurity = 3
            except Exception:
                pass
            workbook = excel.Workbooks.Open(str(input_path), UpdateLinks=0, ReadOnly=True)
            sheets: list[str] = []
            for sheet in workbook.Worksheets:
                rows = _excel_sheet_rows(sheet)
                if not rows:
                    continue
                sheets.append(f"## {sheet.Name}\n\n{_rows_to_markdown(rows)}")
            return "\n\n".join(sheets)
        finally:
            if workbook is not None:
                workbook.Close(False)
            if excel is not None:
                excel.Quit()
            pythoncom.CoUninitialize()

    def _tool_version(self) -> str:
        try:
            return f"pywin32:{importlib.metadata.version('pywin32')}"
        except importlib.metadata.PackageNotFoundError:
            return "pywin32:unknown"


def _heading_level(style_name: str) -> int:
    lowered = style_name.lower()
    for level in range(1, 7):
        if f"heading {level}" in lowered or f"見出し {level}" in style_name:
            return level
    return 0


def _word_table_to_markdown(table) -> str:
    rows: list[list[str]] = []
    for row_idx in range(1, table.Rows.Count + 1):
        row: list[str] = []
        for col_idx in range(1, table.Columns.Count + 1):
            try:
                value = str(table.Cell(row_idx, col_idx).Range.Text)
            except Exception:
                value = ""
            row.append(_clean_cell(value))
        rows.append(row)
    return _rows_to_markdown(rows)


def _excel_sheet_rows(sheet) -> list[list[str]]:
    used = sheet.UsedRange
    row_count = min(int(used.Rows.Count), 200)
    col_count = min(int(used.Columns.Count), 50)
    rows: list[list[str]] = []
    for row_idx in range(1, row_count + 1):
        row: list[str] = []
        for col_idx in range(1, col_count + 1):
            value = used.Cells(row_idx, col_idx).Text
            row.append(str(value).strip())
        if any(cell for cell in row):
            rows.append(row)
    return rows


def _rows_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    header = normalized[0]
    lines = [
        "| " + " | ".join(_escape_cell(cell) for cell in header) + " |",
        "| " + " | ".join("---" for _ in range(width)) + " |",
    ]
    for row in normalized[1:]:
        lines.append("| " + " | ".join(_escape_cell(cell) for cell in row) + " |")
    return "\n".join(lines)


def _clean_cell(value: str) -> str:
    return value.replace("\r", "").replace("\x07", "").replace("\n", " ").strip()


def _escape_cell(value: str) -> str:
    return _clean_cell(value).replace("|", "\\|")
