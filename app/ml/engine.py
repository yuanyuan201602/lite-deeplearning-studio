from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.ml import (
    audio_classifier,
    image_classifier,
    ocr_checker,
    qa_retrieval,
    sensor_model,
    text_classifier,
)
from app.ml.base import MLDataError

__all__ = ["MLDataError", "train_capability", "predict_capability"]

TEXT_SAMPLES_FILE = "text_samples.json"
QA_PAIRS_FILE = "qa_pairs.json"
SENSOR_CSV_FILE = "sensor.csv"
OCR_FILE = "ocr.json"
IMAGE_LABELS_FILE = "image_labels.json"
IMAGES_DIR = "images"
AUDIO_LABELS_FILE = "audio_labels.json"
AUDIO_DIR = "audio"


def train_capability(capability: str, dataset_dir: Path, models_dir: Path) -> dict[str, Any]:
    if capability == "text_classifier":
        return text_classifier.train(_load_json_list(dataset_dir / TEXT_SAMPLES_FILE), models_dir)
    if capability == "image_classifier":
        return image_classifier.train(load_labeled_images(dataset_dir), models_dir)
    if capability == "audio_classifier":
        return audio_classifier.train(load_labeled_audio(dataset_dir), models_dir)
    if capability == "qa_retrieval":
        return qa_retrieval.train(_load_json_list(dataset_dir / QA_PAIRS_FILE), models_dir)
    if capability == "sensor_decision_model":
        return sensor_model.train(_load_text(dataset_dir / SENSOR_CSV_FILE), models_dir)
    if capability == "ocr_typo_checker":
        return ocr_checker.train(_load_ocr_correct_text(dataset_dir), models_dir)
    raise MLDataError(f"暂不支持这种 AI 能力：{capability}")


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
    raise MLDataError(f"暂不支持这种 AI 能力：{capability}")


def load_labeled_images(dataset_dir: Path) -> dict[str, list[bytes]]:
    labels_path = dataset_dir / IMAGE_LABELS_FILE
    if not labels_path.is_file():
        raise MLDataError("还没有上传图片，请先给每个类别上传图片。")
    label_map: dict[str, str] = json.loads(labels_path.read_text(encoding="utf-8"))
    labeled_images: dict[str, list[bytes]] = {}
    for folder_name, label in label_map.items():
        folder = dataset_dir / IMAGES_DIR / folder_name
        images = [path.read_bytes() for path in sorted(folder.glob("*")) if path.is_file()]
        labeled_images[label] = images
    return labeled_images


def load_labeled_audio(dataset_dir: Path) -> dict[str, list[bytes]]:
    labels_path = dataset_dir / AUDIO_LABELS_FILE
    if not labels_path.is_file():
        raise MLDataError("还没有录入声音，请先给每个类别录几段声音。")
    label_map: dict[str, str] = json.loads(labels_path.read_text(encoding="utf-8"))
    labeled_audio: dict[str, list[bytes]] = {}
    for folder_name, label in label_map.items():
        folder = dataset_dir / AUDIO_DIR / folder_name
        clips = [path.read_bytes() for path in sorted(folder.glob("*")) if path.is_file()]
        labeled_audio[label] = clips
    return labeled_audio


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
