"""Classifier registry behind the multi-model selection feature.

Every choice carries student-facing Chinese metadata (principle, strengths,
weaknesses, best-for, school of AI) so the UI can explain how the models
differ — the point is teaching, not just switching estimators.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier

from app.ml.base import MLDataError

CROSS_VAL_MIN_PER_CLASS = 3

CLASSIFIER_INFO: dict[str, dict[str, str]] = {
    "logistic_regression": {
        "name": "逻辑回归",
        "school": "统计学习",
        "principle": "给每个特征打分加权，算出属于每个类别的概率。",
        "strengths": "快、稳定，能输出概率，是大多数任务的可靠起点。",
        "weaknesses": "只能画比较“直”的分类边界，特征不好时容易混淆。",
        "best_for": "特征清晰、数据量不大的任务（默认之选）。",
    },
    "naive_bayes": {
        "name": "朴素贝叶斯",
        "school": "统计学习",
        "principle": "统计每个词在各类别里出现的频率，再用概率公式反推类别。",
        "strengths": "极快，小数据表现好——垃圾邮件过滤就靠它出名。",
        "weaknesses": "假设词和词互相独立，句子结构复杂时会失准。",
        "best_for": "文本分类，尤其是关键词区分明显的场景。",
    },
    "random_forest": {
        "name": "随机森林",
        "school": "集成学习",
        "principle": "训练很多棵各不相同的决策树，预测时让它们投票。",
        "strengths": "抗噪声、不挑数据，通常比单棵树更准。",
        "weaknesses": "模型较大，投票过程不如单棵树的规则直观。",
        "best_for": "数据比较杂、想要稳妥结果的时候。",
    },
    "knn": {
        "name": "K 近邻",
        "school": "实例学习",
        "principle": "不总结规则——预测时找出和新样本最像的 K 个老样本，跟多数走。",
        "strengths": "原理最直观：“物以类聚”。小数据也能用。",
        "weaknesses": "样本多了预测会变慢，容易被无关特征带偏。",
        "best_for": "样本少、特征本身有意义时（比如 MobileNet 提取的图像特征）。",
    },
    "decision_tree": {
        "name": "决策树",
        "school": "规则学习",
        "principle": "自动学出一串 if-else 问题，一步步把数据分开。",
        "strengths": "完全可解释——学到的规则能直接读出来。",
        "weaknesses": "容易死记硬背（过拟合），数据稍变规则就可能大变。",
        "best_for": "传感器数值这类任务，以及需要向别人解释决策过程的场景。",
    },
}

TEXT_CHOICES = ["logistic_regression", "naive_bayes", "random_forest"]
DENSE_CHOICES = ["logistic_regression", "knn", "random_forest"]
SENSOR_CHOICES = ["decision_tree", "random_forest", "knn"]


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
    raise MLDataError(f"暂不支持这种模型：{choice}")


def resolve_choice(model_choice: str | None, allowed: list[str], default: str) -> str:
    if not model_choice:
        return default
    if model_choice not in allowed:
        names = "、".join(CLASSIFIER_INFO[item]["name"] for item in allowed)
        raise MLDataError(f"这个任务不支持所选模型，可选：{names}。")
    return model_choice


def choice_info(choice: str) -> dict[str, str]:
    return {"slug": choice, **CLASSIFIER_INFO[choice]}


def list_choice_info(choices: list[str], default: str) -> list[dict[str, Any]]:
    return [{**choice_info(choice), "default": choice == default} for choice in choices]


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


def compare_rows(
    choices: list[str],
    default: str,
    build_model: Callable[[str], Any],
    features: list,
    labels: list[str],
    counts: dict[str, int],
) -> list[dict[str, Any]]:
    """Fit every choice on the same features and report comparable metrics."""
    rows: list[dict[str, Any]] = []
    for choice in choices:
        start = time.perf_counter()
        model = build_model(choice)
        model.fit(features, labels)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        rows.append(
            {
                "model_choice": choice,
                "name": CLASSIFIER_INFO[choice]["name"],
                "default": choice == default,
                "train_accuracy": float(model.score(features, labels)),
                "cross_val_accuracy": cross_val_accuracy(
                    lambda choice=choice: build_model(choice), features, labels, counts
                ),
                "train_ms": elapsed_ms,
            }
        )
    return rows
