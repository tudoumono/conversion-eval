"""Description: 拡張子ごとの階層化サンプリングで評価サンプルを作成します。"""

from __future__ import annotations

import random
import shutil
from collections import defaultdict
from pathlib import Path

from conversion_eval.pipeline.runner import collect_input_files


DEFAULT_TARGETS = {
    ".doc": 5,
    ".docx": 5,
    ".xls": 3,
    ".xlsx": 3,
    ".pptx": 3,
    ".pdf": 5,
    ".rtf": 3,
    ".bik": 1,
    ".bpg": 1,
    ".bca": 1,
    ".bci": 1,
}


def create_stratified_sample(full_dir: Path, sample_dir: Path, seed: int = 42) -> list[Path]:
    rng = random.Random(seed)
    by_ext: dict[str, list[Path]] = defaultdict(list)
    for path in collect_input_files(full_dir):
        by_ext[path.suffix.lower()].append(path)

    selected: list[Path] = []
    for ext, target in DEFAULT_TARGETS.items():
        files = sorted(by_ext.get(ext, []), key=lambda p: p.stat().st_size)
        if not files:
            continue
        picks: list[Path] = [files[0], files[-1]]
        if len(files) >= 3:
            picks.append(files[len(files) // 2])
        remaining = [p for p in files if p not in picks]
        rng.shuffle(remaining)
        picks.extend(remaining[: max(0, target - len(picks))])
        selected.extend(picks[:target])

    for path in selected:
        rel = path.relative_to(full_dir)
        target_path = sample_dir / rel
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target_path)
    return selected
