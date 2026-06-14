from __future__ import annotations

import base64
import json
import os
import random
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

# Per-class caps for dataset import. Some organized datasets ship tens of
# thousands of images (MNIST ~56k); the MobileNet embedder runs once per image
# at train time, so an uncapped import would make a classroom train crawl.
IMPORT_CAPS = {"light": 100, "standard": 300, "full": None}
DEFAULT_IMPORT_CAP = "standard"

# The held-out test/ split is copied here (outside dataset/, so export never sees
# it and it never joins training) purely to power step 3's "sample a test item".
EVAL_DIR = "dataset_eval"
EVAL_MEDIA_DIR = "media"
EVAL_MANIFEST_FILE = "manifest.json"
EVAL_PER_CLASS = 20
EVAL_TEXT_LIMIT = 200


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

    # ----- organized dataset import -----

    def import_platform_dataset(
        self,
        info: ProjectInfo,
        capability: str,
        dataset_dir: Path,
        cap: str = DEFAULT_IMPORT_CAP,
    ) -> dict[str, Any]:
        """Load a pre-organized dataset (train/<label>/ + test/<label>/) into the project.

        train/ becomes the project's training data (same storage the manual
        uploader writes); test/ is copied to dataset_eval/ for step-3 sampling.
        """
        per_class_cap = IMPORT_CAPS.get(cap, IMPORT_CAPS[DEFAULT_IMPORT_CAP])
        if capability == "image_classifier":
            return self.import_image_dataset(info, dataset_dir, per_class_cap)
        if capability == "audio_classifier":
            return self.import_audio_dataset(info, dataset_dir, per_class_cap)
        if capability == "text_classifier":
            return self.import_text_dataset(info, dataset_dir)
        if capability == "sensor_decision_model":
            return self.import_sensor_dataset(info, dataset_dir)
        raise MLDataError("这个任务暂不支持从整理数据集导入。")

    def import_image_dataset(
        self, info: ProjectInfo, dataset_dir: Path, per_class_cap: int | None
    ) -> dict[str, Any]:
        counts = self._import_media_train(
            info, dataset_dir, per_class_cap, SAFE_IMAGE_SUFFIXES, MAX_IMAGE_BYTES,
            engine.IMAGE_LABELS_FILE, engine.IMAGES_DIR, "图片",
        )
        eval_count = self._store_eval_media(
            info, dataset_dir, SAFE_IMAGE_SUFFIXES, MAX_IMAGE_BYTES, "image"
        )
        return {"class_counts": counts, "eval_count": eval_count}

    def import_audio_dataset(
        self, info: ProjectInfo, dataset_dir: Path, per_class_cap: int | None
    ) -> dict[str, Any]:
        counts = self._import_media_train(
            info, dataset_dir, per_class_cap, SAFE_AUDIO_SUFFIXES, MAX_AUDIO_BYTES,
            engine.AUDIO_LABELS_FILE, engine.AUDIO_DIR, "声音",
        )
        eval_count = self._store_eval_media(
            info, dataset_dir, SAFE_AUDIO_SUFFIXES, MAX_AUDIO_BYTES, "audio"
        )
        return {"class_counts": counts, "eval_count": eval_count}

    def import_text_dataset(self, info: ProjectInfo, dataset_dir: Path) -> dict[str, Any]:
        samples = self._read_samples_file(dataset_dir / "train" / "text_samples.json")
        if not samples:
            raise MLDataError("这个文本数据集的训练样本是空的。")
        self.save_text_samples(info, samples)
        eval_samples = self._read_samples_file(dataset_dir / "test" / "text_samples.json")
        eval_count = self._store_eval_text(info, eval_samples)
        counts: dict[str, int] = {}
        for sample in samples:
            label = sample.get("label", "").strip()
            if label:
                counts[label] = counts.get(label, 0) + 1
        return {"class_counts": counts, "eval_count": eval_count}

    def import_sensor_dataset(self, info: ProjectInfo, dataset_dir: Path) -> dict[str, Any]:
        csv_path = dataset_dir / "sensor_data.csv"
        if not csv_path.is_file():
            raise MLDataError("这个数据集里没有找到 sensor_data.csv。")
        self.save_sensor_csv(info, csv_path.read_text(encoding="utf-8"))
        self._clear_eval(info)  # sensor is tested by typing values, no held-out split
        return {"class_counts": {}, "eval_count": 0}

    def _import_media_train(
        self,
        info: ProjectInfo,
        dataset_dir: Path,
        per_class_cap: int | None,
        suffixes: set[str],
        max_bytes: int,
        labels_file: str,
        media_dir: str,
        noun: str,
    ) -> dict[str, int]:
        train_root = dataset_dir / "train"
        label_dirs = (
            sorted(p for p in train_root.iterdir() if p.is_dir())
            if train_root.is_dir()
            else []
        )
        if not label_dirs:
            raise MLDataError(f"这个数据集里没有按类别分好的 train 目录，无法导入{noun}。")
        # Importing replaces this project's media (rather than appending), so that
        # re-importing with a cap draws a fresh random subset for a new experiment,
        # and importing a second dataset never mixes classes from the first.
        self._clear_media(info.project_id, labels_file, media_dir)
        counts: dict[str, int] = {}
        for label_dir in label_dirs:
            files = [
                p for p in label_dir.iterdir() if p.is_file() and p.suffix.lower() in suffixes
            ]
            # Under a cap we sample at random, so "标准·300张" gives a different
            # 300 each import — letting a teacher compare runs on different subsets.
            if per_class_cap is not None and len(files) > per_class_cap:
                files = random.sample(files, per_class_cap)
            folder = self._media_folder(info.project_id, label_dir.name, True, labels_file, media_dir)
            saved = 0
            for src in files:
                if src.stat().st_size > max_bytes:
                    continue
                shutil.copyfile(src, folder / f"{uuid4().hex[:12]}{src.suffix.lower()}")
                saved += 1
            if saved:
                counts[label_dir.name] = saved
        if not counts:
            raise MLDataError(f"没有从这个数据集导入到任何{noun}。")
        self._touch(info)
        return counts

    def _clear_media(self, project_id: str, labels_file: str, media_dir: str) -> None:
        shutil.rmtree(self.dataset_dir(project_id) / media_dir, ignore_errors=True)
        labels_path = self.dataset_dir(project_id) / labels_file
        if labels_path.exists():
            labels_path.unlink()

    # ----- held-out eval set (step 3 sampling) -----

    def eval_dir(self, project_id: str) -> Path:
        return self.project_dir(project_id) / EVAL_DIR

    def _clear_eval(self, info: ProjectInfo) -> None:
        shutil.rmtree(self.eval_dir(info.project_id), ignore_errors=True)

    def _store_eval_media(
        self, info: ProjectInfo, dataset_dir: Path, suffixes: set[str], max_bytes: int, kind: str
    ) -> int:
        self._clear_eval(info)
        test_root = dataset_dir / "test"
        if not test_root.is_dir():
            return 0
        eval_root = self.eval_dir(info.project_id)
        (eval_root / EVAL_MEDIA_DIR).mkdir(parents=True, exist_ok=True)
        items: list[dict[str, str]] = []
        for label_dir in sorted(p for p in test_root.iterdir() if p.is_dir()):
            files = [
                p for p in label_dir.iterdir() if p.is_file() and p.suffix.lower() in suffixes
            ]
            if len(files) > EVAL_PER_CLASS:
                files = random.sample(files, EVAL_PER_CLASS)
            for src in files:
                if src.stat().st_size > max_bytes:
                    continue
                rel = f"{EVAL_MEDIA_DIR}/{uuid4().hex[:12]}{src.suffix.lower()}"
                shutil.copyfile(src, eval_root / rel)
                items.append({"label": label_dir.name, "file": rel})
        self._write_eval_manifest(info, kind, items)
        return len(items)

    def _store_eval_text(self, info: ProjectInfo, eval_samples: list[dict[str, str]]) -> int:
        self._clear_eval(info)
        items = [
            {"label": s["label"].strip(), "text": s["text"].strip()}
            for s in eval_samples[:EVAL_TEXT_LIMIT]
            if s.get("text", "").strip() and s.get("label", "").strip()
        ]
        self._write_eval_manifest(info, "text", items)
        return len(items)

    def _write_eval_manifest(self, info: ProjectInfo, kind: str, items: list[dict[str, str]]) -> None:
        if not items:
            return
        eval_root = self.eval_dir(info.project_id)
        eval_root.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(
            eval_root / EVAL_MANIFEST_FILE,
            json.dumps({"kind": kind, "items": items}, ensure_ascii=False, indent=2),
        )

    def _read_eval_manifest(self, info: ProjectInfo) -> dict[str, Any] | None:
        path = self.eval_dir(info.project_id) / EVAL_MANIFEST_FILE
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def eval_count(self, info: ProjectInfo) -> int:
        manifest = self._read_eval_manifest(info)
        return len(manifest.get("items", [])) if manifest else 0

    def sample_eval_predict(self, info: ProjectInfo, capability: str) -> dict[str, Any]:
        """Pick a random held-out test item, run the trained model on it, and
        return the true label alongside the prediction so step 3 can show both."""
        manifest = self._read_eval_manifest(info)
        if not manifest or not manifest.get("items"):
            raise MLDataError("这个项目还没有测试集。请导入带测试集的整理数据集后再抽样。")
        item = random.choice(manifest["items"])
        kind = manifest.get("kind")
        result: dict[str, Any] = {"kind": kind, "true_label": item["label"]}
        if kind == "text":
            result["text"] = item["text"]
            result["prediction"] = self.predict(
                info, capability, {"text": item["text"], "values": {}}
            )
            return result
        data = (self.eval_dir(info.project_id) / item["file"]).read_bytes()
        suffix = Path(item["file"]).suffix.lower()
        if kind == "image":
            result["prediction"] = self.predict(info, capability, {"image_bytes": data})
            mime = "image/png" if suffix == ".png" else "image/jpeg"
            result["image_data_url"] = f"data:{mime};base64,{base64.b64encode(data).decode()}"
            return result
        if kind == "audio":
            result["prediction"] = self.predict(info, capability, {"audio_bytes": data})
            return result
        raise MLDataError("不支持的测试集类型。")

    @staticmethod
    def _read_samples_file(path: Path) -> list[dict[str, str]]:
        if not path.is_file():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        samples = data.get("samples") if isinstance(data, dict) else data
        return samples if isinstance(samples, list) else []

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
        self,
        info: ProjectInfo,
        capability: str,
        model_choice: str | None = None,
        feature_mode: str | None = None,
    ) -> dict[str, Any]:
        report = engine.train_capability(
            capability,
            self.dataset_dir(info.project_id),
            self.models_dir(info.project_id),
            model_choice,
            feature_mode,
        )
        info.train_report = report
        info.train_history = self._appended_history(info.train_history, report)
        self._save_info(info)
        return report

    @staticmethod
    def _appended_history(history: list[dict], report: dict[str, Any]) -> list[dict]:
        """Keep a short rolling log of each training's headline metrics for the
        before/after comparison; only the last few matter, so cap the list."""
        entry = {
            "trained_at": report.get("trained_at"),
            "sample_count": report.get("sample_count"),
            "model_name": report.get("model_name"),
            "feature_mode": report.get("feature_mode"),
            "train_accuracy": report.get("train_accuracy"),
            "cross_val_accuracy": report.get("cross_val_accuracy"),
        }
        return (history + [entry])[-8:]

    def compare_models(
        self, info: ProjectInfo, capability: str, feature_mode: str | None = None
    ) -> list[dict[str, Any]]:
        return engine.compare_capability(
            capability, self.dataset_dir(info.project_id), feature_mode
        )

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
