from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.models import ProjectWorkspace


class ExportService:
    def create_zip(self, workspace: ProjectWorkspace) -> Path:
        export_path = workspace.exports_dir / f"{workspace.project_id}.zip"
        with ZipFile(export_path, "w", ZIP_DEFLATED) as archive:
            for path in sorted(workspace.generated_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(workspace.generated_dir).as_posix())
        return export_path
