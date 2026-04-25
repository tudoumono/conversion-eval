"""Description: .env を読み込み、相対パスの環境変数をプロジェクト基準に整えます。"""

from __future__ import annotations

import os
from pathlib import Path


PATH_ENV_VARS = {
    "CONVERSION_EVAL_ASCII_TMP",
    "HF_HOME",
    "HF_HUB_CACHE",
}


def load_env(root: Path, env_file: Path | None = None) -> None:
    env_path = env_file or root / ".env"
    _load_dotenv(env_path)
    _make_paths_root_relative(root)


def _load_dotenv(env_path: Path) -> None:
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        _load_dotenv_fallback(env_path)
        return
    load_dotenv(dotenv_path=env_path, override=False)


def _load_dotenv_fallback(env_path: Path) -> None:
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def _make_paths_root_relative(root: Path) -> None:
    for key in PATH_ENV_VARS:
        value = os.environ.get(key)
        if not value:
            continue
        path = Path(value)
        if path.is_absolute():
            continue
        os.environ[key] = str(root / path)
