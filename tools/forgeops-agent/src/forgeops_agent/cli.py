from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path
from urllib.request import urlopen

import psutil

from forgeops_agent import __version__
from forgeops_agent.benchmark import benchmark_models
from forgeops_agent.config import OrchestratorConfig
from forgeops_agent.errors import AgentError
from forgeops_agent.git import compact_diff
from forgeops_agent.models import TaskStatus
from forgeops_agent.orchestrator import Orchestrator
from forgeops_agent.policy import scan_secrets, validate_changed_paths
from forgeops_agent.system import (
    command_version,
    executable,
    gpu_metrics,
    ollama_version,
    resource_snapshot,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forgeops-agent")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor")
    commands.add_parser("models")
    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("--model", action="append", dest="models")

    delegate = commands.add_parser("delegate")
    delegate.add_argument("task_file", type=Path)
    create = commands.add_parser("create-task")
    create.add_argument("--from-template", required=True, type=Path)
    create.add_argument("--output", type=Path)

    run = commands.add_parser("run")
    run.add_argument("task_id")
    add_risk_flags(run)
    run_next = commands.add_parser("run-next")
    add_risk_flags(run_next)
    supervise = commands.add_parser("supervise")
    supervise.add_argument("--watch", action="store_true")
    add_risk_flags(supervise)

    commands.add_parser("queue")
    status = commands.add_parser("status")
    status.add_argument("task_id", nargs="?")
    diff = commands.add_parser("diff")
    diff.add_argument("task_id")
    report = commands.add_parser("report")
    report.add_argument("task_id")
    review = commands.add_parser("review-package")
    review.add_argument("task_id")
    retry = commands.add_parser("retry")
    retry.add_argument("task_id")
    retry.add_argument("--feedback", required=True, type=Path)
    cancel = commands.add_parser("cancel")
    cancel.add_argument("task_id")
    cleanup = commands.add_parser("cleanup")
    cleanup.add_argument("task_id")
    approve = commands.add_parser("approve")
    approve.add_argument("task_id")
    reject = commands.add_parser("reject")
    reject.add_argument("task_id")
    reject.add_argument("--reason", required=True)
    prepare = commands.add_parser("prepare-merge")
    prepare.add_argument("task_id")
    commands.add_parser("stop-all")
    commands.add_parser("clear-stop")

    policy = commands.add_parser("policy-check-worktree")
    policy.add_argument("task_id")
    return parser


def add_risk_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--allow-medium-risk", action="store_true")
    parser.add_argument("--allow-high-risk", action="store_true")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = OrchestratorConfig.load()
        orchestrator = Orchestrator(config)
        return dispatch(args, config, orchestrator)
    except AgentError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


def dispatch(args, config: OrchestratorConfig, orchestrator: Orchestrator) -> int:
    command = args.command
    if command == "doctor":
        print_json(doctor(config, orchestrator))
        return 0
    if command == "models":
        with urlopen(f"{config.ollama_url.rstrip('/')}/api/tags", timeout=10) as response:
            payload = json.load(response)
        print_json(
            {
                "primary": config.primary_model,
                "fallback": config.fallback_model,
                "context_tokens": config.context_tokens,
                "installed": [
                    {"name": item["name"], "size_gb": round(item["size"] / 1024**3, 2)}
                    for item in payload.get("models", [])
                ],
            }
        )
        return 0
    if command == "benchmark":
        models = args.models or [
            item
            for item in (config.primary_model, config.fallback_model)
            if item
        ]
        result = benchmark_models(
            config.repo_root, config.ollama_url, models, config.context_tokens
        )
        write_benchmark_report(config.ai_root, result)
        print_json(result)
        return 0
    if command == "delegate":
        task = orchestrator.delegate(args.task_file.resolve())
        print(f"TASK: {task.id}\nSTATUS: QUEUED")
        return 0
    if command == "create-task":
        source = args.from_template.resolve()
        output = args.output or Path.cwd() / source.name
        output.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        print(output.resolve())
        return 0
    if command == "run":
        state = orchestrator.run_task(args.task_id, **risk_flags(args))
        print_state(config, state)
        return 0 if state.status is TaskStatus.COMPLETED else 1
    if command == "run-next":
        state = orchestrator.run_next(**risk_flags(args))
        if state is None:
            print("STATUS: IDLE")
            return 0
        print_state(config, state)
        return 0 if state.status is TaskStatus.COMPLETED else 1
    if command == "supervise":
        orchestrator.supervise(watch=args.watch, **risk_flags(args))
        print("STATUS: STOPPED" if (config.ai_root / "STOP").exists() else "STATUS: IDLE")
        return 0
    if command == "queue":
        tasks = []
        for task in orchestrator.store.queued():
            ready, blocked = orchestrator.store.dependencies_ready(task)
            tasks.append(
                {
                    "id": task.id,
                    "title": task.title,
                    "risk": task.risk.value,
                    "ready": ready,
                    "blocked_by": blocked,
                }
            )
        print_json({"count": len(tasks), "tasks": tasks})
        return 0
    if command == "status":
        if args.task_id:
            print_json(orchestrator.store.load_state(args.task_id).to_dict())
        else:
            status_path = config.ai_root / "status.json"
            print(status_path.read_text(encoding="utf-8") if status_path.exists() else '{"status":"IDLE"}')
        return 0
    if command == "diff":
        state = orchestrator.store.load_state(args.task_id)
        if not state.worktree or not state.base_commit:
            raise AgentError("Task has no worktree")
        print(compact_diff(Path(state.worktree), state.base_commit))
        return 0
    if command == "report":
        path = config.ai_root / "reports" / f"{args.task_id.upper()}.md"
        if not path.exists():
            raise AgentError(f"Report not found: {path}")
        print(path.read_text(encoding="utf-8"))
        return 0
    if command == "review-package":
        print(orchestrator.review_package(args.task_id))
        return 0
    if command == "retry":
        print_json(orchestrator.retry(args.task_id, args.feedback.resolve()).to_dict())
        return 0
    if command == "cancel":
        print_json(orchestrator.cancel(args.task_id).to_dict())
        return 0
    if command == "cleanup":
        print_json(orchestrator.cleanup(args.task_id).to_dict())
        return 0
    if command == "approve":
        print_json(orchestrator.approve(args.task_id).to_dict())
        return 0
    if command == "reject":
        print_json(orchestrator.reject(args.task_id, args.reason).to_dict())
        return 0
    if command == "prepare-merge":
        print_json(orchestrator.prepare_merge(args.task_id))
        return 0
    if command == "stop-all":
        orchestrator.stop_all()
        print("STATUS: STOPPED\nKILL_SWITCH: .ai/STOP")
        return 0
    if command == "clear-stop":
        (config.ai_root / "STOP").unlink(missing_ok=True)
        print("STATUS: READY")
        return 0
    if command == "policy-check-worktree":
        task = orchestrator.store.load_task(args.task_id)
        state = orchestrator.store.load_state(task.id)
        if not state.worktree or not state.base_commit:
            raise AgentError("Task has no worktree")
        from forgeops_agent.git import changed_files

        paths = changed_files(Path(state.worktree), state.base_commit)
        path_result = validate_changed_paths(task, paths, config.protected_path_prefixes)
        secret_result = scan_secrets(Path(state.worktree), paths)
        print_json(
            {
                "paths": asdict(path_result),
                "secrets": asdict(secret_result),
                "valid": path_result.valid and secret_result.valid,
            }
        )
        return 0 if path_result.valid and secret_result.valid else 1
    raise AgentError(f"Unsupported command: {command}")


def risk_flags(args) -> dict[str, bool]:
    return {
        "allow_medium": bool(getattr(args, "allow_medium_risk", False)),
        "allow_high": bool(getattr(args, "allow_high_risk", False)),
    }


def doctor(config: OrchestratorConfig, orchestrator: Orchestrator) -> dict[str, object]:
    return {
        "orchestrator_version": __version__,
        "repository": str(config.repo_root),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu": platform.processor(),
        "logical_cpus": psutil.cpu_count(),
        "resources": resource_snapshot(config.repo_root),
        "gpu": gpu_metrics(),
        "tools": {
            "git": command_version(["git", "--version"]),
            "docker": command_version(["docker", "--version"]),
            "node": command_version(["node", "--version"]),
            "npm": command_version(["npm", "--version"]),
            "gh": command_version(["gh", "--version"]),
            "wsl": command_version(["wsl", "--version"]),
            "nvidia_smi": executable("nvidia-smi"),
        },
        "ollama": {
            "url": config.ollama_url,
            "version": ollama_version(config.ollama_url),
            "primary_model": config.primary_model,
            "context_tokens": config.context_tokens,
        },
        "agent": orchestrator.runner.doctor(),
        "kill_switch": (config.ai_root / "STOP").exists(),
    }


def write_benchmark_report(ai_root: Path, result: dict) -> None:
    reports = ai_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "model-benchmark.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    sections = []
    for model in result["models"]:
        cases = "\n".join(
            f"- {case['name']}: score {case['score']}, {case['duration_seconds']} s, {case.get('tokens_per_second') or 'N/A'} tok/s"
            for case in model["cases"]
        )
        sections.append(
            f"## {model['model']}\n\nQuality: {model['quality_score']}\n\nAverage speed: {model['average_tokens_per_second']} tok/s\n\n{cases}"
        )
    markdown = f"""# Local model benchmark

Generated from reproducible Ollama API calls against controlled ForgeOps-oriented prompts.

- Context: {result['context_tokens']} tokens
- Primary: `{result['primary']}`
- Fallback: `{result['fallback']}`
- Selection: {result['selection_method']}

{chr(10).join(sections)}
"""
    (reports / "model-benchmark.md").write_text(markdown, encoding="utf-8")


def print_state(config: OrchestratorConfig, state) -> None:
    report = config.ai_root / "reports" / f"{state.task_id}.md"
    print(
        f"TASK: {state.task_id}\n"
        f"STATUS: {state.status.value}\n"
        f"BRANCH: {state.branch or 'N/A'}\n"
        f"WORKTREE: {state.worktree or 'N/A'}\n"
        f"COMMIT: {state.commit or 'N/A'}\n"
        f"TESTS: {state.test_status}\n"
        f"REPORT: {report}\n"
        "REVIEW_REQUIRED: true"
    )


def print_json(value) -> None:
    print(json.dumps(value, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
