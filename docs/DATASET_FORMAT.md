# 教学数据集标准格式规范

本文件定义 **Lite DeepLearning Studio** 平台「从整理好的数据集导入」功能所读取的数据集标准格式。整理数据集的人（含自动化工具，如 Codex）请严格按本规范产出，平台即可一键导入到学生项目，让学生走完整流程：**准备数据 → 训练模型 → 测试效果 → 导出材料**。

> 阅读对象：负责清洗 / 转换 / 整理数据集的人或工具。
> 平台侧实现见 `app/services/dataset_library.py`（扫描与列出）和 `app/services/project_service.py`（导入逻辑）。

---

## 1. 顶层目录结构

所有数据集放在一个**数据集根目录**下。平台通过环境变量 `LDS_DATASETS_ROOT` 指向它（默认是项目根的 `datasets/`）。

```text
<数据集根目录>/
  01_可直接用于平台主流程/        # ← 只有这个目录下的数据集会被平台扫描
    图像分类/
      <数据集名>/
      <数据集名>/
    文本分类/
      <数据集名>/
    音频分类/
      <数据集名>/
    传感器决策_CSV/
      <数据集名>/
    智能问答/                    # 规划中（见 §3.5），格式已定义
    文字查错_OCR/                # 规划中（见 §3.6），格式已定义
  02_暂不纳入平台主流程/          # 平台忽略；放检测/权重/原始语料等
```

**硬性规则**

- 平台**只扫描** `01_可直接用于平台主流程/<分类>/<数据集>/` 这一层（深度固定为两级）。放浅或放深都不会被发现。
- 每个 `<数据集>` 目录**必须**有一个 `platform_dataset.json`（见 §2），否则被跳过。
- 不要包含 `__MACOSX/`、`.DS_Store` 等压缩垃圾文件。
- 暂不支持训练导出的数据（目标检测、模型权重、未标注图片、需二次转换的原始语料）放 `02_暂不纳入平台主流程/`，平台不会读取。

---

## 2. 清单文件 `platform_dataset.json`

每个数据集目录根下必须有此文件。平台用它来在导入下拉里展示该数据集，并校验类型。

```json
{
  "id": "唯一ID字符串",
  "title": "数据集中文名（展示给老师/学生）",
  "ai_capability": "image_classifier",
  "labels": ["类别1", "类别2", "类别3"],
  "train_count": 1200,
  "test_count": 300,
  "recommended_model": "可选，仅信息展示"
}
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | ✅ | 全库唯一。导入时平台按 id 定位，不依赖目录名。建议用稳定的来源 id。|
| `title` | ✅ | 展示名称。**这是老师在下拉里看到的名字**，要清楚可读。|
| `ai_capability` | ✅ | 决定导入逻辑。必须是 §3 列出的合法值之一。|
| `labels` | ✅ | 类别名数组。**必须等于真实类别**，且与图像/音频的子目录名一致。**不得混入文件名**（如 `"cat.jpg"` 这类是错误的，会被平台过滤但说明数据有问题）。|
| `train_count` | 建议 | 训练样本总数，仅用于展示。|
| `test_count` | 建议 | 测试样本总数，仅用于展示。|
| `recommended_model` | 否 | 自由文本，仅信息展示，平台不据此改变行为。|

`ai_capability` 合法值：`image_classifier`、`text_classifier`、`audio_classifier`、`sensor_decision_model`、`qa_retrieval`、`ocr_typo_checker`。

---

## 3. 各能力的数据格式

> **导入器当前支持状态**：✅ 已支持＝平台「从整理数据集导入」可直接读取；🕗 规划中＝格式已定义、待接入导入器（产出可以先按此准备）。

### 3.1 图像分类 `image_classifier` ✅

```text
<数据集>/
  platform_dataset.json
  train/<类别名>/*.jpg|*.jpeg|*.png|*.bmp|*.gif|*.webp
  test/<类别名>/*.jpg|...           # 可选，强烈建议
```

- **类别 = 直接装图片的那层文件夹名**。`train/猫/`、`train/狗/` → 类别「猫」「狗」。
- **类别名必须人类可读**。用 `train/瓢虫/`、`train/蝴蝶/`，**不要**用 `train/0/`、`train/1/`——学生会直接看到这些名字。
- 不要再套 `training_set/`、`images/` 等中间层；图片直接放在 `train/<类别名>/` 下。
- 单张图片 ≤ 8MB；超限的会被跳过。
- `test/` 与 `train/` 类别一致；用于第 3 步「从测试集随机抽样测试」。

### 3.2 文本分类 `text_classifier` ✅

```text
<数据集>/
  platform_dataset.json
  train/text_samples.json
  test/text_samples.json            # 可选，强烈建议
```

`text_samples.json` 格式：

```json
{
  "samples": [
    {"text": "样本文本内容", "label": "类别名"},
    {"text": "另一条样本", "label": "类别名"}
  ]
}
```

- 每条样本必须同时有非空 `text` 和 `label`。
- `label` 集合应等于 `platform_dataset.json` 的 `labels`。
- 一行一条，文本不要超长（适合 K12 句子/短段落）。

### 3.3 音频分类 `audio_classifier` ✅

```text
<数据集>/
  platform_dataset.json
  train/<类别名>/*.wav
  test/<类别名>/*.wav               # 可选，强烈建议
```

- 只接受 `.wav`。建议 16kHz、单声道（平台特征提取按此设计）。
- 单个文件 ≤ 10MB。
- 类别规则同图像：文件夹名即类别，需可读。

### 3.4 传感器决策 `sensor_decision_model` ✅

```text
<数据集>/
  platform_dataset.json
  sensor_data.csv
```

`sensor_data.csv` 格式：带表头的 CSV，**最后一列是动作标签**，前面各列是传感器数值。

```csv
temperature,humidity,action
30,80,开风扇
22,40,不动作
31,85,开风扇
```

- **最后一列必须是离散的动作标签**（重复出现、可枚举），这是分类目标。
- **不要用连续量当标签**（例如「距离=40.45」这种回归数据）。平台只做分类，连续标签会让每个值各成一类、无法训练。若原始是回归数据，需先分桶成「近/中/远」这类离散类别。
- 每种动作至少若干行（见 §4 样本量）。
- 此能力没有独立 test 集（学生在第 3 步手动输入数值测试）。

### 3.5 智能问答 `qa_retrieval` 🕗

```text
<数据集>/
  platform_dataset.json             # ai_capability = qa_retrieval，labels 可留空 []
  train/qa_pairs.json
```

`qa_pairs.json` 格式：

```json
{
  "pairs": [
    {"question": "开馆时间是几点？", "answer": "上午9点到下午5点。"},
    {"question": "门票多少钱？", "answer": "成人20元，学生半价。"}
  ]
}
```

- 检索式问答：同一个 `answer` 可以对应多种 `question` 问法，越丰富越好。
- 无类别概念，`labels` 写 `[]`。

### 3.6 文字查错 `ocr_typo_checker` 🕗

OCR 查错不是「多样本数据集」，而是一份**标准答案**。

```text
<数据集>/
  platform_dataset.json             # ai_capability = ocr_typo_checker
  ocr_reference.json
```

`ocr_reference.json` 格式：

```json
{
  "correct_text": "这是知识卡片上的正确文字。",
  "observed_sample": "这是知识卡片上的错误文字。"
}
```

- `correct_text` 必填（标准答案）；`observed_sample` 选填（一段带错字的示例，用于演示）。

---

## 4. 通用质量约束（务必遵守）

1. **类别名可读**：所有类别（图像/音频文件夹名、文本/CSV 的 label）都是直接展示给学生的，用中文或有意义的英文词，**禁止纯数字编号**。
2. **类别一致性**：`platform_dataset.json.labels`、目录名、样本里的 label 三者必须一致，互相对得上。
3. **样本量**：平台在每类少于 **10** 条时会提示数据偏少；交叉验证需要每类 ≥ **3** 条。每类建议至少 10 条以上，分类边界清晰。
4. **训练/测试分离**：`train/` 与 `test/` 内容不重叠。`test/` 可选但强烈建议——它驱动第 3 步「从测试集随机抽样测试」。
5. **体积**：大数据集没问题，平台导入时按「轻量(每类100) / 标准(每类300) / 完全(全部)」**随机抽取**，并且每次导入是**替换**而非累加，方便老师用不同子集做多次对比实验。但单文件大小仍受 §3 限制。
6. **编码**：JSON 一律 UTF-8；CSV 用半角逗号分隔（不要全角逗号）。
7. **干净**：不带 `__MACOSX/`、`.DS_Store`、缩略图等无关文件。

---

## 5. 自检清单

整理完一个数据集后，逐项确认：

- [ ] 放在 `01_可直接用于平台主流程/<分类>/<数据集名>/`，深度正确。
- [ ] 有 `platform_dataset.json`，字段齐全、`ai_capability` 合法。
- [ ] `labels` = 真实类别，无文件名、无纯数字编号。
- [ ] 图像/音频：`train/<类别名>/` 直接装文件，无多余中间层。
- [ ] 文本：`train/text_samples.json` 为 `{"samples":[{text,label}]}`。
- [ ] 传感器：CSV 末列为离散动作标签，不是连续量。
- [ ] 有 `test/`（图像/音频/文本），与 train 不重叠。
- [ ] 无压缩垃圾文件；JSON 为 UTF-8。
- [ ] 每类样本量达标（建议 ≥10）。
