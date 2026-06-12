from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from PIL import Image

from app.ml import classifiers, pretrained
from app.ml.base import MODEL_FILE, MLDataError, class_counts, now_text, write_model_meta

IMAGE_SIZE = (32, 32)
MIN_IMAGES_PER_CLASS = 2

MODEL_CHOICES = classifiers.DENSE_CHOICES
DEFAULT_MODEL = "logistic_regression"

# Feature modes. "mobilenet_v2" uses the pretrained ONNX embedder (transfer
# learning, robust to lighting/position); "pixel" is the dependency-free
# fallback. The mode is stored with the model so predict always matches train.
FEATURE_MODE_EMBEDDING = "mobilenet_v2"
FEATURE_MODE_PIXEL = "pixel"

EMBEDDER_MISSING_HINT = (
    f"这个模型是用 MobileNet 迁移学习特征训练的，但现在找不到预训练模型文件。"
    f"{pretrained.DOWNLOAD_HINT}"
)


def active_feature_mode() -> str:
    return FEATURE_MODE_EMBEDDING if pretrained.has_image_embedder() else FEATURE_MODE_PIXEL


def _open_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except Exception as exc:
        raise MLDataError("这张图片打不开，请换一张 PNG 或 JPG 图片。") from exc
    return image


def image_features(data: bytes, feature_mode: str = FEATURE_MODE_PIXEL) -> list[float]:
    image = _open_image(data)
    if feature_mode == FEATURE_MODE_EMBEDDING:
        return pretrained.embed_image(image)
    resized = image.convert("RGB").resize(IMAGE_SIZE)
    pixels = np.asarray(resized, dtype=np.float64) / 255.0
    return pixels.flatten().tolist()


def _prepare_features(
    labeled_images: dict[str, list[bytes]],
) -> tuple[list[list[float]], list[str], str]:
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

    feature_mode = active_feature_mode()
    features: list[list[float]] = []
    labels: list[str] = []
    for label, images in usable.items():
        for data in images:
            features.append(image_features(data, feature_mode))
            labels.append(label)
    return features, labels, feature_mode


def train(
    labeled_images: dict[str, list[bytes]],
    models_dir: Path,
    model_choice: str | None = None,
) -> dict[str, Any]:
    choice = classifiers.resolve_choice(model_choice, MODEL_CHOICES, DEFAULT_MODEL)
    features, labels, feature_mode = _prepare_features(labeled_images)
    counts = class_counts(labels)

    model = classifiers.make_classifier(choice, len(labels))
    model.fit(features, labels)
    train_accuracy = float(model.score(features, labels))
    cross_val_accuracy = classifiers.cross_val_accuracy(
        lambda: classifiers.make_classifier(choice, len(labels)), features, labels, counts
    )

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "feature_mode": feature_mode, "model_choice": choice},
        models_dir / MODEL_FILE,
    )
    meta = {
        "capability": "image_classifier",
        "labels": sorted(counts),
        "sample_count": len(labels),
        "class_counts": counts,
        "train_accuracy": train_accuracy,
        "cross_val_accuracy": cross_val_accuracy,
        "feature_mode": feature_mode,
        "model_choice": choice,
        "model_name": classifiers.CLASSIFIER_INFO[choice]["name"],
        "trained_at": now_text(),
    }
    write_model_meta(models_dir, meta)
    return meta


def compare(labeled_images: dict[str, list[bytes]]) -> list[dict[str, Any]]:
    features, labels, _ = _prepare_features(labeled_images)
    counts = class_counts(labels)
    return classifiers.compare_rows(
        MODEL_CHOICES,
        DEFAULT_MODEL,
        lambda choice: classifiers.make_classifier(choice, len(labels)),
        features,
        labels,
        counts,
    )


def _load_store(models_dir: Path) -> dict[str, Any]:
    model_path = models_dir / MODEL_FILE
    if not model_path.is_file():
        raise MLDataError("还没有训练模型，请先完成“训练模型”这一步。")
    store = joblib.load(model_path)
    if not isinstance(store, dict):
        # Models trained before the transfer-learning upgrade are bare estimators.
        store = {"model": store, "feature_mode": FEATURE_MODE_PIXEL}
    return store


def predict(models_dir: Path, image_bytes: bytes) -> dict[str, Any]:
    store = _load_store(models_dir)
    feature_mode = store.get("feature_mode", FEATURE_MODE_PIXEL)
    if feature_mode == FEATURE_MODE_EMBEDDING and not pretrained.has_image_embedder():
        raise MLDataError(EMBEDDER_MISSING_HINT)
    model = store["model"]
    features = image_features(image_bytes, feature_mode)
    label = str(model.predict([features])[0])
    probabilities = model.predict_proba([features])[0]
    scores = {
        str(class_label): round(float(probability), 4)
        for class_label, probability in zip(model.classes_, probabilities)
    }
    return {"label": label, "scores": scores, "feature_mode": feature_mode}
