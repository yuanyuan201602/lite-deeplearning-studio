from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.models import GenerationRequest, ProjectWorkspace

SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


class WorkspaceService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create_workspace(self, request: GenerationRequest) -> ProjectWorkspace:
        project_id = self._make_project_id(request.project_name)
        project_dir = self.root / "projects" / project_id
        generated_dir = project_dir / "generated"
        exports_dir = project_dir / "exports"
        logs_dir = project_dir / "logs"
        metadata_path = project_dir / "metadata.json"

        for folder in (generated_dir, exports_dir, logs_dir):
            folder.mkdir(parents=True, exist_ok=True)

        metadata = {
            "project_id": project_id,
            "project_name": request.project_name,
            "student_name": request.student_name,
            "competition_slug": request.competition_slug,
            "task_slug": request.task_slug,
            "target_hardware": request.target_hardware,
            "dataset_notes": request.dataset_notes,
            "class_labels": request.class_labels,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return ProjectWorkspace(
            project_id=project_id,
            project_dir=project_dir,
            generated_dir=generated_dir,
            exports_dir=exports_dir,
            logs_dir=logs_dir,
            metadata_path=metadata_path,
        )

    def _make_project_id(self, project_name: str) -> str:
        normalized = SAFE_NAME_PATTERN.sub("-", project_name.strip()).strip("-").lower()
        prefix = normalized or "project"
        return f"{prefix[:32]}-{uuid4().hex[:8]}"
