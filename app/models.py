from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


HardwareTarget = Literal["student_laptop", "jetson_nano", "raspberry_pi", "esp32", "generic"]
AiCapability = Literal[
    "text_classifier",
    "ocr_typo_checker",
    "image_classifier",
    "qa_retrieval",
    "sensor_decision_model",
]
SampleDatasetKind = Literal["text", "ocr", "image", "qa", "sensor"]
DataOrigin = Literal["sample", "user"]
VoiceProfile = Literal[
    "dfrobot_tts_broadcast",
    "unihiker_keyword_voice",
    "jetson_voice_agent_stub",
    "none",
]


class TaskDefinition(BaseModel):
    slug: str
    title: str
    summary: str
    student_goal: str
    group: str
    requirement_source: str
    competition_requirements: list[str]
    ai_capability: AiCapability
    sample_dataset_kind: SampleDatasetKind
    runtime_requirements: list[str]
    voice_profile: VoiceProfile
    paused_features: list[str] = Field(default_factory=list)
    suggested_hardware: list[HardwareTarget]
    required_outputs: list[str]
    starter_steps: list[str]


class CompetitionDefinition(BaseModel):
    slug: str
    title: str
    summary: str
    tasks: list[TaskDefinition]


class GenerationRequest(BaseModel):
    competition_slug: str
    task_slug: str
    project_name: str = Field(min_length=1, max_length=80)
    student_name: str = Field(default="", max_length=80)
    target_hardware: HardwareTarget = "student_laptop"
    dataset_notes: str = Field(default="", max_length=1000)
    class_labels: list[str] = Field(default_factory=list)
    text_csv: str = Field(default="", max_length=12000)
    qa_text: str = Field(default="", max_length=12000)
    sensor_csv: str = Field(default="", max_length=12000)
    ocr_correct_text: str = Field(default="", max_length=1000)
    ocr_observed_text: str = Field(default="", max_length=1000)

    @property
    def data_origin(self) -> DataOrigin:
        pasted_values = [
            self.text_csv,
            self.qa_text,
            self.sensor_csv,
            self.ocr_correct_text,
            self.ocr_observed_text,
        ]
        return "user" if any(value.strip() for value in pasted_values) else "sample"


class ProjectWorkspace(BaseModel):
    project_id: str
    project_dir: Path
    generated_dir: Path
    exports_dir: Path
    logs_dir: Path
    metadata_path: Path


class GenerationResult(BaseModel):
    workspace: ProjectWorkspace
    generated_files: list[Path]
    export_path: Path
