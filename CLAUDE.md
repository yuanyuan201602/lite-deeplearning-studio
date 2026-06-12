# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Lite DeepLearning Studio is a K12 machine-learning workbench for student AI competitions (used by 南昌市第二十三中学). Students complete a project in four in-browser steps: 准备数据 → 训练模型 → 测试效果 → 导出材料. Training happens in-app (scikit-learn); the export zip bundles the trained model, the student's data, runnable Python scripts, hardware notes, and submission checklists.

Two competition editions ship from a single codebase:
- **智能博物** (`smart_museum`) — face intro, OCR typo checking, text classification, Q&A retrieval
- **优创未来** (`future_creator`) — image recognition, sensor decision, voice interaction

The active edition is controlled by the `LDS_EDITION` env var or the `--edition` CLI flag.

## Common Commands

```bash
# Dev server (auto-reload)
python scripts/start_studio.py --reload

# Fetch pretrained ONNX models (MobileNet transfer learning + SSD detection).
# Optional: everything degrades to pixel features / face detection without them.
python scripts/download_pretrained.py

# Run a specific edition
python scripts/start_studio.py --edition smart_museum

# Tests
python -m pytest -q
python -m pytest tests/test_ml_engine.py            # single test file

# Lint
python -m ruff check app scripts packaging tests

# Acceptance (renders + runs every task's export; --with-web drives the full HTTP flow)
python scripts/acceptance_check.py --rounds 1 --with-web

# Build release / student installer zips
python packaging/build_release.py
python packaging/build_student_installer.py --edition smart_museum --output dist/SmartMuseum-Windows-Setup.zip

# Server deployment
docker compose up -d --build
```

## Architecture

```
app/main.py               App factory (create_app). HTML routes: / (workbench: general ML tasks +
                          competition entries), /competition/{slug}, /workflow, /projects (form POST),
                          /project/{id}, /exports, /playground/detect (face-detection demo +
                          /api/playground/detect; needs .[vision], degrades with install hint).
                          Mounts the JSON API router.
app/api.py                JSON API under /api/projects/{id}: state, data/{text,qa,sensor,ocr,images,audio},
                          train, predict, predict/{image,audio}, export (export 400s until trained).
                          MLDataError → 400 with Chinese detail.
app/models.py             Pydantic models and Literal types (TaskDefinition, ProjectInfo, GenerationRequest).
app/task_catalog.py       Static catalog of all tasks; list_competitions / get_task helpers.
                          GENERAL_ML ("general_ml") holds non-competition practice tasks for the
                          workbench homepage; it bypasses edition filtering and has no /competition page.
app/ml/                   In-app ML engine, one module per ai_capability:
                          text_classifier, image_classifier, audio_classifier, qa_retrieval,
                          sensor_model, ocr_checker; object_detector.py is the cv2-optional demo.
                          engine.py dispatches by capability; base.py has MLDataError + model meta I/O.
                          classifiers.py is the multi-model registry (per-task choices + student-facing
                          Chinese metadata + compare_rows); the four classifier tasks accept a
                          model_choice and expose POST train/compare for same-data comparison.
app/services/
  project_service.py      Project persistence under workspace/projects/<id>/ (dataset/, models/,
                          generated/, exports/, metadata.json); train/predict orchestration.
  template_service.py     Renders the export package (train.py, predict.py, ai_runtime/, speech/, docs).
  export_service.py       export_project(): builds GenerationRequest from stored data, renders templates,
                          copies the in-app trained model into the package, zips it.
templates/                Jinja2 pages (index, workflow=create form, project=4-step workflow).
static/app.js             All project-page interactivity (data editors, train, test, export via fetch).
static/logo.svg           School badge placeholder — replace the file to swap in the real logo.
```

### Key invariant: in-app model ↔ exported package compatibility

The exported `ai_runtime/core.py` (rendered by template_service) must load the model trained in-app:
- image features are dual-mode, recorded in the joblib store `{"model", "feature_mode"}`:
  "mobilenet_v2" = MobileNetV2 ONNX embedding (224×224, ImageNet mean/std, 1000-d output;
  needs models_pretrained/ + onnxruntime, export bundles the .onnx into models/pretrained/),
  "pixel" = 32×32 RGB /255 flatten fallback. Preprocessing identical in `app/ml/pretrained.py`
  and the template; predict always uses the mode stored at train time.
- audio features: 16kHz mono resample, 1024/512 framing, 16 log band energies + RMS/ZCR mean&std —
  identical in `app/ml/audio_classifier.py` and the template
- qa store keys: `{"vectorizer", "matrix", "rows"}`; questions are space-stripped and interrogative
  stopwords removed before vectorizing (QUESTION_STOPWORDS mirrored in both places)
- sensor store: `{"model", "feature_names"}`; CSV is header-driven, last column = action label
- export copies `models/model.joblib` → `models/<capability>.joblib` in the package

If you change one side, change the other and run `tests/test_generation_services.py` (it executes the
exported `predict.py`/`run.py` in a subprocess).

### Adding a Task

1. Add a `TaskDefinition` in `app/task_catalog.py` (append to `SMART_MUSEUM_TASKS` or `FUTURE_CREATOR_TASKS`).
2. Reuse an existing `ai_capability`; a new capability needs an `app/ml/` module, an `engine.py` branch,
   a data editor + test builder in `static/app.js`, and dataset storage in `project_service.py`.

## Dependencies

- Base install (`pip install -e .`) includes scikit-learn/numpy/joblib/onnxruntime — all in-app
  training works. `models_pretrained/` (gitignored, ~40MB) enables MobileNet transfer learning for
  images and SSD object detection; installers/Docker fetch it automatically at build time.
- `.[ocr]` (EasyOCR/Torch/OpenCV) is only for photo OCR in the exported package; heavy, keep optional.
- `.[dev]`: pytest, httpx, ruff. Ruff line-length is 100.
