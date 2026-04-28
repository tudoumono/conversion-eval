"""Description: 入力ファイル一覧を集め、複数パターンの実行を制御します。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from conversion_eval.models import Pattern, RunRecord
from conversion_eval.pipeline.pipeline import run_one


SUPPORTED_EXTENSIONS = {
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".pdf",
    ".pptx",
    ".rtf",
    ".bik",
    ".bpg",
    ".bca",
    ".bci",
}

SERIAL_PREPROCESSORS = {"com", "com_pdf"}
SERIAL_CONVERTERS = {"com_direct"}


@dataclass(frozen=True)
class _RunTask:
    index: int
    pattern: Pattern
    input_path: Path


def collect_input_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def run_patterns(
    patterns: list[Pattern],
    input_dir: Path,
    intermediate_root: Path,
    output_root: Path,
    noise_config: dict,
    workers: int = 1,
    ocr_workers: int = 1,
) -> list[RunRecord]:
    files = collect_input_files(input_dir)
    tasks = _build_tasks(patterns, files)
    if workers <= 1:
        return [
            _run_task(
                task,
                input_dir=input_dir,
                intermediate_root=intermediate_root,
                output_root=output_root,
                noise_config=noise_config,
            )
            for task in tasks
        ]

    records_by_index: dict[int, RunRecord] = {}
    serial_tasks = [task for task in tasks if _requires_serial_execution(task.pattern)]
    parallel_tasks = [task for task in tasks if not _requires_serial_execution(task.pattern)]
    normal_tasks = [task for task in parallel_tasks if not task.pattern.uses_ocr]
    ocr_tasks = [task for task in parallel_tasks if task.pattern.uses_ocr]
    task_locks = _build_task_locks(parallel_tasks)

    # Office COMは同時実行で不安定になりやすいため、workers指定時も直列で処理します。
    for task in serial_tasks:
        records_by_index[task.index] = _run_task(
            task,
            input_dir=input_dir,
            intermediate_root=intermediate_root,
            output_root=output_root,
            noise_config=noise_config,
        )

    records_by_index.update(
        _run_parallel_tasks(
            normal_tasks,
            max_workers=workers,
            input_dir=input_dir,
            intermediate_root=intermediate_root,
            output_root=output_root,
            noise_config=noise_config,
            task_locks=task_locks,
        )
    )
    records_by_index.update(
        _run_parallel_tasks(
            ocr_tasks,
            max_workers=min(workers, max(1, ocr_workers)),
            input_dir=input_dir,
            intermediate_root=intermediate_root,
            output_root=output_root,
            noise_config=noise_config,
            task_locks=task_locks,
        )
    )

    return [records_by_index[task.index] for task in tasks]


def _build_tasks(patterns: list[Pattern], files: list[Path]) -> list[_RunTask]:
    tasks: list[_RunTask] = []
    for pattern in patterns:
        for input_path in files:
            if not pattern.applies_to(input_path):
                continue
            tasks.append(_RunTask(index=len(tasks), pattern=pattern, input_path=input_path))
    return tasks


def _requires_serial_execution(pattern: Pattern) -> bool:
    return pattern.preprocessor in SERIAL_PREPROCESSORS or pattern.converter in SERIAL_CONVERTERS


def _run_parallel_tasks(
    tasks: list[_RunTask],
    max_workers: int,
    input_dir: Path,
    intermediate_root: Path,
    output_root: Path,
    noise_config: dict,
    task_locks: dict[tuple[str, Path], Lock],
) -> dict[int, RunRecord]:
    if not tasks:
        return {}
    records: dict[int, RunRecord] = {}
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        futures = {
            executor.submit(
                _run_task,
                task,
                input_dir,
                intermediate_root,
                output_root,
                noise_config,
                task_locks.get(_lock_key(task)),
            ): task.index
            for task in tasks
        }
        for future in as_completed(futures):
            records[futures[future]] = future.result()
    return records


def _run_task(
    task: _RunTask,
    input_dir: Path,
    intermediate_root: Path,
    output_root: Path,
    noise_config: dict,
    task_lock: Lock | None = None,
) -> RunRecord:
    if task_lock is not None:
        with task_lock:
            return _run_one_task(task, input_dir, intermediate_root, output_root, noise_config)
    return _run_one_task(task, input_dir, intermediate_root, output_root, noise_config)


def _run_one_task(
    task: _RunTask,
    input_dir: Path,
    intermediate_root: Path,
    output_root: Path,
    noise_config: dict,
) -> RunRecord:
    return run_one(
        pattern=task.pattern,
        input_path=task.input_path,
        root_input_dir=input_dir,
        intermediate_root=intermediate_root,
        output_root=output_root,
        noise_config=noise_config,
    )


def _build_task_locks(tasks: list[_RunTask]) -> dict[tuple[str, Path], Lock]:
    locks: dict[tuple[str, Path], Lock] = {}
    for task in tasks:
        key = _lock_key(task)
        if key is not None:
            locks.setdefault(key, Lock())
    return locks


def _lock_key(task: _RunTask) -> tuple[str, Path] | None:
    if task.pattern.preprocessor == "none":
        return None
    return (task.pattern.preprocessor, task.input_path)
