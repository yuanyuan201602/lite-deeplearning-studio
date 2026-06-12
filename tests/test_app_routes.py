import math
import struct
import wave
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


def make_wav_bytes(frequency: float, duration: float = 0.5, rate: int = 16000) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        frames = bytearray()
        for index in range(int(duration * rate)):
            value = int(0.5 * 32767 * math.sin(2 * math.pi * frequency * index / rate))
            frames += struct.pack("<h", value)
        writer.writeframes(bytes(frames))
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


def test_homepage_shows_general_tasks_and_competition_entries(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/")

    assert "机器学习任务" in response.text
    assert "图像分类" in response.text
    assert "文本分类" in response.text
    assert "智能问答" in response.text
    assert "传感器决策" in response.text
    assert "/competition/smart_museum" in response.text
    assert "/competition/future_creator" in response.text


def test_competition_page_lists_competition_tasks(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/competition/smart_museum")

    assert response.status_code == 200
    assert "挑战三：非遗文化分类学览" in response.text
    assert "挑战一：认识非遗传承匠人" in response.text


def test_competition_page_respects_edition_and_hides_general(tmp_path: Path) -> None:
    client = make_client(tmp_path, edition="smart_museum")

    assert client.get("/competition/smart_museum").status_code == 200
    assert client.get("/competition/future_creator").status_code == 404
    assert client.get("/competition/general_ml").status_code == 404


def test_general_task_available_in_every_edition(tmp_path: Path) -> None:
    client = make_client(tmp_path, edition="smart_museum")

    response = client.get("/workflow/general_ml/general_text_classifier")

    assert response.status_code == 200
    assert "文本分类" in response.text


def test_general_task_project_full_flow(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(
        client, "general_ml", "general_text_classifier", "通用文本练习"
    )

    save = client.post(
        f"/api/projects/{project_id}/data/text",
        json={
            "samples": [
                {"text": "晴天 出门 散步", "label": "好天气"},
                {"text": "阳光 温暖 舒适", "label": "好天气"},
                {"text": "暴雨 打雷 进屋", "label": "坏天气"},
                {"text": "大风 降温 添衣", "label": "坏天气"},
            ]
        },
    )
    assert save.status_code == 200

    train = client.post(f"/api/projects/{project_id}/train")
    assert train.status_code == 200

    predict = client.post(f"/api/projects/{project_id}/predict", json={"text": "晴天 散步"})
    assert predict.status_code == 200
    assert predict.json()["label"] == "好天气"

    page = client.get("/")
    assert "通用文本练习" in page.text


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
    assert "挑战三：非遗文化分类学览" in response.text
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


def test_audio_project_upload_train_predict(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(
        client, "general_ml", "general_audio_classifier", "声音流程"
    )

    for label, frequency in (("低音", 220.0), ("高音", 880.0)):
        upload = client.post(
            f"/api/projects/{project_id}/data/audio",
            data={"label": label},
            files=[
                (
                    "files",
                    (f"{index}.wav", make_wav_bytes(frequency * (1 + 0.03 * index)), "audio/wav"),
                )
                for index in range(2)
            ],
        )
        assert upload.status_code == 200

    state = client.get(f"/api/projects/{project_id}/state").json()
    assert state["dataset"]["class_counts"] == {"低音": 2, "高音": 2}

    train = client.post(f"/api/projects/{project_id}/train")
    assert train.status_code == 200

    predict = client.post(
        f"/api/projects/{project_id}/predict/audio",
        files={"file": ("probe.wav", make_wav_bytes(900.0), "audio/wav")},
    )
    assert predict.status_code == 200
    assert predict.json()["label"] == "高音"


def test_audio_upload_rejects_non_wav(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "general_ml", "general_audio_classifier", "格式校验")

    upload = client.post(
        f"/api/projects/{project_id}/data/audio",
        data={"label": "低音"},
        files=[("files", ("clip.mp3", b"fake-mp3", "audio/mpeg"))],
    )

    assert upload.status_code == 400
    assert "WAV" in upload.json()["detail"]


def test_train_accepts_classifier_choice_and_state_lists_choices(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "smart_museum", "heritage_text_classifier", "模型选择")

    state = client.get(f"/api/projects/{project_id}/state").json()
    slugs = [choice["slug"] for choice in state["model_choices"]]
    assert slugs == ["logistic_regression", "naive_bayes", "random_forest"]
    assert all("principle" in choice and "best_for" in choice for choice in state["model_choices"])

    client.post(
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

    train = client.post(
        f"/api/projects/{project_id}/train", json={"classifier": "naive_bayes"}
    )
    assert train.status_code == 200
    assert train.json()["report"]["model_choice"] == "naive_bayes"

    bad = client.post(f"/api/projects/{project_id}/train", json={"classifier": "gpt4"})
    assert bad.status_code == 400
    assert "可选" in bad.json()["detail"]


def test_train_compare_returns_rows_for_all_models(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(
        client, "future_creator", "sensor_decision_template", "模型对比"
    )
    client.post(
        f"/api/projects/{project_id}/data/sensor",
        json={
            "csv": "体温,距离,动作\n38.6,12,提醒\n36.7,45,观察\n37.8,20,提醒\n36.5,60,观察\n39.0,9,提醒\n36.4,70,观察"
        },
    )

    response = client.post(f"/api/projects/{project_id}/train/compare")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert [row["model_choice"] for row in rows] == ["decision_tree", "random_forest", "knn"]
    assert all(row["cross_val_accuracy"] is not None for row in rows)

    # Compare must not persist a model: training step still required.
    state = client.get(f"/api/projects/{project_id}/state").json()
    assert state["project"]["train_report"] is None


def test_train_compare_without_data_returns_friendly_400(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "smart_museum", "heritage_text_classifier", "空对比")

    response = client.post(f"/api/projects/{project_id}/train/compare")

    assert response.status_code == 400
    assert "准备数据" in response.json()["detail"]


def test_export_without_training_returns_friendly_400(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "smart_museum", "heritage_text_classifier", "未训练导出")

    response = client.post(f"/api/projects/{project_id}/export")

    assert response.status_code == 400
    assert "训练模型" in response.json()["detail"]


def test_sensor_save_accepts_fullwidth_commas_and_validates_early(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(
        client, "future_creator", "sensor_decision_template", "传感器校验"
    )

    fullwidth = client.post(
        f"/api/projects/{project_id}/data/sensor",
        json={
            "csv": "体温，距离，动作\n38.6，12，提醒\n36.7，45，观察\n37.8，20，提醒\n36.5，60，观察"
        },
    )
    assert fullwidth.status_code == 200

    train = client.post(f"/api/projects/{project_id}/train")
    assert train.status_code == 200

    header_only = client.post(
        f"/api/projects/{project_id}/data/sensor",
        json={"csv": "体温,距离,动作"},
    )
    assert header_only.status_code == 400
    assert "数据太少" in header_only.json()["detail"]


def test_create_project_with_spaces_only_name_returns_422(tmp_path: Path) -> None:
    response = make_client(tmp_path).post(
        "/projects",
        data={
            "competition_slug": "smart_museum",
            "task_slug": "heritage_text_classifier",
            "project_name": "   ",
        },
    )

    assert response.status_code == 422


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


def test_collect_page_renders(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "smart_museum", "heritage_text_classifier", "采集测试")

    response = client.get(f"/collect/{project_id}")

    assert response.status_code == 200
    assert "collect-state" in response.text
    assert "采集数据" in response.text


def test_collect_page_404_on_missing_project(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    assert client.get("/collect/nonexistent").status_code == 404


def test_data_packs_list_returns_array(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.get("/api/data-packs")

    assert response.status_code == 200
    packs = response.json()
    assert isinstance(packs, list)
    assert len(packs) > 0
    first = packs[0]
    assert "capability" in first
    assert "file" in first
    assert "name" in first


def test_load_text_pack_saves_samples(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "smart_museum", "heritage_text_classifier", "文本包测试")

    response = client.post(
        f"/api/projects/{project_id}/data/pack",
        json={"pack_file": "smart_museum_text.json"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["dataset"]["sample_count"] > 0


def test_load_sensor_pack_saves_csv(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "general_ml", "general_sensor_decision", "传感器包测试")

    response = client.post(
        f"/api/projects/{project_id}/data/pack",
        json={"pack_file": "general_sensor_health.json"},
    )

    assert response.status_code == 200
    assert response.json()["dataset"]["sample_count"] > 0


def test_load_image_task_pack_returns_400(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    project_id = create_project(client, "smart_museum", "heritage_face_intro", "图像任务卡测试")

    response = client.post(
        f"/api/projects/{project_id}/data/pack",
        json={"pack_file": "smart_museum_image_task.json"},
    )

    assert response.status_code == 400
    assert "采集助手" in response.json()["detail"]
