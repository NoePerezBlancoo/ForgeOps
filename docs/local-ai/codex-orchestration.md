# Codex orchestration protocol

Codex remains the architect, security owner and reviewer. The local agent implements bounded work.

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
