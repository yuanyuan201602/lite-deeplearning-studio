from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from build_release import iter_release_files


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "lite-deeplearning-studio-student-installer.zip"
PACKAGE_ROOT = "lite-deeplearning-studio"


INSTALL_SH = """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

EXTRA="${1:-ai}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

if [ "$EXTRA" = "ocr" ]; then
  python -m pip install -e ".[ai,ocr]"
else
  python -m pip install -e ".[ai]"
fi

echo "安装完成。运行 ./start_macos_linux.sh 后打开 http://127.0.0.1:8000"
"""


START_SH = """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
python scripts/start_studio.py
"""


INSTALL_PS1 = """$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$extra = "ai"
if ($args.Count -gt 0) {
    $extra = $args[0]
}

python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install --upgrade pip

if ($extra -eq "ocr") {
    .\\.venv\\Scripts\\python.exe -m pip install -e ".[ai,ocr]"
} else {
    .\\.venv\\Scripts\\python.exe -m pip install -e ".[ai]"
}

Write-Host "安装完成。运行 .\\start_windows.ps1 后打开 http://127.0.0.1:8000"
"""


START_PS1 = """$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
.\\.venv\\Scripts\\python.exe scripts\\start_studio.py
"""


README = """# Lite DeepLearning Studio 学生机安装包

## macOS / Linux

基础安装：

```bash
./install_macos_linux.sh
./start_macos_linux.sh
```

OCR 增强安装：

```bash
./install_macos_linux.sh ocr
./start_macos_linux.sh
```

## Windows PowerShell

基础安装：

```powershell
.\\install_windows.ps1
.\\start_windows.ps1
```

OCR 增强安装：

```powershell
.\\install_windows.ps1 ocr
.\\start_windows.ps1
```

启动后打开：

```text
http://127.0.0.1:8000
```

基础安装适合大多数课堂任务；OCR 增强安装用于智能博物错别字识别任务，下载更慢，占用空间更大。
"""


GENERATED_FILES = {
    "README_STUDENT_INSTALL.md": README,
    "install_macos_linux.sh": INSTALL_SH,
    "start_macos_linux.sh": START_SH,
    "install_windows.ps1": INSTALL_PS1,
    "start_windows.ps1": START_PS1,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a student-machine installer zip.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Installer zip path. Default: dist/lite-deeplearning-studio-student-installer.zip",
    )
    return parser.parse_args()


def add_text_file(archive: ZipFile, relative_name: str, content: str) -> None:
    info = ZipInfo(f"{PACKAGE_ROOT}/{relative_name}")
    if relative_name.endswith(".sh"):
        info.external_attr = 0o755 << 16
    archive.writestr(info, content)


def build_installer(output_path: Path) -> Path:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_path in iter_release_files():
            archive.write(
                file_path,
                f"{PACKAGE_ROOT}/{file_path.relative_to(PROJECT_ROOT).as_posix()}",
            )
        for relative_name, content in GENERATED_FILES.items():
            add_text_file(archive, relative_name, content)

    return output_path


def main() -> None:
    args = parse_args()
    output_path = build_installer(args.output)
    print(f"Student installer written to {output_path}")


if __name__ == "__main__":
    main()
