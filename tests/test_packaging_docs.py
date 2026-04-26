from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_text(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_repository_delivery_docs_exist_with_install_paths() -> None:
    required_docs = [
        "README.md",
        "docs/INSTALLATION.md",
        "docs/GITHUB_RELEASE.md",
        "docs/TRAINING_INDEX.md",
        "docs/TRAINING_SMART_MUSEUM.md",
        "docs/TRAINING_FUTURE_CREATOR.md",
    ]

    for doc_path in required_docs:
        assert (PROJECT_ROOT / doc_path).is_file(), f"{doc_path} is missing"

    combined_docs = "\n".join(read_text(doc_path) for doc_path in required_docs)
    for keyword in [
        "Lite DeepLearning Studio",
        "基础安装",
        "OCR 安装",
        "开发安装",
        "python -m uvicorn app.main:app",
        "python scripts/start_studio.py",
        "python packaging/build_release.py",
        "python packaging/build_student_installer.py",
        "lite-deeplearning-studio-student-installer.zip",
        "LiteDeepLearningStudio-Windows-Setup.zip",
        "SmartMuseum-Windows-Setup.zip",
        "FutureCreator-Windows-Setup.zip",
        "行空板 M10",
        "DFRobot",
        "SmartMuseum-Windows-Setup.zip",
        "FutureCreator-Windows-Setup.zip",
        "一键安装.bat",
        "启动软件.bat",
    ]:
        assert keyword in combined_docs


def test_training_docs_cover_install_and_competition_tasks() -> None:
    smart_museum = read_text("docs/TRAINING_SMART_MUSEUM.md")
    future_creator = read_text("docs/TRAINING_FUTURE_CREATOR.md")

    for keyword in [
        "SmartMuseum-Windows-Setup.zip",
        "挑战一：认识非遗传承匠人",
        "挑战二：了解非遗专业知识",
        "挑战三：非遗文化分类学览",
        "挑战四：非遗文化深化认知",
        "行空板 M10",
        "DFRobot",
    ]:
        assert keyword in smart_museum

    for keyword in [
        "FutureCreator-Windows-Setup.zip",
        "小学组：语音互动与单类图像识别",
        "初中组：视觉模型训练与调用",
        "高中组：大模型语音互动、视觉识别与运动控制",
        "传感器决策程序模板",
        "行空板 M10",
        "DFRobot",
    ]:
        assert keyword in future_creator


def test_delivery_scripts_exist_and_are_import_safe() -> None:
    for script_path in [
        "scripts/start_studio.py",
        "packaging/build_release.py",
        "packaging/build_student_installer.py",
    ]:
        script = PROJECT_ROOT / script_path
        assert script.is_file(), f"{script_path} is missing"
        assert "if __name__ == \"__main__\":" in script.read_text(encoding="utf-8")


def test_student_installer_script_includes_platform_installers() -> None:
    content = read_text("packaging/build_student_installer.py")

    for keyword in [
        "install_macos_linux.sh",
        "start_macos_linux.sh",
        "__EDITION__",
        "__APP_TITLE__",
        "setup.bat",
        "setup_ocr.bat",
        "start.bat",
        "uninstall.bat",
        "一键安装.bat",
        "安装OCR增强.bat",
        "启动软件.bat",
        "卸载本地环境.bat",
        "create_desktop_shortcut.ps1",
        "install_windows.ps1",
        "start_windows.ps1",
    ]:
        assert keyword in content


def test_gitignore_covers_local_artifacts_without_hiding_docs() -> None:
    gitignore = read_text(".gitignore")

    for pattern in [
        ".venv/",
        "__pycache__/",
        ".pytest_cache/",
        ".ruff_cache/",
        "workspace/",
        "tmp/",
        "dist/",
        "*.zip",
    ]:
        assert pattern in gitignore

    assert "!docs/" in gitignore
    assert "!scripts/" in gitignore
    assert "!packaging/" in gitignore
