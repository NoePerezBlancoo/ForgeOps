from pathlib import Path

import pytest

from forgeops_agent.errors import AgentError
from forgeops_agent.runner import AiderRunner


def test_aider_expands_only_existing_task_files(tmp_path: Path):
    source = tmp_path / "backend" / "tests"
    source.mkdir(parents=True)
    (source / "test_one.py").write_text("def test_one(): pass\n", encoding="utf-8")
    (source / "test_two.py").write_text("def test_two(): pass\n", encoding="utf-8")

    files = AiderRunner._expand_task_files(tmp_path, ("backend/tests/",), limit=2)

    assert files == ["backend/tests/test_one.py", "backend/tests/test_two.py"]


def test_aider_rejects_overly_broad_task_context(tmp_path: Path):
    source = tmp_path / "frontend"
    source.mkdir()
    for index in range(3):
        (source / f"file_{index}.tsx").write_text("export {};\n", encoding="utf-8")

    with pytest.raises(AgentError, match="narrow its paths"):
        AiderRunner._expand_task_files(tmp_path, ("frontend/",), limit=2)
