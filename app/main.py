from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.api import create_api_router, register_ml_error_handler
from app.models import AppEdition, ProjectCreateRequest
from app.services.export_service import ExportService
from app.services.project_service import ProjectService
from app.task_catalog import (
    GENERAL_ML,
    get_competition,
    get_task,
    list_competitions,
    normalize_edition,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKSPACE_ROOT = PROJECT_ROOT / "workspace"

SCHOOL_NAME = "南昌市第二十三中学"

# Bumping this busts browser caches for styles.css/logo.svg after an upgrade.
ASSET_VERSION = "0.3.0"

EDITION_LABELS = {
    "all": "Lite DeepLearning Studio",
    "smart_museum": "智能博物轻量版",
    "future_creator": "优创未来轻量版",
}

EDITION_INTROS = {
    "all": "上传数据、训练模型、实时测试，一键导出比赛材料。",
    "smart_museum": "面向智能博物任务：训练文本分类、问答和查错模型，导出行空板 M10 比赛材料。",
    "future_creator": "面向优创未来任务：训练图像识别和传感器决策模型，导出行空板 M10 比赛材料。",
}

HARDWARE_LABELS = {
    "unihiker_m10": "行空板 M10 + DFRobot 开源硬件外设",
    "student_laptop": "学生笔记本",
    "jetson_nano": "NVIDIA Jetson Nano",
    "raspberry_pi": "树莓派 / 行空板",
    "esp32": "ESP32",
    "generic": "其他硬件",
}

STEP_LABELS = {
    "default": ["准备数据", "训练模型", "测试效果", "导出材料"],
    "ocr_typo_checker": ["输入正确文字", "保存正确文字", "查错测试", "导出材料"],
}


def create_app(
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
    edition: AppEdition | str | None = None,
) -> FastAPI:
    app_edition = normalize_edition(edition or os.environ.get("LDS_EDITION", "all"))
    app = FastAPI(title=EDITION_LABELS[app_edition])
    templates = Jinja2Templates(directory=PROJECT_ROOT / "templates")
    app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")

    project_service = ProjectService(workspace_root)
    export_service = ExportService()

    app.include_router(create_api_router(project_service, export_service, app_edition))
    register_ml_error_handler(app)

    def base_context(request: Request) -> dict:
        return {
            "request": request,
            "app_title": EDITION_LABELS[app_edition],
            "app_intro": EDITION_INTROS[app_edition],
            "app_edition": app_edition,
            "school_name": SCHOOL_NAME,
            "asset_version": ASSET_VERSION,
        }

    def visible_projects() -> list:
        visible_slugs = {competition.slug for competition in list_competitions(app_edition)}
        visible_slugs.add(GENERAL_ML.slug)
        return [
            info
            for info in project_service.list_projects()
            if info.competition_slug in visible_slugs
        ]

    def task_title(competition_slug: str, task_slug: str) -> str:
        task = get_task(competition_slug, task_slug, app_edition)
        return task.title if task else task_slug

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        projects = visible_projects()
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                **base_context(request),
                "general_tasks": GENERAL_ML.tasks,
                "competitions": list_competitions(app_edition),
                "recent_projects": projects[:8],
                "task_title": task_title,
            },
        )

    @app.get("/competition/{competition_slug}", response_class=HTMLResponse)
    def competition_page(request: Request, competition_slug: str) -> HTMLResponse:
        competition = get_competition(competition_slug, app_edition)
        if competition is None or competition.slug == GENERAL_ML.slug:
            raise HTTPException(status_code=404, detail="没有找到这个竞赛")
        projects = [
            info for info in visible_projects() if info.competition_slug == competition.slug
        ]
        return templates.TemplateResponse(
            request=request,
            name="competition.html",
            context={
                **base_context(request),
                "competition": competition,
                "competition_projects": projects,
                "task_title": task_title,
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
                **base_context(request),
                "competition": competition,
                "task": task,
                "hardware_labels": HARDWARE_LABELS,
                "error": "",
            },
        )

    @app.post("/projects")
    def create_project(
        request: Request,
        competition_slug: str = Form(...),
        task_slug: str = Form(...),
        project_name: str = Form(...),
        student_name: str = Form(""),
        target_hardware: str = Form("unihiker_m10"),
        dataset_notes: str = Form(""),
    ) -> Response:
        competition = get_competition(competition_slug, app_edition)
        task = get_task(competition_slug, task_slug, app_edition)
        if competition is None or task is None:
            raise HTTPException(status_code=404, detail="没有找到这个任务")
        try:
            create_request = ProjectCreateRequest(
                competition_slug=competition_slug,
                task_slug=task_slug,
                project_name=project_name,
                student_name=student_name,
                target_hardware=target_hardware,
                dataset_notes=dataset_notes,
            )
        except ValidationError as exc:
            return templates.TemplateResponse(
                request=request,
                name="workflow.html",
                context={
                    **base_context(request),
                    "competition": competition,
                    "task": task,
                    "hardware_labels": HARDWARE_LABELS,
                    "error": "请检查项目名称和硬件选择。",
                    "details": exc.errors(),
                },
                status_code=422,
            )
        info = project_service.create_project(create_request)
        return RedirectResponse(url=f"/project/{info.project_id}", status_code=303)

    @app.get("/project/{project_id}", response_class=HTMLResponse)
    def project_page(request: Request, project_id: str) -> HTMLResponse:
        info = project_service.get_project(project_id)
        if info is None:
            raise HTTPException(status_code=404, detail="没有找到这个项目")
        competition = get_competition(info.competition_slug, app_edition)
        task = get_task(info.competition_slug, info.task_slug, app_edition)
        if competition is None or task is None:
            raise HTTPException(status_code=404, detail="没有找到这个任务")

        initial_state = {
            "project": info.model_dump(),
            "dataset": project_service.dataset_summary(info, task.sample_dataset_kind),
            "capability": task.ai_capability,
            "dataset_kind": task.sample_dataset_kind,
        }
        return templates.TemplateResponse(
            request=request,
            name="project.html",
            context={
                **base_context(request),
                "competition": competition,
                "task": task,
                "info": info,
                "hardware_labels": HARDWARE_LABELS,
                "step_labels": STEP_LABELS.get(task.ai_capability, STEP_LABELS["default"]),
                # Rendered with | safe inside a <script> tag, so escape "<" to keep
                # student-provided text from closing the tag.
                "initial_state_json": json.dumps(initial_state, ensure_ascii=False).replace(
                    "<", "\\u003c"
                ),
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
    def not_found(request: Request, exc: HTTPException) -> Response:
        if request.url.path.startswith("/api/"):
            return Response(
                content=json.dumps({"detail": str(exc.detail)}, ensure_ascii=False),
                status_code=404,
                media_type="application/json",
            )
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                **base_context(request),
                "title": "没有找到这个页面",
                "message": str(exc.detail),
            },
            status_code=404,
        )

    return app


app = create_app(edition=os.environ.get("LDS_EDITION", "all"))
