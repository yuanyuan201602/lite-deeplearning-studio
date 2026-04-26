# Lightweight Competition Workflow Design

## Goal

Build a local-first student workflow app that turns common competition tasks into guided, template-based steps. The first version should help a student produce usable files faster than writing scattered Jupyter Notebook code by hand.

## Product Shape

The default experience is Quick Workflow Mode.

Students start with a simple task chooser, then complete one guided workflow. The app produces an export package containing a runnable Python script, a Jupyter notebook, sample input files, hardware notes, and a README.

The first version is not a full AI platform. It does not include multi-user accounts, teacher dashboards, cloud training, advanced experiment tracking, autonomous coding agents, or hardware fleet management.

## Initial Competition Coverage

The first visible release includes two competition entries:

- 智能博物
- 优创未来

Only lightweight template workflows are implemented in V0.1. The platform can expose both entries, but each task uses deterministic templates instead of complex model training pipelines.

## Student Workflow

1. Student opens the homepage.
2. Student chooses a competition and a task.
3. Student fills a small form with task name, dataset notes, target hardware, and optional class labels.
4. Student previews the planned output files.
5. Student clicks Generate.
6. The app creates a project workspace and export package.
7. Student downloads or opens the generated files.

## Core Behaviors

- Load task definitions from static Python data.
- Create a project workspace under `workspace/projects/<project_id>/`.
- Render template files from task configuration.
- Generate a readable `run.py`.
- Generate a simple `notebook.ipynb`.
- Generate a `README.md`.
- Generate hardware guidance.
- Package generated files into a zip archive.
- Store run metadata in a local JSON file for easy inspection.

## Architecture

Use a small FastAPI application with server-rendered HTML. This keeps the first version light and avoids frontend build complexity.

Main units:

- `app/main.py`: FastAPI app, routes, static/template wiring.
- `app/models.py`: typed data models.
- `app/task_catalog.py`: competition and task definitions.
- `app/services/workspace_service.py`: project path creation and metadata persistence.
- `app/services/template_service.py`: deterministic file rendering.
- `app/services/export_service.py`: export package creation.
- `templates/`: student-facing pages.
- `tests/`: pytest coverage for task loading, rendering, workspace creation, and zip export.

## UI Direction

The UI should be calm, task-focused, and not look like a marketing landing page.

Homepage:

- compact header
- two competition choices
- task cards with short descriptions

Workflow page:

- left side: current task and steps
- right side: form and output preview
- one primary Generate action

Result page:

- generated file list
- export zip link
- next action buttons

## Error Handling

- Unknown competition or task returns a friendly 404 page.
- Missing required fields returns form validation feedback.
- Export generation failures return a clear error page with the attempted project id.
- Workspace paths are generated internally; user input is never used directly as a filesystem path.

## Testing

Core tests should verify:

- task catalog exposes expected competitions and tasks
- workspace service creates the required folders and metadata
- template service renders `README.md`, `run.py`, `notebook.ipynb`, and hardware notes
- export service creates a zip containing required files
- FastAPI routes return successful pages for homepage, workflow, and generation

## Out Of Scope For V0.1

- real model training
- YOLO integration
- OCR integration
- LLM assistant
- login and roles
- cloud/server deployment
- device flashing
- serial hardware control

## Acceptance Criteria

- `pytest` passes.
- The app starts locally.
- The homepage shows both competition entries.
- A student can generate an export package for at least one 智能博物 task and one 优创未来 task.
- Generated zip packages contain `README.md`, `run.py`, `notebook.ipynb`, `hardware/README.md`, and `requirements.txt`.
