# CLAUDE.md

This file is the authoritative guide for Claude Code working in this repository. Read it before making changes.

---

## 1. What This Project Is

**Lite DeepLearning Studio** is a K12 in-browser machine-learning workbench used at 南昌市第二十三中学 for AI competition preparation. Students complete an end-to-end AI project in four sequential browser steps without installing anything:

```
准备数据 → 训练模型 → 测试效果 → 导出材料
```

Training runs in-process (scikit-learn). The export zip bundles the trained `.joblib` model, runnable Python scripts (`train.py`, `predict.py`, `run.py`), a 行空板 M10 deployment layer, and competition submission docs.

**Design philosophy:**
- Zero-install for students. Everything runs from a single `python scripts/start_studio.py` the teacher launches once.
- Steps are strictly sequential and locked — step N unlocks only after step N-1 completes. This prevents students from exporting a model-less package.
- The in-app model and the exported `predict.py` must stay byte-identical in their feature extraction. Any change to one side requires the same change on the other (see Section 9).
- Error messages are in Chinese (学生直接看得懂).
- The tutorial sidebar covers 6 chapters of ML theory so students can work without teacher explanations.

---

## 2. Editions

Two competition flavors ship from one codebase. Controlled by `LDS_EDITION` env var or `--edition` CLI flag.

| Edition slug | Name | Capabilities used |
|---|---|---|
| `smart_museum` | 智能博物 | image_classifier, ocr_typo_checker, text_classifier, qa_retrieval |
| `future_creator` | 优创未来 | image_classifier, sensor_decision_model |
| `all` (default) | Lite DeepLearning Studio | all of the above + GENERAL_ML tasks |

`GENERAL_ML` (`slug="general_ml"`) is a special non-competition group always shown on the homepage. It bypasses edition filtering and has no `/competition/` page.

---

## 3. Complete Task Catalog

### GENERAL_ML (always visible, not edition-gated)

| slug | title | ai_capability | sample_dataset_kind |
|---|---|---|---|
| `general_image_classifier` | 图像分类 | `image_classifier` | `image` |
| `general_text_classifier` | 文本分类 | `text_classifier` | `text` |
| `general_audio_classifier` | 语音分类 | `audio_classifier` | `audio` |
| `general_qa_retrieval` | 智能问答 | `qa_retrieval` | `qa` |
| `general_sensor_decision` | 传感器决策 | `sensor_decision_model` | `sensor` |

All 5 GENERAL_TASKS have `concept_intro` (concept card on workflow page) and `step_guides[4]` (collapsible blocks in each step panel) filled in, added in v0.2.0.

### SMART_MUSEUM_TASKS

| slug | title | ai_capability | group |
|---|---|---|---|
| `heritage_face_intro` | 挑战一：认识非遗传承匠人 | `image_classifier` | 小学/初中/高中 |
| `heritage_ocr_typo` | 挑战二：了解非遗专业知识 | `ocr_typo_checker` | 小学/初中/高中 |
| `heritage_text_classifier` | 挑战三：非遗文化分类学览 | `text_classifier` | 小学/初中/高中 |
| `heritage_sentence_classifier` | 挑战四：非遗文化深化认知 | `text_classifier` | 小学/初中/高中 |
| `heritage_qa_helper` | 非遗知识问答模板 | `qa_retrieval` | 创意拓展 |

### FUTURE_CREATOR_TASKS

| slug | title | ai_capability | group |
|---|---|---|---|
| `image_recognition_starter` | 图像识别快速模板 | `image_classifier` | 小学/初中/高中 |
| `sensor_decision_template` | 传感器决策程序模板 | `sensor_decision_model` | 创意应用 |
| `primary_voice_image_interaction` | 小学组：语音互动与单类图像识别 | `image_classifier` | 小学组 |
| `junior_model_calling_workflow` | 初中组：视觉模型训练与调用 | `image_classifier` | 初中组 |
| `senior_llm_vision_motion` | 高中组：大模型语音互动、视觉识别与运动控制 | `image_classifier` | 高中组（含中职） |

---

## 4. Feature Status

### Done (v0.6.0, 2026-06-13) — object detection (phase 1)

- **Trainable detection task** (`ai_capability="object_detector_trainable"`, `sample_dataset_kind="detect"`): a 4-step detection flow with its own front-end (`static/detect.js`, loaded instead of app.js by capability in project.html).
- **Algorithm A · lite detector** (`app/ml/detect_lite.py`): classic-R-CNN-style — `object_detector.propose_boxes()` gives class-agnostic SSD candidate boxes; train crops each labeled box → `image_classifier.image_features_from_image()` (MobileNet/pixel) → LogisticRegression + a 背景 negative class; predict = propose → crop → classify → drop 背景/low-score → NMS. Reuses the image pipeline, runs on CPU in seconds, zero new deps.
- **Annotation tool** (`detect.js`): canvas draw/delete boxes + per-box label + multi-image nav. Storage: `dataset/detect_images/<uuid>` + `dataset/detect_labels.json` (`[{image, boxes:[{x,y,w,h,label}], width, height}]`); served via `GET /api/projects/{id}/detect/image/{name}`.
- **Algorithm cards** (`detect_lite.ALGORITHM_CARDS` via `engine.list_model_choices`): lite (trainable) + YOLO (locked, "下一期"); detection does **no** compare race — the cards just explain the R-CNN↔YOLO difference.
- API: `POST data/detect/image` (upload), `POST data/detect` (save annotations), `POST predict/detect`, `GET detect/image/{name}`.
- Phase 1 = skeleton + annotation + algorithm A. Phase 2 = YOLO (`.[detect]`) + detection export; phase 3 = COCO import. See `docs/PRD_OBJECT_DETECTION.md`.

### Done (v0.5.0, 2026-06-13) — education interactivity

- **Before/after training comparison** (`ProjectInfo.train_history` rolling list via `ProjectService._appended_history`; rendered by `renderTrainDelta()` in app.js): each train appends compact metrics; the report shows a two-bar prev-vs-now comparison + what changed (data/model/feature). Prefers cross-val, falls back to train accuracy when either training lacked it.
- **Word-weight view** (`text_classifier.top_features_per_class` → `train_report["top_features"]`, linear models only; `renderTopFeatures()`): top char n-grams per class shown as chips.
- **Cumulative test-set sampling** (`updateEvalTally()` in app.js): running correct/total + accuracy on the step-3 eval sampler (E07).
- **Deep-learning interactive demos** (`static/learn.js`, mounted into `#demo-datasize / #demo-forward / #demo-boundary` on the explainer page): data-volume↔accuracy slider, click-to-forward-propagate network, decision-boundary/overfitting switcher. All use precomputed/synthetic data — no real training.
- **Python code snippet** on the explainer page ("用 Python 怎么写").
- This completes `docs/PRD_EDUCATION.md` except video (stage 4) — see the PRD's 实施进度 section.

### Done (v0.4.0, 2026-06-13) — education module

- **Competition section hidden from homepage** (`templates/index.html`, Jinja-commented): product is focused on the general education path first; competitions return later on a dedicated page. The `/competition/*` routes still work — only the homepage entry is hidden.
- **Deep-learning explainer page** (`/learn/deep-learning` → `templates/learn_deep_learning.html`): 6 sections of K12 ML/DL theory, all diagrams are inline SVG using the site CSS vars (no chart lib). Reachable from topnav (`base.html`) and a homepage banner.
- **Per-task education content** (`TaskDefinition.real_world_examples / common_mistakes / hands_on_experiments / next_steps`, filled for all 5 GENERAL_TASKS): rendered on workflow.html (生活中的例子) and project.html (动手实验 on train step, 常见误区 on test step, 下一步探索 on export step).
- **Confusion matrix** (`classifiers.confusion_data()` → `train_report["confusion"] = {labels, matrix, basis}` for the 4 classifier capabilities; rendered by `renderConfusion()` in app.js): cross-validated predictions when every class has ≥3 samples, else in-sample (`basis`). QA has no confusion matrix.
- **Model-comparison interpretation**: `renderCompareTable()` adds a Chinese one-liner naming the most reliable + fastest model.
- **Tutorial expansion** (`_tutorial.html`): traditional-programming-vs-ML pseudo-code, "实验思维" callout, new glossary terms (欠拟合/超参数/迁移学习/混淆矩阵), a "读懂混淆矩阵" 2×2 SVG.
- Planning doc: `docs/PRD_EDUCATION.md`.

### Done (v0.3.0, 2026-06-13)

- **Import an organized dataset** (step 1): `app/services/dataset_library.py` scans a teacher-curated tree (`LDS_DATASETS_ROOT`, default `datasets/`, gitignored). Only `01_可直接用于平台主流程/<category>/<dataset>/platform_dataset.json` (fixed depth 2) is scanned; manifests are matched to the project by `ai_capability`. `ProjectService.import_platform_dataset()` copies `train/<label>/` into the project (same storage the manual uploader writes). **Replacement, not append** — re-importing draws a fresh subset and a second dataset never mixes classes with the first. Per-class caps (`轻量100 / 标准300 / 完整None`) keep huge datasets (MNIST ~56k) from making training crawl; under a cap, samples are drawn at random each import. Security: datasets are resolved by scanned `id`, never by a client-supplied path (rejects `../escape`).
- **Held-out test sampling** (step 3): a dataset's `test/` split is copied to `dataset_eval/` — **outside `dataset/`, so it never trains and is never exported**. `POST /eval/sample` picks a random held-out item, runs the trained model, and returns true label + prediction side by side.
- **Algorithm catalog** (`app/ml/classifiers.py`): two groups per task. Trainable CPU estimators (`*_CHOICES`) now include **GBDT (HistGradientBoosting), MLP, SVM** on top of logistic regression / naive bayes / random forest / KNN / decision tree. Display-only deep-learning cards (`*_DISPLAY` + `DISPLAY_INFO`: MobileNet, ResNet, ViT, CLIP, fastText, TextCNN, LSTM, BERT, spectrogram CNN, YAMNet, Wav2Vec2, deep-tabular) render as locked cards — never passed to `make_classifier`, selecting one is rejected server-side (no GPU training backend yet). Every card carries student-facing Chinese metadata (作用/效能/简史/优点/局限).
- **Image feature-extractor picker**: `image_classifier.list_feature_modes()` exposes `mobilenet_v2` (transfer) vs `pixel` (raw 32×32). Resolved at train time and stored in the joblib so predict/export stay consistent. Engine adds `list_feature_modes()`; train/compare thread a `feature_mode` arg.
- **"对比所有模型" perf**: stratified down-sample to `COMPARE_MAX_SAMPLES` (200) before the race; image/audio sample the *file paths* before reading bytes so a multi-GB dataset isn't loaded into memory. The chosen model is still trained on all data.
- **Portable dataset root**: `LDS_DATASETS_ROOT` env var (docker-compose mountable); if the path is absent the import dropdown stays empty and `/api/datasets` returns `[]`.
- **Docs**: `docs/DATASET_FORMAT.md` (manifest spec for whoever curates datasets) and `docs/ALGORITHM_CATALOG.md` (the full algorithm catalog).

### Done (v0.2.0, 2026-06-12)

- **Four-step sequential locking** (`static/app.js: isStepUnlocked()`): Steps 2–4 grey out until the prior step completes. Step 4 stays accessible once exported (re-download allowed without re-exporting).
- **Global tutorial sidebar** (`templates/_tutorial.html` + `static/tutorial.js`): Six chapters of ML theory/practice. Triggered from topnav "✻ 新手教程" button on every page. Slide-in drawer with TOC, scrim, Esc key, body scroll lock.
- **Teaching content on task pages** (`concept_intro` + `step_guides` on TaskDefinition): "了解原理" concept card on workflow.html, collapsible "了解这一步" blocks on each step in project.html — for all 5 GENERAL_ML tasks.
- **Export/download fixed dual-button UX**: Two always-visible buttons — 导出材料包 (trigger) + 下载材料包 (greyed until export done, activates after). No more dynamic link injection.
- **Zip named `项目名_时间戳.zip`**: e.g. `我的智能问答作业_20260612-195520.zip`. Each export creates a new file; older zips are kept.
- **`包内文件说明.md` in every export**: Chinese student-friendly guide to every file, grouped into 5 sections: ①核心运行 ②重新训练 ③行空板/硬件部署 ④语音播报 ⑤比赛提交.
- **Concurrent-save corruption fix**: All dataset/metadata writes use `_atomic_write_text` (tmp file + `os.replace`). All editor save handlers use `onclick =` (not `addEventListener`) to prevent listener stacking after editor rebuilds.
- **Data collection page** (`/collect/{project_id}`): Camera-capture flow for image and audio datasets, separate from the main 4-step project page.
- **Sample data packs** (`data_packs/`): Preloaded JSON datasets for text, QA, sensor tasks (image tasks redirect to the collect page). Loaded via "加载样本数据包" button in step 1 editors.

### Paused / Stub features

Declared in `TaskDefinition.paused_features` — rendered as code stubs in the export template. Students see the skeleton; actual integration requires additional hardware or API keys.

- 摄像头实时拍照 (live camera feed — needs cv2 on 行空板)
- 真实大模型智能体 (LLM agent — needs external API key)
- 真实机械装置控制 (servo/arm control)
- 真实传感器连接 / 真实执行器控制 (physical I/O sensors)
- 语音识别 (on `heritage_qa_helper`)

### Known gaps / future work

- `static/logo.svg` is a placeholder — replace with the real school badge when available.
- Mobile layout untested; designed for teacher-projected or student laptop use.
- Photo OCR (`.[ocr]` extra, EasyOCR) only runs in the exported `run.py`; in-browser step 2 uses a text-diff checker, not real OCR.
- Roadmap per last conversation: 人肉测试 → 数据集扩充 → 平台内教学过程，bug 修复优先.

---

## 5. Architecture

```
app/main.py               App factory (create_app).
                          ASSET_VERSION = "0.10.0" — bump when changing CSS/JS to bust browser caches.
                          HTML route /learn/deep-learning → learn_deep_learning.html (DL explainer, v0.4.0).
                          DATASETS_ROOT = LDS_DATASETS_ROOT env (default datasets/); mounts the datasets
                          router only when the path exists, else dataset import stays disabled.
                          SCHOOL_NAME, EDITION_LABELS, EDITION_INTROS, HARDWARE_LABELS, STEP_LABELS constants.
                          STEP_LABELS has a special entry for "ocr_typo_checker" (different step names).
                          HTML routes: / (homepage), /competition/{slug}, /workflow/{comp}/{task},
                          /projects (POST → create + redirect), /project/{id}, /collect/{id},
                          /exports/{id}/{filename} (zip download), /playground/detect.
app/api.py                JSON API router under /api/projects/{id}/ + /api/data-packs/ + /api/datasets/.
                          v0.3.0 adds POST data/import-dataset (id-resolved + capability-matched) and
                          POST eval/sample; train + train/compare accept feature_mode.
                          MLDataError → HTTP 400 with Chinese detail string.
app/models.py             Pydantic models:
                          - TaskDefinition: full task spec including concept_intro, step_guides
                          - ProjectInfo: persisted project state (includes train_report, export_file)
                          - ProjectWorkspace: path bundle for a project's directories
                          - GenerationRequest: input to template renderer
                          - ProjectCreateRequest: form POST body with strip validators
app/task_catalog.py       Static task catalog. list_competitions(edition) / get_task() filter by edition.
                          GENERAL_ML bypasses edition filter everywhere.
app/ml/
  engine.py               Dispatches train/predict/list_model_choices/list_feature_modes/compare by
                          ai_capability string.
  base.py                 MLDataError, MODEL_FILE ("model.joblib"), MODEL_META_FILE ("model_meta.json").
  classifiers.py          Multi-model registry: trainable CPU estimators (*_CHOICES — incl. GBDT/MLP/SVM)
                          vs display-only deep-learning cards (*_DISPLAY/DISPLAY_INFO, never trained).
                          Student-facing Chinese metadata per card; compare_rows() races every choice on
                          a stratified ≤COMPARE_MAX_SAMPLES (200) sample for side-by-side accuracy.
  text_classifier.py      TF-IDF → sklearn classifiers.
  image_classifier.py     MobileNetV2 ONNX embedding or pixel fallback (student-selectable via
                          list_feature_modes / resolve_feature_mode) → sklearn classifiers.
  audio_classifier.py     16kHz mono → mel band energies → sklearn classifiers.
  qa_retrieval.py         TF-IDF vectorizer + cosine similarity retrieval with QUESTION_STOPWORDS.
  sensor_model.py         CSV (header-driven, last col = label) → decision tree.
  ocr_checker.py          In-browser: text diff only. Export run.py uses EasyOCR.
  pretrained.py           ONNX model loader (models_pretrained/, gitignored ~40 MB).
  object_detector.py      SSD demo for /playground/detect; cv2-optional, degrades gracefully.
app/services/
  dataset_library.py      Read-only scan of the LDS_DATASETS_ROOT tree (v0.3.0). Lists / resolves curated
                          datasets by manifest id for the step-1 import dropdown; never writes.
  project_service.py      CRUD + train/predict/compare under workspace/projects/<id>/.
                          _atomic_write_text(path, text): writes to tmp then os.replace — prevents
                          partial reads from concurrent requests.
                          import_platform_dataset() copies train/ in (replacement semantics + per-class
                          caps) and test/ → dataset_eval/; sample_eval_predict() drives step-3 sampling.
  template_service.py     Renders export package via Jinja2 string templates. Includes:
                          train.py, predict.py, run.py, ai_runtime/core.py (predict_raw()),
                          run_on_unihiker.py (per-capability with on_result() "创意区域" hook),
                          setup_unihiker.sh, deploy.sh/.bat, creative_examples/ snippets,
                          speech/ layer, docs/, 包内文件说明.md.
  export_service.py       export_project(): render templates → copy trained model → create zip.
                          _safe_filename_stem(): strips Windows-illegal chars, collapses spaces to _.
                          Zip named <safe_name>_<YYYYMMDD-HHMMSS>.zip. Old zips are kept.
templates/
  base.html               Shared layout: topnav (school name + tutorial trigger button), page container.
                          Includes _tutorial.html and loads tutorial.js for every page.
  index.html              Homepage: GENERAL_ML task grid + competition cards + recent projects list.
  workflow.html           Project creation form. Shows task title/summary/requirements,
                          renders concept_intro card if task.concept_intro is set,
                          hardware selector, project name input.
  project.html            4-step workflow page. Bootstraps initial_state_json into app.js.
                          Each step panel conditionally renders step_guides[i] as a <details> block.
                          Step 4 export panel: two fixed buttons (export + download), status text.
  competition.html        Competition overview page: task list + existing project cards.
  collect.html            Data collection assistant (camera capture per class label).
  playground_detect.html  Object detection demo page (needs .[vision]).
  _tutorial.html          Tutorial sidebar: scrim + aside drawer with 6-chapter content + TOC.
  error.html              Generic 404/error page.
static/
  app.js                  All project-page interactivity. Key concepts:
                          - stepsDone{0..3} tracks completion; isStepUnlocked(i) gates clicks.
                          - refreshChecks() updates dataset count badges + calls refreshLocks().
                          - buildXxxEditor() functions use onclick= (not addEventListener) to
                            prevent duplicate handlers when editor is rebuilt.
                          - Export: activates #download-button href + removes is-disabled class.
  tutorial.js             Tutorial drawer open/close/scrim/Esc + TOC anchor scrolling within drawer.
  collect.js              Data collection page: camera capture, image/audio upload per label.
  styles.css              All CSS. CSS custom properties: --surface-warm, --line, --muted, --radius-sm.
                          Includes .step-locked, .teach-block, .tutorial-drawer, .btn-download.is-disabled.
  logo.svg                School badge placeholder.
data_packs/
  index.json              List of available sample packs with metadata.
  *.json                  Sample datasets: kind + data (text samples, QA pairs, sensor CSV).
                          image_task kind redirects to collect page (can't inline images).
```

---

## 6. Workspace File Layout

Each project lives under `workspace/projects/<project_id>/`:

```
metadata.json             ProjectInfo (name, task, train_report, export_file, timestamps)
dataset/
  text_samples.json       [{text, label}, ...]
  qa_pairs.json           [{question, answer}, ...]
  sensor_data.csv         CSV with header; last column = action label
  ocr_data.json           {correct_text, observed_sample}
  images/<label>/         PNG/JPEG files per image class
  audio/<label>/          WAV files per audio class
  image_labels.json       [label, ...]  ordered label list
  audio_labels.json       [label, ...]  ordered label list
dataset_eval/             Held-out test split from an imported dataset (v0.3.0). NOT trained, NOT exported.
  manifest.json           {kind, items: [{label, file|text}]}
  media/                  copied test images/audio (text items inline in manifest)
models/
  model.joblib            Trained sklearn pipeline/model
  model_meta.json         {capability, accuracy, model_name, feature_mode, ...}
generated/                Rendered export files (wiped at start of each export)
exports/
  <name>_<timestamp>.zip  One zip per export run; older zips kept
logs/                     Reserved
```

---

## 7. API Endpoints

### `/api/projects/{project_id}/`

| Method | Path suffix | Description |
|---|---|---|
| GET | `state` | Project metadata + dataset summary + model_choices + feature_modes + eval_count |
| POST | `data/text` | `{samples: [{text, label}]}` |
| POST | `data/qa` | `{pairs: [{question, answer}]}` |
| POST | `data/sensor` | `{csv: "..."}` |
| POST | `data/ocr` | `{correct_text, observed_sample}` |
| POST | `data/images` | Multipart: `label` + `files[]` (PNG/JPEG, max 8 MB each) |
| POST | `data/images/remove` | `{label}` |
| POST | `data/audio` | Multipart: `label` + `files[]` (WAV, max 10 MB each) |
| POST | `data/audio/remove` | `{label}` |
| POST | `data/pack` | `{pack_file: "xxx.json"}` — load a sample data pack |
| POST | `data/import-dataset` | `{dataset_id, cap}` — import a curated dataset (v0.3.0) |
| POST | `eval/sample` | Sample one held-out test item + run prediction (v0.3.0) |
| POST | `train` | `{classifier: "", feature_mode: ""}` — empty uses defaults |
| POST | `train/compare` | `{feature_mode: ""}` — compare all models; returns `{rows: [...]}` |
| POST | `predict` | `{text, values}` for text/sensor |
| POST | `predict/image` | Multipart image upload |
| POST | `predict/audio` | Multipart WAV upload |
| POST | `export` | Build zip; **400 if train_report is None** |

### Other routes

- `GET /api/data-packs` — list packs
- `GET /api/data-packs/{pack_id}` — fetch a pack
- `GET /api/datasets?capability=` — list curated datasets (v0.3.0; empty if `LDS_DATASETS_ROOT` unset)
- `POST /api/playground/detect` — SSD object detection (needs `.[vision]`)
- `GET /exports/{project_id}/{filename}` — download zip

---

## 8. Frontend Architecture (app.js)

The project page bootstraps from `initial_state_json` injected server-side into a `<script>` tag. Key state:

```javascript
// Tracks which steps have been completed this session
let stepsDone = {
  0: false,   // true after any successful data save
  1: false,   // true after server returns train_report
  2: false,   // true after any predict call; ephemeral (not persisted server-side)
  3: false,   // true after successful export
};

function isStepUnlocked(i) {
  if (i === 0) return true;
  if (i === 3) return stepsDone[2] || stepsDone[3]; // re-entry if already exported
  return stepsDone[i - 1] || stepsDone[i];
}
```

`refreshChecks()` is called after every data save and on page load. It updates dataset count badges (shown in step headers) and calls `refreshLocks()` to apply/remove `.step-locked` CSS class on step panels.

All `buildXxxEditor()` functions use `saveButton.onclick =` (not `addEventListener`) to prevent duplicate handlers when the editor is rebuilt (e.g. after loading a sample pack).

---

## 9. Key Invariant: In-App Model ↔ Export Compatibility

The exported `ai_runtime/core.py` must load and run the model trained in-app. **If you change feature extraction in `app/ml/`, make the identical change in `app/services/template_service.py`.**

| Capability | Joblib store keys | Feature pipeline |
|---|---|---|
| `image_classifier` | `{model, feature_mode}` | `"mobilenet_v2"`: MobileNetV2 ONNX 224×224 ImageNet-normalized 1000-d; `"pixel"`: 32×32 RGB flatten. Mode recorded at train time; predict reads stored mode. |
| `audio_classifier` | `{model}` | 16kHz mono resample, 1024/512 framing, 16 mel band energies + RMS + ZCR → mean&std (34-d vector). |
| `qa_retrieval` | `{vectorizer, matrix, rows}` | TF-IDF; questions space-stripped + QUESTION_STOPWORDS removed (list mirrored in both files). |
| `sensor_decision_model` | `{model, feature_names}` | CSV header-driven; last column = action label. |
| `text_classifier` | `{model}` | TF-IDF + sklearn pipeline. |
| `ocr_typo_checker` | none | In-browser: text diff. Export: EasyOCR in `run.py` (needs `.[ocr]`). |

On export, `model.joblib` → `models/<capability>.joblib` in package. Image packages also bundle `models/pretrained/mobilenet_v2.onnx`.

Run `tests/test_generation_services.py` after any template change — it executes exported `predict.py`/`run.py` in a subprocess.

---

## 10. Adding a Task

1. Append a `TaskDefinition` to `SMART_MUSEUM_TASKS`, `FUTURE_CREATOR_TASKS`, or `GENERAL_TASKS` in `app/task_catalog.py`.
2. Reuse an existing `ai_capability` where possible. A new capability needs:
   - `app/ml/<capability>.py` with `train()` and `predict()`
   - A branch in `app/ml/engine.py`
   - Dataset storage in `app/services/project_service.py`
   - A data editor + test builder in `static/app.js`
   - A template rendering branch in `app/services/template_service.py`
3. Optionally fill `concept_intro` (shown on workflow.html) and `step_guides` (list of 4 strings for the 4 step panels).
4. Optionally add a sample data pack under `data_packs/` and register it in `data_packs/index.json`.

---

## 11. Common Commands

```bash
# Dev server (auto-reload)
python scripts/start_studio.py --reload

# Dev server with worktree override
PYTHONPATH=.claude/worktrees/<name> python scripts/start_studio.py --reload

# Fetch pretrained ONNX models (~40 MB, gitignored)
python scripts/download_pretrained.py

# Point at a curated dataset library (enables step-1 "import an organized dataset")
LDS_DATASETS_ROOT=/path/to/datasets python scripts/start_studio.py

# Run a specific edition
python scripts/start_studio.py --edition smart_museum

# Tests
python -m pytest -q
python -m pytest tests/test_ml_engine.py
python -m pytest tests/test_generation_services.py   # executes exported predict.py in subprocess

# Lint
python -m ruff check app scripts packaging tests

# Acceptance (renders + HTTP-drives every task's export)
python scripts/acceptance_check.py --rounds 1 --with-web

# Build release / student installer zips
python packaging/build_release.py
python packaging/build_student_installer.py --edition smart_museum --output dist/SmartMuseum-Windows-Setup.zip

# Docker
docker compose up -d --build
```

---

## 12. Dependencies

- **Base** (`pip install -e .`): FastAPI, Jinja2, scikit-learn, numpy, joblib, onnxruntime, Pillow, pydantic, uvicorn. All in-app training works without extras.
- **`.[dev]`**: pytest, httpx, ruff. Ruff line-length is 100.
- **`.[vision]`**: opencv-python-headless. Only for `/playground/detect`. Degrades to install hint without it.
- **`.[ocr]`**: EasyOCR + Torch + OpenCV (~2 GB). Only for photo OCR in the exported `run.py`. Keep optional; do not add to base.
- **`models_pretrained/`** (gitignored, ~40 MB): MobileNetV2 ONNX + SSD ONNX. Fetched by `scripts/download_pretrained.py`. Without it, image classifier falls back to pixel features.
- **`datasets/`** (gitignored, several GB): teacher-curated dataset library scanned by `dataset_library.py`. Override with `LDS_DATASETS_ROOT`. Absent → import dropdown stays empty (no error).

---

## 13. Version History

### v0.6.0 (2026-06-13)

- Object detection phase 1: trainable detection task + canvas annotation tool (`static/detect.js`)
- Algorithm A (lite): R-CNN-style propose (SSD) + crop-classify (MobileNet feature + LogisticRegression + 背景 class) + NMS; reuses image pipeline, CPU/seconds
- Algorithm cards (lite trainable + YOLO locked); detection backend (`detect_lite.py`, `object_detector.propose_boxes`), storage + API. See `docs/PRD_OBJECT_DETECTION.md`

### v0.5.0 (2026-06-13)

- Education interactivity: train before/after comparison (`train_history`), word-weight chips (`top_features`), cumulative test-set sampling (E07)
- Deep-learning explainer interactive demos (`static/learn.js`: data-volume slider, forward-prop, decision boundary) + Python code snippet
- Completes `docs/PRD_EDUCATION.md` except video

### v0.4.0 (2026-06-13)

- Education module: hid homepage competition section; added `/learn/deep-learning` explainer (6 sections, inline-SVG diagrams)
- Per-task education fields (real_world_examples / common_mistakes / hands_on_experiments / next_steps) on all 5 general tasks
- Confusion matrix in train_report (cross-validated when possible) + frontend render; model-comparison interpretation line
- Tutorial expansion (traditional-vs-ML, experiment thinking, new glossary terms, confusion-matrix reading) + `docs/PRD_EDUCATION.md`

### v0.3.0 (2026-06-13)

- Import a teacher-curated organized dataset in step 1 (per-class caps, random sampling, replacement semantics, id-resolved / path-traversal-safe)
- Held-out test-set sampling in step 3 via `dataset_eval/` (isolated from training and export)
- Algorithm catalog: trainable GBDT/MLP/SVM added; deep-learning models shown as locked cards with Chinese explainers
- Selectable image feature extractor (MobileNet transfer vs raw pixels)
- "Compare all models" sped up via stratified ≤200 sampling (paths sampled before reading bytes)
- Portable `LDS_DATASETS_ROOT`; `docs/DATASET_FORMAT.md` + `docs/ALGORITHM_CATALOG.md`
- Fix: oversized sensor CSV save 422 (cap 20k → 2M chars); cross-val skip-hint threshold wording (3 not 10)

### v0.2.0 (2026-06-12)

- Four-step sequential locking with visual grey-out
- Global "新手教程" tutorial sidebar (6 chapters, every page)
- Teaching content: concept cards + step guides for all 5 GENERAL_ML tasks
- Export/download: fixed dual-button layout, zip named `项目名_时间戳.zip`
- `包内文件说明.md` added to every export package
- Fix: concurrent save data corruption (atomic writes + `onclick=` handler deduplication)

### v0.1.0

- Initial release: 4-step in-browser ML workflow; text/image/audio/QA/sensor/OCR capabilities; scikit-learn in-process training; 行空板 M10 deployment export; smart_museum and future_creator competition editions.
