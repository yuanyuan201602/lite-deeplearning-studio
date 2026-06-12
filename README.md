# Lite DeepLearning Studio

Lite DeepLearning Studio 是面向 K12 学生 AI 竞赛的轻量机器学习工作台，由南昌市第二十三中学用于竞赛训练。学生在浏览器里四步完成一个 AI 项目：

1. **准备数据**：粘贴文本 / 上传图片 / 填写表格，不用写代码。
2. **训练模型**：一键在本机训练，立即看到准确率和每类数据量。
3. **测试效果**：输入新数据实时测试，直观看到分类得分。
4. **导出材料**：一键导出比赛材料包，内含训练好的模型、全部数据、可运行的 Python 程序、硬件部署说明和提交清单。

支持的 AI 能力：文本分类、图像识别、知识问答检索、传感器决策、错别字查错。

竞赛覆盖：

- **智能博物**：人脸介绍、错别字 OCR、词语/句子分类、知识问答与 DFRobot 语音播报模板。
- **优创未来**：图像识别、传感器决策、行空板关键词语音互动与提交清单。

客户交付形态拆成两个独立轻量版（`智能博物轻量版`、`优创未来轻量版`），统一硬件基线：行空板 M10 + DFRobot 开源硬件外设。

## 快速开始

推荐 Python 3.11+。基础安装即包含全部应用内训练能力：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/start_studio.py --open
```

也可以直接使用 Uvicorn：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开浏览器访问 `http://127.0.0.1:8000`。

## 安装路径

- 基础安装：`python -m pip install -e .`（含全部训练能力）
- OCR 安装：`python -m pip install -e ".[ocr]"`（仅错别字任务的拍照识别需要）
- 开发安装：`python -m pip install -e ".[dev,ocr]"`

更完整的学生机安装、Windows/macOS 注意事项和常见问题见 [docs/INSTALLATION.md](docs/INSTALLATION.md)。

学生培训文档：

- [智能博物轻量版学生培训文档](docs/TRAINING_SMART_MUSEUM.md)
- [优创未来轻量版学生培训文档](docs/TRAINING_FUTURE_CREATOR.md)
- [培训文档索引](docs/TRAINING_INDEX.md)
- [行空板 M10 + DFRobot 外设硬件选择清单](docs/HARDWARE_CHECKLIST.md)

## 一键部署

### Windows / macOS 学生机安装包

```bash
python packaging/build_student_installer.py
```

默认输出 `dist/lite-deeplearning-studio-student-installer.zip`。学生解压后：

- Windows：双击 `一键安装.bat` 安装，双击 `启动软件.bat` 启动（自动打开浏览器，并创建桌面快捷方式）。
- macOS：双击 `一键安装.command` 安装，双击 `启动软件.command` 启动。

生成 Windows 风格命名或两个独立比赛版本：

```bash
python packaging/build_student_installer.py --output dist/LiteDeepLearningStudio-Windows-Setup.zip
python packaging/build_student_installer.py --edition smart_museum --output dist/SmartMuseum-Windows-Setup.zip
python packaging/build_student_installer.py --edition future_creator --output dist/FutureCreator-Windows-Setup.zip
```

### 服务器部署（全班共用一个网址）

```bash
docker compose up -d --build
```

支持 `LDS_EDITION` / `LDS_PORT` 环境变量切换版本和端口，学生数据持久化在 `workspace/`。详见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

## 常用命令

```bash
python scripts/start_studio.py --host 127.0.0.1 --port 8000
python scripts/start_studio.py --reload
python scripts/start_studio.py --edition smart_museum
python scripts/start_studio.py --edition future_creator
python -m pytest -q
python -m ruff check app scripts packaging tests
python packaging/build_release.py
python packaging/build_student_installer.py
```

`packaging/build_release.py` 会生成轻量源码发布包，默认输出到 `dist/lite-deeplearning-studio-source.zip`。GitHub 仓库和 Release 交付流程见 [docs/GITHUB_RELEASE.md](docs/GITHUB_RELEASE.md)。

## 项目结构

```text
app/            FastAPI 应用、任务目录、ML 引擎和服务层
app/ml/         应用内训练/预测引擎（文本、图像、问答、传感器、查错）
app/services/   项目持久化、导出包生成
templates/      网页模板（首页、任务页、四步项目工作流）
static/         样式、前端交互脚本、校徽
scripts/        本地启动和验收脚本
packaging/      发布包与学生机安装包脚本
docs/           项目、安装、部署、验收和培训文档
tests/          自动化测试
workspace/      学生项目数据（数据集、模型、导出包），默认不提交
```

更换校徽：用正式校徽覆盖 `static/logo.svg`（保持文件名）即可。

## 测试

安装开发依赖后运行：

```bash
python -m pytest -q
```

基础验收（不含 OCR 拍照）：

```bash
python scripts/acceptance_check.py --rounds 5 --with-web
```

含 OCR 拍照识别的完整验收（需先安装 `.[dev,ocr]`）：

```bash
python -m pip install -e ".[dev,ocr]"
python scripts/acceptance_check.py --rounds 5 --require-ai --with-web
```

OCR 任务的拍照识别依赖 EasyOCR、OpenCV 和 Torch，安装较重。普通学生机建议只做基础安装；应用内的文字查错不需要 OCR 依赖。
