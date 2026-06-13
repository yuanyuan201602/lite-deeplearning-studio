import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.ml.base import MLDataError
from app.models import ProjectCreateRequest, ProjectInfo
from app.services import dataset_library
from app.services.project_service import ProjectService

DIRECT = "01_可直接用于平台主流程"


def _png(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (40, 40), color).save(buffer, format="PNG")
    return buffer.getvalue()


def build_image_dataset(root: Path) -> str:
    dataset = root / DIRECT / "图像分类" / "猫狗"
    for split, count in (("train", 5), ("test", 3)):
        for label, color in (("cat", (200, 60, 60)), ("dog", (60, 60, 200))):
            folder = dataset / split / label
            folder.mkdir(parents=True, exist_ok=True)
            for i in range(count):
                (folder / f"{label}{i}.png").write_bytes(_png(color))
    (dataset / "platform_dataset.json").write_text(
        json.dumps(
            {
                "id": "img-001",
                "title": "猫狗二分类",
                "ai_capability": "image_classifier",
                # includes a phantom "cat.png" entry that must be sanitized out
                "labels": ["cat", "cat.png", "dog"],
                "train_count": 10,
                "test_count": 6,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return "img-001"


def build_text_dataset(root: Path) -> str:
    dataset = root / DIRECT / "文本分类" / "情感"
    for split in ("train", "test"):
        (dataset / split).mkdir(parents=True, exist_ok=True)
    (dataset / "train" / "text_samples.json").write_text(
        json.dumps(
            {
                "samples": [
                    {"text": "今天天气真好心情愉快", "label": "正面"},
                    {"text": "我很开心非常满意", "label": "正面"},
                    {"text": "糟糕透了非常失望", "label": "负面"},
                    {"text": "太差劲了讨厌", "label": "负面"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (dataset / "test" / "text_samples.json").write_text(
        json.dumps(
            {"samples": [{"text": "开心满意的一天", "label": "正面"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (dataset / "platform_dataset.json").write_text(
        json.dumps(
            {
                "id": "txt-001",
                "title": "情感分类",
                "ai_capability": "text_classifier",
                "labels": ["正面", "负面"],
                "train_count": 4,
                "test_count": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return "txt-001"


def make_project(tmp_path: Path, task: str) -> tuple[ProjectService, ProjectInfo]:
    service = ProjectService(tmp_path / "workspace")
    info = service.create_project(
        ProjectCreateRequest(
            competition_slug="general_ml",
            task_slug=task,
            project_name="导入测试",
            student_name="学生A",
        )
    )
    return service, info


def test_library_lists_and_filters_by_capability(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    build_image_dataset(root)
    build_text_dataset(root)

    assert len(dataset_library.list_datasets(root)) == 2
    images = dataset_library.list_datasets(root, "image_classifier")
    assert [d["id"] for d in images] == ["img-001"]
    # the phantom "cat.png" label is sanitized away
    assert images[0]["labels"] == ["cat", "dog"]
    assert images[0]["class_count"] == 2


def test_library_resolve_rejects_unknown_id(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    build_image_dataset(root)
    assert dataset_library.resolve_dataset(root, "img-001") is not None
    assert dataset_library.resolve_dataset(root, "../escape") is None
    assert dataset_library.list_datasets(tmp_path / "missing") == []


def test_import_image_dataset_caps_and_isolates_eval(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    dataset_id = build_image_dataset(root)
    service, info = make_project(tmp_path, "general_image_classifier")
    _, dataset_dir = dataset_library.resolve_dataset(root, dataset_id)

    summary = service.import_platform_dataset(info, "image_classifier", dataset_dir, "light")

    assert summary["class_counts"] == {"cat": 5, "dog": 5}
    folders = service.image_folders(info.project_id)
    assert set(folders) == {"cat", "dog"}
    assert all(len(list(folder.glob("*"))) == 5 for folder in folders.values())

    # eval lives outside dataset/ so export never sees it and it never trains
    eval_dir = service.eval_dir(info.project_id)
    assert eval_dir.is_dir()
    assert "dataset_eval" not in {p.name for p in service.dataset_dir(info.project_id).iterdir()}
    assert service.eval_count(info) == 6


def test_import_image_respects_per_class_cap(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    dataset_id = build_image_dataset(root)
    service, info = make_project(tmp_path, "general_image_classifier")
    _, dataset_dir = dataset_library.resolve_dataset(root, dataset_id)

    # cap below the 5-per-class available should clip each class
    service.import_image_dataset(info, dataset_dir, 2)
    counts = service.dataset_summary(info, "image")["class_counts"]
    assert counts == {"cat": 2, "dog": 2}


def test_import_text_then_train_and_sample_eval(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    dataset_id = build_text_dataset(root)
    service, info = make_project(tmp_path, "general_text_classifier")
    _, dataset_dir = dataset_library.resolve_dataset(root, dataset_id)

    summary = service.import_platform_dataset(info, "text_classifier", dataset_dir, "standard")
    assert summary["class_counts"] == {"正面": 2, "负面": 2}
    assert summary["eval_count"] == 1

    service.train(info, "text_classifier", None)
    sample = service.sample_eval_predict(info, "text_classifier")
    assert sample["kind"] == "text"
    assert sample["true_label"] == "正面"
    assert "label" in sample["prediction"]


def test_sample_eval_without_import_raises(tmp_path: Path) -> None:
    service, info = make_project(tmp_path, "general_text_classifier")
    with pytest.raises(MLDataError):
        service.sample_eval_predict(info, "text_classifier")


def test_unsupported_capability_rejected(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    dataset_id = build_image_dataset(root)
    service, info = make_project(tmp_path, "general_image_classifier")
    _, dataset_dir = dataset_library.resolve_dataset(root, dataset_id)
    with pytest.raises(MLDataError):
        service.import_platform_dataset(info, "qa_retrieval", dataset_dir, "standard")


def build_wide_image_dataset(root: Path, per_class: int = 12) -> str:
    """One class 'a' with many distinct-content images, for sampling tests."""
    dataset = root / DIRECT / "图像分类" / "宽数据"
    folder = dataset / "train" / "a"
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(per_class):
        # unique color per image => unique bytes, so copies are distinguishable
        (folder / f"a{i}.png").write_bytes(_png((i * 17 % 256, i * 7 % 256, i * 3 % 256)))
    (dataset / "platform_dataset.json").write_text(
        json.dumps(
            {
                "id": "wide-001",
                "title": "宽数据",
                "ai_capability": "image_classifier",
                "labels": ["a"],
                "train_count": per_class,
                "test_count": 0,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return "wide-001"


def test_reimport_replaces_instead_of_appending(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    dataset_id = build_image_dataset(root)
    service, info = make_project(tmp_path, "general_image_classifier")
    _, dataset_dir = dataset_library.resolve_dataset(root, dataset_id)

    service.import_image_dataset(info, dataset_dir, 3)
    service.import_image_dataset(info, dataset_dir, 3)  # second import must not stack
    counts = service.dataset_summary(info, "image")["class_counts"]
    assert counts == {"cat": 3, "dog": 3}


def test_capped_import_samples_randomly(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    dataset_id = build_wide_image_dataset(root, per_class=12)
    service, info = make_project(tmp_path, "general_image_classifier")
    _, dataset_dir = dataset_library.resolve_dataset(root, dataset_id)

    seen: set[bytes] = set()
    for _ in range(6):
        service.import_image_dataset(info, dataset_dir, 3)
        folder = service.image_folders(info.project_id)["a"]
        files = list(folder.glob("*"))
        assert len(files) == 3  # replace semantics: always exactly the cap
        seen.update(path.read_bytes() for path in files)
    # across several capped imports we should have drawn more than one fixed subset
    assert len(seen) > 3
