# Lightweight Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI MVP for generating lightweight competition workflow export packages.

**Architecture:** Use a server-rendered FastAPI app with small backend services for task definitions, workspace creation, template rendering, and zip export. Keep the UI simple and student-facing.

**Tech Stack:** Python 3.11+, FastAPI, Jinja2, Pydantic, pytest, httpx TestClient.

---

## File Structure

- `pyproject.toml`: package metadata, dependencies, test config.
- `app/main.py`: FastAPI routes and app creation.
- `app/models.py`: Pydantic models for competitions, tasks, and generation requests.
- `app/task_catalog.py`: static competition task catalog.
- `app/services/workspace_service.py`: safe workspace folders and metadata persistence.
- `app/services/template_service.py`: deterministic generated file content.
- `app/services/export_service.py`: export package creation.
- `templates/base.html`: shared layout.
- `templates/index.html`: competition and task chooser.
- `templates/workflow.html`: guided form.
- `templates/result.html`: generated package result page.
- `templates/error.html`: friendly errors.
- `static/styles.css`: calm work-focused UI.
- `tests/test_task_catalog.py`: catalog behavior.
- `tests/test_generation_services.py`: service behavior.
- `tests/test_app_routes.py`: route behavior.

## Tasks

### Task 1: Project Skeleton And Catalog Tests

- [ ] Create Python package folders.
- [ ] Add `pyproject.toml`.
- [ ] Write tests for the task catalog.
- [ ] Run the catalog test and confirm it fails before implementation.
- [ ] Implement task models and catalog.
- [ ] Re-run the catalog test and confirm it passes.

### Task 2: Generation Service Tests

- [ ] Write tests for workspace, template rendering, and zip export.
- [ ] Run the service tests and confirm they fail before implementation.
- [ ] Implement workspace, template, and export services.
- [ ] Re-run service tests and confirm they pass.

### Task 3: Web Route Tests

- [ ] Write tests for homepage, workflow page, and generate action.
- [ ] Run route tests and confirm they fail before route implementation.
- [ ] Implement FastAPI app and routes.
- [ ] Re-run route tests and confirm they pass.

### Task 4: Student UI

- [ ] Add server-rendered templates.
- [ ] Add CSS for a compact student workflow interface.
- [ ] Verify pages render with real task data.

### Task 5: Final Verification

- [ ] Run the full test suite.
- [ ] Start the local app.
- [ ] Open the app in a browser and verify the homepage and generated result path.
