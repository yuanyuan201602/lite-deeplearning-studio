from pathlib import Path
import json
import subprocess
import sys
from zipfile import ZipFile

from app.models import GenerationRequest
from app.services.export_service import ExportService
from app.services.template_service import TemplateService
from app.services.workspace_service import WorkspaceService
from app.task_catalog import get_task
from app.task_catalog import list_competitions


def make_request() -> GenerationRequest:
    return GenerationRequest(
        competition_slug="smart_museum",
        task_slug="heritage_text_classifier",
        project_name="课堂演示",
        student_name="学生A",
        target_hardware="student_laptop",
        dataset_notes="使用三类非遗词语样例。",
        class_labels=["刺绣", "陶艺", "剪纸"],
    )


def test_workspace_service_creates_project_folders(tmp_path: Path) -> None:
    service = WorkspaceService(tmp_path)

    workspace = service.create_workspace(make_request())

    assert workspace.project_dir.exists()
    assert workspace.generated_dir.exists()
    assert workspace.exports_dir.exists()
    assert workspace.logs_dir.exists()
    assert workspace.metadata_path.exists()


def test_template_service_writes_required_files(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path).create_workspace(make_request())
    task = get_task("smart_museum", "heritage_text_classifier")
    assert task is not None

    files = TemplateService().render_task_files(workspace, task, make_request())

    relative_paths = {path.relative_to(workspace.generated_dir).as_posix() for path in files}
    assert {
        "README.md",
        "train.py",
        "predict.py",
        "run.py",
        "ai_runtime/core.py",
        "notebook.ipynb",
        "hardware/README.md",
        "requirements.txt",
        "docs/ai_validation.md",
        "speech/README.md",
        "speech/speech_output.py",
        "speech/voice_config.json",
    }.issubset(relative_paths)
    assert "课堂演示" in (workspace.generated_dir / "README.md").read_text()


def test_text_dataset_paste_overrides_sample_data(tmp_path: Path) -> None:
    request = GenerationRequest(
        competition_slug="smart_museum",
        task_slug="heritage_text_classifier",
        project_name="真实文本数据",
        student_name="学生A",
        target_hardware="student_laptop",
        dataset_notes="课堂采集的词语卡片。",
        class_labels=["戏剧", "技艺"],
        text_csv="text,label\n昆曲唱腔,戏剧\n陶瓷烧制,技艺\n",
    )
    workspace = WorkspaceService(tmp_path).create_workspace(request)
    task = get_task(request.competition_slug, request.task_slug)
    assert task is not None

    TemplateService().render_task_files(workspace, task, request)

    assert (
        workspace.generated_dir / "data_sample" / "text_samples.csv"
    ).read_text() == "text,label\n昆曲唱腔,戏剧\n陶瓷烧制,技艺\n"
    manifest = json.loads(
        (workspace.generated_dir / "data_sample" / "data_manifest.json").read_text()
    )
    assert manifest["data_origin"] == "user"
    assert manifest["source_files"] == ["data_sample/text_samples.csv"]


def test_qa_paste_accepts_tab_separated_pairs(tmp_path: Path) -> None:
    request = GenerationRequest(
        competition_slug="smart_museum",
        task_slug="heritage_qa_helper",
        project_name="真实问答数据",
        student_name="学生A",
        target_hardware="student_laptop",
        dataset_notes="手工整理的问答。",
        qa_text="什么是昆曲\t昆曲是传统戏剧。\n为什么保护非遗\t为了传承文化记忆。",
    )
    workspace = WorkspaceService(tmp_path).create_workspace(request)
    task = get_task(request.competition_slug, request.task_slug)
    assert task is not None

    TemplateService().render_task_files(workspace, task, request)

    qa_pairs = (workspace.generated_dir / "data_sample" / "qa_pairs.csv").read_text()
    assert "什么是昆曲,昆曲是传统戏剧。" in qa_pairs
    assert "为什么保护非遗,为了传承文化记忆。" in qa_pairs
    manifest = json.loads(
        (workspace.generated_dir / "data_sample" / "data_manifest.json").read_text()
    )
    assert manifest["data_origin"] == "user"


def test_ocr_text_fields_override_sample_case(tmp_path: Path) -> None:
    request = GenerationRequest(
        competition_slug="smart_museum",
        task_slug="heritage_ocr_typo",
        project_name="真实OCR数据",
        student_name="学生A",
        target_hardware="student_laptop",
        dataset_notes="现场知识卡片。",
        ocr_correct_text="保护为主抢救第一",
        ocr_observed_text="保护为王抢救第一",
    )
    workspace = WorkspaceService(tmp_path).create_workspace(request)
    task = get_task(request.competition_slug, request.task_slug)
    assert task is not None

    TemplateService().render_task_files(workspace, task, request)

    ocr_cases = (workspace.generated_dir / "data_sample" / "ocr_cases.csv").read_text()
    assert "ocr_card.png,保护为主抢救第一,保护为王抢救第一" in ocr_cases
    manifest = json.loads(
        (workspace.generated_dir / "data_sample" / "data_manifest.json").read_text()
    )
    assert manifest["data_origin"] == "user"


def test_export_service_creates_zip_with_required_files(tmp_path: Path) -> None:
    request = make_request()
    workspace = WorkspaceService(tmp_path).create_workspace(request)
    task = get_task("smart_museum", "heritage_text_classifier")
    assert task is not None
    TemplateService().render_task_files(workspace, task, request)

    export_path = ExportService().create_zip(workspace)

    assert export_path.exists()
    with ZipFile(export_path) as archive:
        names = set(archive.namelist())

    assert {
        "README.md",
        "train.py",
        "predict.py",
        "run.py",
        "ai_runtime/core.py",
        "notebook.ipynb",
        "hardware/README.md",
        "requirements.txt",
        "speech/README.md",
        "speech/speech_output.py",
        "speech/voice_config.json",
    }.issubset(names)


def test_every_catalog_task_exports_its_required_outputs(tmp_path: Path) -> None:
    for competition in list_competitions():
        for task in competition.tasks:
            request = GenerationRequest(
                competition_slug=competition.slug,
                task_slug=task.slug,
                project_name=f"{competition.title}-{task.title}",
                student_name="测试学生",
                target_hardware=task.suggested_hardware[0],
                dataset_notes="竞赛任务覆盖测试。",
                class_labels=["类别A", "类别B", "类别C"],
            )
            workspace = WorkspaceService(tmp_path).create_workspace(request)
            TemplateService().render_task_files(workspace, task, request)

            export_path = ExportService().create_zip(workspace)

            with ZipFile(export_path) as archive:
                names = set(archive.namelist())
            assert set(task.required_outputs).issubset(names)


def test_smart_museum_generates_dfrobot_tts_template(tmp_path: Path) -> None:
    request = make_request()
    workspace = WorkspaceService(tmp_path).create_workspace(request)
    task = get_task("smart_museum", "heritage_text_classifier")
    assert task is not None

    TemplateService().render_task_files(workspace, task, request)

    speech_output = (workspace.generated_dir / "speech" / "speech_output.py").read_text()
    speech_readme = (workspace.generated_dir / "speech" / "README.md").read_text()
    assert "DFRobot" in speech_readme
    assert "serial" in speech_output
    assert "speak" in speech_output


def test_unihiker_voice_tasks_generate_keyword_template(tmp_path: Path) -> None:
    request = GenerationRequest(
        competition_slug="future_creator",
        task_slug="primary_voice_image_interaction",
        project_name="行空板语音验证",
        student_name="学生A",
        target_hardware="student_laptop",
        dataset_notes="关键词语音互动。",
        class_labels=["开始导诊", "停止"],
    )
    workspace = WorkspaceService(tmp_path).create_workspace(request)
    task = get_task(request.competition_slug, request.task_slug)
    assert task is not None

    TemplateService().render_task_files(workspace, task, request)

    config = (workspace.generated_dir / "speech" / "voice_config.json").read_text()
    speech_output = (workspace.generated_dir / "speech" / "speech_output.py").read_text()
    assert "开始导诊" in config
    assert "unihiker" in speech_output
    assert "recognize_keyword" in speech_output


def test_generated_text_classifier_runs_training_and_prediction(tmp_path: Path) -> None:
    request = make_request()
    workspace = WorkspaceService(tmp_path).create_workspace(request)
    task = get_task("smart_museum", "heritage_text_classifier")
    assert task is not None
    TemplateService().render_task_files(workspace, task, request)

    result = subprocess.run(
        [sys.executable, "run.py"],
        cwd=workspace.generated_dir,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (workspace.generated_dir / "models" / "text_classifier.joblib").exists()
    assert (workspace.generated_dir / "outputs" / "predictions.json").exists()
    assert (workspace.generated_dir / "outputs" / "ai_validation_result.json").exists()


def test_generated_non_ocr_ai_tasks_run_locally(tmp_path: Path) -> None:
    for competition in list_competitions():
        for task in competition.tasks:
            if task.ai_capability == "ocr_typo_checker":
                continue
            request = GenerationRequest(
                competition_slug=competition.slug,
                task_slug=task.slug,
                project_name=f"{competition.title}-{task.title}",
                student_name="测试学生",
                target_hardware=task.suggested_hardware[0],
                dataset_notes="本地AI运行测试。",
                class_labels=["类别A", "类别B", "类别C"],
            )
            workspace = WorkspaceService(tmp_path).create_workspace(request)
            TemplateService().render_task_files(workspace, task, request)

            result = subprocess.run(
                [sys.executable, "run.py"],
                cwd=workspace.generated_dir,
                text=True,
                capture_output=True,
                check=False,
            )

            assert result.returncode == 0, result.stderr
            assert (workspace.generated_dir / "outputs" / "predictions.json").exists()
