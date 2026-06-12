from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.ml import engine
from app.ml.base import MLDataError
from app.models import ProjectInfo, TaskDefinition
from app.services.export_service import ExportService
from app.services.project_service import ProjectService
from app.task_catalog import get_task


class TextSamplesPayload(BaseModel):
    samples: list[dict[str, str]] = Field(default_factory=list)


class QaPairsPayload(BaseModel):
    pairs: list[dict[str, str]] = Field(default_factory=list)


class SensorPayload(BaseModel):
    csv: str = Field(default="", max_length=20000)


class OcrPayload(BaseModel):
    correct_text: str = Field(default="", max_length=1000)
    observed_sample: str = Field(default="", max_length=1000)


class PredictPayload(BaseModel):
    text: str = Field(default="", max_length=2000)
    values: dict[str, str] = Field(default_factory=dict)


class TrainPayload(BaseModel):
    classifier: str = Field(default="", max_length=40)


class ImageLabelPayload(BaseModel):
    label: str = Field(min_length=1, max_length=40)


def create_api_router(
    project_service: ProjectService,
    export_service: ExportService,
    edition: str,
) -> APIRouter:
    router = APIRouter(prefix="/api/projects")

    def load_project(project_id: str) -> tuple[ProjectInfo, TaskDefinition]:
        info = project_service.get_project(project_id)
        if info is None:
            raise HTTPException(status_code=404, detail="没有找到这个项目")
        task = get_task(info.competition_slug, info.task_slug, edition)
        if task is None:
            raise HTTPException(status_code=404, detail="没有找到这个任务")
        return info, task

    def project_state(info: ProjectInfo, task: TaskDefinition) -> dict:
        return {
            "project": info.model_dump(),
            "dataset": project_service.dataset_summary(info, task.sample_dataset_kind),
            "capability": task.ai_capability,
            "dataset_kind": task.sample_dataset_kind,
            "model_choices": engine.list_model_choices(task.ai_capability),
        }

    @router.get("/{project_id}/state")
    def get_state(project_id: str) -> dict:
        info, task = load_project(project_id)
        return project_state(info, task)

    @router.post("/{project_id}/data/text")
    def save_text(project_id: str, payload: TextSamplesPayload) -> dict:
        info, task = load_project(project_id)
        project_service.save_text_samples(info, payload.samples)
        return project_state(info, task)

    @router.post("/{project_id}/data/qa")
    def save_qa(project_id: str, payload: QaPairsPayload) -> dict:
        info, task = load_project(project_id)
        project_service.save_qa_pairs(info, payload.pairs)
        return project_state(info, task)

    @router.post("/{project_id}/data/sensor")
    def save_sensor(project_id: str, payload: SensorPayload) -> dict:
        info, task = load_project(project_id)
        project_service.save_sensor_csv(info, payload.csv)
        return project_state(info, task)

    @router.post("/{project_id}/data/ocr")
    def save_ocr(project_id: str, payload: OcrPayload) -> dict:
        info, task = load_project(project_id)
        project_service.save_ocr_text(info, payload.correct_text, payload.observed_sample)
        return project_state(info, task)

    @router.post("/{project_id}/data/images")
    async def upload_images(
        project_id: str,
        label: str = Form(...),
        files: list[UploadFile] = File(...),
    ) -> dict:
        info, task = load_project(project_id)
        images = [(upload.filename or "image.png", await upload.read()) for upload in files]
        saved = project_service.add_images(info, label, images)
        state = project_state(info, task)
        state["saved"] = saved
        return state

    @router.post("/{project_id}/data/images/remove")
    def remove_image_label(project_id: str, payload: ImageLabelPayload) -> dict:
        info, task = load_project(project_id)
        project_service.remove_image_label(info, payload.label)
        return project_state(info, task)

    @router.post("/{project_id}/data/audio")
    async def upload_audio(
        project_id: str,
        label: str = Form(...),
        files: list[UploadFile] = File(...),
    ) -> dict:
        info, task = load_project(project_id)
        clips = [(upload.filename or "clip.wav", await upload.read()) for upload in files]
        saved = project_service.add_audio_clips(info, label, clips)
        state = project_state(info, task)
        state["saved"] = saved
        return state

    @router.post("/{project_id}/data/audio/remove")
    def remove_audio_label(project_id: str, payload: ImageLabelPayload) -> dict:
        info, task = load_project(project_id)
        project_service.remove_audio_label(info, payload.label)
        return project_state(info, task)

    @router.post("/{project_id}/train")
    def train(project_id: str, payload: TrainPayload | None = None) -> dict:
        info, task = load_project(project_id)
        model_choice = payload.classifier if payload else ""
        report = project_service.train(info, task.ai_capability, model_choice or None)
        state = project_state(info, task)
        state["report"] = report
        return state

    @router.post("/{project_id}/train/compare")
    def train_compare(project_id: str) -> dict:
        info, task = load_project(project_id)
        rows = project_service.compare_models(info, task.ai_capability)
        return {"rows": rows}

    @router.post("/{project_id}/predict")
    def predict(project_id: str, payload: PredictPayload) -> dict:
        info, task = load_project(project_id)
        return project_service.predict(
            info,
            task.ai_capability,
            {"text": payload.text, "values": payload.values},
        )

    @router.post("/{project_id}/predict/image")
    async def predict_image(project_id: str, file: UploadFile = File(...)) -> dict:
        info, task = load_project(project_id)
        image_bytes = await file.read()
        return project_service.predict(info, task.ai_capability, {"image_bytes": image_bytes})

    @router.post("/{project_id}/predict/audio")
    async def predict_audio(project_id: str, file: UploadFile = File(...)) -> dict:
        info, task = load_project(project_id)
        audio_bytes = await file.read()
        return project_service.predict(info, task.ai_capability, {"audio_bytes": audio_bytes})

    @router.post("/{project_id}/export")
    def export(project_id: str) -> dict:
        info, task = load_project(project_id)
        # Gate only the student-facing route: without it a fresh project exports a
        # zip whose models/ is empty and predict.py crashes at the competition.
        # Service-level export stays open for teacher template packages
        # (run.py in the package trains on the bundled sample data).
        if info.train_report is None:
            raise MLDataError(
                "还没有训练模型，材料包里会缺少模型文件。请先完成「训练模型」这一步再导出。"
            )
        export_path, generated_files = export_service.export_project(
            info, task, project_service
        )
        workspace = project_service.workspace(info)
        return {
            "download_url": f"/exports/{info.project_id}/{export_path.name}",
            "export_file": export_path.name,
            "files": [
                path.relative_to(workspace.generated_dir).as_posix()
                for path in generated_files
            ],
        }

    return router


def register_ml_error_handler(app) -> None:
    @app.exception_handler(MLDataError)
    def ml_data_error(request, exc: MLDataError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
