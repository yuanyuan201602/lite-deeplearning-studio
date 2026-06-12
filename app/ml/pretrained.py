"""Lazy access to the optional pretrained ONNX models in models_pretrained/.

Everything here degrades gracefully: if onnxruntime or a model file is missing,
callers get None / False and fall back to the lightweight pipelines. Image
preprocessing must stay in sync with the exported ai_runtime/core.py template.
"""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PRETRAINED_DIR = PROJECT_ROOT / "models_pretrained"

IMAGE_EMBEDDER_FILE = "mobilenetv2.onnx"
DETECTOR_FILE = "ssd_mobilenet.onnx"

EMBED_INPUT_SIZE = (224, 224)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

DOWNLOAD_HINT = "请运行 python scripts/download_pretrained.py 下载预训练模型。"

_lock = threading.Lock()
_sessions: dict[str, object] = {}


def _onnxruntime():
    try:
        import onnxruntime
    except ImportError:
        return None
    return onnxruntime


def _session(filename: str):
    path = PRETRAINED_DIR / filename
    if not path.is_file():
        return None
    ort = _onnxruntime()
    if ort is None:
        return None
    key = str(path.resolve())
    with _lock:
        if key not in _sessions:
            try:
                _sessions[key] = ort.InferenceSession(
                    str(path), providers=["CPUExecutionProvider"]
                )
            except Exception:
                # A corrupt or incompatible model file must not break the app.
                _sessions[key] = None
        return _sessions[key]


def has_image_embedder() -> bool:
    return image_embedder_session() is not None


def has_detector() -> bool:
    return detector_session() is not None


def image_embedder_session():
    return _session(IMAGE_EMBEDDER_FILE)


def detector_session():
    return _session(DETECTOR_FILE)


def embed_image(image: Image.Image) -> list[float]:
    """MobileNetV2 forward pass; the 1000-d output works as a transfer-learning feature."""
    session = image_embedder_session()
    if session is None:
        raise RuntimeError("image embedder not available")
    resized = image.convert("RGB").resize(EMBED_INPUT_SIZE)
    pixels = np.asarray(resized, dtype=np.float32) / 255.0
    normalized = (pixels - IMAGENET_MEAN) / IMAGENET_STD
    batch = normalized.transpose(2, 0, 1)[np.newaxis, :]
    output = session.run(None, {session.get_inputs()[0].name: batch})[0]
    return output[0].astype(np.float64).tolist()
