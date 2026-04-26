from pathlib import Path
from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import create_app


def test_homepage_shows_competitions(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "智能博物" in response.text
    assert "优创未来" in response.text


def test_smart_museum_edition_only_shows_smart_museum(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path, edition="smart_museum"))

    response = client.get("/")

    assert response.status_code == 200
    assert "智能博物轻量版" in response.text
    assert "智能博物" in response.text
    assert "优创未来" not in response.text
    assert client.get("/workflow/future_creator/image_recognition_starter").status_code == 404


def test_future_creator_edition_only_shows_future_creator(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path, edition="future_creator"))

    response = client.get("/")

    assert response.status_code == 200
    assert "优创未来轻量版" in response.text
    assert "优创未来" in response.text
    assert "智能博物" not in response.text
    assert client.get("/workflow/smart_museum/heritage_text_classifier").status_code == 404


def test_workflow_page_shows_task_form(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path))

    response = client.get("/workflow/smart_museum/heritage_text_classifier")

    assert response.status_code == 200
    assert "非遗词语分类工作流" in response.text
    assert "生成任务包" in response.text


def test_generate_creates_export_package(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path))

    response = client.post(
        "/generate",
        data={
            "competition_slug": "future_creator",
            "task_slug": "image_recognition_starter",
            "project_name": "图像识别演示",
            "student_name": "学生B",
            "target_hardware": "unihiker_m10",
            "dataset_notes": "三类校园图片。",
            "class_labels": "教室,操场,图书馆",
        },
    )

    assert response.status_code == 200
    assert "任务包已生成" in response.text
    assert ".zip" in response.text
    assert "下载任务包" in response.text


def test_generate_accepts_sensor_csv_and_marks_user_data(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path))

    response = client.post(
        "/generate",
        data={
            "competition_slug": "future_creator",
            "task_slug": "sensor_decision_template",
            "project_name": "传感器真实数据",
            "student_name": "学生B",
            "target_hardware": "unihiker_m10",
            "dataset_notes": "现场采集的医疗提醒数据。",
            "sensor_csv": (
                "temperature,distance,signal,action\n"
                "38.6,12,1,提醒就诊\n"
                "36.7,45,0,继续观察\n"
            ),
        },
    )

    assert response.status_code == 200
    assert "data_origin：user" in response.text
    marker = "/exports/"
    start = response.text.index(marker)
    end = response.text.index('"', start)
    download_url = response.text[start:end]
    export_response = client.get(download_url)
    with ZipFile(BytesIO(export_response.content)) as archive:
        manifest = archive.read("data_sample/data_manifest.json").decode()
        sensor_samples = archive.read("data_sample/sensor_samples.csv").decode()
    assert '"data_origin": "user"' in manifest
    assert "38.6,12,1,提醒就诊" in sensor_samples


def test_unknown_workflow_returns_404(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path))

    response = client.get("/workflow/missing/task")

    assert response.status_code == 404


def test_export_download_returns_zip(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path))
    response = client.post(
        "/generate",
        data={
            "competition_slug": "smart_museum",
            "task_slug": "heritage_text_classifier",
            "project_name": "下载验证",
            "student_name": "学生C",
            "target_hardware": "student_laptop",
            "dataset_notes": "三类词语。",
            "class_labels": "刺绣,陶艺,剪纸",
        },
    )
    marker = "/exports/"
    start = response.text.index(marker)
    end = response.text.index('"', start)
    download_url = response.text[start:end]

    download_response = client.get(download_url)

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/zip"
    assert download_response.content.startswith(b"PK")
