"""Download the pretrained ONNX models used for transfer learning and detection.

Run once after install (the student installer and Docker build do this for you):

    python scripts/download_pretrained.py

Models land in models_pretrained/ at the project root. Everything keeps working
without them — image training falls back to raw-pixel features and the detection
playground falls back to face detection — but with them students get
MobileNet transfer learning and 80-class object detection.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRETRAINED_DIR = PROJECT_ROOT / "models_pretrained"

MODELS = {
    "mobilenetv2.onnx": (
        "https://github.com/onnx/models/raw/main/validated/vision/classification/"
        "mobilenet/model/mobilenetv2-7.onnx"
    ),
    "ssd_mobilenet.onnx": (
        "https://github.com/onnx/models/raw/main/validated/vision/"
        "object_detection_segmentation/ssd-mobilenetv1/model/ssd_mobilenet_v1_10.onnx"
    ),
}

MIN_VALID_BYTES = 1024 * 1024


def download(name: str, url: str, force: bool = False) -> bool:
    target = PRETRAINED_DIR / name
    if target.is_file() and target.stat().st_size > MIN_VALID_BYTES and not force:
        print(f"已存在，跳过：{target.name}（{target.stat().st_size // 1024 // 1024}MB）")
        return True
    PRETRAINED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"正在下载 {name} ……")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
    except Exception as exc:
        print(f"下载失败：{name}（{exc}）", file=sys.stderr)
        return False
    if len(data) < MIN_VALID_BYTES:
        print(f"下载内容异常偏小，已放弃：{name}", file=sys.stderr)
        return False
    target.write_bytes(data)
    print(f"完成：{target.name}（{len(data) // 1024 // 1024}MB）")
    return True


def download_all(force: bool = False) -> bool:
    results = [download(name, url, force) for name, url in MODELS.items()]
    if all(results):
        print("全部预训练模型就绪。")
        return True
    print("部分模型未下载成功；软件仍可使用基础模式。", file=sys.stderr)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Download pretrained ONNX models.")
    parser.add_argument("--force", action="store_true", help="redownload even if present")
    args = parser.parse_args()
    return 0 if download_all(args.force) else 1


if __name__ == "__main__":
    sys.exit(main())
