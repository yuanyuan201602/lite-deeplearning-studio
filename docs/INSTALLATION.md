# 学生机安装说明

本文面向学生自带电脑、机房电脑和教师演示电脑。推荐使用 Python 3.11 或 3.12，并优先在虚拟环境中安装。

当前交付拆成两个独立轻量版：

- 智能博物轻量版：只显示智能博物任务。
- 优创未来轻量版：只显示优创未来任务。

两版统一硬件基线：行空板 M10 + DFRobot 开源硬件外设。

## 1. 准备 Python

确认 Python 可用：

```bash
python --version
```

如果系统只提供 `python3`，后续命令中的 `python` 可以替换为 `python3`。

## 2. 获取代码

从 GitHub 下载源码 zip，或克隆仓库：

```bash
git clone https://github.com/<your-org>/lite-deeplearning-studio.git
cd lite-deeplearning-studio
```

如果使用 GitHub Release 附件，解压 `lite-deeplearning-studio-source.zip` 后进入目录即可。

## 3. 基础安装

基础安装适合大多数学生机，用于打开网页、选择任务、生成导出包，以及运行非 OCR 的轻量样例。

macOS / Linux：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python scripts/start_studio.py
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python scripts/start_studio.py
```

启动后访问：

```text
http://127.0.0.1:8000
```

等价启动命令：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 4. OCR 安装

OCR 安装用于智能博物错别字检查等需要 EasyOCR 的任务。该路径会安装 Torch、OpenCV 和 EasyOCR，下载时间更长，对磁盘和网络要求更高。

```bash
python -m pip install -e ".[ocr]"
python scripts/start_studio.py
```

如果学生机网络较慢，建议教师提前在机房环境中验证安装，或只在需要 OCR 的机器上安装该路径。

## 5. 开发安装

开发安装适合教师、助教或需要改代码的同学，包含测试、lint、轻量 AI 样例和 OCR 依赖。

```bash
python -m pip install -e ".[dev,ai,ocr]"
python -m pytest -q
python -m ruff check app scripts packaging tests
python scripts/start_studio.py --reload
```

如果不需要 OCR，可以使用：

```bash
python -m pip install -e ".[dev,ai]"
```

## 6. 生成发布包

教师或维护者可以生成一个适合上传到 GitHub Release 的源码包：

```bash
python packaging/build_release.py
```

默认输出：

```text
dist/lite-deeplearning-studio-source.zip
```

发布包会包含应用源码、模板、样式、文档、脚本和测试，不包含 `workspace/`、`tmp/`、虚拟环境、缓存和旧 zip。

也可以生成更适合直接发给学生机的安装包：

```bash
python packaging/build_student_installer.py
```

默认输出：

```text
dist/lite-deeplearning-studio-student-installer.zip
```

Windows 学生机也可以生成更像 setup 分发包的文件名：

```bash
python packaging/build_student_installer.py --output dist/LiteDeepLearningStudio-Windows-Setup.zip
```

生成两个独立比赛版本：

```bash
python packaging/build_student_installer.py --edition smart_museum --output dist/SmartMuseum-Windows-Setup.zip
python packaging/build_student_installer.py --edition future_creator --output dist/FutureCreator-Windows-Setup.zip
```

Windows 学生机推荐使用类似 setup 的双击安装入口：

- 基础安装：双击 `一键安装.bat`
- OCR 增强安装：双击 `安装OCR增强.bat`
- 启动：双击 `启动软件.bat`，或使用安装后生成的桌面快捷方式
- 卸载本地运行环境：双击 `卸载本地环境.bat`

包内也保留英文入口：`setup.bat`、`setup_ocr.bat`、`start.bat`、`uninstall.bat`，方便部分 Windows 环境处理中文文件名异常时使用。

其他系统按系统运行：

- macOS / Linux：`./install_macos_linux.sh`，然后 `./start_macos_linux.sh`
- Windows PowerShell 备用方式：`.\install_windows.ps1`，然后 `.\start_windows.ps1`

如果需要 OCR 增强能力，在安装脚本后追加 `ocr`：

```bash
./install_macos_linux.sh ocr
```

```powershell
.\install_windows.ps1 ocr
```

## 7. 常见问题

### 端口被占用

换一个端口启动：

```bash
python scripts/start_studio.py --port 8010
```

### `python` 命令不存在

尝试使用：

```bash
python3 scripts/start_studio.py
```

### OCR 安装很慢

先完成基础安装。只有使用 OCR 工作流时，再执行 OCR 安装命令。

### 不要提交本地生成任务包

学生生成的任务包会放在 `workspace/`，该目录默认由 `.gitignore` 忽略。
