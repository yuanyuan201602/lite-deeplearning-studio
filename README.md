# Lite DeepLearning Studio

Lite DeepLearning Studio 是一个面向中小学生 AI 竞赛的轻量本地工作流工具。它用 FastAPI 和 Jinja2 提供网页入口，帮助学生选择竞赛任务、填写项目信息，并导出可本地运行的训练、推理、硬件说明和提交材料包。

当前覆盖：

- 智能博物：非遗识别、错别字 OCR、文本分类、问答检索与 DFRobot TTS 模板。
- 优创未来：图像识别、传感器决策、语音互动接口、Jetson 语音智能体接口和提交清单。

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

## 常用命令

```bash
python scripts/start_studio.py --host 127.0.0.1 --port 8000
python scripts/start_studio.py --reload
python -m pytest -q
python -m ruff check app scripts packaging tests
python packaging/build_release.py
```

`packaging/build_release.py` 会生成轻量源码发布包，默认输出到 `dist/lite-deeplearning-studio-source.zip`。GitHub 仓库和 Release 交付流程见 [docs/GITHUB_RELEASE.md](docs/GITHUB_RELEASE.md)。

给学生机分发时，推荐生成带安装脚本的安装包：

```bash
python packaging/build_student_installer.py
```

默认输出到 `dist/lite-deeplearning-studio-student-installer.zip`。

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
