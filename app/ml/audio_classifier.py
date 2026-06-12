from __future__ import annotations

import wave
from io import BytesIO
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.ml import classifiers
from app.ml.base import MODEL_FILE, MLDataError, class_counts, now_text, write_model_meta

# Feature extraction must stay in sync with the exported ai_runtime/core.py so the
# in-app trained model keeps working inside the exported package.
SAMPLE_RATE = 16000
FRAME_SIZE = 1024
HOP_SIZE = 512
N_BANDS = 16
MIN_SECONDS = 0.3
MAX_SECONDS = 10.0
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MIN_CLIPS_PER_CLASS = 2

MODEL_CHOICES = classifiers.DENSE_CHOICES
DEFAULT_MODEL = "logistic_regression"


def _decode_wav(data: bytes) -> np.ndarray:
    """Decode PCM WAV bytes to mono float samples in [-1, 1] at SAMPLE_RATE."""
    try:
        with wave.open(BytesIO(data)) as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            rate = reader.getframerate()
            raw = reader.readframes(reader.getnframes())
    except Exception as exc:
        raise MLDataError("这段声音打不开，请使用 WAV 格式的录音（页面录音按钮生成的就是）。") from exc

    if sample_width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    elif sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483648.0
    else:
        raise MLDataError("暂不支持这种 WAV 编码，请使用 8/16/32 位 PCM 录音。")

    if channels > 1:
        samples = samples[: len(samples) // channels * channels]
        samples = samples.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE and len(samples) > 1:
        duration = len(samples) / rate
        target_count = max(int(duration * SAMPLE_RATE), 1)
        positions = np.linspace(0.0, len(samples) - 1.0, target_count)
        samples = np.interp(positions, np.arange(len(samples)), samples)
    return samples[: int(MAX_SECONDS * SAMPLE_RATE)]


def audio_features(data: bytes) -> list[float]:
    if len(data) > MAX_AUDIO_BYTES:
        raise MLDataError("这段声音太大了，请使用 10MB 以内、几秒钟长的录音。")
    samples = _decode_wav(data)
    if len(samples) < int(MIN_SECONDS * SAMPLE_RATE):
        raise MLDataError("这段声音太短了，请录至少半秒钟。")

    window = np.hanning(FRAME_SIZE)
    band_rows: list[np.ndarray] = []
    rms_values: list[float] = []
    zcr_values: list[float] = []
    for start in range(0, len(samples) - FRAME_SIZE + 1, HOP_SIZE):
        frame = samples[start : start + FRAME_SIZE]
        spectrum = np.abs(np.fft.rfft(frame * window))
        bands = np.array_split(spectrum, N_BANDS)
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


def _prepare_features(
    labeled_clips: dict[str, list[bytes]],
) -> tuple[list[list[float]], list[str]]:
    usable = {label: clips for label, clips in labeled_clips.items() if clips}
    if len(usable) < 2:
        raise MLDataError("至少需要 2 个类别的声音才能训练，请先给每个类别录几段声音。")
    thin_classes = [
        label for label, clips in usable.items() if len(clips) < MIN_CLIPS_PER_CLASS
    ]
    if thin_classes:
        raise MLDataError(
            f"这些类别的声音太少：{('、'.join(thin_classes))}。每个类别至少要 {MIN_CLIPS_PER_CLASS} 段。"
        )

    features: list[list[float]] = []
    labels: list[str] = []
    for label, clips in usable.items():
        for data in clips:
            features.append(audio_features(data))
            labels.append(label)
    return features, labels


def train(
    labeled_clips: dict[str, list[bytes]],
    models_dir: Path,
    model_choice: str | None = None,
) -> dict[str, Any]:
    choice = classifiers.resolve_choice(model_choice, MODEL_CHOICES, DEFAULT_MODEL)
    features, labels = _prepare_features(labeled_clips)
    counts = class_counts(labels)

    model = classifiers.make_classifier(choice, len(labels))
    model.fit(features, labels)
    train_accuracy = float(model.score(features, labels))
    cross_val_accuracy = classifiers.cross_val_accuracy(
        lambda: classifiers.make_classifier(choice, len(labels)), features, labels, counts
    )

    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, models_dir / MODEL_FILE)
    meta = {
        "capability": "audio_classifier",
        "labels": sorted(counts),
        "sample_count": len(labels),
        "class_counts": counts,
        "train_accuracy": train_accuracy,
        "cross_val_accuracy": cross_val_accuracy,
        "model_choice": choice,
        "model_name": classifiers.CLASSIFIER_INFO[choice]["name"],
        "trained_at": now_text(),
    }
    write_model_meta(models_dir, meta)
    return meta


def compare(labeled_clips: dict[str, list[bytes]]) -> list[dict[str, Any]]:
    features, labels = _prepare_features(labeled_clips)
    counts = class_counts(labels)
    return classifiers.compare_rows(
        MODEL_CHOICES,
        DEFAULT_MODEL,
        lambda choice: classifiers.make_classifier(choice, len(labels)),
        features,
        labels,
        counts,
    )


def predict(models_dir: Path, audio_bytes: bytes) -> dict[str, Any]:
    model_path = models_dir / MODEL_FILE
    if not model_path.is_file():
        raise MLDataError("还没有训练模型，请先完成“训练模型”这一步。")
    model = joblib.load(model_path)
    features = audio_features(audio_bytes)
    label = str(model.predict([features])[0])
    probabilities = model.predict_proba([features])[0]
    scores = {
        str(class_label): round(float(probability), 4)
        for class_label, probability in zip(model.classes_, probabilities)
    }
    return {"label": label, "scores": scores}
