from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.ml import engine, sensor_model
from app.ml.base import MLDataError
from app.models import ProjectCreateRequest, ProjectInfo, ProjectWorkspace

SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")
SAFE_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
SAFE_AUDIO_SUFFIXES = {".wav"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_AUDIO_BYTES = 10 * 1024 * 1024


class ProjectService:
    def __init__(self, root: Path) -> None:
        self.root = root

    # ----- lifecycle -----

    def create_project(self, request: ProjectCreateRequest) -> ProjectInfo:
        project_id = self._make_project_id(request.project_name)
        now = datetime.now().isoformat(timespec="seconds")
        info = ProjectInfo(
            project_id=project_id,
            project_name=request.project_name,
            student_name=request.student_name,
            competition_slug=request.competition_slug,
            task_slug=request.task_slug,
            target_hardware=request.target_hardware,
            dataset_notes=request.dataset_notes,
            created_at=now,
            updated_at=now,
        )
        for folder in ("dataset", "models", "generated", "exports", "logs"):
            (self.project_dir(project_id) / folder).mkdir(parents=True, exist_ok=True)
        self._save_info(info)
        return info

    def get_project(self, project_id: str) -> ProjectInfo | None:
        metadata_path = self.project_dir(project_id) / "metadata.json"
        if not metadata_path.is_file():
            return None
        return ProjectInfo.model_validate_json(metadata_path.read_text(encoding="utf-8"))

    def list_projects(self) -> list[ProjectInfo]:
        projects_root = self.root / "projects"
        if not projects_root.is_dir():
            return []
        projects = [
            info
            for path in projects_root.iterdir()
            if path.is_dir() and (info := self.get_project(path.name)) is not None
        ]
        return sorted(projects, key=lambda info: info.updated_at, reverse=True)

    def project_dir(self, project_id: str) -> Path:
        return self.root / "projects" / project_id

    def dataset_dir(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "dataset"

    def models_dir(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "models"

    def workspace(self, info: ProjectInfo) -> ProjectWorkspace:
        project_dir = self.project_dir(info.project_id)
        return ProjectWorkspace(
            project_id=info.project_id,
            project_dir=project_dir,
            generated_dir=project_dir / "generated",
            exports_dir=project_dir / "exports",
            logs_dir=project_dir / "logs",
            metadata_path=project_dir / "metadata.json",
        )

    # ----- dataset storage -----

    def save_text_samples(self, info: ProjectInfo, samples: list[dict[str, str]]) -> None:
        cleaned = [
            {"text": sample["text"].strip(), "label": sample["label"].strip()}
            for sample in samples
            if sample.get("text", "").strip() and sample.get("label", "").strip()
        ]
        self._write_dataset_json(info, engine.TEXT_SAMPLES_FILE, cleaned)

    def save_qa_pairs(self, info: ProjectInfo, pairs: list[dict[str, str]]) -> None:
        cleaned = [
            {"question": pair["question"].strip(), "answer": pair["answer"].strip()}
            for pair in pairs
            if pair.get("question", "").strip() and pair.get("answer", "").strip()
        ]
        self._write_dataset_json(info, engine.QA_PAIRS_FILE, cleaned)

    def save_sensor_csv(self, info: ProjectInfo, raw_csv: str) -> None:
        # Validate at save time so problems (full-width commas, missing rows) surface
        # in step 1 with a clear message instead of a confusing failure at train time.
        normalized = sensor_model.normalize_csv_text(raw_csv)
        sensor_model.parse_sensor_csv(normalized)
        path = self.dataset_dir(info.project_id) / engine.SENSOR_CSV_FILE
        self._atomic_write_text(path, normalized.strip() + "\n")
        self._touch(info)

    def save_ocr_text(self, info: ProjectInfo, correct_text: str, observed_sample: str) -> None:
        payload = {
            "correct_text": correct_text.strip(),
            "observed_sample": observed_sample.strip(),
        }
        self._write_dataset_json(info, engine.OCR_FILE, payload)

    def add_images(self, info: ProjectInfo, label: str, images: list[tuple[str, bytes]]) -> int:
        label = label.strip()
        if not label:
            raise MLDataError("请先填写这组图片的类别名称。")
        saved = 0
        folder = self._image_folder(info.project_id, label, create=True)
        for filename, data in images:
            suffix = Path(filename).suffix.lower()
            if suffix not in SAFE_IMAGE_SUFFIXES:
                raise MLDataError(f"不支持的图片格式：{filename}。请上传 PNG 或 JPG。")
            if len(data) > MAX_IMAGE_BYTES:
                raise MLDataError(f"图片太大：{filename}。请使用 8MB 以内的图片。")
            (folder / f"{uuid4().hex[:12]}{suffix}").write_bytes(data)
            saved += 1
        self._touch(info)
        return saved

    def remove_image_label(self, info: ProjectInfo, label: str) -> None:
        self._remove_media_label(info, label, engine.IMAGE_LABELS_FILE, engine.IMAGES_DIR)

    def add_audio_clips(self, info: ProjectInfo, label: str, clips: list[tuple[str, bytes]]) -> int:
        label = label.strip()
        if not label:
            raise MLDataError("请先填写这组声音的类别名称。")
        saved = 0
        folder = self._media_folder(
            info.project_id, label, True, engine.AUDIO_LABELS_FILE, engine.AUDIO_DIR
        )
        for filename, data in clips:
            suffix = Path(filename).suffix.lower()
            if suffix not in SAFE_AUDIO_SUFFIXES:
                raise MLDataError(f"不支持的声音格式：{filename}。请上传 WAV 录音。")
            if len(data) > MAX_AUDIO_BYTES:
                raise MLDataError(f"声音文件太大：{filename}。请使用 10MB 以内的录音。")
            (folder / f"{uuid4().hex[:12]}{suffix}").write_bytes(data)
            saved += 1
        self._touch(info)
        return saved

    def remove_audio_label(self, info: ProjectInfo, label: str) -> None:
        self._remove_media_label(info, label, engine.AUDIO_LABELS_FILE, engine.AUDIO_DIR)

    def _remove_media_label(
        self, info: ProjectInfo, label: str, labels_file: str, media_dir: str
    ) -> None:
        labels_path = self.dataset_dir(info.project_id) / labels_file
        if not labels_path.is_file():
            return
        label_map: dict[str, str] = json.loads(labels_path.read_text(encoding="utf-8"))
        for folder_name, existing_label in list(label_map.items()):
            if existing_label == label:
                shutil.rmtree(
                    self.dataset_dir(info.project_id) / media_dir / folder_name,
                    ignore_errors=True,
                )
                del label_map[folder_name]
        self._atomic_write_text(labels_path, json.dumps(label_map, ensure_ascii=False, indent=2))
        self._touch(info)

    def dataset_summary(self, info: ProjectInfo, dataset_kind: str) -> dict[str, Any]:
        dataset_dir = self.dataset_dir(info.project_id)
        if dataset_kind == "text":
            samples = self._read_dataset_json(dataset_dir / engine.TEXT_SAMPLES_FILE, [])
            counts: dict[str, int] = {}
            for sample in samples:
                counts[sample["label"]] = counts.get(sample["label"], 0) + 1
            return {
                "kind": "text",
                "sample_count": len(samples),
                "class_counts": counts,
                "samples": samples,
            }
        if dataset_kind == "qa":
            pairs = self._read_dataset_json(dataset_dir / engine.QA_PAIRS_FILE, [])
            return {"kind": "qa", "sample_count": len(pairs), "pairs": pairs}
        if dataset_kind == "sensor":
            csv_path = dataset_dir / engine.SENSOR_CSV_FILE
            if not csv_path.is_file():
                return {"kind": "sensor", "sample_count": 0, "columns": [], "csv": ""}
            raw_csv = csv_path.read_text(encoding="utf-8")
            lines = [line for line in raw_csv.splitlines() if line.strip()]
            columns = [cell.strip() for cell in lines[0].split(",")] if lines else []
            return {
                "kind": "sensor",
                "sample_count": max(0, len(lines) - 1),
                "columns": columns,
                "csv": raw_csv.strip(),
            }
        if dataset_kind == "ocr":
            payload = self._read_dataset_json(dataset_dir / engine.OCR_FILE, {})
            correct_text = payload.get("correct_text", "")
            return {
                "kind": "ocr",
                "sample_count": 1 if correct_text else 0,
                "correct_text": correct_text,
                "observed_sample": payload.get("observed_sample", ""),
            }
        if dataset_kind == "image":
            class_counts = {
                label: len([path for path in folder.glob("*") if path.is_file()])
                for label, folder in self.image_folders(info.project_id).items()
            }
            return {
                "kind": "image",
                "sample_count": sum(class_counts.values()),
                "class_counts": class_counts,
            }
        if dataset_kind == "audio":
            class_counts = {
                label: len([path for path in folder.glob("*") if path.is_file()])
                for label, folder in self.audio_folders(info.project_id).items()
            }
            return {
                "kind": "audio",
                "sample_count": sum(class_counts.values()),
                "class_counts": class_counts,
            }
        return {"kind": dataset_kind, "sample_count": 0}

    def load_text_samples(self, project_id: str) -> list[dict[str, str]]:
        return self._read_dataset_json(self.dataset_dir(project_id) / engine.TEXT_SAMPLES_FILE, [])

    def load_qa_pairs(self, project_id: str) -> list[dict[str, str]]:
        return self._read_dataset_json(self.dataset_dir(project_id) / engine.QA_PAIRS_FILE, [])

    def load_sensor_csv(self, project_id: str) -> str:
        path = self.dataset_dir(project_id) / engine.SENSOR_CSV_FILE
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def load_ocr_payload(self, project_id: str) -> dict[str, str]:
        return self._read_dataset_json(self.dataset_dir(project_id) / engine.OCR_FILE, {})

    def image_folders(self, project_id: str) -> dict[str, Path]:
        """Map of class label -> folder of uploaded images."""
        return self._media_folders(project_id, engine.IMAGE_LABELS_FILE, engine.IMAGES_DIR)

    def audio_folders(self, project_id: str) -> dict[str, Path]:
        """Map of class label -> folder of uploaded audio clips."""
        return self._media_folders(project_id, engine.AUDIO_LABELS_FILE, engine.AUDIO_DIR)

    def _media_folders(self, project_id: str, labels_file: str, media_dir: str) -> dict[str, Path]:
        labels_path = self.dataset_dir(project_id) / labels_file
        if not labels_path.is_file():
            return {}
        label_map: dict[str, str] = json.loads(labels_path.read_text(encoding="utf-8"))
        return {
            label: self.dataset_dir(project_id) / media_dir / folder_name
            for folder_name, label in label_map.items()
        }

    # ----- training and prediction -----

    def train(
        self, info: ProjectInfo, capability: str, model_choice: str | None = None
    ) -> dict[str, Any]:
        report = engine.train_capability(
            capability,
            self.dataset_dir(info.project_id),
            self.models_dir(info.project_id),
            model_choice,
        )
        info.train_report = report
        self._save_info(info)
        return report

    def compare_models(self, info: ProjectInfo, capability: str) -> list[dict[str, Any]]:
        return engine.compare_capability(capability, self.dataset_dir(info.project_id))

    def predict(self, info: ProjectInfo, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        return engine.predict_capability(capability, self.models_dir(info.project_id), payload)

    def record_export(self, info: ProjectInfo, export_path: Path) -> None:
        info.export_file = export_path.name
        self._save_info(info)

    # ----- helpers -----

    def _image_folder(self, project_id: str, label: str, create: bool) -> Path:
        return self._media_folder(
            project_id, label, create, engine.IMAGE_LABELS_FILE, engine.IMAGES_DIR
        )

    def _media_folder(
        self, project_id: str, label: str, create: bool, labels_file: str, media_dir: str
    ) -> Path:
        labels_path = self.dataset_dir(project_id) / labels_file
        label_map: dict[str, str] = (
            json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.is_file() else {}
        )
        for folder_name, existing_label in label_map.items():
            if existing_label == label:
                folder = self.dataset_dir(project_id) / media_dir / folder_name
                folder.mkdir(parents=True, exist_ok=True)
                return folder
        if not create:
            raise MLDataError(f"找不到这个类别：{label}。")
        folder_name = str(len(label_map))
        label_map[folder_name] = label
        self._atomic_write_text(labels_path, json.dumps(label_map, ensure_ascii=False, indent=2))
        folder = self.dataset_dir(project_id) / media_dir / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        # Write to a unique temp file then os.replace onto the target. os.replace is
        # atomic on the same filesystem, so a concurrent reader always sees either the
        # complete old file or the complete new one — never an empty/half-written one.
        # Without this, two racing saves (or a save racing a read) corrupt the file.
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    def _write_dataset_json(self, info: ProjectInfo, filename: str, payload: Any) -> None:
        target = self.dataset_dir(info.project_id) / filename
        self._atomic_write_text(target, json.dumps(payload, ensure_ascii=False, indent=2))
        self._touch(info)

    def _read_dataset_json(self, path: Path, default: Any) -> Any:
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _touch(self, info: ProjectInfo) -> None:
        info.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save_info(info)

    def _save_info(self, info: ProjectInfo) -> None:
        metadata_path = self.project_dir(info.project_id) / "metadata.json"
        self._atomic_write_text(metadata_path, info.model_dump_json(indent=2))

    def _make_project_id(self, project_name: str) -> str:
        normalized = SAFE_NAME_PATTERN.sub("-", project_name.strip()).strip("-").lower()
        prefix = normalized or "project"
        return f"{prefix[:32]}-{uuid4().hex[:8]}"
