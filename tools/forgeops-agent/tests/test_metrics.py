from __future__ import annotations

import json

from forgeops_agent.metrics import aggregate_metrics, task_metrics
from forgeops_agent.models import TaskState, TaskStatus


def test_metrics_report_first_pass_acceptance_and_model_score(tmp_path):
    state = TaskState(
        task_id="AI-1001",
        status=TaskStatus.APPROVED,
        model="qwen-test",
        attempt_history=[
            {
                "model_alias": "qwen",
                "model": "qwen-test",
                "duration_seconds": 12.5,
                "status": "COMPLETED",
                "is_fallback": False,
            }
        ],
    )
    (tmp_path / "AI-1001.json").write_text(
        json.dumps(state.to_dict()), encoding="utf-8"
    )

    result = aggregate_metrics(tmp_path)

    assert task_metrics(state)["first_pass_accepted"] is True
    assert result["first_pass_acceptance_percent"] == 100.0
    assert result["models"]["qwen"]["success_first_pass"] == 1
    assert result["models"]["qwen"]["average_duration_seconds"] == 12.5
    assert "token-equivalent" in result["note"]


def test_metrics_count_fallback_and_codex_correction(tmp_path):
    state = TaskState(
        task_id="AI-1002",
        status=TaskStatus.REJECTED,
        model="devstral-test",
        fallback_used=True,
        codex_correction_required=True,
        retry_count=1,
        attempt_history=[
            {
                "model_alias": "qwen",
                "duration_seconds": 4,
                "status": "FAILED_TESTS",
                "is_fallback": False,
            },
            {
                "model_alias": "devstral",
                "duration_seconds": 9,
                "status": "COMPLETED",
                "is_fallback": False,
            },
        ],
    )
    (tmp_path / "AI-1002.json").write_text(
        json.dumps(state.to_dict()), encoding="utf-8"
    )

    result = aggregate_metrics(tmp_path)

    assert result["fallback_tasks"] == 1
    assert result["codex_review_corrections"] == 1
    assert result["models"]["devstral"]["fallback_attempts"] == 1


def test_rejected_state_implies_codex_correction_required():
    state = TaskState.from_dict(
        {"task_id": "AI-1003", "status": "REJECTED", "attempt_history": []}
    )

    assert state.codex_correction_required is True
