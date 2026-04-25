"""Description: 構造指標とノイズ指標をまとめて計算する入口です。"""

from conversion_eval.metrics.failure import classify_failure
from conversion_eval.metrics.noise import compute_noise_metrics
from conversion_eval.metrics.structural import compute_structural_metrics


def compute_all_metrics(text: str) -> dict[str, object]:
    metrics: dict[str, object] = {}
    metrics.update(compute_structural_metrics(text))
    metrics.update(compute_noise_metrics(text))
    return metrics
