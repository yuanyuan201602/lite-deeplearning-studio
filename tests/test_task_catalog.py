from app.models import AiCapability
from app.task_catalog import get_competition, get_task, list_competitions

EXISTING_CAPABILITIES = set(AiCapability.__args__)


def test_catalog_exposes_two_competitions() -> None:
    competitions = list_competitions()

    slugs = {competition.slug for competition in competitions}

    assert slugs == {"smart_museum", "future_creator"}


def test_application_cases_group_is_always_visible() -> None:
    # Mirrors GENERAL_ML: not in the edition-filtered COMPETITIONS list, but
    # resolvable in every edition via the get_competition special-case.
    assert "application_cases" not in {c.slug for c in list_competitions()}
    for edition in ("all", "smart_museum", "future_creator"):
        group = get_competition("application_cases", edition)
        assert group is not None
        assert len(group.tasks) == 3


def test_application_cases_first_batch_reuses_existing_capabilities() -> None:
    group = get_competition("application_cases")
    slugs = {task.slug for task in group.tasks}
    assert slugs == {"case_spam_filter", "case_campus_qa", "case_step_counter"}

    for task in group.tasks:
        # Zero new ML capabilities: every case rides an existing one.
        assert task.ai_capability in EXISTING_CAPABILITIES
        # Application framing fields populated.
        assert task.case_scenario
        assert task.bundled_dataset_id
        assert task.case_domain
        assert task.group == "应用案例"
        # Rendering / export fields must be present like GENERAL_TASKS.
        assert task.concept_intro
        assert len(task.step_guides) == 4
        assert task.real_world_examples
        assert task.next_steps
        assert "README.md" in task.required_outputs


def test_application_case_resolves_via_get_task() -> None:
    task = get_task("application_cases", "case_spam_filter")
    assert task is not None
    assert task.ai_capability == "text_classifier"
    assert task.bundled_dataset_id == "general_text_spam"
    assert get_task("application_cases", "missing") is None


def test_each_competition_has_student_tasks() -> None:
    competitions = list_competitions()

    assert all(competition.tasks for competition in competitions)
    assert any(task.slug == "heritage_text_classifier" for task in competitions[0].tasks)
    assert any(task.slug == "image_recognition_starter" for task in competitions[1].tasks)


def test_get_task_returns_task_with_export_files() -> None:
    task = get_task("smart_museum", "heritage_text_classifier")

    assert task.title == "挑战三：非遗文化分类学览"
    assert "README.md" in task.required_outputs
    assert "notebook.ipynb" in task.required_outputs


def test_unknown_competition_or_task_returns_none() -> None:
    assert get_competition("missing") is None
    assert get_task("smart_museum", "missing") is None


def test_every_task_declares_ai_capability_metadata() -> None:
    for competition in list_competitions():
        for task in competition.tasks:
            assert task.ai_capability
            assert task.sample_dataset_kind
            assert task.runtime_requirements
            assert task.voice_profile


def test_voice_profiles_match_competition_hardware_plan() -> None:
    smart_museum = get_competition("smart_museum")
    future_creator = get_competition("future_creator")
    assert smart_museum is not None
    assert future_creator is not None

    assert {task.voice_profile for task in smart_museum.tasks} == {"dfrobot_tts_broadcast"}
    assert get_task("future_creator", "primary_voice_image_interaction").voice_profile == (
        "unihiker_keyword_voice"
    )
    assert get_task("future_creator", "junior_model_calling_workflow").voice_profile == (
        "unihiker_keyword_voice"
    )
    assert get_task("future_creator", "senior_llm_vision_motion").voice_profile == (
        "unihiker_keyword_voice"
    )


def test_competitions_can_be_filtered_into_independent_editions() -> None:
    assert [competition.slug for competition in list_competitions("smart_museum")] == [
        "smart_museum"
    ]
    assert [competition.slug for competition in list_competitions("future_creator")] == [
        "future_creator"
    ]
    assert get_competition("future_creator", "smart_museum") is None
    assert get_task("future_creator", "image_recognition_starter", "smart_museum") is None


def test_every_task_targets_unihiker_m10_dfrobot_hardware() -> None:
    for competition in list_competitions():
        for task in competition.tasks:
            assert task.suggested_hardware == ["unihiker_m10"]
