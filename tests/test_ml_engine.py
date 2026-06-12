import math
import struct
import wave
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.ml import (
    audio_classifier,
    image_classifier,
    ocr_checker,
    qa_retrieval,
    sensor_model,
    text_classifier,
)
from app.ml.base import MLDataError

TEXT_SAMPLES = [
    {"text": "昆曲 唱腔 舞台 表演", "label": "传统戏剧"},
    {"text": "梨园戏 地方 戏曲 剧目", "label": "传统戏剧"},
    {"text": "德化瓷 烧制 陶土 窑炉", "label": "传统技艺"},
    {"text": "蜡染 技艺 染布 图案", "label": "传统技艺"},
]


def make_image_bytes(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (48, 48), color).save(buffer, format="PNG")
    return buffer.getvalue()


def make_wav_bytes(frequency: float, duration: float = 0.5, rate: int = 16000) -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        frames = bytearray()
        for index in range(int(duration * rate)):
            value = int(0.5 * 32767 * math.sin(2 * math.pi * frequency * index / rate))
            frames += struct.pack("<h", value)
        writer.writeframes(bytes(frames))
    return buffer.getvalue()


def test_text_classifier_naive_bayes_choice(tmp_path: Path) -> None:
    report = text_classifier.train(TEXT_SAMPLES, tmp_path, model_choice="naive_bayes")

    assert report["model_choice"] == "naive_bayes"
    assert report["model_name"] == "朴素贝叶斯"

    result = text_classifier.predict(tmp_path, "昆曲 舞台 演出")
    assert result["label"] == "传统戏剧"


def test_text_classifier_rejects_unknown_choice(tmp_path: Path) -> None:
    with pytest.raises(MLDataError, match="不支持"):
        text_classifier.train(TEXT_SAMPLES, tmp_path, model_choice="transformer")


def test_text_classifier_compare_reports_all_models(tmp_path: Path) -> None:
    rows = text_classifier.compare(TEXT_SAMPLES)

    assert [row["model_choice"] for row in rows] == [
        "logistic_regression",
        "naive_bayes",
        "random_forest",
    ]
    for row in rows:
        assert 0.0 <= row["train_accuracy"] <= 1.0
        assert row["train_ms"] >= 0
        # 2 samples per class is below the cross-val threshold.
        assert row["cross_val_accuracy"] is None


def test_sensor_random_forest_reports_importances(tmp_path: Path) -> None:
    raw_csv = (
        "心率,体温,动作\n"
        "110,38.6,提醒就诊\n72,36.5,继续观察\n118,39.2,提醒就诊\n68,36.8,继续观察\n"
    )

    report = sensor_model.train(raw_csv, tmp_path, model_choice="random_forest")

    assert report["model_choice"] == "random_forest"
    assert "rules_text" not in report
    assert set(report["feature_importances"]) == {"心率", "体温"}

    result = sensor_model.predict(tmp_path, {"心率": "120", "体温": "39.0"})
    assert result["label"] == "提醒就诊"


def test_image_classifier_knn_choice(tmp_path: Path) -> None:
    labeled = {
        "红色卡片": [make_image_bytes((220, 60 + index, 60)) for index in range(3)],
        "绿色卡片": [make_image_bytes((60, 170 + index, 90)) for index in range(3)],
    }

    report = image_classifier.train(labeled, tmp_path, model_choice="knn")

    assert report["model_choice"] == "knn"
    assert report["cross_val_accuracy"] is not None

    result = image_classifier.predict(tmp_path, make_image_bytes((215, 65, 62)))
    assert result["label"] == "红色卡片"


def test_text_classifier_trains_and_predicts(tmp_path: Path) -> None:
    report = text_classifier.train(TEXT_SAMPLES, tmp_path)

    assert report["sample_count"] == 4
    assert report["labels"] == ["传统戏剧", "传统技艺"]
    assert report["train_accuracy"] == 1.0

    result = text_classifier.predict(tmp_path, "昆曲 舞台 演出")
    assert result["label"] == "传统戏剧"
    assert set(result["scores"]) == {"传统戏剧", "传统技艺"}


def test_text_classifier_rejects_single_class(tmp_path: Path) -> None:
    with pytest.raises(MLDataError, match="2 个类别"):
        text_classifier.train(TEXT_SAMPLES[:2], tmp_path)


def test_text_classifier_rejects_thin_classes(tmp_path: Path) -> None:
    with pytest.raises(MLDataError, match="例句太少"):
        text_classifier.train(TEXT_SAMPLES[:3], tmp_path)


def test_predict_without_training_gives_friendly_error(tmp_path: Path) -> None:
    with pytest.raises(MLDataError, match="还没有训练模型"):
        text_classifier.predict(tmp_path, "测试")


def test_image_classifier_trains_and_predicts(tmp_path: Path) -> None:
    labeled = {
        "红色卡片": [make_image_bytes((220, 60 + index, 60)) for index in range(3)],
        "绿色卡片": [make_image_bytes((60, 170 + index, 90)) for index in range(3)],
    }

    report = image_classifier.train(labeled, tmp_path)

    assert report["class_counts"] == {"红色卡片": 3, "绿色卡片": 3}

    result = image_classifier.predict(tmp_path, make_image_bytes((215, 65, 62)))
    assert result["label"] == "红色卡片"


def test_image_classifier_rejects_broken_image(tmp_path: Path) -> None:
    with pytest.raises(MLDataError, match="打不开"):
        image_classifier.train({"甲": [b"not an image"] * 2, "乙": [b"x"] * 2}, tmp_path)


def test_audio_classifier_trains_and_predicts(tmp_path: Path) -> None:
    labeled = {
        "低音": [make_wav_bytes(220.0 * (1 + 0.03 * index)) for index in range(3)],
        "高音": [make_wav_bytes(880.0 * (1 + 0.03 * index)) for index in range(3)],
    }

    report = audio_classifier.train(labeled, tmp_path)

    assert report["capability"] == "audio_classifier"
    assert report["class_counts"] == {"低音": 3, "高音": 3}

    result = audio_classifier.predict(tmp_path, make_wav_bytes(900.0))
    assert result["label"] == "高音"
    assert set(result["scores"]) == {"低音", "高音"}


def test_audio_classifier_rejects_broken_clip(tmp_path: Path) -> None:
    with pytest.raises(MLDataError, match="打不开"):
        audio_classifier.train({"甲": [b"not audio"] * 2, "乙": [b"x"] * 2}, tmp_path)


def test_audio_classifier_rejects_thin_classes(tmp_path: Path) -> None:
    labeled = {"低音": [make_wav_bytes(220.0)], "高音": [make_wav_bytes(880.0)]}
    with pytest.raises(MLDataError, match="声音太少"):
        audio_classifier.train(labeled, tmp_path)


def test_audio_classifier_rejects_too_short_clip(tmp_path: Path) -> None:
    labeled = {
        "低音": [make_wav_bytes(220.0, duration=0.1)] * 2,
        "高音": [make_wav_bytes(880.0)] * 2,
    }
    with pytest.raises(MLDataError, match="太短"):
        audio_classifier.train(labeled, tmp_path)


def test_qa_retrieval_returns_best_answer(tmp_path: Path) -> None:
    pairs = [
        {"question": "什么是非遗", "answer": "世代相传的传统文化。"},
        {"question": "为什么要保护非遗", "answer": "为了传承文化记忆。"},
        {"question": "AI能帮什么忙", "answer": "识别、整理和传播。"},
    ]
    qa_retrieval.train(pairs, tmp_path)

    result = qa_retrieval.predict(tmp_path, "什么是非遗")

    assert result["label"] == "世代相传的传统文化。"
    assert result["confident"] is True
    assert len(result["matches"]) == 3


def test_qa_retrieval_falls_back_when_unrelated(tmp_path: Path) -> None:
    pairs = [
        {"question": "什么是非遗", "answer": "世代相传的传统文化。"},
        {"question": "为什么要保护非遗", "answer": "为了传承文化记忆。"},
        {"question": "怎么参加比赛", "answer": "按照竞赛文件报名。"},
    ]
    qa_retrieval.train(pairs, tmp_path)

    result = qa_retrieval.predict(tmp_path, "ABCDEFG")

    assert result["confident"] is False
    assert result["label"] == qa_retrieval.FALLBACK_ANSWER


def test_qa_retrieval_ignores_shared_interrogative_words(tmp_path: Path) -> None:
    pairs = [
        {"question": "什么是非遗", "answer": "世代相传的传统文化。"},
        {"question": "为什么要保护非遗", "answer": "为了传承文化记忆。"},
        {"question": "怎么参加比赛", "answer": "按照竞赛文件报名。"},
    ]
    qa_retrieval.train(pairs, tmp_path)

    # "什么" alone must not make an unrelated question look like a match.
    result = qa_retrieval.predict(tmp_path, "今天午饭吃什么")

    assert result["confident"] is False
    assert result["label"] == qa_retrieval.FALLBACK_ANSWER


def test_sensor_model_uses_student_columns(tmp_path: Path) -> None:
    raw_csv = (
        "心率,体温,动作\n"
        "110,38.6,提醒就诊\n72,36.5,继续观察\n118,39.2,提醒就诊\n68,36.8,继续观察\n"
    )

    report = sensor_model.train(raw_csv, tmp_path)

    assert report["feature_names"] == ["心率", "体温"]
    assert "体温" in report["rules_text"]

    result = sensor_model.predict(tmp_path, {"心率": "120", "体温": "39.0"})
    assert result["label"] == "提醒就诊"


def test_sensor_model_accepts_fullwidth_commas(tmp_path: Path) -> None:
    raw_csv = (
        "心率，体温，动作\n"
        "110，38.6，提醒就诊\n72，36.5，继续观察\n118，39.2，提醒就诊\n68，36.8，继续观察\n"
    )

    report = sensor_model.train(raw_csv, tmp_path)

    assert report["feature_names"] == ["心率", "体温"]
    result = sensor_model.predict(tmp_path, {"心率": "120", "体温": "39.0"})
    assert result["label"] == "提醒就诊"


def test_sensor_model_reports_bad_rows(tmp_path: Path) -> None:
    raw_csv = "心率,动作\n110,提醒就诊\nabc,继续观察\n80,继续观察\n90,继续观察\n95,提醒就诊\n"
    with pytest.raises(MLDataError, match="第 3 行"):
        sensor_model.train(raw_csv, tmp_path)


def test_ocr_checker_finds_typos_and_broadcast(tmp_path: Path) -> None:
    ocr_checker.train("保护为主抢救第一", tmp_path)

    result = ocr_checker.predict(tmp_path, "保护为王抢救第一")

    assert result["typo_count"] == 1
    assert result["typos"][0] == {"position": 4, "observed": "王", "correct": "主"}
    assert "应更正为" in result["label"]

    clean = ocr_checker.predict(tmp_path, "保护为主抢救第一")
    assert clean["typo_count"] == 0
    assert clean["label"] == "卡片文字全部正确"


def test_ocr_checker_handles_length_mismatch(tmp_path: Path) -> None:
    ocr_checker.train("保护为主抢救第一", tmp_path)

    result = ocr_checker.predict(tmp_path, "保护为抢救第一")

    assert result["typo_count"] >= 1
