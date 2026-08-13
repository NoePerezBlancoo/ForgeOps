from __future__ import annotations

import json
from pathlib import Path

from forgeops_agent.models import Task, TaskState


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def write_task_report(ai_root: Path, task: Task, state: TaskState) -> tuple[Path, Path]:
    reports = ai_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / f"{task.id}.json"
    markdown_path = reports / f"{task.id}.md"
    payload = {
        "task": task.to_dict(),
        "state": state.to_dict(),
        "review_required": True,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    checks = "\n".join(
        f"- {item['name']}: {'PASS' if item['passed'] else 'FAIL'} ({item['summary']})"
        for item in state.check_results
    ) or "- Not run"
    files = "\n".join(f"- `{path}`" for path in state.changed_files) or "- None"
    markdown = f"""# Status

{state.status.value}

# Objective

{task.objective}

# Model

{state.model or 'Not started'}

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
