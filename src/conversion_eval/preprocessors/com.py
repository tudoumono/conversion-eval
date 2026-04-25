"""Description: Office COMを使って旧形式やPDFを新しいOffice形式へ変換します。"""

from __future__ import annotations

import importlib.metadata
import time
from pathlib import Path

from conversion_eval.models import StepResult
from conversion_eval.preprocessors.base import Preprocessor


class ComPreprocessor(Preprocessor):
    def run(self, input_path: Path, intermediate_dir: Path) -> StepResult:
        start = time.perf_counter()
        try:
            intermediate_dir.mkdir(parents=True, exist_ok=True)
            if input_path.suffix.lower() in {".doc", ".docx", ".rtf", ".pdf"}:
                output_path = intermediate_dir / f"{input_path.stem}.docx"
                self._word_to_docx(input_path, output_path)
            elif input_path.suffix.lower() in {".xls", ".xlsx"}:
                output_path = intermediate_dir / f"{input_path.stem}.xlsx"
                self._excel_to_xlsx(input_path, output_path)
            else:
                return StepResult(
                    success=False,
                    elapsed_sec=time.perf_counter() - start,
                    error=f"COM format conversion does not support extension: {input_path.suffix}",
                    tool_version=self._tool_version(),
                )
            return StepResult(
                success=True,
                path=output_path,
                elapsed_sec=time.perf_counter() - start,
                tool_version=self._tool_version(),
            )
        except ImportError:
            return StepResult(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error="pywin32 is not installed. Install pywin32 to enable Office COM format conversion.",
                tool_version="pywin32:missing",
            )
        except Exception as exc:
            return StepResult(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error=f"{type(exc).__name__}: {exc}",
                tool_version=self._tool_version(),
            )

    def _word_to_docx(self, input_path: Path, output_path: Path) -> None:
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
            doc.SaveAs2(str(output_path), FileFormat=16)
        finally:
            if doc is not None:
                doc.Close(False)
            if word is not None:
                word.Quit()
            pythoncom.CoUninitialize()

    def _excel_to_xlsx(self, input_path: Path, output_path: Path) -> None:
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
            workbook.SaveAs(str(output_path), FileFormat=51)
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
