import json
import math
import struct
import subprocess
import sys
import wave
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

from app.models import GenerationRequest, ProjectCreateRequest, ProjectInfo
from app.services.export_service import ExportService
from app.services.project_service import ProjectService
from app.task_catalog import get_task, list_competitions


def make_project(
    tmp_path: Path,
    competition: str = "smart_museum",
    task: str = "heritage_text_classifier",
    name: str = "课堂演示",
) -> tuple[ProjectService, ProjectInfo]:
    service = ProjectService(tmp_path)
    info = service.create_project(
        ProjectCreateRequest(
            competition_slug=competition,
            task_slug=task,
            project_name=name,
            student_name="学生A",
        )
    )
    return service, info


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


TEXT_SAMPLES = [
    {"text": "昆曲 唱腔 舞台", "label": "戏剧"},
    {"text": "梨园戏 地方 剧目", "label": "戏剧"},
    {"text": "德化瓷 烧制 窑炉", "label": "技艺"},
    {"text": "蜡染 染布 图案", "label": "技艺"},
]


def test_project_service_creates_folders_and_metadata(tmp_path: Path) -> None:
    service, info = make_project(tmp_path)

    project_dir = service.project_dir(info.project_id)
    for folder in ("dataset", "models", "generated", "exports", "logs"):
        assert (project_dir / folder).is_dir()
    reloaded = service.get_project(info.project_id)
    assert reloaded is not None
    assert reloaded.project_name == "课堂演示"


def test_export_trained_text_project_bundles_model_and_data(tmp_path: Path) -> None:
    service, info = make_project(tmp_path)
    service.save_text_samples(info, TEXT_SAMPLES)
    service.train(info, "text_classifier")
    task = get_task("smart_museum", "heritage_text_classifier")
    assert task is not None

    export_path, _ = ExportService().export_project(info, task, service)

    with ZipFile(export_path) as archive:
        names = set(archive.namelist())
        text_csv = archive.read("data_sample/text_samples.csv").decode()
        manifest = json.loads(archive.read("data_sample/data_manifest.json").decode())
    assert "models/text_classifier.joblib" in names
    assert "models/model_meta.json" in names
    assert "昆曲 唱腔 舞台,戏剧" in text_csv
    assert manifest["data_origin"] == "user"


def test_exported_predict_runs_with_bundled_model_without_training(tmp_path: Path) -> None:
    service, info = make_project(tmp_path)
    service.save_text_samples(info, TEXT_SAMPLES)
    service.train(info, "text_classifier")
    task = get_task("smart_museum", "heritage_text_classifier")
    assert task is not None
    ExportService().export_project(info, task, service)
    generated_dir = service.workspace(info).generated_dir

    result = subprocess.run(
        [sys.executable, "predict.py"],
        cwd=generated_dir,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    predictions = json.loads(
        (generated_dir / "outputs" / "predictions.json").read_text(encoding="utf-8")
    )
    assert predictions


def test_export_image_project_includes_student_images(tmp_path: Path) -> None:
    service, info = make_project(
        tmp_path, "future_creator", "image_recognition_starter", "图像导出"
    )
    for label, color in (("红色卡片", (220, 60, 60)), ("绿色卡片", (60, 170, 90))):
        service.add_images(
            info, label, [(f"{index}.png", make_image_bytes(color)) for index in range(2)]
        )
    service.train(info, "image_classifier")
    task = get_task("future_creator", "image_recognition_starter")
    assert task is not None

    export_path, _ = ExportService().export_project(info, task, service)

    with ZipFile(export_path) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("data_sample/data_manifest.json").decode())
    image_files = [name for name in names if name.startswith("data_sample/images/")]
    assert len(image_files) == 4
    assert manifest["data_origin"] == "user"
    assert "models/image_classifier.joblib" in names


def test_export_sensor_project_keeps_student_columns_and_runs(tmp_path: Path) -> None:
    service, info = make_project(
        tmp_path, "future_creator", "sensor_decision_template", "传感器导出"
    )
    service.save_sensor_csv(
        info,
        "心率,体温,动作\n110,38.6,提醒就诊\n72,36.5,继续观察\n118,39.2,提醒就诊\n68,36.8,继续观察\n",
    )
    service.train(info, "sensor_decision_model")
    task = get_task("future_creator", "sensor_decision_template")
    assert task is not None
    ExportService().export_project(info, task, service)
    generated_dir = service.workspace(info).generated_dir

    sensor_csv = (generated_dir / "data_sample" / "sensor_samples.csv").read_text()
    assert sensor_csv.startswith("心率,体温,动作")

    result = subprocess.run(
        [sys.executable, "run.py"],
        cwd=generated_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_export_image_project_bundles_embedder_and_predicts(tmp_path: Path) -> None:
    from app.ml import pretrained

    if not pretrained.has_image_embedder():
        import pytest

        pytest.skip("pretrained embedder not downloaded")

    service, info = make_project(
        tmp_path, "future_creator", "image_recognition_starter", "迁移学习导出"
    )
    for label, color in (("红色卡片", (220, 60, 60)), ("绿色卡片", (60, 170, 90))):
        service.add_images(
            info, label, [(f"{index}.png", make_image_bytes(color)) for index in range(2)]
        )
    service.train(info, "image_classifier")
    assert info.train_report["feature_mode"] == "mobilenet_v2"
    task = get_task("future_creator", "image_recognition_starter")
    assert task is not None

    export_path, _ = ExportService().export_project(info, task, service)

    with ZipFile(export_path) as archive:
        names = set(archive.namelist())
    assert "models/pretrained/mobilenetv2.onnx" in names
    assert "models/image_classifier.joblib" in names

    # The exported predict.py must reproduce the embedding features (key invariant).
    generated_dir = service.workspace(info).generated_dir
    result = subprocess.run(
        [sys.executable, "predict.py"],
        cwd=generated_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    predictions = json.loads(
        (generated_dir / "outputs" / "predictions.json").read_text(encoding="utf-8")
    )
    assert {entry["prediction"] for entry in predictions} <= {"红色卡片", "绿色卡片"}


def test_export_audio_project_bundles_model_and_predicts(tmp_path: Path) -> None:
    service, info = make_project(
        tmp_path, "general_ml", "general_audio_classifier", "声音导出"
    )
    for label, frequency in (("低音", 220.0), ("高音", 880.0)):
        service.add_audio_clips(
            info,
            label,
            [
                (f"{index}.wav", make_wav_bytes(frequency * (1 + 0.03 * index)))
                for index in range(2)
            ],
        )
    service.train(info, "audio_classifier")
    task = get_task("general_ml", "general_audio_classifier")
    assert task is not None

    export_path, _ = ExportService().export_project(info, task, service)

    with ZipFile(export_path) as archive:
        names = set(archive.namelist())
    assert "models/audio_classifier.joblib" in names
    audio_files = [name for name in names if name.startswith("data_sample/audio/")]
    assert len(audio_files) == 4

    # The exported predict.py must load the in-app trained model (key invariant).
    generated_dir = service.workspace(info).generated_dir
    result = subprocess.run(
        [sys.executable, "predict.py"],
        cwd=generated_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    predictions = json.loads(
        (generated_dir / "outputs" / "predictions.json").read_text(encoding="utf-8")
    )
    assert predictions
    assert {entry["prediction"] for entry in predictions} <= {"低音", "高音"}


def test_audio_template_trains_and_runs_on_sample_data(tmp_path: Path) -> None:
    service, info = make_project(
        tmp_path, "general_ml", "general_audio_classifier", "声音样例"
    )
    task = get_task("general_ml", "general_audio_classifier")
    assert task is not None
    ExportService().export_project(info, task, service)
    generated_dir = service.workspace(info).generated_dir

    result = subprocess.run(
        [sys.executable, "run.py"],
        cwd=generated_dir,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (generated_dir / "outputs" / "predictions.json").exists()


def test_every_catalog_task_exports_required_outputs_without_training(tmp_path: Path) -> None:
    for competition in list_competitions():
        for task in competition.tasks:
            service, info = make_project(
                tmp_path, competition.slug, task.slug, f"覆盖-{task.slug}"
            )

            export_path, _ = ExportService().export_project(info, task, service)

            with ZipFile(export_path) as archive:
                names = set(archive.namelist())
            assert set(task.required_outputs).issubset(names), task.slug


def test_generated_non_ocr_tasks_run_locally_on_sample_data(tmp_path: Path) -> None:
    for competition in list_competitions():
        for task in competition.tasks:
            if task.ai_capability == "ocr_typo_checker":
                continue
            service, info = make_project(
                tmp_path, competition.slug, task.slug, f"运行-{task.slug}"
            )
            ExportService().export_project(info, task, service)
            generated_dir = service.workspace(info).generated_dir

            result = subprocess.run(
                [sys.executable, "run.py"],
                cwd=generated_dir,
                text=True,
                capture_output=True,
                check=False,
            )

            assert result.returncode == 0, f"{task.slug}: {result.stderr}"
            assert (generated_dir / "outputs" / "predictions.json").exists()


def test_smart_museum_export_keeps_dfrobot_tts_template(tmp_path: Path) -> None:
    service, info = make_project(tmp_path)
    task = get_task("smart_museum", "heritage_text_classifier")
    assert task is not None

    ExportService().export_project(info, task, service)

    generated_dir = service.workspace(info).generated_dir
    speech_output = (generated_dir / "speech" / "speech_output.py").read_text()
    speech_readme = (generated_dir / "speech" / "README.md").read_text()
    assert "DFRobot" in speech_readme
    assert "serial" in speech_output
    assert "speak" in speech_output


def test_unihiker_voice_tasks_keep_keyword_template(tmp_path: Path) -> None:
    service, info = make_project(
        tmp_path, "future_creator", "primary_voice_image_interaction", "行空板语音验证"
    )
    task = get_task("future_creator", "primary_voice_image_interaction")
    assert task is not None

    ExportService().export_project(info, task, service)

    generated_dir = service.workspace(info).generated_dir
    speech_output = (generated_dir / "speech" / "speech_output.py").read_text()
    assert "unihiker" in speech_output
    assert "recognize_keyword" in speech_output


def test_build_generation_request_collects_dataset_fields(tmp_path: Path) -> None:
    service, info = make_project(tmp_path)
    service.save_text_samples(info, TEXT_SAMPLES)
    task = get_task("smart_museum", "heritage_text_classifier")
    assert task is not None

    request = ExportService().build_generation_request(info, task, service)

    assert isinstance(request, GenerationRequest)
    assert request.class_labels == ["戏剧", "技艺"]
    assert "昆曲 唱腔 舞台,戏剧" in request.text_csv
