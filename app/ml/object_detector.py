from __future__ import annotations

from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image

from app.ml import pretrained
from app.ml.base import MLDataError

# Engine order: SSD-MobileNet (80-class COCO, needs models_pretrained/) first,
# Haar face cascade (needs opencv) as fallback, then a friendly install hint.
INSTALL_HINT = (
    f"目标检测体验需要预训练检测模型：{pretrained.DOWNLOAD_HINT}"
    "（或安装视觉组件 pip install -e \".[vision]\" 使用人脸检测基础模式。）"
)

SCORE_THRESHOLD = 0.5
MAX_BOXES = 20
MIN_FACE_SIZE = (40, 40)

# For the trainable lite detector: take many low-objectness SSD boxes as
# class-agnostic candidate regions (the "where might something be" step).
PROPOSAL_SCORE_THRESHOLD = 0.10
MAX_PROPOSALS = 40
MIN_PROPOSAL_SIZE = 8

# COCO 91-id space used by the TF-origin SSD model (gaps are unused ids).
COCO_LABELS_ZH = {
    1: "人", 2: "自行车", 3: "汽车", 4: "摩托车", 5: "飞机", 6: "公交车", 7: "火车",
    8: "卡车", 9: "船", 10: "红绿灯", 11: "消防栓", 13: "停车标志", 14: "停车计时器",
    15: "长椅", 16: "鸟", 17: "猫", 18: "狗", 19: "马", 20: "羊", 21: "牛",
    22: "大象", 23: "熊", 24: "斑马", 25: "长颈鹿", 27: "背包", 28: "雨伞",
    31: "手提包", 32: "领带", 33: "行李箱", 34: "飞盘", 35: "滑雪板", 36: "单板滑雪",
    37: "球", 38: "风筝", 39: "棒球棒", 40: "棒球手套", 41: "滑板", 42: "冲浪板",
    43: "网球拍", 44: "瓶子", 46: "酒杯", 47: "杯子", 48: "叉子", 49: "刀",
    50: "勺子", 51: "碗", 52: "香蕉", 53: "苹果", 54: "三明治", 55: "橙子",
    56: "西兰花", 57: "胡萝卜", 58: "热狗", 59: "披萨", 60: "甜甜圈", 61: "蛋糕",
    62: "椅子", 63: "沙发", 64: "盆栽", 65: "床", 67: "餐桌", 70: "马桶",
    72: "电视", 73: "笔记本电脑", 74: "鼠标", 75: "遥控器", 76: "键盘", 77: "手机",
    78: "微波炉", 79: "烤箱", 80: "烤面包机", 81: "水槽", 82: "冰箱", 84: "书",
    85: "时钟", 86: "花瓶", 87: "剪刀", 88: "泰迪熊", 89: "吹风机", 90: "牙刷",
}


def _has_cv2() -> bool:
    try:
        import cv2  # noqa: F401
    except ImportError:
        return False
    return True


def active_engine() -> str | None:
    """"ssd" (80-class objects), "haar" (faces only) or None."""
    if pretrained.has_detector():
        return "ssd"
    if _has_cv2():
        return "haar"
    return None


def detect(image_bytes: bytes) -> dict[str, Any]:
    engine = active_engine()
    if engine == "ssd":
        return _detect_ssd(image_bytes)
    if engine == "haar":
        return _detect_haar(image_bytes)
    raise MLDataError(INSTALL_HINT)


def _open_rgb(image_bytes: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except Exception as exc:
        raise MLDataError("这张图片打不开，请换一张 PNG 或 JPG 图片。") from exc
    return image.convert("RGB")


def _detect_ssd(image_bytes: bytes) -> dict[str, Any]:
    session = pretrained.detector_session()
    image = _open_rgb(image_bytes)
    width, height = image.size
    batch = np.asarray(image, dtype=np.uint8)[np.newaxis, :]
    outputs = session.run(None, {session.get_inputs()[0].name: batch})
    named = {output.name: value for output, value in zip(session.get_outputs(), outputs)}
    boxes = named["detection_boxes:0"][0]
    classes = named["detection_classes:0"][0]
    scores = named["detection_scores:0"][0]

    results = []
    for box, class_id, score in zip(boxes, classes, scores):
        if score < SCORE_THRESHOLD or len(results) >= MAX_BOXES:
            continue
        ymin, xmin, ymax, xmax = box
        results.append(
            {
                "x": int(xmin * width),
                "y": int(ymin * height),
                "w": int((xmax - xmin) * width),
                "h": int((ymax - ymin) * height),
                "label": COCO_LABELS_ZH.get(int(class_id), "物体"),
                "score": round(float(score), 3),
            }
        )
    return {
        "engine": "ssd",
        "count": len(results),
        "boxes": results,
        "width": width,
        "height": height,
    }


def _detect_haar(image_bytes: bytes) -> dict[str, Any]:
    import cv2

    image = _open_rgb(image_bytes)
    width, height = image.size
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=MIN_FACE_SIZE
    )
    boxes = [
        {"x": int(x), "y": int(y), "w": int(w), "h": int(h), "label": "人脸", "score": None}
        for (x, y, w, h) in faces
    ]
    return {
        "engine": "haar",
        "count": len(boxes),
        "boxes": boxes,
        "width": width,
        "height": height,
    }


def propose_boxes(image_bytes: bytes) -> dict[str, Any]:
    """Class-agnostic candidate boxes (objectness) from the pretrained SSD.

    The lite detector needs «这里好像有个东西» regardless of COCO class, so we
    keep every SSD box above a low score. Requires the SSD model (no Haar fallback —
    faces aren't general proposals)."""
    session = pretrained.detector_session()
    if session is None:
        raise MLDataError(INSTALL_HINT)
    image = _open_rgb(image_bytes)
    width, height = image.size
    batch = np.asarray(image, dtype=np.uint8)[np.newaxis, :]
    outputs = session.run(None, {session.get_inputs()[0].name: batch})
    named = {output.name: value for output, value in zip(session.get_outputs(), outputs)}
    boxes = named["detection_boxes:0"][0]
    scores = named["detection_scores:0"][0]

    proposals: list[dict[str, Any]] = []
    for box, score in zip(boxes, scores):
        if score < PROPOSAL_SCORE_THRESHOLD or len(proposals) >= MAX_PROPOSALS:
            continue
        ymin, xmin, ymax, xmax = box
        x, y = int(xmin * width), int(ymin * height)
        w, h = int((xmax - xmin) * width), int((ymax - ymin) * height)
        if w < MIN_PROPOSAL_SIZE or h < MIN_PROPOSAL_SIZE:
            continue
        proposals.append({"x": x, "y": y, "w": w, "h": h, "score": round(float(score), 3)})
    return {"boxes": proposals, "width": width, "height": height}
