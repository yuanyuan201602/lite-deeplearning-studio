from __future__ import annotations

import csv
import shutil
from io import StringIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.ml.base import MODEL_FILE, MODEL_META_FILE
from app.models import GenerationRequest, ProjectInfo, ProjectWorkspace, TaskDefinition
from app.services.project_service import ProjectService
from app.services.template_service import TemplateService


class ExportService:
    def __init__(self, template_service: TemplateService | None = None) -> None:
        self.template_service = template_service or TemplateService()

    def export_project(
        self,
        info: ProjectInfo,
        task: TaskDefinition,
        project_service: ProjectService,
    ) -> tuple[Path, list[Path]]:
        workspace = project_service.workspace(info)
        shutil.rmtree(workspace.generated_dir, ignore_errors=True)
        workspace.generated_dir.mkdir(parents=True, exist_ok=True)

        request = self.build_generation_request(info, task, project_service)
        user_images = (
            project_service.image_folders(info.project_id)
            if task.sample_dataset_kind == "image"
            else None
        )
        user_audio = (
            project_service.audio_folders(info.project_id)
            if task.sample_dataset_kind == "audio"
            else None
        )
        generated_files = self.template_service.render_task_files(
            workspace, task, request, user_images or None, user_audio or None
        )
        generated_files.extend(self._bundle_trained_model(info, task, project_service, workspace))

        export_path = self.create_zip(workspace)
        project_service.record_export(info, export_path)
        return export_path, generated_files

    def build_generation_request(
        self,
        info: ProjectInfo,
        task: TaskDefinition,
        project_service: ProjectService,
    ) -> GenerationRequest:
        project_id = info.project_id
        text_csv = ""
        qa_text = ""
        class_labels: list[str] = []

        if task.sample_dataset_kind == "text":
            samples = project_service.load_text_samples(project_id)
            text_csv = self._csv(
                ["text", "label"],
                [(sample["text"], sample["label"]) for sample in samples],
            )
            class_labels = sorted({sample["label"] for sample in samples})
        elif task.sample_dataset_kind == "qa":
            pairs = project_service.load_qa_pairs(project_id)
            qa_text = self._csv(
                ["question", "answer"],
                [(pair["question"], pair["answer"]) for pair in pairs],
            )
        elif task.sample_dataset_kind == "image":
            class_labels = sorted(project_service.image_folders(project_id))
        elif task.sample_dataset_kind == "audio":
            class_labels = sorted(project_service.audio_folders(project_id))

        ocr_payload = project_service.load_ocr_payload(project_id)
        return GenerationRequest(
            competition_slug=info.competition_slug,
            task_slug=info.task_slug,
            project_name=info.project_name,
            student_name=info.student_name,
            target_hardware=info.target_hardware,
            dataset_notes=info.dataset_notes,
            class_labels=class_labels,
            text_csv=text_csv if len(text_csv.splitlines()) > 1 else "",
            qa_text=qa_text if len(qa_text.splitlines()) > 1 else "",
            sensor_csv=project_service.load_sensor_csv(project_id),
            ocr_correct_text=ocr_payload.get("correct_text", ""),
            ocr_observed_text=ocr_payload.get("observed_sample", ""),
        )

    def create_zip(self, workspace: ProjectWorkspace) -> Path:
        export_path = workspace.exports_dir / f"{workspace.project_id}.zip"
        workspace.exports_dir.mkdir(parents=True, exist_ok=True)
        with ZipFile(export_path, "w", ZIP_DEFLATED) as archive:
            for path in sorted(workspace.generated_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(workspace.generated_dir).as_posix())
        return export_path

    def _bundle_trained_model(
        self,
        info: ProjectInfo,
        task: TaskDefinition,
        project_service: ProjectService,
        workspace: ProjectWorkspace,
    ) -> list[Path]:
        """Copy the in-app trained model so the exported predict.py works without retraining."""
        models_dir = project_service.models_dir(info.project_id)
        copied: list[Path] = []
        target_dir = workspace.generated_dir / "models"
        target_dir.mkdir(parents=True, exist_ok=True)

        model_path = models_dir / MODEL_FILE
        if model_path.is_file():
            target = target_dir / f"{task.ai_capability}.joblib"
            target.write_bytes(model_path.read_bytes())
            copied.append(target)
        meta_path = models_dir / MODEL_META_FILE
        if meta_path.is_file():
            target = target_dir / MODEL_META_FILE
            target.write_text(meta_path.read_text(encoding="utf-8"), encoding="utf-8")
            copied.append(target)
        return copied

    def _csv(self, headers: list[str], rows: list[tuple[str, str]]) -> str:
        output = StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)
        return output.getvalue()
