# 应用案例（学以致用）二期 · 版本完成报告

> 日期：2026-06-19 · **更新：2026-06-21（补完技术↔案例双向互链，导航闭环）**
> 分支：`docs/application-cases-prd`（基于 v0.7.0，**独立于 v0.8.0**）· 建议作为 **v0.9.0** 落地
> 配套规划：`PRD_APPLICATION_CASES.md`（架构/分期）、`APPLICATION_CASES_SHORTLIST.md`（选型决策）

---

## 1. 概述

二期目标：在「按技术分类」的任务组织之上，新增一层「**按应用案例分类**」，让学生把学过的技术用到真实场景里走完整四步（学以致用）。

本版交付：**该层基础设施 + 5 个典型应用案例 + 技术↔案例双向互链（导航闭环）**，覆盖现有 6 个能力中的 5 个。唯一未做的是车牌检测案例——它依赖 v0.8.0 的 YOLO26，而 0.8 不在本独立分支上（经确认：保持与 0.8 独立，车牌留待 0.8 合入后再接，见 §7）。

实现严守「**零新能力、复用现有四步与引擎**」：未改动 `app/ml/*`。

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
- **标准二 · 一脉相承**：零新 `ai_capability`，每个案例落在现有 6 能力之一，复用同一套四步流程 + `engine.py` + 数据导入 + 教育字段。首页卡片用「**用到：X**」标签明示技术出处；并通过 §4 的双向互链，形成「先学技术 → 再用到场景 → 点回了解原理」的可点击闭环。

---

## 4. 实现清单（基础设施，doc 之外的代码改动）

- `app/models.py` — `TaskDefinition` 新增 3 个可选字段（默认空，纯增量）：`case_scenario` / `bundled_dataset_id` / `case_domain`。
- `app/task_catalog.py` — `APPLICATION_CASES`（5 个 `TaskDefinition`）+ `CompetitionDefinition(slug="application_cases")`；`get_competition()` 对 `application_cases` 做「始终可见」特判（同 `GENERAL_ML`），不进 edition 过滤。**互链映射助手** `related_case_for_capability` / `related_general_task_for_case`（按共享 `ai_capability` 派生，无硬编码）。
- `app/main.py` — 首页路由传入案例 + `CAPABILITY_LABELS`；`/competition/application_cases` 返回 404（同 `general_ml`）；workflow/project 路由注入相关任务上下文；`ASSET_VERSION` 0.12.0 → 0.13.1。
- `templates/index.html` — 新增「应用案例 · 学以致用」`.case-grid` 区，卡片数据驱动自动渲染。
- `templates/workflow.html` — 条件渲染 `case_scenario`；**双向互链**：案例页「本案例用到的技术 → X」可点回对应通用任务；通用任务页「学会了？去真实场景练一练 → 案例名」。
- `templates/project.html` — 通用任务第 4 步导出面板**附加**「去练真实案例 →」链接（不改动原 `next_steps` 教育文案）。
- `static/styles.css` — `.case-grid` / `.case-tag` / `.case-pointer` 等，复用现有 CSS 变量。
- `tests/test_task_catalog.py`、`tests/test_app_routes.py` — 案例数量/slug/能力/字段、路由 200、首页含案例、**互链双向链接存在性、映射助手正确性、检测无案例链接**等覆盖。
- **未触碰** `app/ml/*`。

**提交**（`docs/application-cases-prd`，均无 Co-Authored-By）：
- `b48b834` docs: PRD　`76f36ba` docs: 选型决策　`e165dd4` feat: 首批 3 案例　`b306c05` feat: 扩充图像/语音 2 案例　`4e2e5aa` docs: 完成报告　`f0bf1e8` feat: 技术↔案例双向互链

---

## 5. 测试与验证（orchestrator 独立复跑）

- **ruff**：`All checks passed!`（`app tests`）。
- **全量**：`128 passed, 8 skipped, 1 failed`。
  - 唯一失败 `test_ml_engine.py::test_detect_lite_trains_and_predicts`：本 worktree 缺 gitignored 的 `models_pretrained/`（检测预训练 ONNX），报 `MLDataError: 需要预训练检测模型`。属**环境前置缺失**，且本分支**零检测代码改动**——非回归；装了模型的环境（CI / 主仓）该测试通过（独立测试 Agent 在有模型的环境实测全部通过）。
- **互链渲染验证**（TestClient）：案例页含指向通用任务的链接 ✓；通用任务页含指向案例的链接 ✓；检测任务页**无**案例链接 ✓。
- **首页渲染**（DOM 快照）：「应用案例 · 学以致用」区 5 张卡片齐全，能力标签（用到：文本分类 / 智能问答 / 传感器决策 / 图像分类 / 语音分类）正确。

---

## 6. 循环过程（按要求：Opus 编写 Agent + 独立测试 Agent）

| 轮 | 角色 | 模型 | 产出 |
|---|---|---|---|
| 1 | 编写 Agent | **Opus 4.8** | 基础设施 + 首批 3 案例（`e165dd4`） |
| 2 | 测试 Agent | Sonnet | 独立验证 → PASS（122 passed、ruff clean、scope 无越界） |
| 3 | 编写 Agent | **Opus 4.8** | 扩充图像/语音 2 案例（`b306c05`） |
| 4 | 编写 Agent | **Opus 4.8** | 技术↔案例双向互链（`f0bf1e8`） |
| 终 | orchestrator | — | 独立复跑测试 + 渲染验证 + 本报告 |

---

## 7. 延后 / 未完成（诚实标注）

- **车牌检测案例（目标检测）— 未做（经确认延后）**：需 v0.8.0 的 **YOLO26**（端到端检测，本独立分支不含 0.8）+ 检测导出分支 + 车牌数据。**已与用户确认：保持本分支与 0.8 独立，车牌留待 0.8 合入后再接**（车牌靠 YOLO 才对路，见 PRD §6.1；本分支已有的「轻量检测」对车牌效果有限）。
- **图像/语音案例的「一键数据集」— 待策展**：垃圾分类、语音指令现走「学生自采」（采集页），功能完整；待按 `docs/DATASET_FORMAT.md` 策展整理数据集后，填 `bundled_dataset_id` 实现一键导入。
- **`/cases` 领域分组页 — 有意跳过**：PRD §4.2 明确「案例少时先不做、首页平铺即可」，5 个案例下属于过早建设。案例增多后再加。
- ~~技术任务↔案例双向互链~~ — **本次已完成**（`f0bf1e8`）。

---

## 8. 版本定位与合并建议

- 本分支 6 个提交独立于 0.8，**互不冲突**（application 分支零检测代码）。建议作为 **v0.9.0**；与 0.8 的合并先后由你定。
- **合入 `main` 时再统一补**（避免与 0.8 的版本号/§0 冲突，留到合并时一次性处理）：`CLAUDE.md` §0/§3/§4 的案例层文档、`pyproject.toml` 版本号、`CHANGELOG.md` 条目。

---

## 9. 一句话结论

**二期「应用案例」层 + 5 个典型案例 + 技术↔案例双向互链（导航闭环）已实现并验证通过（除环境前置的检测模型外全绿），完全复用现有四步与引擎、零新能力。** 在「不依赖 0.8」的前提下本版已彻底完成；仅车牌检测因依赖 0.8 的 YOLO 经确认延后。
