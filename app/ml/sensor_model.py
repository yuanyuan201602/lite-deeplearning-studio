from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Any

import joblib
from sklearn.tree import DecisionTreeClassifier, export_text

from app.ml import classifiers
from app.ml.base import MODEL_FILE, MLDataError, class_counts, now_text, write_model_meta

MIN_ROWS = 4
TREE_MAX_DEPTH = 4

MODEL_CHOICES = classifiers.SENSOR_CHOICES
DEFAULT_MODEL = "decision_tree"


def normalize_csv_text(raw_csv: str) -> str:
    """Chinese IMEs produce full-width punctuation; students paste it without noticing."""
    return raw_csv.replace("，", ",").replace("；", ",")


def parse_sensor_csv(raw_csv: str) -> tuple[list[str], list[list[float]], list[str]]:
    """Parse student CSV: header row, numeric feature columns, last column is the action label."""
    raw_csv = normalize_csv_text(raw_csv)
    rows = [row for row in csv.reader(StringIO(raw_csv.strip())) if any(cell.strip() for cell in row)]
    if len(rows) < 1 + MIN_ROWS:
        raise MLDataError(f"数据太少：第一行是表头，下面至少要有 {MIN_ROWS} 行数据。")
    header = [cell.strip() for cell in rows[0]]
    if len(header) < 2:
        raise MLDataError("表格至少需要 1 列传感器数值和最后 1 列动作名称。")

    feature_names = header[:-1]
    features: list[list[float]] = []
    labels: list[str] = []
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            raise MLDataError(f"第 {line_number} 行的列数和表头不一样，请检查逗号。")
        try:
            features.append([float(cell) for cell in row[:-1]])
        except ValueError as exc:
            raise MLDataError(f"第 {line_number} 行有不是数字的传感器数值，请检查。") from exc
        labels.append(row[-1].strip())
    return feature_names, features, labels


def _validated(raw_csv: str) -> tuple[list[str], list[list[float]], list[str]]:
    feature_names, features, labels = parse_sensor_csv(raw_csv)
    if len(set(labels)) < 2:
        raise MLDataError("至少需要 2 种不同的动作，模型才能学会做决定。")
    return feature_names, features, labels


def _make_model(choice: str, sample_count: int):
    if choice == "decision_tree":
        return DecisionTreeClassifier(max_depth=TREE_MAX_DEPTH, random_state=7)
    return classifiers.make_classifier(choice, sample_count)


def train(raw_csv: str, models_dir: Path, model_choice: str | None = None) -> dict[str, Any]:
    choice = classifiers.resolve_choice(model_choice, MODEL_CHOICES, DEFAULT_MODEL)
    feature_names, features, labels = _validated(raw_csv)
    counts = class_counts(labels)

    model = _make_model(choice, len(labels))
    model.fit(features, labels)
    train_accuracy = float(model.score(features, labels))
    cross_val_accuracy = classifiers.cross_val_accuracy(
        lambda: _make_model(choice, len(labels)), features, labels, counts
    )

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_names": feature_names}, models_dir / MODEL_FILE)
    meta = {
        "capability": "sensor_decision_model",
        "labels": sorted(set(labels)),
        "sample_count": len(labels),
        "class_counts": counts,
        "train_accuracy": train_accuracy,
        "cross_val_accuracy": cross_val_accuracy,
        "feature_names": feature_names,
        "model_choice": choice,
        "model_name": classifiers.CLASSIFIER_INFO[choice]["name"],
        "trained_at": now_text(),
    }
    if choice == "decision_tree":
        meta["rules_text"] = export_text(model, feature_names=feature_names)
    if hasattr(model, "feature_importances_"):
        meta["feature_importances"] = {
            name: round(float(value), 3)
            for name, value in zip(feature_names, model.feature_importances_)
        }
    write_model_meta(models_dir, meta)
    return meta


def compare(raw_csv: str) -> list[dict[str, Any]]:
    _, features, labels = _validated(raw_csv)
    counts = class_counts(labels)
    return classifiers.compare_rows(
        MODEL_CHOICES,
        DEFAULT_MODEL,
        lambda choice: _make_model(choice, len(labels)),
        features,
        labels,
        counts,
    )


def predict(models_dir: Path, values: dict[str, str]) -> dict[str, Any]:
    model_path = models_dir / MODEL_FILE
    if not model_path.is_file():
        raise MLDataError("还没有训练模型，请先完成“训练模型”这一步。")
    store = joblib.load(model_path)
    feature_names: list[str] = store["feature_names"]

    row: list[float] = []
    for name in feature_names:
        raw_value = str(values.get(name, "")).strip()
        if not raw_value:
            raise MLDataError(f"请填写传感器数值：{name}。")
        try:
            row.append(float(raw_value))
        except ValueError as exc:
            raise MLDataError(f"“{name}”需要填数字，现在填的是：{raw_value}。") from exc

    action = str(store["model"].predict([row])[0])
    return {
        "input": {name: value for name, value in zip(feature_names, row)},
        "label": action,
        "feature_names": feature_names,
    }
