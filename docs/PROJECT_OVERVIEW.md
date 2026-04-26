# Lite DeepLearning Studio 项目说明

## 1. 项目定位

Lite DeepLearning Studio 是面向中小学生 AI 竞赛的轻量工作流平台。

它的第一版目标不是做一个完整、庞大的深度学习平台，而是把学生原来在 Jupyter Notebook 中手写几十行代码完成的零散工作，整理成可重复、可导出、可检查的流程。

当前项目路线来自两部分需求：

- GPT 对话中确认的产品策略：默认使用轻量 Workflow + 模板 + 可选助手，不以自主 Agent 或 vibe coding 作为核心。
- 两份竞赛任务文件：
  - `附件4：优创未来项目全国活动任务说明.pdf`
  - `附件5：智能博物项目全国活动任务说明.pdf`

## 2. 当前实现范围

当前版本实现的是 Quick Workflow Mode。

按照最新客户要求，交付形态已经拆成两个独立轻量版：

- 智能博物轻量版：只显示智能博物任务，可打包为 `SmartMuseum-Windows-Setup.zip`。
- 优创未来轻量版：只显示优创未来任务，可打包为 `FutureCreator-Windows-Setup.zip`。

两版统一硬件基线：行空板 M10 + DFRobot 开源硬件外设。

学生可以：

1. 打开首页。
2. 选择比赛。
3. 选择具体任务。
4. 填写项目名称、学生姓名、目标硬件、类别或关键词、数据说明。
5. 生成任务包。
6. 获得 zip 导出包。

导出包包含：

- `README.md`
- `train.py`
- `predict.py`
- `run.py`
- `notebook.ipynb`
- `ai_runtime/core.py`
- `requirements.txt`
- `hardware/README.md`
- `submission/README.md`
- `docs/competition_checklist.md`
- `docs/ai_validation.md`
- `speech/README.md`
- `speech/speech_output.py`
- `speech/voice_config.json`
- `data_sample/sample_input.txt`
- `data_sample/` 中的训练/预测样例数据
- `models/` 模型输出目录

## 3. 对竞赛文件的覆盖

### 3.1 智能博物

竞赛文件要求学生设计具备听说、看认、理解思考能力的智能系统，主题为“遇见非遗，传承有我”。

平台当前覆盖以下任务：

| 平台任务 | 对应竞赛要求 | 当前平台作用 |
|---|---|---|
| 挑战一：认识非遗传承匠人 | 人脸卡片识别，按格式显示与播报人物信息 | 生成本地图像分类训练/推理包和 DFRobot TTS 播报模板 |
| 挑战二：了解非遗专业知识 | 识别知识卡片，判断错别字位置并播报更正 | 生成 EasyOCR 错字检查包和 DFRobot TTS 播报模板 |
| 挑战三：非遗文化分类学览 | 训练并调用自建文本分类模型，判断词语类别 | 生成 scikit-learn 文本分类训练/推理包和 DFRobot TTS 播报模板 |
| 挑战四：非遗文化深化认知 | 训练并调用自建文本分类模型，判断句子中非遗类别与名称 | 生成 scikit-learn 句子分类训练/推理包和 DFRobot TTS 播报模板 |
| 创意拓展 | 非遗传承与宣传，突出 AI 技术和人机交互 | 生成 TF-IDF 知识问答检索包、DFRobot TTS 播报模板和提交材料清单 |

### 3.2 优创未来

竞赛文件要求围绕“具身智能、智慧医疗”，结合机器学习、自然语言处理、智能语音、计算机视觉、自定义图像识别等技术完成创意应用作品。

平台当前覆盖以下任务：

| 平台任务 | 对应竞赛要求 | 当前平台作用 |
|---|---|---|
| 小学组：语音互动与单类图像识别 | 关键词语音互动 1 条，4 类卡片中自选 1 类识别 | 图像识别已做本地训练/推理；语音生成行空板关键词识别模板 |
| 初中组：视觉模型训练与调用 | 关键词语音互动，4 类卡片中自选 2 类识别，视觉模型训练与调用 | 图像模型训练/调用已做本地样例闭环；语音生成行空板关键词识别模板 |
| 高中组：大模型语音互动、视觉识别与运动控制 | 大模型角色语音互动、2 类卡片识别、机械装置夹取 3 个立方体 | 视觉识别已做本地训练/推理；生成行空板 M10 语音接口与 DFRobot 外设扩展接口，大模型和机械闭环后续接入 |
| 图像识别快速模板 | 小学/初中/高中图像识别规定技术要求 | 生成本地图像分类训练/推理包 |
| 传感器决策程序模板 | 智慧医疗创意应用、认知推理决策、硬件搭建 | 生成本地决策树训练/推理包和硬件接口说明 |

## 4. 当前不能替代学生完成的部分

平台当前生成的是可本地运行的 AI 任务包，不自动替学生完成现场全部任务。

仍需学生完成：

- 现场公布关键词、卡片、主题后的配置补充。
- 真实图片、语音、文本数据采集。
- 现场真实数据采集后的模型再训练。
- 真实硬件连接、结构搭建、传感器调试。
- 行空板 M10 真实麦克风语音识别联调和大模型服务。
- 演示视频、实物照片、创作说明的最终整理。
- 现场展示和专家问答准备。

这个边界是有意保留的：当前阶段目标是让学生更快完成可运行项目骨架，而不是把平台做成不可控的自动参赛系统。

## 5. 技术架构

当前使用本地优先架构：

- Python 3.11+
- FastAPI
- Jinja2 server-rendered HTML
- Pydantic
- scikit-learn / joblib / numpy / Pillow
- EasyOCR / torch / OpenCV 作为 OCR 可选重依赖
- speech 模板：DFRobot 串口 TTS、行空板关键词识别接口、行空板 M10 语音接口
- pytest
- ruff
- GitHub 交付说明：`docs/GITHUB_RELEASE.md`
- 学生机安装说明：`docs/INSTALLATION.md`

核心目录：

```text
app/
  main.py
  models.py
  task_catalog.py
  services/
    workspace_service.py
    template_service.py
    export_service.py
  ai_runtime/            # 生成到导出包中的本地 AI runtime
templates/
static/
tests/
docs/
workspace/
```

核心服务：

- `task_catalog.py`：维护两项竞赛和所有任务定义。
- `workspace_service.py`：创建本地项目工作区和元数据。
- `template_service.py`：生成训练脚本、预测脚本、AI runtime、样例数据、Notebook、硬件说明、提交材料说明和竞赛核对清单。
- `export_service.py`：将生成物打包为 zip。
- `speech/` 导出目录：生成语音硬件代码、语音配置和部署说明。
- `scripts/start_studio.py --edition smart_museum`：启动智能博物独立版。
- `scripts/start_studio.py --edition future_creator`：启动优创未来独立版。

## 6. 运行方式

推荐使用 Python 3.11+。

安装依赖：

```bash
python -m pip install fastapi jinja2 pillow pydantic python-multipart uvicorn httpx pytest ruff scikit-learn joblib
python -m pip install easyocr opencv-python-headless torch
```

启动应用：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动独立版本：

```bash
python scripts/start_studio.py --edition smart_museum
python scripts/start_studio.py --edition future_creator
```

打开：

```text
http://127.0.0.1:8000
```

## 7. 测试方式

运行测试：

```bash
python -m pytest -q
```

运行真实 AI 验收：

```bash
python scripts/acceptance_check.py --rounds 5 --require-ai
```

运行包含 Web 入口的验收：

```bash
python scripts/acceptance_check.py --rounds 5 --require-ai --with-web
```

运行 lint：

```bash
python -m ruff check app tests
```

当前测试覆盖：

- 两个比赛是否都在目录中。
- 智能博物是否覆盖四个挑战和创意拓展。
- 优创未来是否覆盖小学、初中、高中和创意应用。
- 每个任务是否能生成它声明的必需文件和 AI runtime。
- 非 OCR 任务是否能在样例数据上真实训练/推理。
- OCR 任务是否生成 EasyOCR 验证包；缺少 EasyOCR/torch/opencv 时是否明确失败。
- 智能博物任务是否生成 DFRobot TTS 模板。
- 优创小学/初中是否生成行空板关键词语音模板。
- 优创高中是否生成行空板 M10 语音接口。
- 导出 zip 是否包含必需文件。
- 首页、任务页、生成页、下载路由是否可用。
- 生成的竞赛核对清单是否包含 PDF 中的关键要求。

## 8. 当前测试结论

当前版本的本地验证结果：

- `python -m pytest -q`：35 passed。
- `python -m ruff check app tests scripts`：All checks passed。
- `python scripts/acceptance_check.py --rounds 5 --require-ai --with-web`：通过，包含 5 轮任务包生成与 AI 运行、首页、10 个任务页；两个独立版本分别只显示本比赛任务、10 次表单生成和 10 个 zip 下载检查，共 71 项检查。

这些结果说明平台可以：

- 展示两个竞赛入口。
- 覆盖两份竞赛文件中的主要任务结构。
- 为每个任务生成标准导出包。
- 生成竞赛要求核对清单。
- 生成提交材料说明。
- 提供 zip 下载入口。
- 为文本分类、句子分类、图像分类、知识问答检索、传感器决策生成本地可运行训练/推理包。
- 为 OCR/错别字任务生成 EasyOCR 验证包；当前 OCR 增强环境已通过 `--require-ai` 验收。
- 为智能博物生成 DFRobot 语音合成模块播报代码。
- 为优创未来小学/初中生成行空板关键词语音互动模板。
- 为优创未来高中生成行空板 M10 语音接口与 DFRobot 外设扩展接口。

测试不能证明真实硬件、真实语音识别、真实大模型或机械控制已经完成。它证明的是：平台可以在本地样例数据上完成非 OCR AI 训练/推理闭环；OCR 真实识别闭环取决于 EasyOCR 增强环境。

## 9. 下一阶段建议

下一阶段应按优先级补现场能力：

1. 把样例数据替换为学生采集的真实现场数据。
2. 接入行空板 M10 真实麦克风 API、DFRobot TTS 串口实物和 DFRobot 外设接口。
3. 高中组再评估本地大模型智能体。
4. 对接 行空板 M10、DFRobot 传感器和执行器外设。
5. 增加真实比赛素材回放测试。
6. 完成 GitHub 仓库发布和学生机安装包实机验证。

短期仍建议保持轻量模式，不要过早加入账号系统、教师端、服务器版和自主 Agent。
