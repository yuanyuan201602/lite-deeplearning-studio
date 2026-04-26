# Lite DeepLearning Studio

Lite DeepLearning Studio 是一个面向中小学生 AI 竞赛的轻量本地工作流工具。它用 FastAPI 和 Jinja2 提供网页入口，帮助学生选择竞赛任务、填写项目信息，并导出可本地运行的训练、推理、硬件说明和提交材料包。

当前覆盖：

- 智能博物：非遗识别、错别字 OCR、文本分类、问答检索与 DFRobot TTS 模板。
- 优创未来：图像识别、传感器决策、行空板关键词语音互动、DFRobot 外设接口和提交清单。

客户交付形态拆成两个独立轻量版：

- `智能博物轻量版`
- `优创未来轻量版`

两个版本统一硬件基线：行空板 M10 + DFRobot 开源硬件外设。

## 快速开始

推荐 Python 3.11+。学生机只需要基础安装即可启动网页和生成大多数任务包：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/start_studio.py
```

也可以直接使用 Uvicorn：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开浏览器访问：

```text
http://127.0.0.1:8000
```

## 安装路径

- 基础安装：`python -m pip install -e .`
- OCR 安装：`python -m pip install -e ".[ocr]"`
- 开发安装：`python -m pip install -e ".[dev,ai,ocr]"`

更完整的学生机安装、Windows/macOS 注意事项和常见问题见 [docs/INSTALLATION.md](docs/INSTALLATION.md)。

学生培训文档：

- [智能博物轻量版学生培训文档](docs/TRAINING_SMART_MUSEUM.md)
- [优创未来轻量版学生培训文档](docs/TRAINING_FUTURE_CREATOR.md)
- [培训文档索引](docs/TRAINING_INDEX.md)
- [行空板 M10 + DFRobot 外设硬件选择清单](docs/HARDWARE_CHECKLIST.md)

## 常用命令

```bash
python scripts/start_studio.py --host 127.0.0.1 --port 8000
python scripts/start_studio.py --reload
python scripts/start_studio.py --edition smart_museum
python scripts/start_studio.py --edition future_creator
python -m pytest -q
python -m ruff check app scripts packaging tests
python packaging/build_release.py
```

`packaging/build_release.py` 会生成轻量源码发布包，默认输出到 `dist/lite-deeplearning-studio-source.zip`。GitHub 仓库和 Release 交付流程见 [docs/GITHUB_RELEASE.md](docs/GITHUB_RELEASE.md)。

给学生机分发时，推荐生成带 Windows setup 入口的安装包：

```bash
python packaging/build_student_installer.py
```

默认输出到 `dist/lite-deeplearning-studio-student-installer.zip`。

Windows 学生解压后双击 `一键安装.bat` 安装，再双击 `启动软件.bat` 启动。安装后也会尝试创建桌面快捷方式。

面向 Windows 分发时，也可以生成更直观的文件名：

```bash
python packaging/build_student_installer.py --output dist/LiteDeepLearningStudio-Windows-Setup.zip
```

生成两个独立比赛版本：

```bash
python packaging/build_student_installer.py --edition smart_museum --output dist/SmartMuseum-Windows-Setup.zip
python packaging/build_student_installer.py --edition future_creator --output dist/FutureCreator-Windows-Setup.zip
```

## 项目结构

```text
app/          FastAPI 应用、任务目录和生成服务
templates/    网页模板
static/       页面样式
scripts/      本地启动和验收脚本
packaging/    轻量发布包脚本
docs/         项目、安装、验收和发布文档
tests/        自动化测试
workspace/    本地生成的学生任务包，默认不提交
```

## 测试

安装开发依赖后运行：

```bash
python -m pytest -q
```

需要真实 AI 任务验收时运行：

```bash
python scripts/acceptance_check.py --rounds 5 --require-ai
```

OCR 任务依赖 EasyOCR、OpenCV 和 Torch，安装较重。普通学生机建议先完成基础安装，只有需要错别字 OCR 工作流时再安装 OCR 依赖。
