from __future__ import annotations

import csv
from io import StringIO
import json
from pathlib import Path

from PIL import Image, ImageDraw

from app.models import GenerationRequest, ProjectWorkspace, TaskDefinition


class TemplateService:
    def render_task_files(
        self,
        workspace: ProjectWorkspace,
        task: TaskDefinition,
        request: GenerationRequest,
    ) -> list[Path]:
        files = {
            "README.md": self._render_readme(task, request),
            "train.py": self._render_train_py(task),
            "predict.py": self._render_predict_py(task),
            "run.py": self._render_run_py(task, request),
            "ai_runtime/__init__.py": "",
            "ai_runtime/core.py": self._render_ai_core_py(),
            "notebook.ipynb": self._render_notebook(task, request),
            "requirements.txt": self._render_requirements(request),
            "hardware/README.md": self._render_hardware_notes(request),
            "submission/README.md": self._render_submission_notes(task, request),
            "docs/competition_checklist.md": self._render_competition_checklist(task, request),
            "docs/ai_validation.md": self._render_ai_validation(task),
            "speech/README.md": self._render_speech_readme(task, request),
            "speech/speech_output.py": self._render_speech_output_py(task, request),
            "speech/voice_config.json": self._render_voice_config(task, request),
            "data_sample/sample_input.txt": self._render_sample_input(request),
            "models/.gitkeep": "",
        }

        written_files: list[Path] = []
        for relative_path, content in files.items():
            path = workspace.generated_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written_files.append(path)
        written_files.extend(self._write_sample_dataset(workspace.generated_dir, task, request))
        return written_files

    def _render_readme(self, task: TaskDefinition, request: GenerationRequest) -> str:
        labels = ", ".join(request.class_labels) if request.class_labels else "请在 run.py 中补充"
        steps = "\n".join(f"{index}. {step}" for index, step in enumerate(task.starter_steps, 1))
        return f"""# {request.project_name}

任务：{task.title}

学生：{request.student_name or "未填写"}

目标硬件：{request.target_hardware}

AI 能力：{task.ai_capability}

运行依赖：{", ".join(task.runtime_requirements)}

## 任务目标

{task.student_goal}

## 对应竞赛文件

{task.requirement_source}

## 必须覆盖的竞赛要求

{self._markdown_list(task.competition_requirements)}

## 类别或关键词

{labels}

## 数据说明

{request.dataset_notes or "请补充数据来源、类别数量和样例说明。"}

## 推荐步骤

{steps}

## 运行方式

```bash
python run.py
```

Notebook 版本见 `notebook.ipynb`。硬件迁移说明见 `hardware/README.md`。
"""

    def _render_train_py(self, task: TaskDefinition) -> str:
        return f'''from ai_runtime.core import train


if __name__ == "__main__":
    train("{task.ai_capability}")
'''

    def _render_predict_py(self, task: TaskDefinition) -> str:
        return f'''from ai_runtime.core import predict


if __name__ == "__main__":
    predict("{task.ai_capability}")
'''

    def _render_run_py(self, task: TaskDefinition, request: GenerationRequest) -> str:
        paused = ", ".join(task.paused_features) if task.paused_features else "无"
        return f'''"""Run local AI training and prediction for {task.title}."""

from ai_runtime.core import run_pipeline


if __name__ == "__main__":
    print("任务：{task.title}")
    print("项目：{request.project_name}")
    print("AI能力：{task.ai_capability}")
    print("本轮暂停能力：{paused}")
    run_pipeline("{task.ai_capability}")
'''

    def _render_ai_core_py(self) -> str:
        return r'''from __future__ import annotations

import csv
import json
from pathlib import Path

import joblib
import numpy as np
from PIL import Image
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data_sample"
MODELS_DIR = ROOT / "models"
OUTPUTS_DIR = ROOT / "outputs"


def run_pipeline(capability: str) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    train(capability)
    result = predict(capability)
    validation = {
        "capability": capability,
        "status": result.get("status", "ok"),
        "result": result,
    }
    (OUTPUTS_DIR / "ai_validation_result.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(validation, ensure_ascii=False, indent=2))


def train(capability: str) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    if capability == "text_classifier":
        rows = _read_csv(DATA_DIR / "text_samples.csv")
        model = Pipeline(
            [
                ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(1, 3))),
                ("clf", LogisticRegression(max_iter=500)),
            ]
        )
        model.fit([row["text"] for row in rows], [row["label"] for row in rows])
        joblib.dump(model, MODELS_DIR / "text_classifier.joblib")
    elif capability == "image_classifier":
        features, labels = _load_image_dataset(DATA_DIR / "images")
        model = LogisticRegression(max_iter=500)
        model.fit(features, labels)
        joblib.dump(model, MODELS_DIR / "image_classifier.joblib")
    elif capability == "qa_retrieval":
        rows = _read_csv(DATA_DIR / "qa_pairs.csv")
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3))
        matrix = vectorizer.fit_transform([row["question"] for row in rows])
        joblib.dump(
            {"vectorizer": vectorizer, "matrix": matrix, "rows": rows},
            MODELS_DIR / "qa_retrieval.joblib",
        )
    elif capability == "sensor_decision_model":
        rows = _read_csv(DATA_DIR / "sensor_samples.csv")
        features = [
            [float(row["temperature"]), float(row["distance"]), float(row["signal"])]
            for row in rows
        ]
        labels = [row["action"] for row in rows]
        model = DecisionTreeClassifier(max_depth=4, random_state=7)
        model.fit(features, labels)
        joblib.dump(model, MODELS_DIR / "sensor_decision_model.joblib")
    elif capability == "ocr_typo_checker":
        rows = _read_csv(DATA_DIR / "ocr_cases.csv")
        (MODELS_DIR / "ocr_typo_checker.json").write_text(
            json.dumps({"rows": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        raise ValueError(f"Unknown capability: {capability}")


def predict(capability: str) -> dict:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    if capability == "text_classifier":
        model = joblib.load(MODELS_DIR / "text_classifier.joblib")
        samples = _read_csv(DATA_DIR / "predict_text.csv")
        predictions = [
            {"text": row["text"], "prediction": str(model.predict([row["text"]])[0])}
            for row in samples
        ]
        _write_json("predictions.json", predictions)
        return {"status": "ok", "predictions": predictions}
    if capability == "image_classifier":
        model = joblib.load(MODELS_DIR / "image_classifier.joblib")
        image_paths = sorted((DATA_DIR / "predict_images").glob("*.png"))
        predictions = []
        for image_path in image_paths:
            prediction = str(model.predict([_image_features(image_path)])[0])
            predictions.append({"image": image_path.name, "prediction": prediction})
        _write_json("predictions.json", predictions)
        return {"status": "ok", "predictions": predictions}
    if capability == "qa_retrieval":
        store = joblib.load(MODELS_DIR / "qa_retrieval.joblib")
        samples = _read_csv(DATA_DIR / "predict_questions.csv")
        predictions = []
        for row in samples:
            query = store["vectorizer"].transform([row["question"]])
            scores = cosine_similarity(query, store["matrix"])[0]
            best_index = int(np.argmax(scores))
            answer = store["rows"][best_index]["answer"]
            predictions.append({"question": row["question"], "answer": answer})
        _write_json("predictions.json", predictions)
        return {"status": "ok", "predictions": predictions}
    if capability == "sensor_decision_model":
        model = joblib.load(MODELS_DIR / "sensor_decision_model.joblib")
        samples = _read_csv(DATA_DIR / "predict_sensor.csv")
        predictions = []
        for row in samples:
            features = [[float(row["temperature"]), float(row["distance"]), float(row["signal"])]]
            action = str(model.predict(features)[0])
            predictions.append({"input": row, "action": action})
        _write_json("predictions.json", predictions)
        return {"status": "ok", "predictions": predictions}
    if capability == "ocr_typo_checker":
        return _predict_ocr_typo()
    raise ValueError(f"Unknown capability: {capability}")


def _predict_ocr_typo() -> dict:
    rows = _read_csv(DATA_DIR / "ocr_cases.csv")
    try:
        import easyocr  # type: ignore
    except Exception as exc:
        result = {
            "status": "ocr_environment_missing",
            "message": f"EasyOCR/torch is not available: {exc}",
            "text_fallback": [_compare_text(row["correct_text"], row["observed_text"]) for row in rows],
        }
        _write_json("predictions.json", result)
        return result

    reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
    predictions = []
    for row in rows:
        image_path = DATA_DIR / row["image"]
        recognized = "".join(reader.readtext(str(image_path), detail=0))
        predictions.append(
            {
                "image": row["image"],
                "recognized_text": recognized,
                "typos": _compare_text(row["correct_text"], recognized),
            }
        )
    result = {"status": "ok", "predictions": predictions}
    _write_json("predictions.json", result)
    return result


def _compare_text(correct: str, observed: str) -> list[dict]:
    typos = []
    for index, correct_char in enumerate(correct):
        observed_char = observed[index] if index < len(observed) else ""
        if observed_char != correct_char:
            typos.append(
                {
                    "position": index + 1,
                    "observed": observed_char,
                    "correct": correct_char,
                }
            )
    return typos


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _write_json(name: str, data) -> None:
    (OUTPUTS_DIR / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_image_dataset(root: Path) -> tuple[list[list[float]], list[str]]:
    features = []
    labels = []
    for label_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for image_path in sorted(label_dir.glob("*.png")):
            features.append(_image_features(image_path))
            labels.append(label_dir.name)
    return features, labels


def _image_features(path: Path) -> list[float]:
    image = Image.open(path).convert("RGB").resize((32, 32))
    arr = np.asarray(image, dtype=np.float32) / 255.0
    means = arr.mean(axis=(0, 1))
    stds = arr.std(axis=(0, 1))
    return [float(value) for value in np.concatenate([means, stds])]
'''

    def _render_notebook(self, task: TaskDefinition, request: GenerationRequest) -> str:
        cells = [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    f"# {request.project_name}\\n",
                    f"\\n任务：{task.title}\\n",
                    "\\n这个 Notebook 由平台生成，可从上到下直接运行。\\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "from ai_runtime.core import run_pipeline\\n",
                    f"run_pipeline('{task.ai_capability}')\\n",
                ],
            },
        ]
        notebook = {
            "cells": cells,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "pygments_lexer": "ipython3"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        return json.dumps(notebook, ensure_ascii=False, indent=2)

    def _render_requirements(self, request: GenerationRequest) -> str:
        return "\n".join(
            [
                "joblib>=1.5.0",
                "numpy>=2.0.0",
                "pillow>=10.0.0",
                "scikit-learn>=1.5.0",
                "# Optional for OCR tasks:",
                "# easyocr>=1.7.0",
                "# opencv-python-headless>=4.10.0",
                "# torch>=2.3.0",
                "",
            ]
        )

    def _render_hardware_notes(self, request: GenerationRequest) -> str:
        notes = {
            "student_laptop": "在学生笔记本上运行 `python run.py`，确认输出后再整理到作品材料中。",
            "jetson_nano": "建议先在笔记本生成并测试脚本，再复制到 Jetson Nano 的项目目录运行。",
            "raspberry_pi": "建议通过 Thonny、VS Code Remote 或命令行复制脚本到树莓派运行。",
            "esp32": "ESP32 适合接收上位机生成的结果或执行简化控制逻辑，不建议在板上训练模型。",
            "generic": "先在电脑端验证流程，再根据设备接口改造输入输出。",
        }
        return f"""# 硬件使用说明

目标硬件：{request.target_hardware}

{notes[request.target_hardware]}

## 建议

- 先在电脑端运行 `run.py`。
- 确认输入输出格式。
- 再把核心函数迁移到硬件程序。
- 保留本目录中的 README 作为作品说明材料。
"""

    def _render_submission_notes(self, task: TaskDefinition, request: GenerationRequest) -> str:
        if request.competition_slug == "future_creator":
            folder_name = "优创未来-组别-座位号"
            required_materials = [
                "创作说明：作品名称、作品介绍、AI关键代码、数据集或训练内容、AI器材名称、收获与反思",
                "演示视频：MP4，建议不超过4分钟，包含作品介绍和功能演示",
                "实物照片",
            ]
        else:
            folder_name = "智能博物-组别-座位号"
            required_materials = [
                "实物作品",
                "创作说明：创作意图、作品多角度照片、功能说明、程序代码",
                "演示视频：不超过2分钟，包含作品介绍与演示",
            ]

        return f"""# 提交材料说明

建议提交文件夹命名：`{folder_name}`

项目：{request.project_name}

任务：{task.title}

## 必备材料

{self._markdown_list(required_materials)}

## 平台已生成

- `README.md`
- `train.py`
- `predict.py`
- `run.py`
- `notebook.ipynb`
- `ai_runtime/core.py`
- `hardware/README.md`
- `docs/ai_validation.md`
- `speech/README.md`
- `speech/speech_output.py`
- `speech/voice_config.json`
- `docs/competition_checklist.md`

## 仍需学生补充

- 真实现场数据或图片
- 真实硬件连接和运行照片
- 最终演示视频
- 根据现场主题补充的作品介绍
"""

    def _render_competition_checklist(
        self,
        task: TaskDefinition,
        request: GenerationRequest,
    ) -> str:
        return f"""# 竞赛任务核对清单

项目：{request.project_name}

任务：{task.title}

组别：{task.group}

来源：{task.requirement_source}

## 竞赛文件要求

{self._markdown_list(task.competition_requirements)}

## 当前任务包能帮助完成的部分

- 生成可运行的 Python 训练与预测程序
- 在样例数据上完成本地 AI 训练与推理
- 生成可继续调试的 Jupyter Notebook
- 生成硬件迁移说明
- 生成提交材料清单
- 保留类别、数据说明和目标硬件配置

## AI 能力状态

- AI 能力：{task.ai_capability}
- 语音方案：{task.voice_profile}
- 样例数据：{task.sample_dataset_kind}
- 运行依赖：{", ".join(task.runtime_requirements)}
- 本轮暂停能力：{", ".join(task.paused_features) if task.paused_features else "无"}

## 现场前必须人工确认

- 现场公布的关键词、卡片、主题或专家指定识别对象已经填入程序
- 真实硬件可以稳定运行
- 播报或展示格式与竞赛文件完全一致
- 演示视频、实物照片、创作说明已经补齐
"""

    def _render_speech_readme(self, task: TaskDefinition, request: GenerationRequest) -> str:
        if task.voice_profile == "dfrobot_tts_broadcast":
            body = """# 语音播报说明：DFRobot 语音合成模块

智能博物任务只需要把识别结果按比赛规定格式播报出来，不需要语音识别。

推荐连接方式：

- 主控设备通过串口连接 DFRobot 语音合成模块。
- 程序生成播报文本后调用 `speak(text)`。
- 电脑端没有串口模块时会自动退化为 `print`，方便先调试文本格式。

示例：

```python
from speech.speech_output import speak

speak("昆曲属于传统戏剧")
speak("挑战完成")
```
"""
        elif task.voice_profile == "unihiker_keyword_voice":
            body = """# 语音互动说明：行空板关键词识别

优创未来小学组、初中组要求的是“基于关键词识别的人机语音互动1条”。

本模板面向行空板：

- 使用行空板自带麦克风采集语音。
- 把识别到的文本传给 `recognize_keyword(text)`。
- 命中关键词后返回固定回应和动作编号。
- 真实麦克风 API 会因行空板系统版本不同而变化，所以模板保留 `listen_once()` 接口。

先在电脑端用文本调试关键词，再迁移到行空板。
"""
        elif task.voice_profile == "jetson_voice_agent_stub":
            body = """# 语音智能体接口：Jetson Super Nano

高中组后续使用 NVIDIA Jetson Super Nano + 外接麦克风承载语音智能体。

本轮只生成接口和部署说明，不接入真实大模型、不做麦克风闭环：

- `listen_once()`：后续接麦克风录音和语音识别。
- `agent_reply(text)`：后续接本地大模型或局域网模型服务。
- `speak(text)`：后续接 TTS 或外接语音合成模块。

当前代码可用文本输入模拟完整调用链。
"""
        else:
            body = """# 语音说明

当前任务没有硬性语音互动要求。

平台仍保留 `speech_output.py`，方便后续接入播报或语音交互。
"""
        return f"""{body}

## 当前任务

- 项目：{request.project_name}
- 任务：{task.title}
- 语音方案：{task.voice_profile}
"""

    def _render_voice_config(self, task: TaskDefinition, request: GenerationRequest) -> str:
        keywords = request.class_labels or ["开始导诊", "停止"]
        config = {
            "voice_profile": task.voice_profile,
            "project_name": request.project_name,
            "task_title": task.title,
            "keywords": keywords,
            "default_response": self._default_speech_text(task, request),
            "serial": {
                "port": "/dev/ttyUSB0",
                "baudrate": 9600,
                "encoding": "gbk",
            },
            "jetson": {
                "microphone": "external_usb_microphone",
                "llm_runtime": "paused",
                "tts_runtime": "paused",
            },
        }
        return json.dumps(config, ensure_ascii=False, indent=2)

    def _render_speech_output_py(self, task: TaskDefinition, request: GenerationRequest) -> str:
        if task.voice_profile == "dfrobot_tts_broadcast":
            return self._render_dfrobot_tts_py()
        if task.voice_profile == "unihiker_keyword_voice":
            return self._render_unihiker_keyword_py()
        if task.voice_profile == "jetson_voice_agent_stub":
            return self._render_jetson_voice_agent_py()
        return self._render_no_voice_py()

    def _render_dfrobot_tts_py(self) -> str:
        return '''from __future__ import annotations

import json
from pathlib import Path


CONFIG = json.loads((Path(__file__).parent / "voice_config.json").read_text(encoding="utf-8"))


def speak(text: str, port: str | None = None, baudrate: int | None = None) -> None:
    """Send text to a DFRobot serial TTS module, or print when serial is unavailable."""
    serial_config = CONFIG["serial"]
    target_port = port or serial_config["port"]
    target_baudrate = baudrate or serial_config["baudrate"]
    encoding = serial_config["encoding"]
    try:
        import serial  # type: ignore
    except Exception:
        print(f"播报：{text}")
        return

    payload = text.encode(encoding, errors="ignore")
    with serial.Serial(target_port, target_baudrate, timeout=1) as device:
        device.write(payload)


if __name__ == "__main__":
    speak(CONFIG["default_response"])
'''

    def _render_unihiker_keyword_py(self) -> str:
        return '''from __future__ import annotations

import json
from pathlib import Path


CONFIG = json.loads((Path(__file__).parent / "voice_config.json").read_text(encoding="utf-8"))


def listen_once() -> str:
    """Replace this with the unihiker microphone speech API on device."""
    return input("请输入行空板识别到的语音文本：")


def recognize_keyword(text: str) -> dict:
    for keyword in CONFIG["keywords"]:
        if keyword and keyword in text:
            return {
                "matched": True,
                "keyword": keyword,
                "reply": CONFIG["default_response"],
                "action": "voice_keyword_matched",
            }
    return {
        "matched": False,
        "keyword": "",
        "reply": "没有识别到指定关键词",
        "action": "no_match",
    }


def speak(text: str) -> None:
    """Use UNIHIKER speaker/TTS here; print is kept for desktop debugging."""
    print(f"行空板播报：{text}")


def run_once() -> dict:
    result = recognize_keyword(listen_once())
    speak(result["reply"])
    return result


if __name__ == "__main__":
    print(run_once())
'''

    def _render_jetson_voice_agent_py(self) -> str:
        return '''from __future__ import annotations

import json
from pathlib import Path


CONFIG = json.loads((Path(__file__).parent / "voice_config.json").read_text(encoding="utf-8"))


def listen_once() -> str:
    """Future hook: external microphone ASR on Jetson Super Nano."""
    return input("请输入外接麦克风识别文本：")


def agent_reply(text: str) -> str:
    """Future hook: local LLM agent. Current version keeps deterministic fallback."""
    return f"我是智慧医疗助手，已收到你的问题：{text}"


def speak(text: str) -> None:
    """Future hook: TTS output on Jetson or external speech module."""
    print(f"Jetson播报：{text}")


def run_once() -> str:
    reply = agent_reply(listen_once())
    speak(reply)
    return reply


if __name__ == "__main__":
    run_once()
'''

    def _render_no_voice_py(self) -> str:
        return '''from __future__ import annotations


def speak(text: str) -> None:
    print(f"播报：{text}")


if __name__ == "__main__":
    speak("当前任务没有硬性语音互动要求")
'''

    def _default_speech_text(self, task: TaskDefinition, request: GenerationRequest) -> str:
        if task.voice_profile == "unihiker_keyword_voice":
            return "您好，我已经识别到关键词，正在执行比赛任务。"
        if task.voice_profile == "jetson_voice_agent_stub":
            return "您好，我是智慧医疗语音助手。"
        labels = request.class_labels or ["昆曲", "传统戏剧"]
        if task.slug == "heritage_text_classifier":
            return f"{labels[0]}属于{labels[1] if len(labels) > 1 else '传统戏剧'}"
        if task.slug == "heritage_sentence_classifier":
            return "这是非遗传统技艺类别的制陶技艺"
        if task.slug == "heritage_ocr_typo":
            return "第4个字有误，请更正为主"
        if task.slug == "heritage_face_intro":
            return "这是林女士，传统戏剧中京剧传承人"
        return "挑战完成"

    def _render_ai_validation(self, task: TaskDefinition) -> str:
        ocr_note = ""
        if task.ai_capability == "ocr_typo_checker":
            ocr_note = (
                "\nOCR 任务需要 EasyOCR 和 torch。缺少依赖时，`run.py` 会输出 "
                "`ocr_environment_missing`，不能视为 OCR 能力通过。\n"
            )
        return f"""# AI 验证说明

AI 能力：{task.ai_capability}

运行：

```bash
python run.py
```

预期：

- `models/` 中产生模型或配置文件。
- `outputs/predictions.json` 中产生预测结果。
- `outputs/ai_validation_result.json` 中记录 AI 能力状态。
{ocr_note}
"""

    def _write_sample_dataset(
        self,
        generated_dir: Path,
        task: TaskDefinition,
        request: GenerationRequest,
    ) -> list[Path]:
        source_files: list[str]
        if task.sample_dataset_kind == "text":
            paths = self._write_text_dataset(generated_dir, request)
            source_files = ["data_sample/text_samples.csv"]
        elif task.sample_dataset_kind == "image":
            paths = self._write_image_dataset(generated_dir, request)
            source_files = ["data_sample/images/", "data_sample/predict_images/"]
        elif task.sample_dataset_kind == "qa":
            paths = self._write_qa_dataset(generated_dir, request)
            source_files = ["data_sample/qa_pairs.csv"]
        elif task.sample_dataset_kind == "sensor":
            paths = self._write_sensor_dataset(generated_dir, request)
            source_files = ["data_sample/sensor_samples.csv"]
        else:
            paths = self._write_ocr_dataset(generated_dir, request)
            source_files = ["data_sample/ocr_cases.csv"]
        paths.append(self._write_data_manifest(generated_dir, task, request, source_files))
        return paths

    def _write_text_dataset(self, generated_dir: Path, request: GenerationRequest) -> list[Path]:
        if request.text_csv.strip():
            sample = self._normalize_csv(request.text_csv, ["text", "label"])
        else:
            labels = request.class_labels or ["传统戏剧", "传统技艺", "传统美术"]
            rows = [
                ("昆曲 唱腔 舞台 表演", labels[0]),
                ("四平戏 地方 戏曲 剧目", labels[0]),
                ("德化瓷 烧制 陶土 窑炉", labels[1 % len(labels)]),
                ("蜡染 技艺 染布 图案", labels[1 % len(labels)]),
                ("剪纸 红纸 图样 民俗", labels[2 % len(labels)]),
                ("苏绣 针线 图案 美术", labels[2 % len(labels)]),
            ]
            sample = self._csv(["text", "label"], rows)
        labels = request.class_labels or ["传统戏剧", "传统技艺", "传统美术"]
        predict_rows = [
            ("昆曲 非遗 舞台", ""),
            ("制陶 泥土 烧制", ""),
            ("剪纸 民俗 图案", ""),
        ]
        predict = self._csv(["text", "label"], predict_rows)
        return self._write_files(
            generated_dir,
            {
                "data_sample/text_samples.csv": sample,
                "data_sample/predict_text.csv": predict,
            },
        )

    def _write_qa_dataset(self, generated_dir: Path, request: GenerationRequest) -> list[Path]:
        if request.qa_text.strip():
            qa_pairs = self._qa_to_csv(request.qa_text)
        else:
            qa_pairs = self._csv(
                ["question", "answer"],
                [
                    ("什么是非遗", "非遗是世代相传的传统文化表现形式。"),
                    ("为什么要保护非遗", "保护非遗有助于传承文化记忆和地方智慧。"),
                    ("人工智能能怎样帮助非遗", "AI 可以帮助识别、整理、推荐和传播非遗内容。"),
                ],
            )
        return self._write_files(
            generated_dir,
            {
                "data_sample/qa_pairs.csv": qa_pairs,
                "data_sample/predict_questions.csv": self._csv(
                    ["question"],
                    [
                        ("AI 如何帮助非遗传播",),
                        ("保护非遗有什么意义",),
                    ],
                ),
            },
        )

    def _write_sensor_dataset(self, generated_dir: Path, request: GenerationRequest) -> list[Path]:
        if request.sensor_csv.strip():
            sensor_samples = self._normalize_csv(
                request.sensor_csv,
                ["temperature", "distance", "signal", "action"],
            )
        else:
            sensor_samples = self._csv(
                ["temperature", "distance", "signal", "action"],
                [
                    (38.5, 12, 1, "提醒就诊"),
                    (36.5, 30, 0, "继续观察"),
                    (39.2, 8, 1, "紧急提示"),
                    (37.0, 45, 0, "继续观察"),
                    (38.0, 15, 1, "提醒就诊"),
                ],
            )
        return self._write_files(
            generated_dir,
            {
                "data_sample/sensor_samples.csv": sensor_samples,
                "data_sample/predict_sensor.csv": self._csv(
                    ["temperature", "distance", "signal"],
                    [
                        (38.8, 10, 1),
                        (36.8, 42, 0),
                    ],
                ),
            },
        )

    def _write_ocr_dataset(self, generated_dir: Path, request: GenerationRequest) -> list[Path]:
        correct_text = request.ocr_correct_text.strip() or "保护为主抢救第一"
        observed_text = request.ocr_observed_text.strip() or "保护为王抢救第一"
        paths = self._write_files(
            generated_dir,
            {
                "data_sample/ocr_cases.csv": self._csv(
                    ["image", "correct_text", "observed_text"],
                    [
                        ("ocr_card.png", correct_text, observed_text),
                    ],
                )
            },
        )
        image_path = generated_dir / "data_sample" / "ocr_card.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (420, 96), "white")
        draw = ImageDraw.Draw(image)
        draw.text((16, 32), observed_text, fill="black")
        image.save(image_path)
        paths.append(image_path)
        return paths

    def _write_image_dataset(
        self,
        generated_dir: Path,
        request: GenerationRequest,
    ) -> list[Path]:
        labels = request.class_labels or ["红色卡片", "绿色卡片", "蓝色卡片"]
        colors = [(220, 60, 60), (60, 170, 90), (70, 100, 220)]
        paths: list[Path] = []
        for index, label in enumerate(labels[:3]):
            safe_label = self._safe_label(label)
            for sample_index in range(3):
                path = generated_dir / "data_sample" / "images" / safe_label / f"{sample_index}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                color = tuple(min(255, max(0, c + sample_index * 8)) for c in colors[index % 3])
                image = Image.new("RGB", (64, 64), color)
                image.save(path)
                paths.append(path)
            predict_path = generated_dir / "data_sample" / "predict_images" / f"{safe_label}.png"
            predict_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (64, 64), colors[index % 3]).save(predict_path)
            paths.append(predict_path)
        return paths

    def _write_files(self, generated_dir: Path, files: dict[str, str]) -> list[Path]:
        paths: list[Path] = []
        for relative_path, content in files.items():
            path = generated_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            paths.append(path)
        return paths

    def _csv(self, headers: list[str], rows: list[tuple]) -> str:
        output = StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)
        return output.getvalue()

    def _normalize_csv(self, raw_csv: str, expected_headers: list[str]) -> str:
        reader = csv.DictReader(StringIO(raw_csv.strip()))
        if reader.fieldnames is None:
            return self._csv(expected_headers, [])
        rows = [
            tuple((row.get(header) or "").strip() for header in expected_headers)
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
        return self._csv(expected_headers, rows)

    def _qa_to_csv(self, raw_text: str) -> str:
        reader = csv.reader(StringIO(raw_text.strip()))
        rows = []
        for row in reader:
            if len(row) >= 2:
                rows.append((row[0].strip(), row[1].strip()))
                continue
            line = row[0].strip() if row else ""
            if "\t" in line:
                question, answer = line.split("\t", 1)
                rows.append((question.strip(), answer.strip()))
        return self._csv(["question", "answer"], rows)

    def _write_data_manifest(
        self,
        generated_dir: Path,
        task: TaskDefinition,
        request: GenerationRequest,
        source_files: list[str],
    ) -> Path:
        manifest = {
            "data_origin": self._data_origin(task, request),
            "sample_dataset_kind": task.sample_dataset_kind,
            "source_files": source_files,
        }
        path = generated_dir / "data_sample" / "data_manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _data_origin(self, task: TaskDefinition, request: GenerationRequest) -> str:
        user_data_by_kind = {
            "text": request.text_csv,
            "qa": request.qa_text,
            "sensor": request.sensor_csv,
            "ocr": f"{request.ocr_correct_text}{request.ocr_observed_text}",
            "image": "",
        }
        return "user" if user_data_by_kind[task.sample_dataset_kind].strip() else "sample"

    def _safe_label(self, label: str) -> str:
        return "".join(char if char.isalnum() else "_" for char in label) or "label"

    def _render_sample_input(self, request: GenerationRequest) -> str:
        labels = request.class_labels or ["刺绣", "陶艺", "剪纸"]
        return "\n".join(f"{label}\t这里填写一个样例输入" for label in labels) + "\n"

    def _markdown_list(self, items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)
