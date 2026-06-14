"""算法 A · 轻量检测（候选框 + 框分类器）—— 经典 R-CNN 的简化版。

检测拆成两步：①找候选框（借用预训练 SSD，见 object_detector.propose_boxes）②认每个
框里是什么（这里训练一个 sklearn 分类器）。训练时把学生标注的框裁出来当正样本、随机
取没框中的区域当「背景」负样本；预测时对 SSD 提出的每个候选框分类，丢掉背景与低置信框，
再用 NMS 去重。特征提取复用 image_classifier 那套 MobileNet/像素，保证和图像分类一致。
"""

from __future__ import annotations

import random
from io import BytesIO
from pathlib import Path
from typing import Any

import joblib
from PIL import Image
from sklearn.linear_model import LogisticRegression

from app.ml import image_classifier, object_detector
from app.ml.base import MODEL_FILE, MLDataError, now_text, write_model_meta

ALGORITHM = "lite"
MODEL_NAME = "轻量检测（候选框+分类器）"
BACKGROUND_LABEL = "背景"

# Algorithm cards for the detection training page. lite is trainable now; yolo is
# shown as a locked card (端到端真检测，二期接入，需 .[detect]）so students see the
# full picture and the R-CNN→YOLO contrast.
ALGORITHM_CARDS: list[dict[str, Any]] = [
    {
        "slug": "lite",
        "name": "轻量检测",
        "en_name": "R-CNN (region proposals + classifier)",
        "trainable": True,
        "default": True,
        "school": "经典检测",
        "principle": "先借用预训练网络找出候选框，再训练一个分类器认出每个框里是什么。",
        "performance": "CPU 上几秒就能训完，适合课堂；但「找框」是借来的，精度有限。",
        "strengths": "快、轻、好懂，本机就能跑，不用装额外东西。",
        "weaknesses": "只能检测预训练网络找得出框的目标，找框不是自己学的。",
        "best_for": "课堂上快速体验「检测 = 先找框，再认框」。",
    },
    {
        "slug": "yolo",
        "name": "YOLO 端到端检测",
        "en_name": "YOLOv8 (end-to-end)",
        "trainable": False,
        "default": False,
        "school": "深度检测",
        "principle": "一个网络端到端同时学会「找框」和「认框」，是工业界主流做法。",
        "performance": "精度高、能检测自定义目标；但训练慢、依赖重、建议显卡。",
        "strengths": "真正端到端、精度高，连找框都是自己学的。",
        "weaknesses": "依赖重、CPU 上训练慢，建议配显卡。",
        "best_for": "想要更强、更通用的检测。",
        "note": "下一期接入：需要安装检测进阶组件，建议配显卡。",
    },
]

MIN_TOTAL_BOXES = 3
NMS_IOU = 0.45
PREDICT_MIN_SCORE = 0.55
_RNG = random.Random(7)


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _crop_feature(image: Image.Image, box: tuple[int, int, int, int], feature_mode: str):
    x, y, w, h = box
    crop = image.crop((x, y, x + w, y + h))
    return image_classifier.image_features_from_image(crop, feature_mode)


def _random_negatives(
    width: int, height: int, positives: list[tuple[int, int, int, int]], count: int
) -> list[tuple[int, int, int, int]]:
    """Random boxes that barely overlap any labeled box → 背景 negative samples."""
    negatives: list[tuple[int, int, int, int]] = []
    attempts = 0
    while len(negatives) < count and attempts < count * 20:
        attempts += 1
        w = _RNG.randint(max(8, width // 6), max(9, width // 2))
        h = _RNG.randint(max(8, height // 6), max(9, height // 2))
        x = _RNG.randint(0, max(0, width - w))
        y = _RNG.randint(0, max(0, height - h))
        candidate = (x, y, w, h)
        if all(_iou(candidate, pos) < 0.2 for pos in positives):
            negatives.append(candidate)
    return negatives


def train(
    labeled: list[dict[str, Any]], models_dir: Path, feature_mode: str | None = None
) -> dict[str, Any]:
    feature_mode = image_classifier.resolve_feature_mode(feature_mode)

    features: list[list[float]] = []
    labels: list[str] = []
    class_counts: dict[str, int] = {}
    box_count = 0
    image_count = 0
    background_count = 0

    for item in labeled:
        boxes = item.get("boxes") or []
        if not boxes:
            continue
        image = Image.open(BytesIO(item["image_bytes"])).convert("RGB")
        width, height = image.size
        positives: list[tuple[int, int, int, int]] = []
        for box in boxes:
            rect = (int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"]))
            if rect[2] < 4 or rect[3] < 4:
                continue
            label = str(box["label"]).strip()
            if not label:
                continue
            features.append(_crop_feature(image, rect, feature_mode))
            labels.append(label)
            positives.append(rect)
            class_counts[label] = class_counts.get(label, 0) + 1
            box_count += 1
        if not positives:
            continue
        image_count += 1
        for neg in _random_negatives(width, height, positives, len(positives)):
            features.append(_crop_feature(image, neg, feature_mode))
            labels.append(BACKGROUND_LABEL)
            background_count += 1

    object_labels = sorted(class_counts)
    if not object_labels:
        raise MLDataError("还没有标注任何框，请先在图片上把目标框出来并选好类别。")
    if box_count < MIN_TOTAL_BOXES:
        raise MLDataError(f"标注的框太少了，至少要 {MIN_TOTAL_BOXES} 个框模型才学得动，多框几个吧。")
    if background_count == 0:
        # Degenerate (e.g. boxes fill every image); add the whole frames as background.
        raise MLDataError("图片几乎被框满了，模型分不出「背景」。请让框只圈住目标本身。")

    model = LogisticRegression(max_iter=1000)
    model.fit(features, labels)

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": model, "feature_mode": feature_mode, "classes": object_labels},
        models_dir / MODEL_FILE,
    )
    meta = {
        "capability": "object_detector_trainable",
        "algorithm": ALGORITHM,
        "model_name": MODEL_NAME,
        "labels": object_labels,
        "class_counts": class_counts,
        "box_count": box_count,
        "image_count": image_count,
        "background_count": background_count,
        "feature_mode": feature_mode,
        "trained_at": now_text(),
    }
    write_model_meta(models_dir, meta)
    return meta


def _nms(boxes: list[dict[str, Any]], iou_threshold: float) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for box in sorted(boxes, key=lambda b: b["score"], reverse=True):
        rect = (box["x"], box["y"], box["w"], box["h"])
        if all(_iou(rect, (k["x"], k["y"], k["w"], k["h"])) < iou_threshold for k in kept):
            kept.append(box)
    return kept


def predict(models_dir: Path, image_bytes: bytes) -> dict[str, Any]:
    model_path = models_dir / MODEL_FILE
    if not model_path.is_file():
        raise MLDataError("还没有训练模型，请先完成“训练模型”这一步。")
    store = joblib.load(model_path)
    model = store["model"]
    feature_mode = store["feature_mode"]
    classes = list(model.classes_)

    proposals = object_detector.propose_boxes(image_bytes)
    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    results: list[dict[str, Any]] = []
    for prop in proposals["boxes"]:
        rect = (prop["x"], prop["y"], prop["w"], prop["h"])
        probabilities = model.predict_proba([_crop_feature(image, rect, feature_mode)])[0]
        best_index = int(probabilities.argmax())
        label = str(classes[best_index])
        score = float(probabilities[best_index])
        if label == BACKGROUND_LABEL or score < PREDICT_MIN_SCORE:
            continue
        results.append(
            {"x": prop["x"], "y": prop["y"], "w": prop["w"], "h": prop["h"],
             "label": label, "score": round(score, 3)}
        )

    results = _nms(results, NMS_IOU)
    return {
        "boxes": results,
        "count": len(results),
        "width": proposals["width"],
        "height": proposals["height"],
    }
