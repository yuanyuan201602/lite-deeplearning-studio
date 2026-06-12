from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.ml import image_classifier, pretrained
from app.ml.base import MLDataError

EMBEDDER_PRESENT = pretrained.has_image_embedder()


def make_image_bytes(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (48, 48), color).save(buffer, format="PNG")
    return buffer.getvalue()


def make_labeled_images() -> dict[str, list[bytes]]:
    return {
        "红色卡片": [make_image_bytes((220, 60 + index, 60)) for index in range(3)],
        "绿色卡片": [make_image_bytes((60, 170 + index, 90)) for index in range(3)],
    }


def test_pixel_mode_is_fallback_without_pretrained_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(pretrained, "PRETRAINED_DIR", tmp_path / "missing")

    assert image_classifier.active_feature_mode() == image_classifier.FEATURE_MODE_PIXEL
    features = image_classifier.image_features(
        make_image_bytes((10, 20, 30)), image_classifier.FEATURE_MODE_PIXEL
    )
    assert len(features) == 32 * 32 * 3


def test_pixel_mode_train_and_predict(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pretrained, "PRETRAINED_DIR", tmp_path / "missing")
    models_dir = tmp_path / "models"

    report = image_classifier.train(make_labeled_images(), models_dir)

    assert report["feature_mode"] == image_classifier.FEATURE_MODE_PIXEL

    result = image_classifier.predict(models_dir, make_image_bytes((215, 65, 62)))
    assert result["label"] == "红色卡片"
    assert result["feature_mode"] == image_classifier.FEATURE_MODE_PIXEL


@pytest.mark.skipif(not EMBEDDER_PRESENT, reason="pretrained embedder not downloaded")
def test_embedding_mode_train_and_predict(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"

    report = image_classifier.train(make_labeled_images(), models_dir)

    assert report["feature_mode"] == image_classifier.FEATURE_MODE_EMBEDDING

    result = image_classifier.predict(models_dir, make_image_bytes((215, 65, 62)))
    assert result["label"] == "红色卡片"
    assert result["feature_mode"] == image_classifier.FEATURE_MODE_EMBEDDING


@pytest.mark.skipif(not EMBEDDER_PRESENT, reason="pretrained embedder not downloaded")
def test_embedding_model_without_embedder_gives_friendly_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    models_dir = tmp_path / "models"
    image_classifier.train(make_labeled_images(), models_dir)

    monkeypatch.setattr(pretrained, "PRETRAINED_DIR", tmp_path / "missing")

    with pytest.raises(MLDataError, match="download_pretrained"):
        image_classifier.predict(models_dir, make_image_bytes((215, 65, 62)))


@pytest.mark.skipif(not EMBEDDER_PRESENT, reason="pretrained embedder not downloaded")
def test_embedding_features_have_fixed_dimension() -> None:
    features = image_classifier.image_features(
        make_image_bytes((100, 100, 100)), image_classifier.FEATURE_MODE_EMBEDDING
    )
    assert len(features) == 1000
