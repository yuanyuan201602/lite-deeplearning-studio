from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.models import AppEdition, GenerationRequest, GenerationResult
from app.services.export_service import ExportService
from app.services.template_service import TemplateService
from app.services.workspace_service import WorkspaceService
from app.task_catalog import get_competition, get_task, list_competitions, normalize_edition

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


EDITION_LABELS = {
    "all": "Lite DeepLearning Studio",
    "smart_museum": "智能博物轻量版",
    "future_creator": "优创未来轻量版",
}

EDITION_INTROS = {
    "all": "选择比赛任务，生成可运行的比赛材料。",
    "smart_museum": "面向智能博物任务，使用行空板 M10 + DFRobot 开源硬件外设完成识别、展示和播报。",
    "future_creator": "面向优创未来任务，使用行空板 M10 + DFRobot 开源硬件外设完成语音、视觉和决策项目。",
}


def create_app(
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
    edition: AppEdition | str | None = None,
) -> FastAPI:
    app_edition = normalize_edition(edition or os.environ.get("LDS_EDITION", "all"))
    app = FastAPI(title=EDITION_LABELS[app_edition])
    templates = Jinja2Templates(directory=PROJECT_ROOT / "templates")
    app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")

    workspace_service = WorkspaceService(workspace_root)
    template_service = TemplateService()
    export_service = ExportService()

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "request": request,
                "competitions": list_competitions(app_edition),
                "app_title": EDITION_LABELS[app_edition],
                "app_intro": EDITION_INTROS[app_edition],
                "app_edition": app_edition,
            },
        )

    @app.get("/favicon.ico")
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/workflow/{competition_slug}/{task_slug}", response_class=HTMLResponse)
    def workflow(request: Request, competition_slug: str, task_slug: str) -> HTMLResponse:
        competition = get_competition(competition_slug, app_edition)
        task = get_task(competition_slug, task_slug, app_edition)
        if competition is None or task is None:
            raise HTTPException(status_code=404, detail="没有找到这个任务")

        return templates.TemplateResponse(
            request=request,
            name="workflow.html",
            context={
                "request": request,
                "competition": competition,
                "task": task,
                "hardware_labels": HARDWARE_LABELS,
                "app_title": EDITION_LABELS[app_edition],
                "app_intro": EDITION_INTROS[app_edition],
                "app_edition": app_edition,
                "error": "",
            },
        )

    @app.post("/generate", response_class=HTMLResponse)
    def generate(
        request: Request,
        competition_slug: str = Form(...),
        task_slug: str = Form(...),
        project_name: str = Form(...),
        student_name: str = Form(""),
        target_hardware: str = Form("unihiker_m10"),
        dataset_notes: str = Form(""),
        class_labels: str = Form(""),
        text_csv: str = Form(""),
        qa_text: str = Form(""),
        sensor_csv: str = Form(""),
        ocr_correct_text: str = Form(""),
        ocr_observed_text: str = Form(""),
    ) -> HTMLResponse:
        competition = get_competition(competition_slug, app_edition)
        task = get_task(competition_slug, task_slug, app_edition)
        if competition is None or task is None:
            raise HTTPException(status_code=404, detail="没有找到这个任务")

        try:
            generation_request = GenerationRequest(
                competition_slug=competition_slug,
                task_slug=task_slug,
                project_name=project_name,
                student_name=student_name,
                target_hardware=target_hardware,
                dataset_notes=dataset_notes,
                class_labels=parse_labels(class_labels),
                text_csv=text_csv,
                qa_text=qa_text,
                sensor_csv=sensor_csv,
                ocr_correct_text=ocr_correct_text,
                ocr_observed_text=ocr_observed_text,
            )
        except ValidationError as exc:
            return templates.TemplateResponse(
                request=request,
                name="workflow.html",
                context={
                    "request": request,
                    "competition": competition,
                    "task": task,
                    "hardware_labels": HARDWARE_LABELS,
                    "app_title": EDITION_LABELS[app_edition],
                    "app_intro": EDITION_INTROS[app_edition],
                    "app_edition": app_edition,
                    "error": "请检查项目名称、硬件选择和类别填写。",
                    "details": exc.errors(),
                },
                status_code=422,
            )

        workspace = workspace_service.create_workspace(generation_request)
        generated_files = template_service.render_task_files(workspace, task, generation_request)
        export_path = export_service.create_zip(workspace)
        result = GenerationResult(
            workspace=workspace,
            generated_files=generated_files,
            export_path=export_path,
        )

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "request": request,
                "competition": competition,
                "task": task,
                "generation": generation_request,
                "result": result,
                "files": [
                    path.relative_to(workspace.generated_dir).as_posix() for path in generated_files
                ],
                "download_url": f"/exports/{workspace.project_id}/{export_path.name}",
                "app_title": EDITION_LABELS[app_edition],
                "app_intro": EDITION_INTROS[app_edition],
                "app_edition": app_edition,
            },
        )

    @app.get("/exports/{project_id}/{filename}")
    def download_export(project_id: str, filename: str) -> FileResponse:
        export_path = workspace_root / "projects" / project_id / "exports" / filename
        if not export_path.is_file() or export_path.suffix != ".zip":
            raise HTTPException(status_code=404, detail="没有找到导出包")
        return FileResponse(
            export_path,
            media_type="application/zip",
            filename=filename,
        )

    @app.exception_handler(404)
    def not_found(request: Request, exc: HTTPException) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "request": request,
                "title": "没有找到这个任务",
                "message": str(exc.detail),
                "app_title": EDITION_LABELS[app_edition],
                "app_intro": EDITION_INTROS[app_edition],
                "app_edition": app_edition,
            },
            status_code=404,
        )

    return app


def parse_labels(raw_labels: str) -> list[str]:
    return [
        label.strip()
        for label in raw_labels.replace("，", ",").split(",")
        if label.strip()
    ]


HARDWARE_LABELS = {
    "unihiker_m10": "行空板 M10 + DFRobot 开源硬件外设",
    "student_laptop": "学生笔记本",
    "jetson_nano": "NVIDIA Jetson Nano",
    "raspberry_pi": "树莓派 / 行空板",
    "esp32": "ESP32",
    "generic": "其他硬件",
}


app = create_app(edition=os.environ.get("LDS_EDITION", "all"))
