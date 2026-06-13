"""Classifier registry behind the multi-model selection feature.

Every choice carries student-facing Chinese metadata (作用/效能/简史/优点/局限 plus
school of AI) so the training-page cards can teach how the models differ.

Two groups per task:
- **Trainable** estimators the app can fit on a CPU and export to joblib
  (`*_CHOICES` lists). These drive `make_classifier` / `compare` / `resolve_choice`.
- **Display-only** deep-learning entries (`*_DISPLAY` lists, metadata in
  `DISPLAY_INFO`). Shown as locked cards so students see the full landscape; a
  future GPU-detection step can ungrey the ones a machine can actually run.
  They are never passed to `make_classifier` (the platform has no GPU training
  backend yet), so selecting one is blocked in the UI and rejected server-side.
"""

from __future__ import annotations

import random
import time
from typing import Any, Callable

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from app.ml.base import MLDataError, class_counts

CROSS_VAL_MIN_PER_CLASS = 3

# "对比所有模型" is a quick race, not a final fit. Heavier estimators (GBDT, MLP)
# fitted + cross-validated on a few thousand high-dim samples can take minutes,
# which looks like a hang. Cap the race to a stratified sample so it stays snappy
# regardless of dataset size; the chosen model is still trained on all the data.
COMPARE_MAX_SAMPLES = 300

# ---- trainable estimators (CPU, joblib-exportable) ----

CLASSIFIER_INFO: dict[str, dict[str, str]] = {
    "logistic_regression": {
        "name": "逻辑回归",
        "en_name": "Logistic Regression",
        "school": "统计学习",
        "tier": "classical",
        "requires_gpu": False,
        "principle": "给每个特征打分加权，算出属于每个类别的概率。",
        "performance": "快而稳、能输出概率，是大多数任务的可靠基线。",
        "history": "源自统计学（1958，Cox），机器学习最常用的线性分类器。",
        "strengths": "快、稳定，能输出概率，是大多数任务的可靠起点。",
        "weaknesses": "只能画比较“直”的分类边界，特征不好时容易混淆。",
        "best_for": "特征清晰、数据量不大的任务（默认之选）。",
    },
    "naive_bayes": {
        "name": "朴素贝叶斯",
        "en_name": "Naive Bayes",
        "school": "统计学习",
        "tier": "classical",
        "requires_gpu": False,
        "principle": "统计每个词在各类别里出现的频率，再用概率公式反推类别。",
        "performance": "极快、小数据表现好，关键词区分明显时尤佳。",
        "history": "1960s 起用于文本分类，垃圾邮件过滤靠它成名。",
        "strengths": "极快，小数据表现好——垃圾邮件过滤就靠它出名。",
        "weaknesses": "假设词和词互相独立，句子结构复杂时会失准。",
        "best_for": "文本分类，尤其是关键词区分明显的场景。",
    },
    "random_forest": {
        "name": "随机森林",
        "en_name": "Random Forest",
        "school": "集成学习",
        "tier": "classical",
        "requires_gpu": False,
        "principle": "训练很多棵各不相同的决策树，预测时让它们投票。",
        "performance": "抗噪、不挑数据，通常比单棵树准，是常用的强基线。",
        "history": "2001 年 Breiman 提出，长期是表格/特征分类的强基线。",
        "strengths": "抗噪声、不挑数据，通常比单棵树更准。",
        "weaknesses": "模型较大，投票过程不如单棵树的规则直观。",
        "best_for": "数据比较杂、想要稳妥结果的时候。",
    },
    "knn": {
        "name": "K 近邻",
        "en_name": "K-Nearest Neighbors",
        "school": "实例学习",
        "tier": "classical",
        "requires_gpu": False,
        "principle": "不总结规则——预测时找出和新样本最像的 K 个老样本，跟多数走。",
        "performance": "原理直观，小数据可用；在 MobileNet 这类有意义的特征上不错。",
        "history": "1950s–60s 提出，最古老的模式识别方法之一。",
        "strengths": "原理最直观：“物以类聚”。小数据也能用。",
        "weaknesses": "样本多了预测会变慢，容易被无关特征带偏。",
        "best_for": "样本少、特征本身有意义时（比如 MobileNet 提取的图像特征）。",
    },
    "decision_tree": {
        "name": "决策树",
        "en_name": "Decision Tree",
        "school": "规则学习",
        "tier": "classical",
        "requires_gpu": False,
        "principle": "自动学出一串 if-else 问题，一步步把数据分开。",
        "performance": "完全可解释——学到的规则能直接读出，最适合教学。",
        "history": "CART（1984，Breiman）、ID3/C4.5（1986–1993，Quinlan）奠基。",
        "strengths": "完全可解释——学到的规则能直接读出来。",
        "weaknesses": "容易死记硬背（过拟合），数据稍变规则就可能大变。",
        "best_for": "传感器数值这类任务，以及需要向别人解释决策过程的场景。",
    },
    "gbdt": {
        "name": "梯度提升",
        "en_name": "Gradient Boosting (HistGB)",
        "school": "集成学习",
        "tier": "classical",
        "requires_gpu": False,
        "principle": "一棵接一棵地训练小树，每棵专门纠正前面犯的错（残差）。",
        "performance": "表格/特征任务上常年最强之一；用 scikit-learn 自带实现，无需额外依赖。",
        "history": "1999/2001 Friedman 提出，XGBoost(2016)、LightGBM(2017) 发扬光大。",
        "strengths": "精度高，对特征尺度不敏感，表格数据上常胜。",
        "weaknesses": "小数据容易过拟合，参数比单模型多。",
        "best_for": "图像/语音的数值特征、传感器表格等数据较多的任务。",
    },
    "mlp": {
        "name": "多层感知机",
        "en_name": "Multi-Layer Perceptron",
        "school": "神经网络",
        "tier": "light_nn",
        "requires_gpu": False,
        "principle": "全连接的小型神经网络，自动学习特征之间的非线性组合。",
        "performance": "表达力强，能体验“神经网络”；小数据上可能欠拟合或过拟合。",
        "history": "1986 年反向传播算法让它实用化，是神经网络复兴的起点。",
        "strengths": "表达力强，四类数值任务都能用，是理解神经网络的入门载体。",
        "weaknesses": "不可解释，要调网络结构与迭代次数，小数据不稳。",
        "best_for": "想让学生体验“神经网络”概念时。",
    },
    "svm": {
        "name": "支持向量机",
        "en_name": "Support Vector Machine",
        "school": "统计学习",
        "tier": "classical",
        "requires_gpu": False,
        "principle": "找一条“间隔最大”的分界线把类别分开，核函数还能画弯的边界。",
        "performance": "中小数据、特征清晰时精度高、泛化好。",
        "history": "1995 年 Cortes & Vapnik 提出，深度学习兴起前的主流算法。",
        "strengths": "泛化能力强，理论漂亮，中小数据稳健。",
        "weaknesses": "大数据慢、需要缩放，默认不直接输出概率。",
        "best_for": "传感器/表格这类中小规模数值任务。",
    },
}

# ---- display-only deep-learning catalog (not trainable in-app yet) ----

DISPLAY_INFO: dict[str, dict[str, Any]] = {
    "mobilenet": {
        "name": "MobileNet",
        "en_name": "MobileNet v2/v3",
        "school": "深度卷积网络",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "用深度可分离卷积做的轻量 CNN，专为手机/边缘设备设计。",
        "performance": "体量小、CPU 推理快，精度/速度平衡好——边缘端首选。本平台已用它做图像特征提取。",
        "history": "Google，v1(2017)→v2(2018)→v3(2019)。",
        "strengths": "轻量、CPU 可推理。",
        "weaknesses": "训练需显卡；精度略低于大模型。",
        "best_for": "迁移学习的图像特征提取器。",
    },
    "resnet": {
        "name": "ResNet 残差网络",
        "en_name": "ResNet",
        "school": "深度卷积网络",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "引入“跳跃连接”，让卷积网络能堆到上百层而不退化。",
        "performance": "2015 年 ImageNet 冠军，至今最常用的骨干网之一。",
        "history": "2015 年何恺明等（微软亚研院）提出。",
        "strengths": "精度高、迁移效果好。",
        "weaknesses": "大版本较重，训练需显卡。",
        "best_for": "高精度图像识别（需显卡）。",
    },
    "vit": {
        "name": "视觉 Transformer",
        "en_name": "Vision Transformer (ViT)",
        "school": "Transformer",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "把图像切成小块当作序列，用 Transformer 自注意力做分类。",
        "performance": "大数据下超过 CNN，是当前图像 SOTA 的主流方向。",
        "history": "2020 年 Google 提出，把 NLP 的 Transformer 引入视觉。",
        "strengths": "上限高、可扩展。",
        "weaknesses": "吃数据吃算力，小数据不如 CNN，训练/推理都偏重。",
        "best_for": "大规模图像任务（需显卡）。",
    },
    "clip": {
        "name": "CLIP 图文模型",
        "en_name": "CLIP",
        "school": "多模态",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "图文对比学习，可“零样本”按文字标签识别新类别，无需再训练。",
        "performance": "泛化极强，不训练也能识别没见过的类别。",
        "history": "2021 年 OpenAI 提出。",
        "strengths": "零样本、泛化强。",
        "weaknesses": "模型大，边缘端吃力。",
        "best_for": "零样本图像识别（需显卡/较强算力）。",
    },
    "fasttext": {
        "name": "fastText",
        "en_name": "fastText",
        "school": "词向量",
        "tier": "deep",
        "requires_gpu": False,
        "principle": "用词与子词向量 + 线性分类，兼顾词形变化。",
        "performance": "训练飞快、效果好，工业界常用的轻量文本方案。",
        "history": "2016 年 Facebook 开源。",
        "strengths": "快、轻、对词形鲁棒。",
        "weaknesses": "语义理解仍有限。",
        "best_for": "大规模文本分类（CPU 即可，后续可接入）。",
    },
    "textcnn": {
        "name": "TextCNN",
        "en_name": "TextCNN",
        "school": "深度卷积网络",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "用卷积在词向量上捕捉局部 n-gram 特征做分类。",
        "performance": "短文本分类又快又好。",
        "history": "2014 年 Yoon Kim 提出。",
        "strengths": "结构简单、短文本强。",
        "weaknesses": "捕捉长距依赖弱，训练建议用显卡。",
        "best_for": "短文本分类（需显卡训练）。",
    },
    "lstm": {
        "name": "LSTM 长短期记忆",
        "en_name": "LSTM / GRU",
        "school": "循环神经网络",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "按顺序读文本并记住上下文，擅长序列与长依赖。",
        "performance": "Transformer 出现前的 NLP 主力。",
        "history": "LSTM 1997（Hochreiter & Schmidhuber）、GRU 2014。",
        "strengths": "擅长序列建模。",
        "weaknesses": "训练慢、难并行，已被 Transformer 取代。",
        "best_for": "序列文本任务（需显卡）。",
    },
    "bert": {
        "name": "BERT 预训练语言模型",
        "en_name": "BERT / DistilBERT",
        "school": "Transformer",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "自注意力理解全局语义，预训练后微调到分类。",
        "performance": "中文文本分类 SOTA；DistilBERT 是轻量蒸馏版。",
        "history": "Transformer 2017、BERT 2018（均 Google）。",
        "strengths": "语义理解最强。",
        "weaknesses": "训练需显卡，CPU 推理偏慢，不适合课堂现训。",
        "best_for": "高精度文本理解（需显卡）。",
    },
    "cnn_spectrogram": {
        "name": "频谱图 CNN",
        "en_name": "Spectrogram CNN",
        "school": "深度卷积网络",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "把声音转成频谱图当“图片”，用 CNN 分类。",
        "performance": "环境声/乐器分类效果好。",
        "history": "2015 年起广泛用于音频分类。",
        "strengths": "比手工特征强。",
        "weaknesses": "训练需显卡才高效。",
        "best_for": "音频分类（需显卡训练）。",
    },
    "yamnet": {
        "name": "YAMNet 音频网络",
        "en_name": "YAMNet / VGGish / PANNs",
        "school": "深度卷积网络",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "在大规模音频上预训练的网络，可当现成的音频特征提取器。",
        "performance": "YAMNet 基于 MobileNet、CPU 可推理，比手工特征强很多。",
        "history": "VGGish 2017、YAMNet 2019、PANNs 2019/2020。",
        "strengths": "现成、特征强。",
        "weaknesses": "训练需显卡；平台宜当特征器。",
        "best_for": "音频迁移学习特征提取（后续可接入）。",
    },
    "wav2vec": {
        "name": "Wav2Vec2 / Whisper",
        "en_name": "Wav2Vec2 / Whisper",
        "school": "Transformer",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "自监督语音表示 / 端到端语音识别。",
        "performance": "语音识别 SOTA，Whisper 多语种强。",
        "history": "Wav2Vec2 2020（Meta）、Whisper 2022（OpenAI）。",
        "strengths": "识别精度高、多语种。",
        "weaknesses": "重，CPU 推理慢，需显卡。",
        "best_for": "语音识别（需显卡）。",
    },
    "deep_tabular": {
        "name": "深度表格网络",
        "en_name": "TabNet / FT-Transformer / TabPFN",
        "school": "神经网络",
        "tier": "deep",
        "requires_gpu": True,
        "principle": "专为表格设计的神经网络（注意力 / Transformer / 先验拟合）。",
        "performance": "少数大表格上能追平梯度提升；多数情况仍打不过 GBDT。",
        "history": "TabNet 2020、FT-Transformer 2021、TabPFN 2022。",
        "strengths": "前沿、可端到端。",
        "weaknesses": "工程成本高，通常不如 GBDT，建议用显卡。",
        "best_for": "大规模表格研究（需显卡）。",
    },
}

ALL_INFO: dict[str, dict[str, Any]] = {**CLASSIFIER_INFO, **DISPLAY_INFO}

# Trainable choices per data shape (drive train / compare / resolve).
TEXT_CHOICES = ["logistic_regression", "naive_bayes", "random_forest", "mlp"]
DENSE_CHOICES = ["logistic_regression", "knn", "random_forest", "gbdt", "mlp"]
SENSOR_CHOICES = ["decision_tree", "random_forest", "knn", "gbdt", "svm"]

# Display-only cards per task (locked in the UI; never trained in-app yet).
IMAGE_DISPLAY = ["svm", "mobilenet", "resnet", "vit", "clip"]
AUDIO_DISPLAY = ["svm", "cnn_spectrogram", "yamnet", "wav2vec"]
TEXT_DISPLAY = ["svm", "fasttext", "textcnn", "lstm", "bert"]
SENSOR_DISPLAY = ["deep_tabular"]


def make_classifier(choice: str, sample_count: int):
    if choice == "logistic_regression":
        return LogisticRegression(max_iter=1000)
    if choice == "naive_bayes":
        return MultinomialNB()
    if choice == "random_forest":
        return RandomForestClassifier(n_estimators=80, random_state=7)
    if choice == "knn":
        return KNeighborsClassifier(n_neighbors=max(1, min(3, sample_count - 1)))
    if choice == "decision_tree":
        return DecisionTreeClassifier(max_depth=4, random_state=7)
    if choice == "gbdt":
        # HistGradientBoosting needs dense input — only offered on dense/tabular tasks.
        return HistGradientBoostingClassifier(random_state=7)
    if choice == "mlp":
        return MLPClassifier(hidden_layer_sizes=(64,), max_iter=400, random_state=7)
    if choice == "svm":
        # Only offered where prediction needs no probabilities (sensor task).
        return SVC(random_state=7)
    raise MLDataError(f"暂不支持这种模型：{choice}")


def resolve_choice(model_choice: str | None, allowed: list[str], default: str) -> str:
    if not model_choice:
        return default
    if model_choice not in allowed:
        names = "、".join(ALL_INFO[item]["name"] for item in allowed if item in ALL_INFO)
        raise MLDataError(f"这个任务不支持所选模型，可训练的有：{names}。")
    return model_choice


def _card(slug: str, default: str, trainable: bool) -> dict[str, Any]:
    info = ALL_INFO[slug]
    return {"slug": slug, "default": slug == default, "trainable": trainable, **info}


def list_choice_info(
    trainable: list[str],
    display: list[str],
    default: str,
) -> list[dict[str, Any]]:
    """Cards for the training page: trainable estimators first, locked deep cards after."""
    cards = [_card(slug, default, True) for slug in trainable]
    cards += [_card(slug, default, False) for slug in display if slug in ALL_INFO]
    return cards


def cross_val_accuracy(
    build_model: Callable[[], Any],
    features: list,
    labels: list[str],
    counts: dict[str, int],
) -> float | None:
    min_count = min(counts.values())
    if min_count < CROSS_VAL_MIN_PER_CLASS:
        return None
    folds = min(3, min_count)
    scores = cross_val_score(
        build_model(),
        features,
        labels,
        cv=StratifiedKFold(n_splits=folds, shuffle=True, random_state=7),
    )
    return float(np.mean(scores))


def subsample_labeled(labeled: dict[str, list], cap: int = COMPARE_MAX_SAMPLES) -> dict[str, list]:
    """Cap a {label: [items]} map to ~cap items, stratified, for the compare race.

    Used before expensive feature extraction (e.g. MobileNet over every image), so
    "对比所有模型" stays fast no matter how large the imported dataset is.
    """
    total = sum(len(items) for items in labeled.values())
    if total <= cap:
        return labeled
    rng = random.Random(7)
    sampled: dict[str, list] = {}
    for label, items in labeled.items():
        take = min(len(items), max(2, round(len(items) * cap / total)))
        sampled[label] = rng.sample(items, take)
    return sampled


def _subsample_for_compare(features: list, labels: list[str]) -> tuple[list, list[str]]:
    """Stratified down-sample to COMPARE_MAX_SAMPLES so the race stays fast.
    Index-based, so it works for dense vectors and raw text alike."""
    if len(labels) <= COMPARE_MAX_SAMPLES:
        return features, labels
    rng = random.Random(7)
    by_label: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        by_label.setdefault(label, []).append(index)
    total = len(labels)
    keep: list[int] = []
    for indices in by_label.values():
        take = min(len(indices), max(2, round(len(indices) * COMPARE_MAX_SAMPLES / total)))
        keep.extend(rng.sample(indices, take))
    keep.sort()
    return [features[i] for i in keep], [labels[i] for i in keep]


def compare_rows(
    choices: list[str],
    default: str,
    build_model: Callable[[str], Any],
    features: list,
    labels: list[str],
    counts: dict[str, int],
) -> list[dict[str, Any]]:
    """Fit every choice on the same features and report comparable metrics."""
    features, labels = _subsample_for_compare(features, labels)
    counts = class_counts(labels)
    rows: list[dict[str, Any]] = []
    for choice in choices:
        start = time.perf_counter()
        model = build_model(choice)
        model.fit(features, labels)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        rows.append(
            {
                "model_choice": choice,
                "name": ALL_INFO[choice]["name"],
                "default": choice == default,
                "train_accuracy": float(model.score(features, labels)),
                "cross_val_accuracy": cross_val_accuracy(
                    lambda choice=choice: build_model(choice), features, labels, counts
                ),
                "train_ms": elapsed_ms,
            }
        )
    return rows
