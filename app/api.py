from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.ml import engine
from app.ml.base import MLDataError
from app.models import ProjectInfo, TaskDefinition
from app.services import dataset_library
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
    feature_mode: str = Field(default="", max_length=40)


class ImageLabelPayload(BaseModel):
    label: str = Field(min_length=1, max_length=40)


class LoadPackPayload(BaseModel):
    pack_file: str = Field(min_length=1, max_length=80)


class ImportDatasetPayload(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=80)
    cap: str = Field(default="standard", max_length=20)


def create_datasets_router(datasets_root: Path | None) -> APIRouter:
    router = APIRouter(prefix="/api/datasets")

    @router.get("")
    def list_datasets(capability: str = "") -> list:
        if datasets_root is None:
            return []
        return dataset_library.list_datasets(datasets_root, capability or None)

    return router


def create_packs_router(data_packs_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/data-packs")

    @router.get("")
    def list_packs() -> list:
        index_file = data_packs_root / "index.json"
        if not index_file.is_file():
            return []
        return json.loads(index_file.read_text(encoding="utf-8"))

    @router.get("/{pack_id}")
    def get_pack(pack_id: str) -> dict:
        pack_file = data_packs_root / f"{pack_id}.json"
        if not pack_file.is_file() or ".." in pack_id or "/" in pack_id:
            raise HTTPException(status_code=404, detail="没有找到这个样本包")
        return json.loads(pack_file.read_text(encoding="utf-8"))

    return router


def create_api_router(
    project_service: ProjectService,
    export_service: ExportService,
    edition: str,
    data_packs_root: Path | None = None,
    datasets_root: Path | None = None,
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
            "feature_modes": engine.list_feature_modes(task.ai_capability),
            "eval_count": project_service.eval_count(info),
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
        feature_mode = payload.feature_mode if payload else ""
        report = project_service.train(
            info, task.ai_capability, model_choice or None, feature_mode or None
        )
        state = project_state(info, task)
        state["report"] = report
        return state

    @router.post("/{project_id}/train/compare")
    def train_compare(project_id: str, payload: TrainPayload | None = None) -> dict:
        info, task = load_project(project_id)
        feature_mode = payload.feature_mode if payload else ""
        rows = project_service.compare_models(info, task.ai_capability, feature_mode or None)
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

    @router.post("/{project_id}/data/pack")
    def load_pack(project_id: str, payload: LoadPackPayload) -> dict:
        info, task = load_project(project_id)
        if data_packs_root is None:
            raise HTTPException(status_code=503, detail="样本包功能未启用")
        pack_file = data_packs_root / payload.pack_file
        if not pack_file.is_file() or ".." in payload.pack_file or "/" in payload.pack_file:
            raise HTTPException(status_code=404, detail="没有找到这个样本包文件")
        pack = json.loads(pack_file.read_text(encoding="utf-8"))
        kind = pack.get("kind", "")
        if kind == "text":
            project_service.save_text_samples(info, pack["samples"])
        elif kind == "qa":
            project_service.save_qa_pairs(info, pack["pairs"])
        elif kind == "sensor":
            project_service.save_sensor_csv(info, pack["csv"])
        elif kind == "image_task":
            raise HTTPException(
                status_code=400,
                detail="图像采集任务卡无法直接导入数据，请前往「数据采集助手」页面用摄像头拍摄。",
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的样本包类型：{kind}")
        return project_state(info, task)

    @router.post("/{project_id}/data/import-dataset")
    def import_dataset(project_id: str, payload: ImportDatasetPayload) -> dict:
        info, task = load_project(project_id)
        if datasets_root is None:
            raise HTTPException(status_code=503, detail="整理数据集导入未启用")
        resolved = dataset_library.resolve_dataset(datasets_root, payload.dataset_id)
        if resolved is None:
            raise HTTPException(status_code=404, detail="没有找到这个数据集")
        manifest, dataset_dir = resolved
        if manifest["ai_capability"] != task.ai_capability:
            raise HTTPException(status_code=400, detail="这个数据集和当前任务的类型不匹配。")
        summary = project_service.import_platform_dataset(
            info, task.ai_capability, dataset_dir, payload.cap
        )
        state = project_state(info, task)
        state["imported"] = summary
        return state

    @router.post("/{project_id}/eval/sample")
    def eval_sample(project_id: str) -> dict:
        info, task = load_project(project_id)
        return project_service.sample_eval_predict(info, task.ai_capability)

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
