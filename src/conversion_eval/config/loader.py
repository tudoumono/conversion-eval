"""Description: patterns.yaml と noise_rules.yaml をPythonオブジェクトへ変換します。"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from conversion_eval.models import Pattern


ALLOWED_LLM_PROVIDERS = {"none", "ollama", "openai"}


def load_patterns(path: Path) -> list[Pattern]:
    data = _load_yaml_like(path)
    patterns = data.get("patterns", [])
    return [_pattern_from_item(item) for item in patterns]


def load_noise_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"enabled": False, "rules": []}
    return _load_yaml_like(path)


def _load_yaml_like(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        return _load_minimal_yaml(path)

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


def _load_minimal_yaml(path: Path) -> dict[str, Any]:
    """PyYAMLがない場合に、このプロジェクト用の単純なYAMLだけを読む補助パーサーです。"""
    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if path.name == "patterns.yaml":
        return {"patterns": _parse_patterns(lines)}

    data: dict[str, Any] = {"rules": []}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("enabled:"):
            data["enabled"] = _parse_scalar(stripped.split(":", 1)[1].strip())
    return data


def _pattern_from_item(item: dict[str, Any]) -> Pattern:
    uses_llm = _parse_bool(item.get("uses_llm", False))
    llm_provider = _normalize_llm_provider(item.get("llm_provider", "none"))
    _validate_llm_policy(str(item["id"]), uses_llm, llm_provider)

    return Pattern(
        id=str(item["id"]),
        name=str(item["name"]),
        preprocessor=str(item["preprocessor"]),
        converter=str(item["converter"]),
        applicable_extensions=tuple(str(ext).lower() for ext in item["applicable_extensions"]),
        uses_llm=uses_llm,
        llm_provider=llm_provider,
        uses_ocr=_parse_bool(item.get("uses_ocr", False)),
        force_full_page_ocr=_parse_bool(item.get("force_full_page_ocr", False)),
        uses_internal_models=_parse_bool(item.get("uses_internal_models", False)),
        allow_network_download=_parse_bool(item.get("allow_network_download", False)),
    )


def _normalize_llm_provider(value: Any) -> str:
    provider = str(value or "none").strip().lower()
    if provider not in ALLOWED_LLM_PROVIDERS:
        allowed = ", ".join(sorted(ALLOWED_LLM_PROVIDERS))
        raise ValueError(f"llm_provider は {allowed} のいずれかを指定してください: {provider}")
    return provider


def _validate_llm_policy(pattern_id: str, uses_llm: bool, llm_provider: str) -> None:
    if uses_llm and llm_provider == "none":
        raise ValueError(
            f"{pattern_id}: uses_llm=true の場合は llm_provider に ollama または openai を指定してください。"
        )
    if not uses_llm and llm_provider != "none":
        raise ValueError(
            f"{pattern_id}: llm_provider={llm_provider} を指定する場合は uses_llm=true にしてください。"
        )


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0", ""}:
            return False
    return bool(value)


def _parse_patterns(lines: list[str]) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- id:"):
            if current:
                patterns.append(current)
            current = {"id": _parse_scalar(stripped.split(":", 1)[1].strip())}
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = _parse_scalar(value.strip())
    if current:
        patterns.append(current)
    return patterns


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("'\"") for part in inner.split(",")]
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value.strip("'\"")
