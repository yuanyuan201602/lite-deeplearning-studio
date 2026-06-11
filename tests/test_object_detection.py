from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app
from app.ml import object_detector


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


def test_detect_page_renders_with_availability_hint(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/playground/detect")

    assert response.status_code == 200
    assert "目标检测体验" in response.text
    if not object_detector.is_available():
        assert "vision" in response.text


def test_detect_api_friendly_error_without_cv2(tmp_path: Path) -> None:
    if object_detector.is_available():
        pytest.skip("opencv installed; degradation path not reachable")

    response = make_client(tmp_path).post(
        "/api/playground/detect",
        files={"file": ("photo.png", make_image_bytes(), "image/png")},
    )

    assert response.status_code == 400
    assert "vision" in response.json()["detail"]


def test_detect_api_returns_box_list_with_cv2(tmp_path: Path) -> None:
    pytest.importorskip("cv2")

    response = make_client(tmp_path).post(
        "/api/playground/detect",
        files={"file": ("photo.png", make_image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == len(data["boxes"])
    assert data["width"] == 120
    assert data["height"] == 120
