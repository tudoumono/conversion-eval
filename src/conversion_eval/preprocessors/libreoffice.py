"""Description: LibreOfficeを使って旧Office形式を新しいOffice形式へ変換します。"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from conversion_eval.models import StepResult
from conversion_eval.preprocessors.base import Preprocessor


CONVERT_TARGETS = {
    ".doc": ("docx", ".docx"),
    ".rtf": ("docx", ".docx"),
    ".xls": ("xlsx", ".xlsx"),
}

PASSTHROUGH_EXTENSIONS = {
    ".docx",
    ".xlsx",
    ".pptx",
}

SOFFICE_ENV_KEYS = (
    "CONVERSION_EVAL_LIBREOFFICE_PATH",
    "SOFFICE_PATH",
    "LIBREOFFICE_PATH",
)

WINDOWS_CANDIDATES = (
    Path("C:/Program Files/LibreOffice/program/soffice.com"),
    Path("C:/Program Files/LibreOffice/program/soffice.exe"),
    Path("C:/Program Files (x86)/LibreOffice/program/soffice.com"),
    Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"),
)


class LibreOfficePreprocessor(Preprocessor):
    def run(self, input_path: Path, intermediate_dir: Path) -> StepResult:
        start = time.perf_counter()
        soffice = _find_soffice()
        if soffice is None:
            return StepResult(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error=(
                    "LibreOffice executable was not found. Add soffice to PATH "
                    "or set CONVERSION_EVAL_LIBREOFFICE_PATH in .env."
                ),
                tool_version="libreoffice:missing",
            )

        suffix = input_path.suffix.lower()
        try:
            intermediate_dir.mkdir(parents=True, exist_ok=True)
            if suffix in PASSTHROUGH_EXTENSIONS:
                output_path = intermediate_dir / input_path.name
                shutil.copy2(input_path, output_path)
                return StepResult(
                    success=True,
                    path=output_path,
                    elapsed_sec=time.perf_counter() - start,
                    tool_version=_tool_version(soffice),
                )

            target = CONVERT_TARGETS.get(suffix)
            if target is None:
                return StepResult(
                    success=False,
                    elapsed_sec=time.perf_counter() - start,
                    error=f"LibreOffice format conversion does not support extension: {input_path.suffix}",
                    tool_version=_tool_version(soffice),
                )

            convert_to, output_suffix = target
            output_dir = intermediate_dir / f"{input_path.stem}_{suffix.lstrip('.')}_libreoffice"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{input_path.stem}{output_suffix}"
            _remove_stale_output(output_path)
            completed = _run_soffice(soffice, input_path, output_dir, convert_to)
            if not output_path.exists():
                return StepResult(
                    success=False,
                    elapsed_sec=time.perf_counter() - start,
                    error=_format_failure("LibreOffice did not create the expected output file.", completed),
                    tool_version=_tool_version(soffice),
                )

            return StepResult(
                success=True,
                path=output_path,
                elapsed_sec=time.perf_counter() - start,
                tool_version=_tool_version(soffice),
            )
        except subprocess.TimeoutExpired:
            return StepResult(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error="LibreOffice format conversion timed out.",
                timeout=True,
                tool_version=_tool_version(soffice),
            )
        except Exception as exc:
            return StepResult(
                success=False,
                elapsed_sec=time.perf_counter() - start,
                error=f"{type(exc).__name__}: {exc}",
                tool_version=_tool_version(soffice),
            )


def _find_soffice() -> Path | None:
    for key in SOFFICE_ENV_KEYS:
        value = os.environ.get(key)
        if not value:
            continue
        candidate = _resolve_soffice_path(Path(value))
        if candidate is not None:
            return candidate

    for command in ("soffice", "libreoffice"):
        found = shutil.which(command)
        if found:
            return Path(found)

    for candidate in WINDOWS_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _resolve_soffice_path(path: Path) -> Path | None:
    if path.is_file():
        return path
    candidate = path / "soffice.com"
    if candidate.is_file():
        return candidate
    candidate = path / "soffice.exe"
    if candidate.is_file():
        return candidate
    candidate = path / "program" / "soffice.com"
    if candidate.is_file():
        return candidate
    candidate = path / "program" / "soffice.exe"
    if candidate.is_file():
        return candidate
    return None


def _run_soffice(
    soffice: Path,
    input_path: Path,
    output_dir: Path,
    convert_to: str,
) -> subprocess.CompletedProcess[str]:
    profile_dir = output_dir / "_lo_profile"
    temp_dir = output_dir / "_lo_temp"
    profile_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    user_installation = profile_dir.resolve().as_uri()
    env = os.environ.copy()
    env["TMP"] = str(temp_dir.resolve())
    env["TEMP"] = str(temp_dir.resolve())
    # LibreOfficeは変換結果をstdoutに出すことがあるため、失敗時の診断用に捕捉します。
    try:
        return subprocess.run(
            [
                str(soffice),
                f"-env:UserInstallation={user_installation}",
                "--headless",
                "--invisible",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--norestore",
                "--nolockcheck",
                "--convert-to",
                convert_to,
                "--outdir",
                str(output_dir),
                str(input_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)
        shutil.rmtree(temp_dir, ignore_errors=True)


def _remove_stale_output(output_path: Path) -> None:
    if output_path.exists():
        output_path.unlink()


def _format_failure(message: str, completed: subprocess.CompletedProcess[str]) -> str:
    details = " ".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    if details:
        return f"{message} returncode={completed.returncode}; {details}"
    return f"{message} returncode={completed.returncode}"


def _tool_version(soffice: Path) -> str:
    try:
        completed = subprocess.run(
            [str(soffice), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        return "libreoffice:unknown"
    version = (completed.stdout or completed.stderr).strip()
    return f"libreoffice:{version or 'unknown'}"
