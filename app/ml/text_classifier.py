from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

from app.ml import classifiers
from app.ml.base import MODEL_FILE, MLDataError, class_counts, now_text, write_model_meta

MIN_SAMPLES_PER_CLASS = 2

MODEL_CHOICES = classifiers.TEXT_CHOICES
DISPLAY_CHOICES = classifiers.TEXT_DISPLAY
DEFAULT_MODEL = "logistic_regression"


def build_pipeline(model_choice: str = DEFAULT_MODEL, sample_count: int = 0) -> Pipeline:
    # char_wb n-grams work for Chinese text without needing a tokenizer.
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3))),
            ("clf", classifiers.make_classifier(model_choice, sample_count)),
        ]
    )


def _prepare(samples: list[dict[str, str]]) -> tuple[list[str], list[str], dict[str, int]]:
    texts = [sample["text"].strip() for sample in samples if sample["text"].strip()]
    labels = [sample["label"].strip() for sample in samples if sample["text"].strip()]
    if len(set(labels)) < 2:
        raise MLDataError("至少需要 2 个类别才能训练分类模型，请给每个类别添加例句。")
    counts = class_counts(labels)
    thin_classes = [label for label, count in counts.items() if count < MIN_SAMPLES_PER_CLASS]
    if thin_classes:
        raise MLDataError(
            f"这些类别的例句太少：{('、'.join(thin_classes))}。每个类别至少要 {MIN_SAMPLES_PER_CLASS} 条。"
        )
    return texts, labels, counts


def train(
    samples: list[dict[str, str]],
    models_dir: Path,
    model_choice: str | None = None,
) -> dict[str, Any]:
    choice = classifiers.resolve_choice(model_choice, MODEL_CHOICES, DEFAULT_MODEL)
    texts, labels, counts = _prepare(samples)

    model = build_pipeline(choice, len(texts))
    model.fit(texts, labels)
    train_accuracy = float(model.score(texts, labels))
    cross_val_accuracy = classifiers.cross_val_accuracy(
        lambda: build_pipeline(choice, len(texts)), texts, labels, counts
    )

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, models_dir / MODEL_FILE)
    meta = {
        "capability": "text_classifier",
        "labels": sorted(counts),
        "sample_count": len(texts),
        "class_counts": counts,
        "train_accuracy": train_accuracy,
        "cross_val_accuracy": cross_val_accuracy,
        "model_choice": choice,
        "model_name": classifiers.CLASSIFIER_INFO[choice]["name"],
        "trained_at": now_text(),
    }
    write_model_meta(models_dir, meta)
    return meta


def compare(samples: list[dict[str, str]]) -> list[dict[str, Any]]:
    texts, labels, counts = _prepare(samples)
    return classifiers.compare_rows(
        MODEL_CHOICES,
        DEFAULT_MODEL,
        lambda choice: build_pipeline(choice, len(texts)),
        texts,
        labels,
        counts,
    )


def predict(models_dir: Path, text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise MLDataError("请输入要测试的文本。")
    model = _load_model(models_dir)
    label = str(model.predict([text])[0])
    scores = _probability_scores(model, text)
    return {"input": text, "label": label, "scores": scores}


def _load_model(models_dir: Path) -> Pipeline:
    model_path = models_dir / MODEL_FILE
    if not model_path.is_file():
        raise MLDataError("还没有训练模型，请先完成“训练模型”这一步。")
    return joblib.load(model_path)


def _probability_scores(model: Pipeline, text: str) -> dict[str, float]:
    probabilities = model.predict_proba([text])[0]
    return {
        str(label): round(float(probability), 4)
        for label, probability in zip(model.classes_, probabilities)
    }
