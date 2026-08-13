# ForgeOps local AI orchestrator

This directory contains development tooling only. It is not imported, built or deployed by the ForgeOps runtime.

The supervisor creates one `ai/*` branch and one sibling Git worktree per task. Aider runs inside a read-only Docker container with only that worktree mounted. It receives task files as editable and context files as read-only. Offline tasks use an internal Docker network whose only reachable service is a narrow proxy to the host Ollama API.

Start with:

```powershell
.\scripts\install-forgeops-agent.ps1
.\scripts\forgeops-agent.ps1 doctor
.\scripts\forgeops-agent.ps1 queue
```

Configuration and templates are versioned. Runtime state, logs, task reports, locks, prompts and the `.ai/STOP` kill switch remain local.

LOW tasks route to Qwen3-Coder for throughput and can fall back once to Devstral after a recoverable agent or quality-gate failure. Security, scope and policy failures never fall back. Run `forgeops-agent routing` for the active policy and `forgeops-agent metrics` for first-pass acceptance data.
