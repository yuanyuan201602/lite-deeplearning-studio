from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.ml.base import MODEL_FILE, MLDataError, now_text, write_model_meta

MIN_PAIRS = 3
LOW_CONFIDENCE_THRESHOLD = 0.15
FALLBACK_ANSWER = "这个问题我还没有学过，请换一个问题试试。"


def _strip_spaces(text: str) -> str:
    return "".join(text.split())


def train(pairs: list[dict[str, str]], models_dir: Path) -> dict[str, Any]:
    cleaned = [
        {"question": pair["question"].strip(), "answer": pair["answer"].strip()}
        for pair in pairs
        if pair["question"].strip() and pair["answer"].strip()
    ]
    if len(cleaned) < MIN_PAIRS:
        raise MLDataError(f"问答对太少，至少需要 {MIN_PAIRS} 组“问题|答案”。")

    # Plain "char" on whitespace-stripped text: "char_wb" pads words with spaces,
    # and that shared space n-gram makes totally unrelated questions look similar.
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3))
    matrix = vectorizer.fit_transform([_strip_spaces(pair["question"]) for pair in cleaned])

    models_dir.mkdir(parents=True, exist_ok=True)
    # Key name "rows" matches the exported ai_runtime/core.py, so the bundled model
    # keeps working when students run predict.py from the exported package.
    joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "rows": cleaned}, models_dir / MODEL_FILE)
    meta = {
        "capability": "qa_retrieval",
        "labels": [],
        "sample_count": len(cleaned),
        "class_counts": {},
        "train_accuracy": None,
        "cross_val_accuracy": None,
        "trained_at": now_text(),
    }
    write_model_meta(models_dir, meta)
    return meta


def predict(models_dir: Path, question: str) -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise MLDataError("请输入要测试的问题。")
    model_path = models_dir / MODEL_FILE
    if not model_path.is_file():
        raise MLDataError("还没有训练模型，请先完成“训练模型”这一步。")
    store = joblib.load(model_path)

    query = store["vectorizer"].transform([_strip_spaces(question)])
    scores = cosine_similarity(query, store["matrix"])[0]
    ranked = np.argsort(scores)[::-1][:3]
    matches = [
        {
            "question": store["rows"][int(index)]["question"],
            "answer": store["rows"][int(index)]["answer"],
            "score": round(float(scores[int(index)]), 4),
        }
        for index in ranked
    ]
    best = matches[0]
    confident = best["score"] >= LOW_CONFIDENCE_THRESHOLD
    return {
        "input": question,
        "label": best["answer"] if confident else FALLBACK_ANSWER,
        "matched_question": best["question"] if confident else "",
        "confident": confident,
        "matches": matches,
    }
