from __future__ import annotations

from typing import Any

import numpy as np

from app.ml.base import MLDataError

# Haar cascades ship inside the opencv package itself, so the experience works
# offline once `.[vision]` is installed — no extra model download needed.
INSTALL_HINT = (
    "目标检测体验需要先安装视觉组件：在软件目录运行 pip install -e \".[vision]\"。"
    "装过「安装OCR增强」的电脑已经包含这个组件，可以直接使用。"
)

MIN_FACE_SIZE = (40, 40)


def is_available() -> bool:
    try:
        import cv2  # noqa: F401
    except ImportError:
        return False
    return True


def _load_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise MLDataError(INSTALL_HINT) from exc
    return cv2


def detect_faces(image_bytes: bytes) -> dict[str, Any]:
    cv2 = _load_cv2()
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise MLDataError("这张图片打不开，请换一张 PNG 或 JPG 图片。")

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=MIN_FACE_SIZE
    )
    boxes = [
        {"x": int(x), "y": int(y), "w": int(w), "h": int(h), "label": "人脸"}
        for (x, y, w, h) in faces
    ]
    return {
        "count": len(boxes),
        "boxes": boxes,
        "width": int(image.shape[1]),
        "height": int(image.shape[0]),
    }
