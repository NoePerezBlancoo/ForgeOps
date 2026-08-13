# Codex orchestration protocol

Codex remains the architect, security owner and reviewer. The local agent implements bounded work.

If a task can be executed safely and verified by the local agent, Codex should prefer delegation instead of implementing it directly. Codex reserves its work for architecture, planning, specifications, review, security, integration and complex decisions.

> Si una tarea puede ejecutarse de forma segura y verificable por el agente local, Codex debe preferir delegarla en lugar de implementarla directamente.

## Model routing

Routing is explicit configuration in `.ai/config/models.yaml`; metrics never change it automatically.

- LOW uses Qwen3-Coder first for throughput, with Devstral as the recovery model.
- MEDIUM requires Codex approval. `preferred_model: auto` starts with Qwen; use `preferred_model: devstral` for delicate bounded logic.
- HIGH remains owned by Codex. Only tightly scoped mechanical work may be delegated with the explicit risk override, using Devstral.
- CRITICAL is forbidden for local execution.

Qwen failures caused by the agent, tests, lint or build can route once to Devstral. Scope, protected-path, secret, security, policy, timeout and kill-switch failures terminate immediately. Devstral can never bypass a policy.

Use `preferred_model: auto`, `qwen` or `devstral` in task YAML. A quality rejection after review can be sent directly to Devstral:

```powershell
.\scripts\forgeops-agent.ps1 retry AI-0001 --model devstral --feedback feedback.md
.\scripts\forgeops-agent.ps1 run AI-0001
```

Once Codex delegates a task, it must wait for the result or cancel the delegation before editing the same files. Codex and the local agent must not implement the same task simultaneously.

## Delegate

Good candidates are focused tests, small UI work, responsive fixes, accessibility, documentation and mechanical cleanup. Medium-risk business logic requires explicit `--allow-medium-risk`. Auth, permissions, RLS, migrations, billing and infrastructure should remain with Codex. Production and destructive tasks are classified CRITICAL and cannot run.

1. Copy a template and assign a unique `AI-NNNN` id.
2. Define narrow `allowed_paths`, checks, timeout and dependencies.
3. Run `delegate`, then `run` or leave it for `supervise`.
4. Read `review-package`, not the full log.
5. Review the diff and checks; use `retry`, `approve` or `reject`.
6. Merge manually only after `prepare-merge` succeeds.

```powershell
.\scripts\forgeops-agent.ps1 delegate task.yaml
.\scripts\forgeops-agent.ps1 run AI-0001
.\scripts\forgeops-agent.ps1 review-package AI-0001
.\scripts\forgeops-agent.ps1 approve AI-0001
.\scripts\forgeops-agent.ps1 metrics
```

The completion contract is machine-readable:

```text
TASK: AI-0001
STATUS: COMPLETED
BRANCH: ai/0001-example
WORKTREE: ...
COMMIT: ...
TESTS: PASS
REPORT: ...
REVIEW_REQUIRED: true
```

Security is layered: isolated worktree, protected branch checks, filtered host environment, container without Docker socket, offline network proxy restricted to Ollama, explicit editable/read-only files, disabled agent shell suggestions, path validation, secret scanning, trusted supervisor checks and supervisor-only commits.
