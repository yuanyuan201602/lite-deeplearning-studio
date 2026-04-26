from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import create_app  # noqa: E402
from app.models import GenerationRequest, TaskDefinition  # noqa: E402
from app.services.export_service import ExportService  # noqa: E402
from app.services.template_service import TemplateService  # noqa: E402
from app.services.workspace_service import WorkspaceService  # noqa: E402
from app.task_catalog import list_competitions  # noqa: E402

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


PLATFORM_REQUIREMENT_KEYWORDS = {
    "smart_museum": [
        "人脸",
        "错别字",
        "自建文本分类模型",
        "挑战完成",
        "创作说明",
        "演示视频",
    ],
    "future_creator": [
        "语音互动",
        "图像识别",
        "视觉模型训练",
        "大模型",
        "机械装置",
        "创作说明",
        "演示视频",
        "实物照片",
    ],
}

REQUIRED_EXPORT_FILES = {
    "README.md",
    "run.py",
    "notebook.ipynb",
    "requirements.txt",
    "hardware/README.md",
    "submission/README.md",
    "docs/competition_checklist.md",
    "data_sample/sample_input.txt",
    "speech/README.md",
    "speech/speech_output.py",
    "speech/voice_config.json",
}

DOWNLOAD_HREF_RE = re.compile(r'href="(?P<url>/exports/[^"]+\.zip)"')


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run generated package acceptance checks and optional web workflow checks."
    )
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--require-ai", action="store_true")
    parser.add_argument(
        "--edition",
        choices=["all", "smart_museum", "future_creator"],
        default="all",
        help="Only validate one independent app edition.",
    )
    parser.add_argument(
        "--with-web",
        action="store_true",
        help="Also check homepage, task pages, form generation, and zip downloads.",
    )
    parser.add_argument("--keep-output", action="store_true")
    args = parser.parse_args()

    report: dict[str, object] = {
        "rounds": args.rounds,
        "require_ai": args.require_ai,
        "with_web": args.with_web,
        "edition": args.edition,
        "checks": [],
    }
    temp_dir = Path(tempfile.mkdtemp(prefix="lds-acceptance-"))
    failures: list[str] = []

    try:
        for round_index in range(1, args.rounds + 1):
            round_root = temp_dir / f"round-{round_index}"
            failures.extend(
                run_round(
                    round_index,
                    round_root,
                    report,
                    require_ai=args.require_ai,
                    edition=args.edition,
                )
            )

        if args.with_web:
            failures.extend(run_web_checks(temp_dir / "web", report, edition=args.edition))

        report_path = Path("docs/acceptance-test-report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        if failures:
            print("ACCEPTANCE FAILED")
            for failure in failures:
                print(f"- {failure}")
            print(f"Report: {report_path}")
            return 1

        print(f"ACCEPTANCE PASSED: {args.rounds} rounds")
        if args.with_web:
            print("WEB CHECKS PASSED")
        print(f"Report: {report_path}")
        return 0
    finally:
        if args.keep_output:
            print(f"Kept temp output: {temp_dir}")
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_round(
    round_index: int,
    round_root: Path,
    report: dict[str, object],
    require_ai: bool,
    edition: str,
) -> list[str]:
    failures: list[str] = []
    workspace_service = WorkspaceService(round_root)
    template_service = TemplateService()
    export_service = ExportService()

    platform_text_by_competition: dict[str, list[str]] = {}
    for competition in list_competitions(edition):
        platform_text_by_competition.setdefault(competition.slug, [])
        for task in competition.tasks:
            request = GenerationRequest(
                competition_slug=competition.slug,
                task_slug=task.slug,
                project_name=f"验收第{round_index}轮-{competition.title}-{task.title}",
                student_name="验收学生",
                target_hardware=task.suggested_hardware[0],
                dataset_notes="按照竞赛文件进行自动验收。",
                class_labels=["类别A", "类别B", "类别C"],
            )
            workspace = workspace_service.create_workspace(request)
            template_service.render_task_files(workspace, task, request)
            export_path = export_service.create_zip(workspace)

            check = {
                "round": round_index,
                "competition": competition.slug,
                "task": task.slug,
                "export_path": str(export_path),
                "passed": True,
                "failures": [],
            }
            task_failures, exported_text = validate_export(export_path, competition.slug, task)
            platform_text_by_competition[competition.slug].append(exported_text)
            task_failures.extend(
                run_generated_script(
                    workspace.generated_dir,
                    task.ai_capability,
                    require_ai=require_ai,
                )
            )

            if task_failures:
                check["passed"] = False
                check["failures"] = task_failures
                failures.extend(task_failures)
            report["checks"].append(check)
    failures.extend(validate_platform_coverage(round_index, platform_text_by_competition, report))
    return failures


def validate_export(
    export_path: Path,
    competition_slug: str,
    task: TaskDefinition,
) -> tuple[list[str], str]:
    failures: list[str] = []
    if not export_path.is_file():
        return [f"{competition_slug}/{task.slug}: export zip missing"], ""

    with ZipFile(export_path) as archive:
        names = set(archive.namelist())
        missing = REQUIRED_EXPORT_FILES - names
        if missing:
            failures.append(f"{competition_slug}/{task.slug}: missing files {sorted(missing)}")
        readme = archive.read("README.md").decode("utf-8")
        checklist = archive.read("docs/competition_checklist.md").decode("utf-8")
        submission = archive.read("submission/README.md").decode("utf-8")
        speech_readme = archive.read("speech/README.md").decode("utf-8")
        speech_output = archive.read("speech/speech_output.py").decode("utf-8")
        voice_config = archive.read("speech/voice_config.json").decode("utf-8")

    combined = f"{readme}\n{checklist}\n{submission}\n{speech_readme}\n{speech_output}\n{voice_config}"
    for keyword in task.competition_requirements:
        if keyword not in combined:
            failures.append(f"{competition_slug}/{task.slug}: missing requirement {keyword}")
    for keyword in ("创作说明", "演示视频"):
        if keyword not in combined:
            failures.append(f"{competition_slug}/{task.slug}: missing submission keyword {keyword}")
    if competition_slug == "future_creator" and "实物照片" not in combined:
        failures.append(f"{competition_slug}/{task.slug}: missing submission keyword 实物照片")
    failures.extend(validate_voice_profile(competition_slug, task, speech_readme, speech_output, voice_config))

    return failures, combined


def validate_voice_profile(
    competition_slug: str,
    task: TaskDefinition,
    speech_readme: str,
    speech_output: str,
    voice_config: str,
) -> list[str]:
    failures: list[str] = []
    combined = f"{speech_readme}\n{speech_output}\n{voice_config}"
    if task.voice_profile == "dfrobot_tts_broadcast":
        for keyword in ("DFRobot", "serial", "speak"):
            if keyword not in combined:
                failures.append(f"{competition_slug}/{task.slug}: missing voice keyword {keyword}")
    elif task.voice_profile == "unihiker_keyword_voice":
        for keyword in ("unihiker", "recognize_keyword", "keywords"):
            if keyword not in combined:
                failures.append(f"{competition_slug}/{task.slug}: missing voice keyword {keyword}")
    elif task.voice_profile == "jetson_voice_agent_stub":
        for keyword in ("Jetson", "listen_once", "agent_reply"):
            if keyword not in combined:
                failures.append(f"{competition_slug}/{task.slug}: missing voice keyword {keyword}")
    return failures


def validate_platform_coverage(
    round_index: int,
    platform_text_by_competition: dict[str, list[str]],
    report: dict[str, object],
) -> list[str]:
    failures: list[str] = []
    for competition_slug, keywords in PLATFORM_REQUIREMENT_KEYWORDS.items():
        if competition_slug not in platform_text_by_competition:
            continue
        combined = "\n".join(platform_text_by_competition.get(competition_slug, []))
        missing = [keyword for keyword in keywords if keyword not in combined]
        check = {
            "round": round_index,
            "competition": competition_slug,
            "task": "__platform_coverage__",
            "passed": not missing,
            "failures": missing,
        }
        report["checks"].append(check)
        for keyword in missing:
            failures.append(f"{competition_slug}: platform missing keyword {keyword}")
    return failures


def run_web_checks(workspace_root: Path, report: dict[str, object], edition: str) -> list[str]:
    from fastapi.testclient import TestClient

    failures: list[str] = []
    client = TestClient(create_app(workspace_root=workspace_root, edition=edition))

    index_response = client.get("/")
    index_failures: list[str] = []
    if index_response.status_code != 200:
        index_failures.append(f"homepage returned {index_response.status_code}")
    for competition in list_competitions(edition):
        if competition.title not in index_response.text:
            index_failures.append(f"homepage missing competition {competition.title}")

    report["checks"].append(
        {
            "round": "web",
            "competition": "__all__",
            "task": "__homepage__",
            "passed": not index_failures,
            "failures": index_failures,
        }
    )
    failures.extend(index_failures)

    for competition in list_competitions(edition):
        for task in competition.tasks:
            task_failures = run_web_task_check(client, competition.slug, task)
            report["checks"].append(
                {
                    "round": "web",
                    "competition": competition.slug,
                    "task": task.slug,
                    "passed": not task_failures,
                    "failures": task_failures,
                }
            )
            failures.extend(task_failures)
    return failures


def run_web_task_check(
    client: TestClient,
    competition_slug: str,
    task: TaskDefinition,
) -> list[str]:
    failures: list[str] = []
    workflow_response = client.get(f"/workflow/{competition_slug}/{task.slug}")
    if workflow_response.status_code != 200:
        return [
            f"{competition_slug}/{task.slug}: workflow returned "
            f"{workflow_response.status_code}"
        ]
    if task.title not in workflow_response.text:
        failures.append(f"{competition_slug}/{task.slug}: workflow missing task title")

    generate_response = client.post(
        "/generate",
        data={
            "competition_slug": competition_slug,
            "task_slug": task.slug,
            "project_name": f"Web验收-{task.title}",
            "student_name": "验收学生",
            "target_hardware": task.suggested_hardware[0],
            "dataset_notes": "Web 入口验收。",
            "class_labels": "类别A,类别B,类别C",
        },
    )
    if generate_response.status_code != 200:
        return [
            f"{competition_slug}/{task.slug}: generate returned "
            f"{generate_response.status_code}"
        ]

    download_url = find_download_url(generate_response.text)
    if download_url is None:
        return [f"{competition_slug}/{task.slug}: generated page missing zip download link"]

    download_response = client.get(download_url)
    if download_response.status_code != 200:
        failures.append(
            f"{competition_slug}/{task.slug}: download returned {download_response.status_code}"
        )
    if not download_response.content.startswith(b"PK"):
        failures.append(f"{competition_slug}/{task.slug}: downloaded file is not a zip")
    return failures


def find_download_url(html: str) -> str | None:
    match = DOWNLOAD_HREF_RE.search(html)
    if match is None:
        return None
    return match.group("url")


def run_generated_script(
    generated_dir: Path,
    capability: str,
    require_ai: bool,
) -> list[str]:
    script_path = generated_dir / "run.py"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=generated_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    failures: list[str] = []
    if result.returncode != 0:
        return [f"{script_path}: run.py failed with {result.stderr.strip()}"]

    predictions_path = generated_dir / "outputs" / "predictions.json"
    validation_path = generated_dir / "outputs" / "ai_validation_result.json"
    if not predictions_path.is_file():
        failures.append(f"{script_path}: missing outputs/predictions.json")
    if not validation_path.is_file():
        failures.append(f"{script_path}: missing outputs/ai_validation_result.json")

    if require_ai and validation_path.is_file():
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        status = validation.get("status")
        if status != "ok":
            failures.append(f"{script_path}: AI status is {status}")

    expected_model = {
        "text_classifier": "text_classifier.joblib",
        "image_classifier": "image_classifier.joblib",
        "qa_retrieval": "qa_retrieval.joblib",
        "sensor_decision_model": "sensor_decision_model.joblib",
        "ocr_typo_checker": "ocr_typo_checker.json",
    }[capability]
    if require_ai and not (generated_dir / "models" / expected_model).is_file():
        failures.append(f"{script_path}: missing model file {expected_model}")

    return failures


if __name__ == "__main__":
    raise SystemExit(main())
