from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.ml import (
    audio_classifier,
    classifiers,
    detect_lite,
    image_classifier,
    ocr_checker,
    qa_retrieval,
    sensor_model,
    text_classifier,
)
from app.ml.base import MLDataError

__all__ = [
    "MLDataError",
    "train_capability",
    "predict_capability",
    "compare_capability",
    "list_model_choices",
    "list_feature_modes",
]

TEXT_SAMPLES_FILE = "text_samples.json"
QA_PAIRS_FILE = "qa_pairs.json"
SENSOR_CSV_FILE = "sensor.csv"
OCR_FILE = "ocr.json"
IMAGE_LABELS_FILE = "image_labels.json"
IMAGES_DIR = "images"
AUDIO_LABELS_FILE = "audio_labels.json"
AUDIO_DIR = "audio"
DETECT_LABELS_FILE = "detect_labels.json"
DETECT_IMAGES_DIR = "detect_images"


def train_capability(
    capability: str,
    dataset_dir: Path,
    models_dir: Path,
    model_choice: str | None = None,
    feature_mode: str | None = None,
) -> dict[str, Any]:
    if capability == "text_classifier":
        return text_classifier.train(
            _load_json_list(dataset_dir / TEXT_SAMPLES_FILE), models_dir, model_choice
        )
    if capability == "image_classifier":
        return image_classifier.train(
            load_labeled_images(dataset_dir), models_dir, model_choice, feature_mode
        )
    if capability == "audio_classifier":
        return audio_classifier.train(load_labeled_audio(dataset_dir), models_dir, model_choice)
    if capability == "qa_retrieval":
        return qa_retrieval.train(_load_json_list(dataset_dir / QA_PAIRS_FILE), models_dir)
    if capability == "sensor_decision_model":
        return sensor_model.train(
            _load_text(dataset_dir / SENSOR_CSV_FILE), models_dir, model_choice
        )
    if capability == "ocr_typo_checker":
        return ocr_checker.train(_load_ocr_correct_text(dataset_dir), models_dir)
    if capability == "object_detector_trainable":
        if model_choice and model_choice != "lite":
            raise MLDataError("YOLO 端到端检测将在下一期接入，先用「轻量检测」体验完整四步吧。")
        return detect_lite.train(load_labeled_detect(dataset_dir), models_dir, feature_mode)
    raise MLDataError(f"暂不支持这种 AI 能力：{capability}")


def compare_capability(
    capability: str, dataset_dir: Path, feature_mode: str | None = None
) -> list[dict[str, Any]]:
    """Fit every available model on the same data; nothing is persisted."""
    if capability == "text_classifier":
        return text_classifier.compare(_load_json_list(dataset_dir / TEXT_SAMPLES_FILE))
    if capability == "image_classifier":
        sampled = load_labeled_images(dataset_dir, classifiers.COMPARE_MAX_SAMPLES)
        return image_classifier.compare(sampled, feature_mode)
    if capability == "audio_classifier":
        return audio_classifier.compare(load_labeled_audio(dataset_dir, classifiers.COMPARE_MAX_SAMPLES))
    if capability == "sensor_decision_model":
        return sensor_model.compare(_load_text(dataset_dir / SENSOR_CSV_FILE))
    raise MLDataError("这个任务只有一种处理方式，不需要对比模型。")


def list_model_choices(capability: str) -> list[dict[str, Any]]:
    if capability == "object_detector_trainable":
        return [dict(card) for card in detect_lite.ALGORITHM_CARDS]
    modules = {
        "text_classifier": text_classifier,
        "image_classifier": image_classifier,
        "audio_classifier": audio_classifier,
        "sensor_decision_model": sensor_model,
    }
    module = modules.get(capability)
    if module is None:
        return []
    return classifiers.list_choice_info(
        module.MODEL_CHOICES, module.DISPLAY_CHOICES, module.DEFAULT_MODEL
    )


def list_feature_modes(capability: str) -> list[dict[str, Any]]:
    """Feature-extractor options for the task (only image offers a choice)."""
    if capability == "image_classifier":
        return image_classifier.list_feature_modes()
    return []


def predict_capability(capability: str, models_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if capability == "text_classifier":
        return text_classifier.predict(models_dir, str(payload.get("text", "")))
    if capability == "image_classifier":
        image_bytes = payload.get("image_bytes")
        if not image_bytes:
            raise MLDataError("请选择一张要测试的图片。")
        return image_classifier.predict(models_dir, image_bytes)
    if capability == "audio_classifier":
        audio_bytes = payload.get("audio_bytes")
        if not audio_bytes:
            raise MLDataError("请先录一段或上传一段要测试的声音。")
        return audio_classifier.predict(models_dir, audio_bytes)
    if capability == "qa_retrieval":
        return qa_retrieval.predict(models_dir, str(payload.get("text", "")))
    if capability == "sensor_decision_model":
        return sensor_model.predict(models_dir, payload.get("values", {}))
    if capability == "ocr_typo_checker":
        return ocr_checker.predict(models_dir, str(payload.get("text", "")))
    if capability == "object_detector_trainable":
        image_bytes = payload.get("image_bytes")
        if not image_bytes:
            raise MLDataError("请选择一张要测试的图片。")
        return detect_lite.predict(models_dir, image_bytes)
    raise MLDataError(f"暂不支持这种 AI 能力：{capability}")


def _load_labeled_media(
    dataset_dir: Path, labels_file: str, media_dir: str, missing_hint: str, sample_cap: int | None
) -> dict[str, list[bytes]]:
    labels_path = dataset_dir / labels_file
    if not labels_path.is_file():
        raise MLDataError(missing_hint)
    label_map: dict[str, str] = json.loads(labels_path.read_text(encoding="utf-8"))
    paths_by_label: dict[str, list[Path]] = {
        label: [p for p in sorted((dataset_dir / media_dir / folder).glob("*")) if p.is_file()]
        for folder, label in label_map.items()
    }
    # For "对比所有模型" we only need a small stratified sample; sampling the paths
    # before reading avoids loading every file's bytes (hundreds of MB) into memory.
    if sample_cap is not None:
        paths_by_label = classifiers.subsample_labeled(paths_by_label, sample_cap)
    return {label: [p.read_bytes() for p in paths] for label, paths in paths_by_label.items()}


def load_labeled_images(dataset_dir: Path, sample_cap: int | None = None) -> dict[str, list[bytes]]:
    return _load_labeled_media(
        dataset_dir, IMAGE_LABELS_FILE, IMAGES_DIR,
        "还没有上传图片，请先给每个类别上传图片。", sample_cap,
    )


def load_labeled_audio(dataset_dir: Path, sample_cap: int | None = None) -> dict[str, list[bytes]]:
    return _load_labeled_media(
        dataset_dir, AUDIO_LABELS_FILE, AUDIO_DIR,
        "还没有录入声音，请先给每个类别录几段声音。", sample_cap,
    )


def load_labeled_detect(dataset_dir: Path) -> list[dict[str, Any]]:
    labels_path = dataset_dir / DETECT_LABELS_FILE
    if not labels_path.is_file():
        raise MLDataError("还没有标注图片，请先上传图片并把目标框出来。")
    items = json.loads(labels_path.read_text(encoding="utf-8"))
    loaded: list[dict[str, Any]] = []
    for item in items:
        image_path = dataset_dir / DETECT_IMAGES_DIR / item.get("image", "")
        if not image_path.is_file():
            continue
        loaded.append(
            {
                "image_bytes": image_path.read_bytes(),
                "boxes": item.get("boxes", []),
                "width": item.get("width"),
                "height": item.get("height"),
            }
        )
    if not loaded:
        raise MLDataError("还没有标注图片，请先上传图片并把目标框出来。")
    return loaded


def _load_json_list(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise MLDataError("还没有添加训练数据，请先完成“准备数据”这一步。")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_text(path: Path) -> str:
    if not path.is_file():
        raise MLDataError("还没有添加训练数据，请先完成“准备数据”这一步。")
    return path.read_text(encoding="utf-8")


def _load_ocr_correct_text(dataset_dir: Path) -> str:
    path = dataset_dir / OCR_FILE
    if not path.is_file():
        raise MLDataError("还没有输入正确文字，请先完成“准备数据”这一步。")
    return json.loads(path.read_text(encoding="utf-8")).get("correct_text", "")
