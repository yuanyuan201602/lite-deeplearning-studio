from __future__ import annotations

import csv
import math
import struct
import wave
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
        user_images: dict[str, Path] | None = None,
        user_audio: dict[str, Path] | None = None,
    ) -> list[Path]:
        files = {
            "包内文件说明.md": self._render_file_manifest(task, request),
            "README.md": self._render_readme(task, request),
            "train.py": self._render_train_py(task),
            "predict.py": self._render_predict_py(task),
            "run.py": self._render_run_py(task, request),
            "run_on_unihiker.py": self._render_run_on_unihiker_py(task),
            "setup_unihiker.sh": self._render_setup_unihiker_sh(),
            "deploy.sh": self._render_deploy_sh(request),
            "deploy.bat": self._render_deploy_bat(request),
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
            "creative_examples/01_display_result.py": self._render_creative_example_display(),
            "creative_examples/02_trigger_buzzer.py": self._render_creative_example_buzzer(),
            "creative_examples/03_count_and_log.py": self._render_creative_example_counter(),
            "creative_examples/04_servo_control.py": self._render_creative_example_servo(),
        }

        written_files: list[Path] = []
        for relative_path, content in files.items():
            path = workspace.generated_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written_files.append(path)
        written_files.extend(
            self._write_sample_dataset(
                workspace.generated_dir, task, request, user_images, user_audio
            )
        )
        return written_files

    def _render_file_manifest(self, task: TaskDefinition, request: GenerationRequest) -> str:
        """A student-friendly guide to what each file in the package is for."""
        model_file = f"models/{task.ai_capability}.joblib"
        return f"""# 包内文件说明 · {request.project_name}

这个材料包里的文件比较多，但**不是每个都要你动手**。下面按重要程度分组说明，
先看「① 核心运行」就够跑通模型了；部署到硬件、参加比赛时再看后面几组。

---

## ① 核心运行（最重要，先看这些）

| 文件 / 文件夹 | 作用 |
| --- | --- |
| `README.md` | 作品总说明：任务目标、怎么运行。先读它。 |
| `predict.py` | 命令行预测脚本。在电脑上 `python predict.py` 就能用模型，**评审验证的核心**。 |
| `run.py` | 通用运行入口，会调用训练好的模型做预测。 |
| `{model_file}` | 训练好的模型文件，predict.py / run.py 靠它工作。**不要删**。 |
| `models/model.meta.json` | 模型的配置信息（特征方式等），和模型文件配套。 |
| `ai_runtime/` | 模型加载和预测的核心代码（`predict_raw()`），上面的脚本都会用到。 |
| `requirements.txt` | 运行需要的 Python 库清单，`pip install -r requirements.txt` 一次装好。 |
| 你的数据文件夹 / `data_sample/` | 你在第 1 步准备的数据，以及一份示例输入，方便测试。 |

## ② 重新训练（想自己再练一遍时看）

| 文件 | 作用 |
| --- | --- |
| `train.py` | 用包里的数据重新训练模型的脚本。 |
| `notebook.ipynb` | Jupyter 笔记本版流程，适合一步步看、做教学演示。 |

## ③ 行空板 / 硬件部署（要把模型放到板子上时看）

| 文件 | 作用 |
| --- | --- |
| `run_on_unihiker.py` | 在行空板 M10 上运行的脚本，带一个可自由发挥的「创意区域」。 |
| `setup_unihiker.sh` | 在板子上一键安装依赖。 |
| `deploy.sh` / `deploy.bat` | 把材料包传到板子上（Mac/Linux 用 .sh，Windows 用 .bat）。 |
| `hardware/README.md` | 硬件接线和迁移说明。 |
| `creative_examples/` | 4 个扩展示例：显示结果、蜂鸣器、计数记录、舵机控制，给创意发挥用。 |

## ④ 语音播报（任务需要说话时看）

| 文件 | 作用 |
| --- | --- |
| `speech/speech_output.py` | 把预测结果用语音读出来。 |
| `speech/voice_config.json` | 语音参数配置（音色、语速等）。 |
| `speech/README.md` | 语音功能的使用说明。 |

## ⑤ 比赛提交（参加竞赛时看）

| 文件 | 作用 |
| --- | --- |
| `submission/README.md` | 提交材料的组织说明。 |
| `docs/competition_checklist.md` | 比赛提交清单，逐项对照检查。 |
| `docs/ai_validation.md` | 如何证明模型真的能用的验证说明。 |

---

**一句话**：只是练习，关注 ①；要上板子，加看 ③④；要交比赛，再看 ⑤。
"""

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
import wave
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

# Must mirror app/ml/qa_retrieval.py so the bundled in-app model keeps working.
# Longer words first so "为什么" is removed before "什么".
QA_QUESTION_STOPWORDS = [
    "为什么", "怎么样", "什么", "怎样", "怎么", "如何", "哪些", "哪个", "哪里",
    "请问", "一下", "是", "的", "吗", "呢", "啊", "？", "?",
]


def _normalize_question(text: str) -> str:
    stripped = "".join(text.split())
    normalized = stripped
    for word in QA_QUESTION_STOPWORDS:
        normalized = normalized.replace(word, "")
    return normalized or stripped


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
        feature_mode = _active_image_feature_mode()
        features, labels = _load_image_dataset(DATA_DIR / "images", feature_mode)
        model = LogisticRegression(max_iter=1000)
        model.fit(features, labels)
        joblib.dump(
            {"model": model, "feature_mode": feature_mode},
            MODELS_DIR / "image_classifier.joblib",
        )
    elif capability == "audio_classifier":
        features, labels = _load_audio_dataset(DATA_DIR / "audio")
        model = LogisticRegression(max_iter=1000)
        model.fit(features, labels)
        joblib.dump(model, MODELS_DIR / "audio_classifier.joblib")
    elif capability == "qa_retrieval":
        rows = _read_csv(DATA_DIR / "qa_pairs.csv")
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3))
        matrix = vectorizer.fit_transform([_normalize_question(row["question"]) for row in rows])
        joblib.dump(
            {"vectorizer": vectorizer, "matrix": matrix, "rows": rows},
            MODELS_DIR / "qa_retrieval.joblib",
        )
    elif capability == "sensor_decision_model":
        feature_names, features, labels = _read_sensor_csv(DATA_DIR / "sensor_samples.csv")
        model = DecisionTreeClassifier(max_depth=4, random_state=7)
        model.fit(features, labels)
        joblib.dump(
            {"model": model, "feature_names": feature_names},
            MODELS_DIR / "sensor_decision_model.joblib",
        )
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
        store = joblib.load(MODELS_DIR / "image_classifier.joblib")
        if not isinstance(store, dict):
            store = {"model": store, "feature_mode": "pixel"}
        model = store["model"]
        feature_mode = store.get("feature_mode", "pixel")
        image_paths = sorted(
            path
            for path in (DATA_DIR / "predict_images").glob("*")
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
        )
        predictions = []
        for image_path in image_paths:
            prediction = str(model.predict([_image_features(image_path, feature_mode)])[0])
            predictions.append({"image": image_path.name, "prediction": prediction})
        _write_json("predictions.json", predictions)
        return {"status": "ok", "predictions": predictions}
    if capability == "audio_classifier":
        model = joblib.load(MODELS_DIR / "audio_classifier.joblib")
        clips = sorted((DATA_DIR / "predict_audio").glob("*.wav"))
        predictions = []
        for clip in clips:
            prediction = str(model.predict([_audio_features(clip)])[0])
            predictions.append({"audio": clip.name, "prediction": prediction})
        _write_json("predictions.json", predictions)
        return {"status": "ok", "predictions": predictions}
    if capability == "qa_retrieval":
        store = joblib.load(MODELS_DIR / "qa_retrieval.joblib")
        samples = _read_csv(DATA_DIR / "predict_questions.csv")
        predictions = []
        for row in samples:
            query = store["vectorizer"].transform([_normalize_question(row["question"])])
            scores = cosine_similarity(query, store["matrix"])[0]
            best_index = int(np.argmax(scores))
            answer = store["rows"][best_index]["answer"]
            predictions.append({"question": row["question"], "answer": answer})
        _write_json("predictions.json", predictions)
        return {"status": "ok", "predictions": predictions}
    if capability == "sensor_decision_model":
        store = joblib.load(MODELS_DIR / "sensor_decision_model.joblib")
        model = store["model"]
        feature_names = store["feature_names"]
        samples = _read_csv(DATA_DIR / "predict_sensor.csv")
        predictions = []
        for row in samples:
            features = [[float(row[name]) for name in feature_names]]
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


def _read_sensor_csv(path: Path) -> tuple[list[str], list[list[float]], list[str]]:
    """Header-driven: every column except the last is a numeric feature, the last is the action."""
    with path.open(encoding="utf-8", newline="") as file:
        rows = [row for row in csv.reader(file) if any(cell.strip() for cell in row)]
    feature_names = [cell.strip() for cell in rows[0][:-1]]
    features = [[float(cell) for cell in row[:-1]] for row in rows[1:]]
    labels = [row[-1].strip() for row in rows[1:]]
    return feature_names, features, labels


def _write_json(name: str, data) -> None:
    (OUTPUTS_DIR / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_image_dataset(root: Path, feature_mode: str) -> tuple[list[list[float]], list[str]]:
    features = []
    labels = []
    for label_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for image_path in sorted(label_dir.glob("*")):
            if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}:
                continue
            features.append(_image_features(image_path, feature_mode))
            labels.append(label_dir.name)
    return features, labels


AUDIO_SAMPLE_RATE = 16000
AUDIO_FRAME_SIZE = 1024
AUDIO_HOP_SIZE = 512
AUDIO_N_BANDS = 16


def _decode_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        rate = reader.getframerate()
        raw = reader.readframes(reader.getnframes())
    if sample_width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    elif sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")
    if channels > 1:
        samples = samples[: len(samples) // channels * channels]
        samples = samples.reshape(-1, channels).mean(axis=1)
    if rate != AUDIO_SAMPLE_RATE and len(samples) > 1:
        duration = len(samples) / rate
        target_count = max(int(duration * AUDIO_SAMPLE_RATE), 1)
        positions = np.linspace(0.0, len(samples) - 1.0, target_count)
        samples = np.interp(positions, np.arange(len(samples)), samples)
    return samples[: AUDIO_SAMPLE_RATE * 10]


def _audio_features(path: Path) -> list[float]:
    # Must mirror app/ml/audio_classifier.py so the bundled in-app model keeps working.
    samples = _decode_wav(path)
    window = np.hanning(AUDIO_FRAME_SIZE)
    band_rows = []
    rms_values = []
    zcr_values = []
    for start in range(0, len(samples) - AUDIO_FRAME_SIZE + 1, AUDIO_HOP_SIZE):
        frame = samples[start : start + AUDIO_FRAME_SIZE]
        spectrum = np.abs(np.fft.rfft(frame * window))
        bands = np.array_split(spectrum, AUDIO_N_BANDS)
        band_rows.append(np.log1p(np.array([band.mean() for band in bands])))
        rms_values.append(float(np.sqrt(np.mean(frame**2))))
        zcr_values.append(float(np.mean(np.abs(np.diff(np.sign(frame))) > 0)))
    bands_matrix = np.array(band_rows)
    features = np.concatenate(
        [
            bands_matrix.mean(axis=0),
            bands_matrix.std(axis=0),
            [np.mean(rms_values), np.std(rms_values)],
            [np.mean(zcr_values), np.std(zcr_values)],
        ]
    )
    return features.tolist()


def _load_audio_dataset(root: Path) -> tuple[list[list[float]], list[str]]:
    features: list[list[float]] = []
    labels: list[str] = []
    for label_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for clip in sorted(label_dir.glob("*.wav")):
            features.append(_audio_features(clip))
            labels.append(label_dir.name)
    return features, labels


# ---- image features (must stay identical to the studio's in-app pipeline) ----

PRETRAINED_EMBEDDER = MODELS_DIR / "pretrained" / "mobilenetv2.onnx"
EMBED_INPUT_SIZE = (224, 224)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
_EMBEDDER_SESSION = None


def _embedder_session():
    global _EMBEDDER_SESSION
    if _EMBEDDER_SESSION is None and PRETRAINED_EMBEDDER.is_file():
        import onnxruntime

        _EMBEDDER_SESSION = onnxruntime.InferenceSession(
            str(PRETRAINED_EMBEDDER), providers=["CPUExecutionProvider"]
        )
    return _EMBEDDER_SESSION


def _active_image_feature_mode() -> str:
    if PRETRAINED_EMBEDDER.is_file():
        try:
            import onnxruntime  # noqa: F401
        except ImportError:
            return "pixel"
        return "mobilenet_v2"
    return "pixel"


def _image_features(path: Path, feature_mode: str = "pixel") -> list[float]:
    image = Image.open(path).convert("RGB")
    if feature_mode == "mobilenet_v2":
        session = _embedder_session()
        if session is None:
            raise RuntimeError(
                "模型使用 MobileNet 特征训练，需要 models/pretrained/mobilenetv2.onnx "
                "和 onnxruntime（pip install onnxruntime）。"
            )
        resized = image.resize(EMBED_INPUT_SIZE)
        pixels = np.asarray(resized, dtype=np.float32) / 255.0
        normalized = (pixels - IMAGENET_MEAN) / IMAGENET_STD
        batch = normalized.transpose(2, 0, 1)[np.newaxis, :]
        output = session.run(None, {session.get_inputs()[0].name: batch})[0]
        return output[0].astype(np.float64).tolist()
    arr = np.asarray(image.resize((32, 32)), dtype=np.float64) / 255.0
    return arr.flatten().tolist()


def _image_features_from_bytes(data: bytes, feature_mode: str = "pixel") -> list[float]:
    from io import BytesIO
    image = Image.open(BytesIO(data)).convert("RGB")
    if feature_mode == "mobilenet_v2":
        session = _embedder_session()
        if session is None:
            raise RuntimeError(
                "模型使用 MobileNet 特征训练，需要 models/pretrained/mobilenetv2.onnx 和 onnxruntime。"
            )
        resized = image.resize(EMBED_INPUT_SIZE)
        pixels = np.asarray(resized, dtype=np.float32) / 255.0
        normalized = (pixels - IMAGENET_MEAN) / IMAGENET_STD
        batch = normalized.transpose(2, 0, 1)[np.newaxis, :]
        output = session.run(None, {session.get_inputs()[0].name: batch})[0]
        return output[0].astype(np.float64).tolist()
    arr = np.asarray(image.resize((32, 32)), dtype=np.float64) / 255.0
    return arr.flatten().tolist()


def _audio_features_from_bytes(data: bytes) -> list[float]:
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        return _audio_features(Path(tmp_path))
    finally:
        os.unlink(tmp_path)


def predict_raw(capability: str, data) -> dict:
    """Predict directly from raw data — used by run_on_unihiker.py.

    data types by capability:
      text_classifier / qa_retrieval : str
      image_classifier               : bytes (JPEG/PNG) or Path
      audio_classifier               : bytes (WAV) or Path
      sensor_decision_model          : dict[str, float | str]
    """
    OUTPUTS_DIR.mkdir(exist_ok=True)
    if capability == "text_classifier":
        model = joblib.load(MODELS_DIR / "text_classifier.joblib")
        label = str(model.predict([data])[0])
        scores = {c: float(p) for c, p in zip(model.classes_, model.predict_proba([data])[0])}
        return {"label": label, "scores": scores}
    if capability == "image_classifier":
        store = joblib.load(MODELS_DIR / "image_classifier.joblib")
        if not isinstance(store, dict):
            store = {"model": store, "feature_mode": "pixel"}
        model = store["model"]
        feature_mode = store.get("feature_mode", "pixel")
        if isinstance(data, (bytes, bytearray)):
            features = _image_features_from_bytes(bytes(data), feature_mode)
        else:
            features = _image_features(Path(data), feature_mode)
        label = str(model.predict([features])[0])
        scores = {c: float(p) for c, p in zip(model.classes_, model.predict_proba([features])[0])}
        return {"label": label, "scores": scores}
    if capability == "audio_classifier":
        model = joblib.load(MODELS_DIR / "audio_classifier.joblib")
        if isinstance(data, (bytes, bytearray)):
            features = _audio_features_from_bytes(bytes(data))
        else:
            features = _audio_features(Path(data))
        label = str(model.predict([features])[0])
        scores = {c: float(p) for c, p in zip(model.classes_, model.predict_proba([features])[0])}
        return {"label": label, "scores": scores}
    if capability == "qa_retrieval":
        store = joblib.load(MODELS_DIR / "qa_retrieval.joblib")
        query = store["vectorizer"].transform([_normalize_question(str(data))])
        sims = cosine_similarity(query, store["matrix"])[0]
        best = int(np.argmax(sims))
        confidence = float(sims[best])
        return {
            "label": store["rows"][best]["answer"],
            "question": store["rows"][best]["question"],
            "confidence": confidence,
            "confident": confidence >= 0.15,
        }
    if capability == "sensor_decision_model":
        store = joblib.load(MODELS_DIR / "sensor_decision_model.joblib")
        model = store["model"]
        feature_names = store["feature_names"]
        features = [[float(data[name]) for name in feature_names]]
        label = str(model.predict(features)[0])
        return {"label": label, "feature_names": feature_names}
    raise ValueError(f"Unknown capability: {capability}")
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
                "onnxruntime>=1.18.0",
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
            "unihiker_m10": (
                "统一硬件路线：行空板 M10 负责本地运行、屏幕显示、摄像头/麦克风接入；"
                "DFRobot 开源硬件外设负责语音合成、传感器输入或执行器输出。"
            ),
            "student_laptop": "在学生笔记本上运行 `python run.py`，确认输出后再整理到作品材料中。",
            "jetson_nano": "建议先在笔记本生成并测试脚本，再复制到 Jetson Nano 的项目目录运行。",
            "raspberry_pi": "建议通过 Thonny、VS Code Remote 或命令行复制脚本到树莓派运行。",
            "esp32": "ESP32 适合接收上位机生成的结果或执行简化控制逻辑，不建议在板上训练模型。",
            "generic": "先在电脑端验证流程，再根据设备接口改造输入输出。",
        }
        return f"""# 硬件使用说明

目标硬件：{request.target_hardware}

{notes[request.target_hardware]}

## 行空板 M10 + DFRobot 外设基线

- 先在电脑端用样例数据跑通 `python run.py`。
- 迁移到行空板 M10 时，保留 `data_sample/`、`models/` 和 `ai_runtime/`。
- 智能博物优先接 DFRobot 语音合成模块完成播报。
- 优创未来优先接 DFRobot 摄像头、传感器、舵机或执行器模块完成外设交互。
- 串口、I2C、引脚编号和模块供电要按实物连接重新确认。

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
- `train.py` / `predict.py` / `run.py`
- `run_on_unihiker.py` — 行空板骨架脚本（修改 `on_result()` 实现创意效果）
- `setup_unihiker.sh` / `deploy.sh` / `deploy.bat` — 一键部署工具
- `creative_examples/` — 创意代码片段示例（显示/蜂鸣器/计数/舵机）
- `notebook.ipynb`
- `ai_runtime/core.py`
- `hardware/README.md`
- `docs/ai_validation.md`
- `speech/README.md` / `speech/speech_output.py` / `speech/voice_config.json`
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

    # ------------------------------------------------------------------ Unihiker

    def _render_run_on_unihiker_py(self, task: TaskDefinition) -> str:
        cap = task.ai_capability
        if cap == "text_classifier":
            return self._unihiker_text_classifier()
        if cap == "image_classifier":
            return self._unihiker_image_classifier()
        if cap == "audio_classifier":
            return self._unihiker_audio_classifier()
        if cap == "sensor_decision_model":
            return self._unihiker_sensor_decision()
        if cap == "qa_retrieval":
            return self._unihiker_qa_retrieval()
        # Fallback for ocr or unknown capabilities
        return self._unihiker_generic(cap)

    def _unihiker_text_classifier(self) -> str:
        return '''\
"""行空板运行脚本 — 文本分类

在行空板上通过 OCR 或键盘输入文字，模型判断类别后显示在屏幕上。

运行方式：
  python run_on_unihiker.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_runtime.core import predict_raw

# ── 行空板硬件初始化 ───────────────────────────────────────────
try:
    from unihiker import GUI   # 行空板官方库，出厂固件已内置
    gui = GUI()
    _ON_BOARD = True
except Exception:
    _ON_BOARD = False
    print("未检测到行空板环境，使用终端模式运行。")


def _show(text: str) -> None:
    if _ON_BOARD:
        gui.clear()
        gui.draw_text(text=text, x=120, y=160, font_size=16, color="#1f1e1d", origin="center")
    else:
        print(text)


# ================================================================
#  创意区域 — 只需修改这个函数
#  label      : 预测到的类别（你训练时设定的标签）
#  confidence : 最高置信度，0.0~1.0
# ================================================================
def on_result(label: str, confidence: float) -> None:
    # 默认：屏幕显示"类别  置信度%"
    _show(f"{label}  {confidence:.0%}")


# ── 主循环（无需修改）────────────────────────────────────────────
def main() -> None:
    _show("文本分类已就绪，输入文字后回车")
    while True:
        text = input("输入文字（回车确认）: ").strip()
        if not text:
            continue
        result = predict_raw("text_classifier", text)
        confidence = max(result["scores"].values()) if result.get("scores") else 0.0
        on_result(result["label"], confidence)


if __name__ == "__main__":
    main()
'''

    def _unihiker_image_classifier(self) -> str:
        return '''\
"""行空板运行脚本 — 图像分类

连接 USB 摄像头后，按 A 键拍照，模型识别类别并显示在屏幕上。

运行方式：
  python run_on_unihiker.py

外设要求：
  - USB 摄像头接行空板 USB-A 口（免驱）
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_runtime.core import predict_raw

# ── 行空板硬件初始化 ───────────────────────────────────────────
try:
    from unihiker import GUI               # 行空板官方库，出厂固件已内置
    from pinpong.board import Board        # pinpong 硬件控制库，同样已内置
    from pinpong.extension.unihiker import button_a
    Board().begin()
    gui = GUI()
    _ON_BOARD = True
except Exception:
    _ON_BOARD = False
    print("未检测到行空板环境，使用终端模式（按 Enter 触发）。")

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False
    print("未找到 opencv-python，请先运行 setup_unihiker.sh 安装依赖。")


def _show(text: str) -> None:
    if _ON_BOARD:
        gui.clear()
        gui.draw_text(text=text, x=120, y=160, font_size=16, color="#1f1e1d", origin="center")
    else:
        print(text)


# ================================================================
#  创意区域 — 只需修改这个函数
#  label      : 预测到的类别
#  confidence : 置信度 0.0~1.0
#  frame      : 当前帧（numpy array，可进一步处理）
# ================================================================
def on_result(label: str, confidence: float, frame) -> None:
    # 默认：屏幕显示识别结果
    _show(f"{label}\\n{confidence:.0%}")


# ── 主循环（无需修改）────────────────────────────────────────────
def main() -> None:
    if not _HAS_CV2:
        return
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        _show("找不到摄像头，请检查 USB 连接")
        return

    _show("按 A 键拍照识别")
    prev_pressed = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            if _ON_BOARD:
                pressed = button_a.is_pressed()
                triggered = pressed and not prev_pressed
                prev_pressed = pressed
            else:
                # 终端模式：按 Enter 触发
                triggered = len(input("按 Enter 拍照（q 退出）: ")) == 0

            if triggered:
                _show("识别中...")
                _, img_bytes = cv2.imencode(".jpg", frame)
                result = predict_raw("image_classifier", img_bytes.tobytes())
                confidence = max(result["scores"].values()) if result.get("scores") else 0.0
                on_result(result["label"], confidence, frame)

            time.sleep(0.05)
    finally:
        cap.release()


if __name__ == "__main__":
    main()
'''

    def _unihiker_audio_classifier(self) -> str:
        return '''\
"""行空板运行脚本 — 音频分类

按 A 键录音 3 秒，模型判断声音类别后显示在屏幕上。
行空板有内置麦克风，录音用官方 unihiker.Audio 类，无需额外外设。

运行方式：
  python run_on_unihiker.py
"""
from __future__ import annotations

import io
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_runtime.core import predict_raw

# ── 行空板硬件初始化 ───────────────────────────────────────────
try:
    from unihiker import GUI, Audio        # 行空板官方库，出厂固件已内置
    from pinpong.board import Board        # pinpong 硬件控制库，同样已内置
    from pinpong.extension.unihiker import button_a
    Board().begin()
    gui = GUI()
    audio = Audio()                        # 板载麦克风
    _ON_BOARD = True
except Exception:
    _ON_BOARD = False
    print("未检测到行空板环境，使用终端模式运行（电脑录音需要 pip install sounddevice）。")

RECORD_SECONDS = 3
SAMPLE_RATE = 16000


def _show(text: str) -> None:
    if _ON_BOARD:
        gui.clear()
        gui.draw_text(text=text, x=120, y=160, font_size=16, color="#1f1e1d", origin="center")
    else:
        print(text)


def _record_wav(seconds: int = RECORD_SECONDS) -> bytes:
    """Record from microphone and return WAV bytes."""
    if _ON_BOARD:
        clip = Path("/tmp/unihiker_record.wav")
        audio.record(str(clip), seconds)   # 官方阻塞式录音 API
        return clip.read_bytes()
    import sounddevice as sd               # 电脑端调试用
    data = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data.tobytes())
    return buf.getvalue()


# ================================================================
#  创意区域 — 只需修改这个函数
#  label      : 预测到的声音类别
#  confidence : 置信度 0.0~1.0
# ================================================================
def on_result(label: str, confidence: float) -> None:
    _show(f"{label}\\n{confidence:.0%}")


# ── 主循环（无需修改）────────────────────────────────────────────
def main() -> None:
    _show(f"按 A 键录音 {RECORD_SECONDS} 秒")
    prev_pressed = False

    while True:
        if _ON_BOARD:
            pressed = button_a.is_pressed()
            triggered = pressed and not prev_pressed
            prev_pressed = pressed
        else:
            triggered = len(input("按 Enter 录音（q 退出）: ")) == 0

        if triggered:
            _show(f"录音中… {RECORD_SECONDS}s")
            wav_bytes = _record_wav()
            _show("识别中...")
            result = predict_raw("audio_classifier", wav_bytes)
            confidence = max(result["scores"].values()) if result.get("scores") else 0.0
            on_result(result["label"], confidence)

        time.sleep(0.05)


if __name__ == "__main__":
    main()
'''

    def _unihiker_sensor_decision(self) -> str:
        return '''\
"""行空板运行脚本 — 传感器决策

读取行空板内置六轴传感器（或外接传感器），模型判断动作后显示在屏幕上。
默认使用内置加速度计（X/Y/Z）作为输入特征，请根据你的训练数据修改。

运行方式：
  python run_on_unihiker.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_runtime.core import predict_raw

# ── 行空板硬件初始化 ───────────────────────────────────────────
try:
    from unihiker import GUI               # 行空板官方库，出厂固件已内置
    from pinpong.board import Board        # pinpong 硬件控制库，同样已内置
    # 板载元件都是现成实例：accelerometer/gyroscope/light/buzzer/button_a/button_b
    from pinpong.extension.unihiker import accelerometer
    Board().begin()
    gui = GUI()
    _ON_BOARD = True
except Exception:
    _ON_BOARD = False
    print("未检测到行空板环境，使用模拟数据运行。")


def _show(text: str) -> None:
    if _ON_BOARD:
        gui.clear()
        gui.draw_text(text=text, x=120, y=160, font_size=16, color="#1f1e1d", origin="center")
    else:
        print(text)


def _read_sensors() -> dict:
    """读取传感器数据并返回特征字典。

    !! 修改这里以匹配你的训练数据列名 !!
    训练 CSV 的列名必须与这里的键名完全一致。
    """
    if _ON_BOARD:
        return {
            "X轴加速度": accelerometer.get_x(),
            "Y轴加速度": accelerometer.get_y(),
            "Z轴加速度": accelerometer.get_z(),
        }
    else:
        # 终端模式：逐个输入数值
        print("模拟输入（直接回车使用默认值 0）：")
        x = float(input("  X轴加速度: ") or 0)
        y = float(input("  Y轴加速度: ") or 0)
        z = float(input("  Z轴加速度: ") or 9.8)
        return {"X轴加速度": x, "Y轴加速度": y, "Z轴加速度": z}


# ================================================================
#  创意区域 — 只需修改这个函数
#  action  : 模型判断的动作（你训练时设定的标签）
#  sensors : 传入的传感器数据字典
# ================================================================
def on_result(action: str, sensors: dict) -> None:
    # 默认：屏幕显示动作名称
    _show(f"动作: {action}")


# ── 主循环（无需修改）────────────────────────────────────────────
def main() -> None:
    _show("传感器决策已就绪")
    while True:
        sensors = _read_sensors()
        result = predict_raw("sensor_decision_model", sensors)
        on_result(result["label"], sensors)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
'''

    def _unihiker_qa_retrieval(self) -> str:
        return '''\
"""行空板运行脚本 — 智能问答

在行空板上通过键盘输入问题，系统检索最相关的答案并显示在屏幕上。

运行方式：
  python run_on_unihiker.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_runtime.core import predict_raw

# ── 行空板硬件初始化 ───────────────────────────────────────────
try:
    from unihiker import GUI   # 行空板官方库，出厂固件已内置
    gui = GUI()
    _ON_BOARD = True
except Exception:
    _ON_BOARD = False
    print("未检测到行空板环境，使用终端模式运行。")


def _show(title: str, body: str) -> None:
    if _ON_BOARD:
        gui.clear()
        gui.draw_text(text=title, x=120, y=40, font_size=14, color="#d97757", origin="center")
        gui.draw_text(text=body, x=10, y=80, font_size=13, color="#1f1e1d", origin="top_left")
    else:
        print(f"问：{title}")
        print(f"答：{body}")


# ================================================================
#  创意区域 — 只需修改这个函数
#  question   : 输入的问题
#  answer     : 检索到的答案
#  confident  : 是否高置信（True/False）
# ================================================================
def on_result(question: str, answer: str, confident: bool) -> None:
    if confident:
        _show(question, answer)
    else:
        _show(question, "抱歉，我还不清楚这个问题。")


# ── 主循环（无需修改）────────────────────────────────────────────
def main() -> None:
    _show("智能问答", "请输入你的问题")
    while True:
        question = input("输入问题（回车确认）: ").strip()
        if not question:
            continue
        result = predict_raw("qa_retrieval", question)
        on_result(question, result["label"], result.get("confident", False))


if __name__ == "__main__":
    main()
'''

    def _unihiker_generic(self, capability: str) -> str:
        return f'''\
"""行空板运行脚本 — {capability}

运行方式：
  python run_on_unihiker.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_runtime.core import predict_raw


# ================================================================
#  创意区域 — 修改 on_result() 实现你的创意效果
# ================================================================
def on_result(result: dict) -> None:
    print(result)


def main() -> None:
    data = input("输入内容: ").strip()
    result = predict_raw("{capability}", data)
    on_result(result)


if __name__ == "__main__":
    main()
'''

    # ---------------------------------------------------------- deploy scripts

    def _render_setup_unihiker_sh(self) -> str:
        return '''\
#!/bin/bash
# setup_unihiker.sh — 在行空板上运行一次，安装所有运行依赖
# 用法：bash setup_unihiker.sh

set -e

echo "=== 行空板依赖安装脚本 ==="
echo "需要行空板已联网（WiFi 或 USB 共享网络）"
echo ""

# 基础 ML 依赖
pip install --upgrade scikit-learn joblib numpy pillow onnxruntime

# 摄像头支持（图像分类任务需要）
pip install opencv-python-headless || echo "opencv 安装失败，图像识别不可用"

# 行空板官方库 unihiker（屏幕/录音）和 pinpong（按键/传感器/蜂鸣器/舵机）
# 出厂固件已内置，这里只做升级，失败不影响使用
pip install -U unihiker pinpong || echo "unihiker/pinpong 升级跳过，使用出厂版本"

echo ""
echo "=== 安装完成 ==="
echo "运行 python run_on_unihiker.py 启动程序"
'''

    def _render_deploy_sh(self, request: GenerationRequest) -> str:
        proj = request.project_name or "project"
        return f'''\
#!/bin/bash
# deploy.sh — Mac/Linux：把项目文件传输到行空板
# 用法：bash deploy.sh [行空板IP]
#   默认 IP 为 10.1.2.3（USB 直连默认地址）

BOARD_IP="${{1:-10.1.2.3}}"
BOARD_USER="root"
REMOTE_DIR="/root/{proj}"

echo "部署到行空板 $BOARD_IP ..."
ssh "$BOARD_USER@$BOARD_IP" "mkdir -p $REMOTE_DIR"
scp -r ai_runtime models run_on_unihiker.py setup_unihiker.sh \\
    "$BOARD_USER@$BOARD_IP:$REMOTE_DIR/"

echo ""
echo "=== 部署完成 ==="
echo "在行空板上运行："
echo "  ssh root@$BOARD_IP"
echo "  cd $REMOTE_DIR"
echo "  bash setup_unihiker.sh   # 首次运行安装依赖"
echo "  python run_on_unihiker.py"
'''

    def _render_deploy_bat(self, request: GenerationRequest) -> str:
        proj = request.project_name or "project"
        return f'''\
@echo off
REM deploy.bat — Windows：把项目文件传输到行空板
REM 用法：deploy.bat [行空板IP]
REM   默认 IP 为 10.1.2.3（USB 直连默认地址）

SET BOARD_IP=%1
IF "%BOARD_IP%"=="" SET BOARD_IP=10.1.2.3
SET BOARD_USER=root
SET REMOTE_DIR=/root/{proj}

echo 部署到行空板 %BOARD_IP% ...
ssh %BOARD_USER%@%BOARD_IP% "mkdir -p %REMOTE_DIR%"
scp -r ai_runtime models run_on_unihiker.py setup_unihiker.sh ^
    %BOARD_USER%@%BOARD_IP%:%REMOTE_DIR%/

echo.
echo === 部署完成 ===
echo 在行空板上运行：
echo   ssh root@%BOARD_IP%
echo   cd %REMOTE_DIR%
echo   bash setup_unihiker.sh
echo   python run_on_unihiker.py
'''

    # ------------------------------------------------------ creative examples

    def _render_creative_example_display(self) -> str:
        return '''\
"""示例 01 — 屏幕显示识别结果（默认效果）

把这段代码复制到 run_on_unihiker.py 的 on_result() 函数中。
"""


def on_result(label: str, confidence: float, **kwargs) -> None:
    if _ON_BOARD:
        gui.clear()
        color = "#2ecc71" if confidence >= 0.8 else "#e67e22"
        gui.draw_text(text=label, x=120, y=130, font_size=22, color=color, origin="center")
        gui.draw_text(
            text=f"置信度 {confidence:.0%}", x=120, y=175, font_size=14,
            color="#666", origin="center"
        )
    else:
        print(f"识别结果: {label} ({confidence:.0%})")
'''

    def _render_creative_example_buzzer(self) -> str:
        return '''\
"""示例 02 — 识别到特定类别时响铃

把这段代码复制到 run_on_unihiker.py 的 on_result() 函数中。
行空板背面板载蜂鸣器，pinpong 提供现成的 buzzer 实例，无需接线。
"""
from pinpong.extension.unihiker import buzzer

# !! 修改这里：改为你希望触发蜂鸣器的类别名称 !!
TRIGGER_LABELS = {"猫", "狗", "异常"}


def on_result(label: str, confidence: float, **kwargs) -> None:
    _show(f"{label}  {confidence:.0%}")
    if label in TRIGGER_LABELS and confidence >= 0.7:
        buzzer.pitch(494, 1)   # 播放一个音符：音高 494Hz，1 拍
        # 也可以播放内置音乐：buzzer.play(buzzer.BA_DING, buzzer.Once)
'''

    def _render_creative_example_counter(self) -> str:
        return '''\
"""示例 03 — 统计各类别出现次数

把这段代码复制到 run_on_unihiker.py 的 on_result() 函数中。
"""
from collections import Counter

_counts: Counter = Counter()


def on_result(label: str, confidence: float, **kwargs) -> None:
    if confidence >= 0.6:
        _counts[label] += 1
    lines = [f"{k}: {v}次" for k, v in _counts.most_common(5)]
    _show("\\n".join(lines) if lines else "等待识别...")
'''

    def _render_creative_example_servo(self) -> str:
        return '''\
"""示例 04 — 识别结果控制舵机角度

把这段代码复制到 run_on_unihiker.py 的 on_result() 函数中。
舵机接行空板 3Pin I/O 口的 PWM 引脚（带 ~ 标记）。

注意：板载接口只能接 9g 小舵机；金属大舵机电流大，
需要扩展板独立供电，直接接板载口可能损坏行空板。
"""
from pinpong.board import Pin, Servo

# !! 修改这里：类别名称对应的舵机角度（0~180 度）!!
LABEL_TO_ANGLE = {
    "左转": 0,
    "停止": 90,
    "右转": 180,
}

servo = Servo(Pin(Pin.P23))   # 根据实际接线修改引脚


def on_result(label: str, confidence: float, **kwargs) -> None:
    _show(f"{label}  {confidence:.0%}")
    if confidence >= 0.7 and label in LABEL_TO_ANGLE:
        servo.write_angle(LABEL_TO_ANGLE[label])
'''

    def _write_sample_dataset(
        self,
        generated_dir: Path,
        task: TaskDefinition,
        request: GenerationRequest,
        user_images: dict[str, Path] | None = None,
        user_audio: dict[str, Path] | None = None,
    ) -> list[Path]:
        source_files: list[str]
        if task.sample_dataset_kind == "text":
            paths = self._write_text_dataset(generated_dir, request)
            source_files = ["data_sample/text_samples.csv"]
        elif task.sample_dataset_kind == "image":
            paths = self._write_image_dataset(generated_dir, request, user_images)
            source_files = ["data_sample/images/", "data_sample/predict_images/"]
        elif task.sample_dataset_kind == "audio":
            paths = self._write_audio_dataset(generated_dir, request, user_audio)
            source_files = ["data_sample/audio/", "data_sample/predict_audio/"]
        elif task.sample_dataset_kind == "qa":
            paths = self._write_qa_dataset(generated_dir, request)
            source_files = ["data_sample/qa_pairs.csv"]
        elif task.sample_dataset_kind == "sensor":
            paths = self._write_sensor_dataset(generated_dir, request)
            source_files = ["data_sample/sensor_samples.csv"]
        else:
            paths = self._write_ocr_dataset(generated_dir, request)
            source_files = ["data_sample/ocr_cases.csv"]
        paths.append(
            self._write_data_manifest(
                generated_dir, task, request, source_files, user_images, user_audio
            )
        )
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
            # Keep the student's own column names: the exported runtime reads the header
            # and treats the last column as the action label.
            sensor_samples = request.sensor_csv.strip() + "\n"
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
                "data_sample/predict_sensor.csv": self._sensor_predict_csv(sensor_samples),
            },
        )

    def _sensor_predict_csv(self, sensor_samples: str) -> str:
        """Build predict rows from the training CSV: same feature columns, no action column."""
        rows = list(csv.reader(StringIO(sensor_samples.strip())))
        header = rows[0][:-1]
        feature_rows = [tuple(row[:-1]) for row in rows[1:3] if len(row) == len(rows[0])]
        return self._csv(header, feature_rows)

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
        user_images: dict[str, Path] | None = None,
    ) -> list[Path]:
        if user_images:
            return self._copy_user_images(generated_dir, user_images)
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

    def _copy_user_images(
        self,
        generated_dir: Path,
        user_images: dict[str, Path],
    ) -> list[Path]:
        return self._copy_user_media(generated_dir, user_images, "images", "predict_images")

    def _copy_user_media(
        self,
        generated_dir: Path,
        user_folders: dict[str, Path],
        data_dirname: str,
        predict_dirname: str,
    ) -> list[Path]:
        paths: list[Path] = []
        for label, source_folder in user_folders.items():
            safe_label = self._safe_label(label)
            media_files = sorted(path for path in source_folder.glob("*") if path.is_file())
            for media_file in media_files:
                target = (
                    generated_dir / "data_sample" / data_dirname / safe_label / media_file.name
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(media_file.read_bytes())
                paths.append(target)
            if media_files:
                predict_target = (
                    generated_dir
                    / "data_sample"
                    / predict_dirname
                    / f"{safe_label}{media_files[0].suffix}"
                )
                predict_target.parent.mkdir(parents=True, exist_ok=True)
                predict_target.write_bytes(media_files[0].read_bytes())
                paths.append(predict_target)
        return paths

    def _write_audio_dataset(
        self,
        generated_dir: Path,
        request: GenerationRequest,
        user_audio: dict[str, Path] | None = None,
    ) -> list[Path]:
        if user_audio:
            return self._copy_user_media(generated_dir, user_audio, "audio", "predict_audio")
        labels = request.class_labels or ["低音", "高音"]
        base_frequencies = [220.0, 880.0, 440.0]
        paths: list[Path] = []
        for index, label in enumerate(labels[:3]):
            safe_label = self._safe_label(label)
            base = base_frequencies[index % len(base_frequencies)]
            for sample_index in range(3):
                path = generated_dir / "data_sample" / "audio" / safe_label / f"{sample_index}.wav"
                self._write_sine_wav(path, base * (1.0 + 0.04 * sample_index))
                paths.append(path)
            predict_path = generated_dir / "data_sample" / "predict_audio" / f"{safe_label}.wav"
            self._write_sine_wav(predict_path, base * 1.02)
            paths.append(predict_path)
        return paths

    def _write_sine_wav(
        self, path: Path, frequency: float, duration: float = 0.6, rate: int = 16000
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        frames = bytearray()
        for index in range(int(duration * rate)):
            value = int(0.4 * 32767 * math.sin(2 * math.pi * frequency * index / rate))
            frames += struct.pack("<h", value)
        with wave.open(str(path), "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(rate)
            writer.writeframes(bytes(frames))

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
        user_images: dict[str, Path] | None = None,
        user_audio: dict[str, Path] | None = None,
    ) -> Path:
        manifest = {
            "data_origin": self._data_origin(task, request, user_images, user_audio),
            "sample_dataset_kind": task.sample_dataset_kind,
            "source_files": source_files,
        }
        path = generated_dir / "data_sample" / "data_manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _data_origin(
        self,
        task: TaskDefinition,
        request: GenerationRequest,
        user_images: dict[str, Path] | None = None,
        user_audio: dict[str, Path] | None = None,
    ) -> str:
        user_data_by_kind = {
            "text": request.text_csv,
            "qa": request.qa_text,
            "sensor": request.sensor_csv,
            "ocr": f"{request.ocr_correct_text}{request.ocr_observed_text}",
            "image": "yes" if user_images else "",
            "audio": "yes" if user_audio else "",
        }
        return "user" if user_data_by_kind[task.sample_dataset_kind].strip() else "sample"

    def _safe_label(self, label: str) -> str:
        return "".join(char if char.isalnum() else "_" for char in label) or "label"

    def _render_sample_input(self, request: GenerationRequest) -> str:
        labels = request.class_labels or ["刺绣", "陶艺", "剪纸"]
        return "\n".join(f"{label}\t这里填写一个样例输入" for label in labels) + "\n"

    def _markdown_list(self, items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)
