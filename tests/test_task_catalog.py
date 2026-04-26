from app.task_catalog import get_competition, get_task, list_competitions


def test_catalog_exposes_two_competitions() -> None:
    competitions = list_competitions()

    slugs = {competition.slug for competition in competitions}

    assert slugs == {"smart_museum", "future_creator"}


def test_each_competition_has_student_tasks() -> None:
    competitions = list_competitions()

    assert all(competition.tasks for competition in competitions)
    assert any(task.slug == "heritage_text_classifier" for task in competitions[0].tasks)
    assert any(task.slug == "image_recognition_starter" for task in competitions[1].tasks)


def test_get_task_returns_task_with_export_files() -> None:
    task = get_task("smart_museum", "heritage_text_classifier")

    assert task.title == "非遗词语分类工作流"
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
