from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app


def make_client(tmp_path: Path, edition: str | None = None) -> TestClient:
    return TestClient(create_app(workspace_root=tmp_path, edition=edition))


def make_image_bytes(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (48, 48), color).save(buffer, format="PNG")
    return buffer.getvalue()


def create_project(client: TestClient, competition: str, task: str, name: str) -> str:
    response = client.post(
        "/projects",
        data={
            "competition_slug": competition,
            "task_slug": task,
            "project_name": name,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response.headers["location"].rsplit("/", 1)[-1]


def test_homepage_shows_competitions_and_school(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/")

    assert response.status_code == 200
    assert "智能博物" in response.text
    assert "优创未来" in response.text
    assert "南昌市第二十三中学" in response.text
    assert "logo.svg" in response.text


def test_smart_museum_edition_only_shows_smart_museum(tmp_path: Path) -> None:
    client = make_client(tmp_path, edition="smart_museum")

    response = client.get("/")

    assert response.status_code == 200
    assert "智能博物轻量版" in response.text
    assert "优创未来" not in response.text
    assert client.get("/workflow/future_creator/image_recognition_starter").status_code == 404


def test_future_creator_edition_only_shows_future_creator(tmp_path: Path) -> None:
    client = make_client(tmp_path, edition="future_creator")

    response = client.get("/")

    assert response.status_code == 200
    assert "优创未来轻量版" in response.text
    assert "智能博物" not in response.text
    assert client.get("/workflow/smart_museum/heritage_text_classifier").status_code == 404


def test_workflow_page_shows_create_form(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/workflow/smart_museum/heritage_text_classifier")

    assert response.status_code == 200
    assert "非遗词语分类工作流" in response.text
    assert "创建项目" in response.text


def test_create_project_redirects_to_project_page(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    project_id = create_project(
        client, "smart_museum", "heritage_text_classifier", "我的分类器"
    )

    page = client.get(f"/project/{project_id}")
    assert page.status_code == 200
    assert "我的分类器" in page.text
    assert "initial-state" in page.text


def test_create_project_with_blank_name_returns_422(tmp_path: Path) -> None:
    response = make_client(tmp_path).post(
        "/projects",
        data={
            "competition_slug": "smart_museum",
            "task_slug": "heritage_text_classifier",
            "project_name": "",
        },
    )

    assert response.status_code == 422


def test_text_project_full_flow(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "smart_museum", "heritage_text_classifier", "文本流程")

    save = client.post(
        f"/api/projects/{project_id}/data/text",
        json={
            "samples": [
                {"text": "昆曲 唱腔 舞台", "label": "戏剧"},
                {"text": "梨园戏 地方 剧目", "label": "戏剧"},
                {"text": "德化瓷 烧制 窑炉", "label": "技艺"},
                {"text": "蜡染 染布 图案", "label": "技艺"},
            ]
        },
    )
    assert save.status_code == 200
    assert save.json()["dataset"]["sample_count"] == 4

    train = client.post(f"/api/projects/{project_id}/train")
    assert train.status_code == 200
    assert train.json()["report"]["train_accuracy"] == 1.0

    predict = client.post(f"/api/projects/{project_id}/predict", json={"text": "昆曲 舞台"})
    assert predict.status_code == 200
    assert predict.json()["label"] == "戏剧"

    export = client.post(f"/api/projects/{project_id}/export")
    assert export.status_code == 200
    download = client.get(export.json()["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
    with ZipFile(BytesIO(download.content)) as archive:
        names = set(archive.namelist())
    assert "models/text_classifier.joblib" in names
    assert "train.py" in names
    assert "data_sample/text_samples.csv" in names


def test_image_project_upload_train_predict(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(
        client, "future_creator", "image_recognition_starter", "图像流程"
    )

    for label, color in (("红色卡片", (220, 60, 60)), ("绿色卡片", (60, 170, 90))):
        upload = client.post(
            f"/api/projects/{project_id}/data/images",
            data={"label": label},
            files=[
                ("files", (f"{index}.png", make_image_bytes(color), "image/png"))
                for index in range(2)
            ],
        )
        assert upload.status_code == 200

    state = client.get(f"/api/projects/{project_id}/state").json()
    assert state["dataset"]["class_counts"] == {"红色卡片": 2, "绿色卡片": 2}

    train = client.post(f"/api/projects/{project_id}/train")
    assert train.status_code == 200

    predict = client.post(
        f"/api/projects/{project_id}/predict/image",
        files={"file": ("probe.png", make_image_bytes((215, 65, 62)), "image/png")},
    )
    assert predict.status_code == 200
    assert predict.json()["label"] == "红色卡片"


def test_train_without_data_returns_friendly_400(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "smart_museum", "heritage_text_classifier", "空项目")

    response = client.post(f"/api/projects/{project_id}/train")

    assert response.status_code == 400
    assert "准备数据" in response.json()["detail"]


def test_unknown_project_and_workflow_return_404(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    assert client.get("/workflow/missing/task").status_code == 404
    assert client.get("/project/missing").status_code == 404
    assert client.get("/api/projects/missing/state").status_code == 404


def test_homepage_lists_recent_projects(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    create_project(client, "smart_museum", "heritage_text_classifier", "最近项目甲")

    response = client.get("/")

    assert "继续我的项目" in response.text
    assert "最近项目甲" in response.text
