from pathlib import Path

import pytest
import yaml

from forgeops_agent.errors import ConfigurationError, PolicyError
from forgeops_agent.models import Risk, Task
from forgeops_agent.policy import scan_secrets, validate_changed_paths, validate_task_policy


def test_task_parser_normalizes_paths():
    task = Task.from_dict(
        {
            "id": "AI-0042",
            "title": "Improve docs",
            "objective": "Clarify one local development document without product changes.",
            "allowed_paths": ["docs\\local-ai\\"],
            "risk": "low",
        }
    )
    assert task.id == "AI-0042"
    assert task.allowed_paths == ("docs/local-ai/",)
    assert task.risk is Risk.LOW


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allowed_paths", "backend/tests/"),
        ("allow_network", "false"),
        ("max_attempts", "3"),
    ],
)
def test_task_parser_rejects_wrong_field_types(field, value):
    data = {
        "id": "AI-0042",
        "title": "Strict schema",
        "objective": "Reject values that do not match the documented task schema.",
        "allowed_paths": ["backend/tests/"],
        "risk": "LOW",
    }
    data[field] = value
    with pytest.raises(ConfigurationError):
        Task.from_dict(data)


def test_task_parser_rejects_unknown_fields():
    with pytest.raises(ConfigurationError, match="Unknown task fields"):
        Task.from_dict(
            {
                "id": "AI-0042",
                "title": "Strict schema",
                "objective": "Reject undocumented fields before a task reaches the queue.",
                "allowed_paths": ["backend/tests/"],
                "risk": "LOW",
                "shell_access": True,
            }
        )


@pytest.mark.parametrize("path", ["../outside", "C:/Users/private", "/etc/passwd", ".git/config"])
def test_task_parser_rejects_unsafe_paths(path: str):
    with pytest.raises(ConfigurationError):
        Task.from_dict(
            {
                "id": "AI-0042",
                "title": "Unsafe task",
                "objective": "This task deliberately contains an unsafe repository path.",
                "allowed_paths": [path],
                "risk": "LOW",
            }
        )


def test_critical_task_is_rejected():
    with pytest.raises(ConfigurationError, match="CRITICAL"):
        Task.from_dict(
            {
                "id": "AI-0042",
                "title": "Production operation",
                "objective": "Attempt a production operation that must never be delegated.",
                "allowed_paths": ["docs/"],
                "risk": "CRITICAL",
            }
        )


def test_medium_and_high_tasks_require_explicit_override(sample_task):
    medium = Task(**{**sample_task.__dict__, "risk": Risk.MEDIUM})
    high = Task(**{**sample_task.__dict__, "risk": Risk.HIGH})
    with pytest.raises(PolicyError, match="MEDIUM"):
        validate_task_policy(medium, ("deploy/",))
    with pytest.raises(PolicyError, match="HIGH"):
        validate_task_policy(high, ("deploy/",), allow_medium=True)


def test_scope_validation_detects_outside_change(sample_task):
    result = validate_changed_paths(
        sample_task,
        ["backend/tests/test_auth.py", "frontend/app/page.tsx"],
        ("deploy/",),
    )
    assert not result.valid
    assert result.violations == ("outside allowed_paths: frontend/app/page.tsx",)


def test_fake_secret_is_detected(tmp_path: Path):
    suspect = tmp_path / "suspect.txt"
    suspect.write_text("RAILWAY_TOKEN=FAKE_CONTROLLED_TOKEN_1234567890", encoding="utf-8")
    result = scan_secrets(tmp_path, ["suspect.txt"])
    assert not result.valid
    assert "Railway token" in result.violations[0]


def test_all_versioned_task_templates_are_valid():
    root = Path(__file__).resolve().parents[3]
    templates = sorted((root / ".ai" / "tasks" / "templates").glob("*.yaml"))
    assert templates
    for path in templates:
        Task.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")))
