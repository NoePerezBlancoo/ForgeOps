from __future__ import annotations

import json
from pathlib import Path

from forgeops_agent.metrics import task_metrics
from forgeops_agent.models import Task, TaskState


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def write_task_report(ai_root: Path, task: Task, state: TaskState) -> tuple[Path, Path]:
    reports = ai_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / f"{task.id}.json"
    markdown_path = reports / f"{task.id}.md"
    performance = _performance(state)
    payload = {
        "task": task.to_dict(),
        "state": state.to_dict(),
        "model_routing": {
            "primary_model": state.routing_primary,
            "fallback_model": state.routing_fallback,
            "actual_model_used": state.model,
            "risk": task.risk.value,
            "preferred_model": task.preferred_model.value,
            "reason": state.routing_reason,
        },
        "attempts": state.attempt_history,
        "fallback": {
            "used": state.fallback_used,
            "reason": state.fallback_reason,
        },
        "performance": performance,
        "metrics": task_metrics(state),
        "review_required": True,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    checks = "\n".join(
        f"- {item['name']}: {'PASS' if item['passed'] else 'FAIL'} ({item['summary']})"
        for item in state.check_results
    ) or "- Not run"
    files = "\n".join(f"- `{path}`" for path in state.changed_files) or "- None"
    attempts = _attempts_markdown(state)
    markdown = f"""# Status

{state.status.value}

# Objective

{task.objective}

# Model routing

Primary model: `{state.routing_primary or 'N/A'}`
Fallback model: `{state.routing_fallback or 'None'}`
Actual model used: `{state.model or 'Not started'}`
Preferred model: `{task.preferred_model.value}`
Risk: {task.risk.value}
Routing reason: {state.routing_reason or 'Not evaluated'}

# Attempts

{attempts}

# Fallback

Fallback used: {_yes_no(state.fallback_used)}
Fallback reason: {state.fallback_reason or 'None'}

# Performance

Total local duration: {performance['duration_seconds']} s
Generated tokens: {performance['generated_tokens'] if performance['generated_tokens'] is not None else 'N/A'}
Observed tokens/sec: {performance['tokens_per_second'] if performance['tokens_per_second'] is not None else 'N/A'}
Available RAM after final attempt: {performance['memory_available_gb'] if performance['memory_available_gb'] is not None else 'N/A'} GB
VRAM used after final attempt: {performance['gpu_memory_used_mb'] if performance['gpu_memory_used_mb'] is not None else 'N/A'} MB
Codex correction required: {_yes_no(state.codex_correction_required)}
Task retry count: {state.retry_count}

# Duration

Started: {state.started_at or 'N/A'}
Finished: {state.finished_at or 'N/A'}

# Files changed

{files}

# Checks executed

{checks}

# Commit

{state.commit or 'No commit'}

# Diff summary

{len(state.changed_files)} file(s) changed.

# Decisions

The orchestrator enforced worktree, branch, scope, secret and quality policies.

# Risks

Declared risk: {task.risk.value}.

# Warnings

{state.error or 'None'}

# Recommendation for Codex

Review the compact package and approve or reject the task. Approval does not merge it.

# Human review required

{_yes_no(True)}
"""
    markdown_path.write_text(markdown, encoding="utf-8")
    return markdown_path, json_path


def _attempts_markdown(state: TaskState) -> str:
    sections: list[str] = []
    for item in state.attempt_history:
        checks = ", ".join(
            f"{check['name']}={'PASS' if check['passed'] else 'FAIL'}"
            for check in item.get("checks", [])
        ) or "Not run"
        sections.append(
            "\n".join(
                (
                    f"## Attempt {item.get('attempt', '?')}",
                    f"- Model: `{item.get('model', 'N/A')}`",
                    f"- Duration: {item.get('duration_seconds', 0)} s",
                    f"- Status: {item.get('status', 'UNKNOWN')}",
                    f"- Checks: {checks}",
                    f"- Reason: {item.get('reason') or 'None'}",
                    f"- Reason for retry: {item.get('reason_for_retry') or 'None'}",
                )
            )
        )
    return "\n\n".join(sections) or "No local attempts recorded."


def _performance(state: TaskState) -> dict[str, float | int | None]:
    duration = sum(float(item.get("duration_seconds") or 0) for item in state.attempt_history)
    token_attempts = [
        item for item in state.attempt_history if item.get("generated_tokens") is not None
    ]
    generated_tokens = (
        sum(int(item["generated_tokens"]) for item in token_attempts)
        if token_attempts
        else None
    )
    token_duration = sum(
        float(item.get("agent_duration_seconds") or 0) for item in token_attempts
    )
    final_resources = (
        state.attempt_history[-1].get("resources_after", {})
        if state.attempt_history
        else {}
    )
    gpu = final_resources.get("gpu") or {}
    return {
        "duration_seconds": round(duration, 2),
        "generated_tokens": generated_tokens,
        "tokens_per_second": (
            round(generated_tokens / token_duration, 2)
            if generated_tokens is not None and token_duration > 0
            else None
        ),
        "memory_available_gb": final_resources.get("memory_available_gb"),
        "gpu_memory_used_mb": gpu.get("memory_used_mb"),
    }


def write_review_package(
    ai_root: Path,
    task: Task,
    state: TaskState,
    diff: str,
) -> Path:
    reports = ai_root / "reports"
    path = reports / f"{task.id}-review.md"
    check_lines = "\n".join(
        f"- {item['name']}: {'PASS' if item['passed'] else 'FAIL'}"
        for item in state.check_results
    ) or "- Not run"
    content = f"""# {task.id}: {task.title}

Status: **{state.status.value}**
Risk: **{task.risk.value}**
Branch: `{state.branch or 'N/A'}`
Commit: `{state.commit or 'N/A'}`
Model: `{state.model or 'N/A'}`
Fallback used: **{_yes_no(state.fallback_used)}**

## Objective

{task.objective}

## Scope

Allowed: {', '.join(task.allowed_paths)}

## Checks

{check_lines}

## Warnings

{state.error or 'None'}

## Diff

```diff
{diff}
```
"""
    path.write_text(content, encoding="utf-8")
    return path
