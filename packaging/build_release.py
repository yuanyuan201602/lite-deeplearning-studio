from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "dist"
DEFAULT_RELEASE_NAME = "lite-deeplearning-studio-source.zip"

INCLUDE_PATHS = [
    "app",
    "templates",
    "static",
    "docs",
    "scripts",
    "packaging",
    "tests",
    "models_pretrained",
    "README.md",
    ".gitignore",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
]


def ensure_pretrained_models() -> None:
    """Fetch the ONNX models so release/installer zips work offline on student PCs."""
    import sys

    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    try:
        from download_pretrained import download_all

        download_all()
    except Exception as exc:  # network failures must not block packaging
        print(f"预训练模型下载失败（{exc}），安装包将以基础模式发布。")
EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "workspace",
    "tmp",
    "dist",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a lightweight source release zip for GitHub Releases."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / DEFAULT_RELEASE_NAME,
        help="Release zip path. Default: dist/lite-deeplearning-studio-source.zip",
    )
    return parser.parse_args()


def should_include(path: Path) -> bool:
    relative_parts = path.relative_to(PROJECT_ROOT).parts
    if any(part in EXCLUDED_DIR_NAMES for part in relative_parts):
        return False
    return path.suffix not in EXCLUDED_SUFFIXES


def iter_release_files() -> list[Path]:
    files: list[Path] = []
    for include_path in INCLUDE_PATHS:
        path = PROJECT_ROOT / include_path
        if not path.exists():
            continue
        if path.is_file():
            if should_include(path):
                files.append(path)
            continue
        files.extend(
            child
            for child in path.rglob("*")
            if child.is_file() and should_include(child)
        )
    return sorted(files)


def build_release(output_path: Path) -> Path:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_path in iter_release_files():
            archive.write(file_path, file_path.relative_to(PROJECT_ROOT))

    return output_path


def main() -> None:
    args = parse_args()
    ensure_pretrained_models()
    output_path = build_release(args.output)
    print(f"Release zip written to {output_path}")


if __name__ == "__main__":
    main()
