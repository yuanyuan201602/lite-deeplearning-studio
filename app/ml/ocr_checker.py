from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from app.ml.base import MLDataError, now_text, write_model_meta

CORRECT_TEXT_FILE = "ocr_correct_text.json"


def train(correct_text: str, models_dir: Path) -> dict[str, Any]:
    """The typo checker has no trainable model: it memorizes the correct card text."""
    correct_text = correct_text.strip()
    if len(correct_text) < 2:
        raise MLDataError("请先输入知识卡片上的正确文字。")

    models_dir.mkdir(parents=True, exist_ok=True)
    (models_dir / CORRECT_TEXT_FILE).write_text(
        json.dumps({"correct_text": correct_text}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    meta = {
        "capability": "ocr_typo_checker",
        "labels": [],
        "sample_count": len(correct_text),
        "class_counts": {},
        "train_accuracy": None,
        "cross_val_accuracy": None,
        "trained_at": now_text(),
    }
    write_model_meta(models_dir, meta)
    return meta


def predict(models_dir: Path, observed_text: str) -> dict[str, Any]:
    observed_text = observed_text.strip()
    if not observed_text:
        raise MLDataError("请输入拍照识别出来的文字。")
    correct_path = models_dir / CORRECT_TEXT_FILE
    if not correct_path.is_file():
        raise MLDataError("还没有保存正确文字，请先完成“保存正确文字”这一步。")
    correct_text = json.loads(correct_path.read_text(encoding="utf-8"))["correct_text"]

    typos = compare_text(correct_text, observed_text)
    broadcast = build_broadcast(typos)
    return {
        "input": observed_text,
        "correct_text": correct_text,
        "typos": typos,
        "label": broadcast,
        "typo_count": len(typos),
    }


def compare_text(correct: str, observed: str) -> list[dict[str, Any]]:
    if len(correct) == len(observed):
        return [
            {"position": index + 1, "observed": observed_char, "correct": correct_char}
            for index, (correct_char, observed_char) in enumerate(zip(correct, observed))
            if correct_char != observed_char
        ]

    typos: list[dict[str, Any]] = []
    matcher = difflib.SequenceMatcher(a=observed, b=correct, autojunk=False)
    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        typos.append(
            {
                "position": b_start + 1,
                "observed": observed[a_start:a_end],
                "correct": correct[b_start:b_end],
            }
        )
    return typos


def build_broadcast(typos: list[dict[str, Any]]) -> str:
    if not typos:
        return "卡片文字全部正确"
    parts = [
        f"第{typo['position']}个字“{typo['observed'] or '缺字'}”应更正为“{typo['correct']}”"
        for typo in typos
    ]
    return "，".join(parts)
