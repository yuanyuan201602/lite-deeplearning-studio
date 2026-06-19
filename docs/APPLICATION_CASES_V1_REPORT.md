# 应用案例（学以致用）二期 · 版本完成报告

> 日期：2026-06-19 · 分支：`docs/application-cases-prd`（基于 v0.7.0，**独立于 v0.8.0**）· 建议作为 **v0.9.0** 落地
> 配套规划：`PRD_APPLICATION_CASES.md`（架构/分期）、`APPLICATION_CASES_SHORTLIST.md`（选型决策）

---

## 1. 概述

二期目标：在「按技术分类」的任务组织之上，新增一层「**按应用案例分类**」，让学生把学过的技术用到真实场景里走完整四步（学以致用）。

本版交付：**该层的基础设施 + 5 个典型应用案例**（覆盖现有 6 个能力中的 5 个）。唯一未做的是车牌检测案例——它依赖 v0.8.0 的 YOLO26，而 0.8 不在本独立分支上（见 §6）。

实现完全遵守「**零新能力、复用现有四步与引擎**」：未改动 `app/ml/*`。

---

## 2. 交付的案例（5 个 · 每个 = 现有能力 + 真实场景）

| 案例 | 复用能力（一脉相承） | 真实场景（典型触点） | 数据方式 | slug |
|---|---|---|---|---|
| 垃圾短信拦截 | 文本分类 `text_classifier` | 手机拦截骚扰短信 | 现成样本包 `general_text_spam` | `case_spam_filter` |
| 校园问答助手 | 智能问答 `qa_retrieval` | 智能客服/公众号自动回复 | 现成样本包 `general_qa_school` | `case_campus_qa` |
| 运动计步 | 传感器决策 `sensor_decision_model` | 手环「今日步数」 | 现成样本包 `general_sensor_motion` | `case_step_counter` |
| 垃圾分类 | 图像分类 `image_classifier` | 垃圾分类桶 / 智能垃圾桶 | 学生自采（采集页） | `case_garbage_sort` |
| 语音指令 | 语音分类 `audio_classifier` | 小爱同学「开灯/关灯」 | 学生自采（采集页） | `case_voice_command` |

---

## 3. 两条选型标准的落实

- **标准一 · 典型/生活常用**：每个案例都对应一个学生亲身用过的产品（手机拦截、智能客服、手环、垃圾分类桶、语音音箱）。抽象练习（如形状分类）被明确排除（见 SHORTLIST §6）。
- **标准二 · 一脉相承**：零新 `ai_capability`，每个案例落在现有 6 能力之一，复用同一套四步流程 + `engine.py` + 数据导入 + 教育字段。首页卡片用「**用到：X**」标签明示其技术出处，形成「先学技术 → 再用到场景」的闭环。

---

## 4. 实现清单（基础设施，doc 之外的代码改动）

- `app/models.py` — `TaskDefinition` 新增 3 个可选字段（默认空，纯增量）：`case_scenario` / `bundled_dataset_id` / `case_domain`。
- `app/task_catalog.py` — `APPLICATION_CASES`（5 个 `TaskDefinition`）+ `CompetitionDefinition(slug="application_cases")`；`get_competition()` 对 `application_cases` 做「始终可见」特判（同 `GENERAL_ML`），不进 edition 过滤。
- `app/main.py` — 首页路由传入案例 + `CAPABILITY_LABELS`（能力→中文名）；`/competition/application_cases` 返回 404（同 `general_ml`）；`ASSET_VERSION` 0.12.0 → 0.13.0。
- `templates/index.html` — 新增「应用案例 · 学以致用」`.case-grid` 区（机器学习任务区与深度学习地图 banner 之间），卡片数据驱动自动渲染。
- `templates/workflow.html` — 条件渲染 `case_scenario` + 「用到的技术」指针（仅在字段存在时，不影响现有任务）。
- `static/styles.css` — `.case-grid` / `.case-tag` 等，复用现有 CSS 变量与卡片语言。
- `tests/test_task_catalog.py`、`tests/test_app_routes.py` — 新增/扩展：案例数量、slug、能力、字段、路由 200、首页含案例标题等覆盖。
- **未触碰** `app/ml/*`。

**提交**（`docs/application-cases-prd`，均无 Co-Authored-By）：
- `b48b834` docs: PRD　`76f36ba` docs: 选型决策　`e165dd4` feat: 首批 3 案例　`b306c05` feat: 扩充图像/语音 2 案例

---

## 5. 测试与验证（orchestrator 独立复跑）

- **ruff**：`All checks passed!`（`app tests`）。
- **新增测试**：`tests/test_task_catalog.py` + `tests/test_app_routes.py` → **51 passed**。
- **全量**：`122 passed, 8 skipped, 1 failed`。
  - 唯一失败 `test_ml_engine.py::test_detect_lite_trains_and_predicts`：本 worktree 缺 gitignored 的 `models_pretrained/`（检测预训练 ONNX），报 `MLDataError: 需要预训练检测模型`。属**环境前置缺失**，且本分支**零检测代码改动**——非回归；装了模型的环境（CI / 主仓）该测试通过（独立测试 Agent 在有模型的环境实测全 122 通过）。
- **浏览器渲染**（DOM 快照，server 跑 worktree 代码）：首页「应用案例 · 学以致用」区 **5 张卡片**齐全（垃圾短信拦截 / 校园问答助手 / 运动计步 / 垃圾分类 / 语音指令），能力标签（用到：文本分类 / 智能问答 / 传感器决策 / 图像分类 / 语音分类）正确；案例 workflow 路由 200。（preview 截图工具本环境返回空白，已用 DOM 快照 + 路由测试替代取证。）

---

## 6. 循环过程（按要求：Opus 编写 Agent + 独立测试 Agent）

| 轮 | 角色 | 模型 | 产出 |
|---|---|---|---|
| 1 | 编写 Agent | **Opus 4.8** | 基础设施 + 首批 3 案例（`e165dd4`） |
| 2 | 测试 Agent | Sonnet | 独立验证：122 passed、ruff clean、scope 无越界 → PASS |
| 3 | 编写 Agent | **Opus 4.8** | 扩充图像/语音 2 案例（`b306c05`） |
| 终 | orchestrator | — | 独立复跑测试 + 浏览器 DOM 验证 + 本报告 |

---

## 7. 延后 / 未完成（诚实标注）

- **车牌检测案例（目标检测）— 未做**：需 v0.8.0 的 **YOLO26**（端到端检测，本独立分支不含 0.8）+ 检测导出分支 + 车牌数据。待 0.8 合入后接（车牌靠 YOLO 才对路，见 PRD §6.1）。
- **图像/语音案例的「一键数据集」— 待策展**：垃圾分类、语音指令现走「学生自采」（采集页），功能完整；待按 `docs/DATASET_FORMAT.md` 策展整理数据集后，填 `bundled_dataset_id` 实现一键导入。
- **PRD 二期增强项 — 未做**：`/cases` 领域分组页、技术任务↔案例双向 `next_steps` 互链。

---

## 8. 版本定位与合并建议

- 本分支 4 个提交独立于 0.8，**互不冲突**（application 分支零检测代码）。建议作为 **v0.9.0**；与 0.8 的合并先后由你定。
- **合入 `main` 时再统一补**（避免与 0.8 的版本号/§0 冲突，留到合并时一次性处理）：`CLAUDE.md` §0/§3/§4 的案例层文档、`pyproject.toml` 版本号、`CHANGELOG.md` 条目。

---

## 9. 一句话结论

**二期「应用案例」层 + 5 个典型案例已实现并验证通过（除环境前置的检测模型外全绿），完全复用现有四步与引擎、零新能力；仅车牌检测因依赖 0.8 的 YOLO 延后。** 本版可作为 v0.9.0 的核心，待与 0.8 协调合并。
