from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression

from app.ml.base import MODEL_FILE, MLDataError, now_text, write_model_meta

IMAGE_SIZE = (32, 32)
MIN_IMAGES_PER_CLASS = 2


def image_features(data: bytes) -> list[float]:
    try:
        with Image.open(BytesIO(data)) as image:
            resized = image.convert("RGB").resize(IMAGE_SIZE)
    except Exception as exc:
        raise MLDataError("这张图片打不开，请换一张 PNG 或 JPG 图片。") from exc
    pixels = np.asarray(resized, dtype=np.float64) / 255.0
    return pixels.flatten().tolist()


def train(labeled_images: dict[str, list[bytes]], models_dir: Path) -> dict[str, Any]:
    usable = {label: images for label, images in labeled_images.items() if images}
    if len(usable) < 2:
        raise MLDataError("至少需要 2 个类别的图片才能训练，请先给每个类别上传图片。")
    thin_classes = [
        label for label, images in usable.items() if len(images) < MIN_IMAGES_PER_CLASS
    ]
    if thin_classes:
        raise MLDataError(
            f"这些类别的图片太少：{('、'.join(thin_classes))}。每个类别至少要 {MIN_IMAGES_PER_CLASS} 张。"
        )

    features: list[list[float]] = []
    labels: list[str] = []
    for label, images in usable.items():
        for data in images:
            features.append(image_features(data))
            labels.append(label)

    model = LogisticRegression(max_iter=1000)
    model.fit(features, labels)
    train_accuracy = float(model.score(features, labels))

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, models_dir / MODEL_FILE)
    meta = {
        "capability": "image_classifier",
        "labels": sorted(usable),
        "sample_count": len(labels),
        "class_counts": {label: len(images) for label, images in usable.items()},
        "train_accuracy": train_accuracy,
        "cross_val_accuracy": None,
        "trained_at": now_text(),
    }
    write_model_meta(models_dir, meta)
    return meta


def predict(models_dir: Path, image_bytes: bytes) -> dict[str, Any]:
    model_path = models_dir / MODEL_FILE
    if not model_path.is_file():
        raise MLDataError("还没有训练模型，请先完成“训练模型”这一步。")
    model = joblib.load(model_path)
    features = image_features(image_bytes)
    label = str(model.predict([features])[0])
    probabilities = model.predict_proba([features])[0]
    scores = {
        str(class_label): round(float(probability), 4)
        for class_label, probability in zip(model.classes_, probabilities)
    }
    return {"label": label, "scores": scores}
