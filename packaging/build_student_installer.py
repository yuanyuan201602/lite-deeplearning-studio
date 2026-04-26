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


SETUP_BAT = """@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo Lite DeepLearning Studio Setup
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 Python。请先安装 Python 3.11 或 3.12，并勾选 Add python.exe to PATH。
  echo 下载地址: https://www.python.org/downloads/
  pause
  exit /b 1
)

python -m venv .venv
if errorlevel 1 (
  echo [ERROR] 创建本地运行环境失败。
  pause
  exit /b 1
)

".venv\\Scripts\\python.exe" -m pip install --upgrade pip
".venv\\Scripts\\python.exe" -m pip install -e ".[ai]"
if errorlevel 1 (
  echo [ERROR] 安装依赖失败，请检查网络或联系老师。
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1

echo.
echo 安装完成。
echo 可以双击 start.bat 启动，或使用桌面快捷方式。
echo 启动后打开 http://127.0.0.1:8000
pause
"""


SETUP_OCR_BAT = """@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo Lite DeepLearning Studio OCR Setup
echo ========================================
echo.
echo OCR 增强安装会下载 EasyOCR、Torch 和 OpenCV，耗时更长。
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 Python。请先安装 Python 3.11 或 3.12，并勾选 Add python.exe to PATH。
  echo 下载地址: https://www.python.org/downloads/
  pause
  exit /b 1
)

python -m venv .venv
if errorlevel 1 (
  echo [ERROR] 创建本地运行环境失败。
  pause
  exit /b 1
)

".venv\\Scripts\\python.exe" -m pip install --upgrade pip
".venv\\Scripts\\python.exe" -m pip install -e ".[ai,ocr]"

if errorlevel 1 (
  echo [ERROR] OCR 增强依赖安装失败。基础功能仍可使用。
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1

echo OCR 增强安装完成。
echo 可以双击 start.bat 启动，或使用桌面快捷方式。
pause
"""


START_BAT = """@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\\Scripts\\python.exe" (
  echo 尚未安装，请先双击 setup.bat。
  pause
  exit /b 1
)
echo Lite DeepLearning Studio 正在启动...
echo 浏览器地址: http://127.0.0.1:8000
".venv\\Scripts\\python.exe" scripts\\start_studio.py
pause
"""


UNINSTALL_BAT = """@echo off
setlocal
cd /d "%~dp0"
echo 这会删除本目录中的 .venv 和 workspace。
choice /C YN /M "确认卸载本地运行环境和学生生成任务包吗"
if errorlevel 2 exit /b 0

if exist ".venv" rmdir /S /Q ".venv"
if exist "workspace" rmdir /S /Q "workspace"

echo 卸载完成。项目源码目录仍保留，如需彻底删除，请删除整个文件夹。
pause
"""


CREATE_SHORTCUT_PS1 = """$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Lite DeepLearning Studio.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $root "start.bat"
$shortcut.WorkingDirectory = $root
$shortcut.Description = "启动 Lite DeepLearning Studio"
$shortcut.Save()
Write-Host "已创建桌面快捷方式：$shortcutPath"
"""


WINDOWS_INSTALL_README = """# Windows 学生机安装说明

## 推荐方式

1. 解压整个安装包。
2. 双击 `setup.bat`。
3. 安装完成后双击 `start.bat`，或使用桌面快捷方式。
4. 浏览器打开 `http://127.0.0.1:8000`。

## OCR 增强安装

如果要使用智能博物错别字 OCR 任务，双击：

```text
setup_ocr.bat
```

OCR 会下载 EasyOCR、Torch 和 OpenCV，速度较慢。普通图像识别、文本分类、问答和传感器任务只需要 `setup.bat`。

## 卸载

双击 `uninstall.bat` 会删除本地运行环境 `.venv` 和学生生成的 `workspace`。

如果需要彻底删除，直接删除整个文件夹。
"""


README = """# Lite DeepLearning Studio 学生机安装包

## Windows 推荐方式

基础安装：

```text
双击 setup.bat
双击 start.bat
```

OCR 增强安装：

```text
双击 setup_ocr.bat
双击 start.bat
```

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

如果学校电脑限制 `.bat`，可以改用 PowerShell：

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
    "README_WINDOWS_SETUP.txt": WINDOWS_INSTALL_README,
    "setup.bat": SETUP_BAT,
    "setup_ocr.bat": SETUP_OCR_BAT,
    "start.bat": START_BAT,
    "uninstall.bat": UNINSTALL_BAT,
    "create_desktop_shortcut.ps1": CREATE_SHORTCUT_PS1,
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
