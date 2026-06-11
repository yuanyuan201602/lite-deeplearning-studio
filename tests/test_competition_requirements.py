import subprocess
import sys

from app.models import ProjectCreateRequest
from app.services.export_service import ExportService
from app.services.project_service import ProjectService
from app.task_catalog import get_task, list_competitions


def test_smart_museum_catalog_covers_pdf_challenges() -> None:
    smart_museum = next(
        competition for competition in list_competitions() if competition.slug == "smart_museum"
    )

    task_slugs = {task.slug for task in smart_museum.tasks}

    assert {
        "heritage_face_intro",
        "heritage_ocr_typo",
        "heritage_text_classifier",
        "heritage_sentence_classifier",
        "heritage_qa_helper",
    }.issubset(task_slugs)


def test_future_creator_catalog_covers_group_requirements() -> None:
    future_creator = next(
        competition for competition in list_competitions() if competition.slug == "future_creator"
    )

    groups = {task.group for task in future_creator.tasks}

    assert {"小学组", "初中组", "高中组（含中职）", "创意应用"}.issubset(groups)


def test_generated_checklist_mentions_pdf_submission_requirements(tmp_path) -> None:
    service = ProjectService(tmp_path)
    info = service.create_project(
        ProjectCreateRequest(
            competition_slug="future_creator",
            task_slug="senior_llm_vision_motion",
            project_name="高中组验证",
            student_name="学生D",
            dataset_notes="现场卡片和夹取任务。",
        )
    )
    task = get_task("future_creator", "senior_llm_vision_motion")
    assert task is not None

    ExportService().export_project(info, task, service)

    generated_dir = service.workspace(info).generated_dir
    checklist = (generated_dir / "docs" / "competition_checklist.md").read_text()
    submission = (generated_dir / "submission" / "README.md").read_text()
    assert "大模型" in checklist
    assert "机械装置" in checklist
    assert "AI 能力：image_classifier" in checklist
    assert "本轮暂停能力" in checklist
    assert "创作说明" in submission
    assert "演示视频" in submission
    assert "实物照片" in submission


def test_acceptance_script_documents_web_check_option() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/acceptance_check.py", "--help"],
        text=True,
        capture_output=True,
        check=True,
    )

    assert "--with-web" in result.stdout
    assert "--edition" in result.stdout
