# Agent Instructions

## Project Identity

This project is the first implementation track for the student competition AI platform.

The primary goal is to build a lightweight, immediately usable workflow system for students who previously completed competition tasks in Jupyter Notebook with small amounts of code.

The platform should not feel like a heavy AI development system. It should feel like a guided task workflow that helps students quickly generate usable outputs:

- trained lightweight models
- runnable Python scripts
- Jupyter notebooks
- hardware-ready example code
- export packages for competition use

## Product Direction

Default product mode: Quick Workflow Mode.

Students should start from a small number of clear task entries, not from a complex platform dashboard.

The first usable version should answer one question:

> Can a student complete a competition task faster and more reliably than writing scattered notebook code by hand?

If a feature does not help this goal, defer it.

## Core Principles

- Prefer one guided workflow over many disconnected pages.
- Prefer templates and generated files over free-form coding.
- Prefer deterministic steps over autonomous agents.
- Prefer CPU-friendly models and stable libraries over newest models.
- Prefer clear student-facing language over machine learning jargon.
- Keep teacher or advanced features separate from the student default path.
- Do not build a large platform before the workflow proves useful.

## Initial Scope

The first project should focus on the lightweight workflow route.

Build these first:

- Competition selection
- Task selection
- Step-by-step workflow page
- Simple dataset or input upload
- Template-based configuration
- One-click generation of notebook/script assets
- Basic training or processing command wrapper
- Export package generation

Do not build these in the first pass:

- Multi-user server system
- Teacher dashboard
- Full experiment management
- Cloud training
- Complex permission system
- Fully autonomous LLM agent
- Large model fine-tuning
- Hardware fleet management

## Architecture Preferences

Use a local-first architecture.

Recommended baseline:

- Python 3.11+
- FastAPI for backend APIs
- SQLite for local metadata
- pathlib for file paths
- pydantic for request and data models
- pytest for tests
- TypeScript for frontend if a frontend framework is introduced

Keep backend logic separated into small services:

- workflow service
- template service
- export service
- task runner service
- project workspace service

Avoid microservices in the first version.

## AI And Model Choices

Use mature, stable, CPU-friendly solutions first.

For lightweight text classification or tabular tasks, prefer:

- scikit-learn
- jieba or other stable tokenization tools when Chinese text is needed

For image classification, prefer:

- PyTorch only when needed
- torchvision pretrained models only when the environment can support them
- simple template code that can run locally

For object detection, defer full YOLO integration unless a specific competition task requires it.

When YOLO is required, prefer a stable Ultralytics YOLO release and isolate it behind optional dependencies.

## Jupyter Role

Jupyter is an advanced or compatibility path, not the main student workflow.

The platform may generate notebooks, but the user experience should not require students to write every line manually.

Generated notebooks should be:

- readable
- short
- runnable from top to bottom
- aligned with generated scripts

## Assistant Role

If an assistant is added, it should guide choices and explain errors.

It must not be the core execution engine.

The core workflow should work without an LLM.

Assistant features may include:

- explaining the current step
- recommending a template
- explaining an error message
- summarizing generated files

Assistant features must not include:

- freely rewriting project code without user confirmation
- deciding competition outputs autonomously
- replacing deterministic workflow steps

## Workspace And Exports

Each task run should write outputs into a clear workspace folder.

Suggested structure:

```text
workspace/
  projects/
    <project_id>/
      inputs/
      generated/
      outputs/
      exports/
      logs/
```

Export packages should be simple and inspectable.

Suggested export structure:

```text
export_package/
  README.md
  run.py
  notebook.ipynb
  model/
  data_sample/
  hardware/
  requirements.txt
```

## Coding Standards

Follow the repository and global Codex instructions.

Python:

- target Python 3.11+
- use type hints
- use pathlib instead of os.path
- use pydantic or dataclasses for structured data
- format with black
- lint with ruff
- test with pytest

TypeScript:

- prefer TypeScript over JavaScript
- use ES modules
- prefer const over let
- format with Prettier
- lint with ESLint

## Testing Expectations

Add tests for core workflow logic, especially:

- task definition loading
- template rendering
- export package generation
- workspace path handling
- invalid input handling

Before considering a feature complete, run the relevant tests when available.

## Development Style

Make small, verifiable changes.

Prefer a working thin slice over a broad unfinished skeleton.

For each major feature, aim to produce:

- one visible student-facing workflow
- one generated artifact
- one test or verification path

Do not commit changes unless explicitly asked.
