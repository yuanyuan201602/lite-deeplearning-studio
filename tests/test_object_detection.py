from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app
from app.ml import object_detector, pretrained

DETECTOR_PRESENT = pretrained.has_detector()


def make_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(workspace_root=tmp_path))


def make_image_bytes(color: tuple[int, int, int] = (200, 200, 200)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (120, 120), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_homepage_links_detect_playground(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/")

    assert "/playground/detect" in response.text
    assert "目标检测体验" in response.text


def test_detect_page_renders_with_engine_status(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/playground/detect")

    assert response.status_code == 200
    assert "目标检测体验" in response.text
    if object_detector.active_engine() == "ssd":
        assert "SSD-MobileNet" in response.text
    else:
        assert "download_pretrained" in response.text or "vision" in response.text


@pytest.mark.skipif(not DETECTOR_PRESENT, reason="pretrained detector not downloaded")
def test_detect_api_uses_ssd_engine(tmp_path: Path) -> None:
    response = make_client(tmp_path).post(
        "/api/playground/detect",
        files={"file": ("photo.png", make_image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["engine"] == "ssd"
    assert data["count"] == len(data["boxes"])
    assert data["width"] == 120
    assert data["height"] == 120


def test_detect_api_friendly_hint_without_any_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(pretrained, "PRETRAINED_DIR", tmp_path / "missing")
    if object_detector._has_cv2():
        pytest.skip("opencv installed; haar fallback would handle this")

    response = make_client(tmp_path).post(
        "/api/playground/detect",
        files={"file": ("photo.png", make_image_bytes(), "image/png")},
    )

    assert response.status_code == 400
    assert "download_pretrained" in response.json()["detail"]


def test_detect_api_rejects_broken_image(tmp_path: Path) -> None:
    if object_detector.active_engine() is None:
        pytest.skip("no detection engine available")

    response = make_client(tmp_path).post(
        "/api/playground/detect",
        files={"file": ("photo.png", b"not an image", "image/png")},
    )

    assert response.status_code == 400
    assert "打不开" in response.json()["detail"]
