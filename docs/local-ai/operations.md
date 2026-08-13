# Local AI operations

## Normal workflow

```powershell
.\scripts\forgeops-agent.ps1 doctor
.\scripts\forgeops-agent.ps1 queue
.\scripts\forgeops-agent.ps1 delegate path\task.yaml
.\scripts\forgeops-agent.ps1 run AI-0001
.\scripts\forgeops-agent.ps1 review-package AI-0001
.\scripts\forgeops-agent.ps1 approve AI-0001
.\scripts\forgeops-agent.ps1 prepare-merge AI-0001
```

`approve` records Codex review. It never merges. `prepare-merge` only checks approval, worktree cleanliness and ancestry.

For changed backend Python files, the supervisor applies deterministic Ruff import fixes and formatting to the already validated file list. It then recalculates the diff and repeats scope and secret validation before running the required checks. The formatter cannot expand the task scope.

For corrections:

```powershell
.\scripts\forgeops-agent.ps1 retry AI-0001 --model devstral --feedback feedback.md
.\scripts\forgeops-agent.ps1 run AI-0001
```

The retry reuses the existing branch and worktree until `max_attempts` is reached.

## Long-running supervisor

```powershell
.\scripts\forgeops-agent.ps1 supervise --watch
.\scripts\forgeops-agent.ps1 stop-all
.\scripts\forgeops-agent.ps1 clear-stop
```

`stop-all` creates `.ai/STOP` and asks active task containers to stop. With an empty queue, watch mode reports `IDLE` and waits; it never invents tasks.

Runtime status is written to `.ai/status.json`. Logs rotate to a bounded 10 MB tail and remain ignored by Git. After a restart, abandoned `RUNNING` tasks become `INTERRUPTED` instead of being assumed alive.

## Model maintenance

```powershell
ollama list
ollama ps
.\scripts\forgeops-agent.ps1 models
.\scripts\forgeops-agent.ps1 routing
.\scripts\forgeops-agent.ps1 metrics
.\scripts\forgeops-agent.ps1 benchmark
ollama rm MODEL_NAME
```

Models are never removed automatically.

`models` reports readiness and routing roles. `routing` prints the configured risk policy. `metrics` reports task counts, model attempts, fallback rate, Codex corrections and first-pass acceptance without estimating Codex token equivalents. Metrics are observational and never tune routing automatically.

## Optional startup

Automatic startup is deliberately opt-in. To run the supervisor after signing in, create a
Windows Task Scheduler entry that starts PowerShell in the repository and executes:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\forgeops-agent.ps1 supervise --watch
```

Configure it for the current user, only when Docker Desktop and Ollama are available, and
without elevated privileges. `stop-all` remains the immediate kill switch.
