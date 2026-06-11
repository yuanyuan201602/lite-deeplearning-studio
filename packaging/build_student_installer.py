from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from build_release import iter_release_files


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "lite-deeplearning-studio-student-installer.zip"
PACKAGE_ROOT = "lite-deeplearning-studio"
EDITION_TITLES = {
    "all": "Lite DeepLearning Studio",
    "smart_museum": "智能博物轻量版",
    "future_creator": "优创未来轻量版",
}


INSTALL_SH = """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export LDS_EDITION="__EDITION__"

EXTRA="${1:-base}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

if [ "$EXTRA" = "ocr" ]; then
  python -m pip install -e ".[ocr]"
else
  python -m pip install -e .
fi

echo "安装完成。运行 ./start_macos_linux.sh 后打开 http://127.0.0.1:8000"
"""


START_SH = """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export LDS_EDITION="__EDITION__"
source .venv/bin/activate
python scripts/start_studio.py --open
"""


INSTALL_COMMAND = """#!/usr/bin/env bash
# macOS 双击入口：一键安装 __APP_TITLE__
set -euo pipefail
cd "$(dirname "$0")"
export LDS_EDITION="__EDITION__"

echo "========================================"
echo "__APP_TITLE__ 一键安装 (macOS)"
echo "========================================"

PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[错误] 未找到 Python。请先到 https://www.python.org/downloads/ 安装 Python 3.11+。"
  read -r -p "按回车键退出..." _
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

echo ""
echo "安装完成。双击 启动软件.command 即可启动，浏览器会自动打开。"
read -r -p "按回车键退出..." _
"""


START_COMMAND = """#!/usr/bin/env bash
# macOS 双击入口：启动 __APP_TITLE__
set -euo pipefail
cd "$(dirname "$0")"
export LDS_EDITION="__EDITION__"

if [ ! -x ".venv/bin/python" ]; then
  echo "尚未安装，请先双击 一键安装.command。"
  read -r -p "按回车键退出..." _
  exit 1
fi

echo "__APP_TITLE__ 正在启动，浏览器会自动打开 http://127.0.0.1:8000"
.venv/bin/python scripts/start_studio.py --open
"""


INSTALL_PS1 = """$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:LDS_EDITION = "__EDITION__"

$extra = "base"
if ($args.Count -gt 0) {
    $extra = $args[0]
}

python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install --upgrade pip

if ($extra -eq "ocr") {
    .\\.venv\\Scripts\\python.exe -m pip install -e ".[ocr]"
} else {
    .\\.venv\\Scripts\\python.exe -m pip install -e "."
}

Write-Host "安装完成。运行 .\\start_windows.ps1 后打开 http://127.0.0.1:8000"
"""


START_PS1 = """$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:LDS_EDITION = "__EDITION__"
.\\.venv\\Scripts\\python.exe scripts\\start_studio.py --open
"""


FIND_PYTHON_BAT_SNIPPET = """set PYTHON_CMD=python
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] 未找到 Python。请先安装 Python 3.11 或 3.12，并勾选 Add python.exe to PATH。
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
  )
  set PYTHON_CMD=py -3
)
"""


SETUP_BAT = f"""@echo off
setlocal
cd /d "%~dp0"
set LDS_EDITION=__EDITION__
echo ========================================
echo __APP_TITLE__ Setup
echo ========================================
echo.

{FIND_PYTHON_BAT_SNIPPET}
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
  echo [ERROR] 创建本地运行环境失败。
  pause
  exit /b 1
)

".venv\\Scripts\\python.exe" -m pip install --upgrade pip
".venv\\Scripts\\python.exe" -m pip install -e "."
if errorlevel 1 (
  echo [ERROR] 安装依赖失败，请检查网络或联系老师。
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1

echo.
echo 安装完成。
echo 可以双击 启动软件.bat 启动，或使用桌面快捷方式。
echo 启动后浏览器会自动打开 http://127.0.0.1:8000
pause
"""


SETUP_OCR_BAT = f"""@echo off
setlocal
cd /d "%~dp0"
set LDS_EDITION=__EDITION__
echo ========================================
echo __APP_TITLE__ OCR Setup
echo ========================================
echo.
echo OCR 增强安装会下载 EasyOCR、Torch 和 OpenCV，耗时更长。
echo.

{FIND_PYTHON_BAT_SNIPPET}
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
  echo [ERROR] 创建本地运行环境失败。
  pause
  exit /b 1
)

".venv\\Scripts\\python.exe" -m pip install --upgrade pip
".venv\\Scripts\\python.exe" -m pip install -e ".[ocr]"

if errorlevel 1 (
  echo [ERROR] OCR 增强依赖安装失败。基础功能仍可使用。
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1

echo OCR 增强安装完成。
echo 可以双击 启动软件.bat 启动，或使用桌面快捷方式。
pause
"""


START_BAT = """@echo off
setlocal
cd /d "%~dp0"
set LDS_EDITION=__EDITION__
if not exist ".venv\\Scripts\\python.exe" (
  echo 尚未安装，请先双击 一键安装.bat。
  pause
  exit /b 1
)
echo __APP_TITLE__ 正在启动...
echo 浏览器会自动打开 http://127.0.0.1:8000
".venv\\Scripts\\python.exe" scripts\\start_studio.py --open
pause
"""


UNINSTALL_BAT = """@echo off
setlocal
cd /d "%~dp0"
echo 这会删除本目录中的 .venv 和 workspace。
choice /C YN /M "确认卸载本地运行环境和学生项目数据吗"
if errorlevel 2 exit /b 0

if exist ".venv" rmdir /S /Q ".venv"
if exist "workspace" rmdir /S /Q "workspace"

echo 卸载完成。项目源码目录仍保留，如需彻底删除，请删除整个文件夹。
pause
"""


CREATE_SHORTCUT_PS1 = """$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "__APP_TITLE__.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $root "start.bat"
$shortcut.WorkingDirectory = $root
$shortcut.Description = "启动 __APP_TITLE__"
$shortcut.Save()
Write-Host "已创建桌面快捷方式：$shortcutPath"
"""


WINDOWS_INSTALL_README = """# __APP_TITLE__ Windows 学生机安装说明

## 推荐方式

1. 解压整个安装包。
2. 双击 `一键安装.bat`。
3. 安装完成后双击 `启动软件.bat`，或使用桌面快捷方式。
4. 浏览器会自动打开 `http://127.0.0.1:8000`。

## OCR 增强安装

如果要使用智能博物错别字 OCR 任务的拍照识别，双击：

```text
安装OCR增强.bat
```

OCR 会下载 EasyOCR、Torch 和 OpenCV，速度较慢。文本分类、图像识别、问答、传感器和文字查错任务只需要 `一键安装.bat`。

## 卸载

双击 `卸载本地环境.bat` 会删除本地运行环境 `.venv` 和学生项目数据 `workspace`。

如果需要彻底删除，直接删除整个文件夹。
"""


README = """# __APP_TITLE__ 学生机安装包

## Windows 推荐方式

基础安装：

```text
双击 一键安装.bat
双击 启动软件.bat
```

OCR 增强安装：

```text
双击 安装OCR增强.bat
双击 启动软件.bat
```

## macOS 推荐方式

```text
双击 一键安装.command
双击 启动软件.command
```

第一次双击 .command 文件时，如果系统提示“无法验证开发者”，
请右键点击文件，选择“打开”。

## macOS / Linux 命令行

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

```powershell
.\\install_windows.ps1
.\\start_windows.ps1
```

启动后浏览器会自动打开：

```text
http://127.0.0.1:8000
```

基础安装适合所有课堂任务（含应用内训练）；OCR 增强安装只用于智能博物错别字拍照识别，下载更慢，占用空间更大。
"""


GENERATED_FILES = {
    "README_STUDENT_INSTALL.md": README,
    "README_WINDOWS_SETUP.txt": WINDOWS_INSTALL_README,
    "setup.bat": SETUP_BAT,
    "setup_ocr.bat": SETUP_OCR_BAT,
    "start.bat": START_BAT,
    "uninstall.bat": UNINSTALL_BAT,
    "一键安装.bat": SETUP_BAT,
    "安装OCR增强.bat": SETUP_OCR_BAT,
    "启动软件.bat": START_BAT,
    "卸载本地环境.bat": UNINSTALL_BAT,
    "一键安装.command": INSTALL_COMMAND,
    "启动软件.command": START_COMMAND,
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
    parser.add_argument(
        "--edition",
        choices=["all", "smart_museum", "future_creator"],
        default="all",
        help="App edition to package.",
    )
    return parser.parse_args()


def render_generated_content(content: str, edition: str) -> str:
    return content.replace("__EDITION__", edition).replace("__APP_TITLE__", EDITION_TITLES[edition])


def add_text_file(archive: ZipFile, relative_name: str, content: str, edition: str) -> None:
    info = ZipInfo(f"{PACKAGE_ROOT}/{relative_name}")
    if relative_name.endswith((".sh", ".command")):
        info.external_attr = 0o755 << 16
    archive.writestr(info, render_generated_content(content, edition))


def build_installer(output_path: Path, edition: str = "all") -> Path:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_path in iter_release_files():
            archive.write(
                file_path,
                f"{PACKAGE_ROOT}/{file_path.relative_to(PROJECT_ROOT).as_posix()}",
            )
        for relative_name, content in GENERATED_FILES.items():
            add_text_file(archive, relative_name, content, edition)

    return output_path


def main() -> None:
    args = parse_args()
    output_path = build_installer(args.output, args.edition)
    print(f"Student installer written to {output_path}")


if __name__ == "__main__":
    main()
