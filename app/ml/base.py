from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

MODEL_FILE = "model.joblib"
MODEL_META_FILE = "model_meta.json"


class MLDataError(ValueError):
    """Raised when student-provided data cannot be trained or predicted on.

    The message is shown directly to students, so keep it friendly Chinese.
    """


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def write_model_meta(models_dir: Path, meta: dict[str, Any]) -> None:
    models_dir.mkdir(parents=True, exist_ok=True)
    (models_dir / MODEL_META_FILE).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_model_meta(models_dir: Path) -> dict[str, Any]:
    meta_path = models_dir / MODEL_META_FILE
    if not meta_path.is_file():
        raise MLDataError("还没有训练模型，请先完成“训练模型”这一步。")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def class_counts(labels: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return counts
