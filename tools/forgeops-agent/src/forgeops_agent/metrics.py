from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from forgeops_agent.models import TaskState, TaskStatus

REVIEWED_STATUSES = {TaskStatus.APPROVED, TaskStatus.REJECTED}
COMPLETED_STATUSES = {TaskStatus.COMPLETED, TaskStatus.APPROVED}


def task_metrics(state: TaskState) -> dict[str, Any]:
    duration = round(
        sum(float(item.get("duration_seconds") or 0) for item in state.attempt_history),
        2,
    )
    fallback_attempts = sum(
        bool(item.get("is_fallback")) for item in state.attempt_history
    )
    return {
        "task_id": state.task_id,
        "local_attempts": len(state.attempt_history),
        "model": state.model,
        "duration_seconds": duration,
        "fallback_count": max(fallback_attempts, int(state.fallback_used)),
        "result": state.status.value,
        "codex_correction_required": state.codex_correction_required,
        "retry_count": state.retry_count,
        "first_pass_accepted": _first_pass_accepted(state),
    }


def aggregate_metrics(state_root: Path) -> dict[str, Any]:
    states = _load_states(state_root)
    attempted = [state for state in states if state.attempt_history]
    completed = [state for state in attempted if state.status in COMPLETED_STATUSES]
    reviewed = [state for state in attempted if state.status in REVIEWED_STATUSES]
    first_pass = [state for state in reviewed if _first_pass_accepted(state)]
    fallback_tasks = [state for state in attempted if state.fallback_used]
    model_attempts: dict[str, list[tuple[TaskState, dict[str, Any]]]] = defaultdict(list)
    for state in attempted:
        for attempt in state.attempt_history:
            alias = str(attempt.get("model_alias") or attempt.get("model") or "unknown")
            model_attempts[alias].append((state, attempt))

    model_scores: dict[str, dict[str, Any]] = {}
    for alias, entries in sorted(model_attempts.items()):
        task_ids = {state.task_id for state, _ in entries}
        direct_ids = {
            state.task_id
            for state, attempt in entries
            if state.attempt_history and attempt is state.attempt_history[0]
        }
        reviewed_direct_ids = {
            state.task_id
            for state, attempt in entries
            if state.status in REVIEWED_STATUSES
            and state.attempt_history
            and attempt is state.attempt_history[0]
        }
        fallback_count = sum(bool(attempt.get("is_fallback")) for _, attempt in entries)
        accepted_ids = {
            state.task_id
            for state, _ in entries
            if _first_pass_accepted(state)
            and state.attempt_history[0].get("model_alias") == alias
        }
        durations = [float(attempt.get("duration_seconds") or 0) for _, attempt in entries]
        model_scores[alias] = {
            "tasks": len(task_ids),
            "direct_tasks": len(direct_ids),
            "reviewed_direct_tasks": len(reviewed_direct_ids),
            "fallback_attempts": fallback_count,
            "success_first_pass": len(accepted_ids),
            "average_duration_seconds": round(sum(durations) / len(durations), 2),
            "first_pass_acceptance_percent": _percent(
                len(accepted_ids), len(reviewed_direct_ids)
            ),
        }

    durations = [task_metrics(state)["duration_seconds"] for state in attempted]
    return {
        "tasks_attempted": len(attempted),
        "tasks_completed": len(completed),
        "tasks_reviewed": len(reviewed),
        "first_pass_accepted": len(first_pass),
        "first_pass_acceptance_percent": _percent(len(first_pass), len(reviewed)),
        "average_local_duration_seconds": (
            round(sum(durations) / len(durations), 2) if durations else 0.0
        ),
        "fallback_tasks": len(fallback_tasks),
        "fallback_rate_percent": _percent(len(fallback_tasks), len(attempted)),
        "codex_review_corrections": sum(
            state.codex_correction_required for state in attempted
        ),
        "models": model_scores,
        "tasks": [task_metrics(state) for state in attempted],
        "note": "No Codex token-equivalent estimate is calculated.",
    }


def _load_states(state_root: Path) -> list[TaskState]:
    states: list[TaskState] = []
    for path in sorted(state_root.glob("AI-*.json")):
        try:
            states.append(TaskState.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError, TypeError):
            continue
    return states


def _first_pass_accepted(state: TaskState) -> bool:
    return bool(
        state.status is TaskStatus.APPROVED
        and len(state.attempt_history) == 1
        and not state.fallback_used
        and not state.codex_correction_required
        and state.attempt_history[0].get("status") == TaskStatus.COMPLETED.value
    )


def _percent(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0
