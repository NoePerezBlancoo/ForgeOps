# Local AI installation

## Requirements

- Windows 11 with WSL2.
- Docker Desktop running.
- Git, Python 3.12 or newer and PowerShell.
- Ollama for Windows bound to `127.0.0.1:11434`.
- At least 50 GB free for the two recommended coding models.

## Installation

```powershell
winget install --id Ollama.Ollama --exact
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11434", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_CONTEXT_LENGTH", "32768", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "10m", "User")
ollama pull qwen3-coder:30b
ollama pull devstral-small-2:24b
.\scripts\install-forgeops-agent.ps1
.\scripts\forgeops-agent.ps1 doctor
```

Restart Ollama after changing user environment variables. The orchestrator also sends `num_ctx=32768` explicitly during benchmarks. A 32K context is the practical target for this workstation; larger contexts increase KV-cache memory and may force avoidable CPU offload.

Aider 0.86.0 is installed in the local agent image, not in ForgeOps production images. The image is built lazily on the first task. Only the task worktree is mounted and no Docker socket, SSH directory, browser profile or user home is exposed.

OpenHands 1.16.0 was evaluated first, but both local candidates produced invalid tool calls in its current SDK integration. Aider was selected because its one-shot mode supports Ollama, explicit editable files and read-only context without exposing an agent shell. Ubuntu 24.04 under WSL2 remains useful for diagnostics; the supported automation path is the Docker runner so Windows host files stay outside the sandbox.

## First task

```powershell
.\scripts\forgeops-agent.ps1 delegate .ai\tasks\templates\low-backend-tests.yaml
.\scripts\forgeops-agent.ps1 run AI-0001
.\scripts\forgeops-agent.ps1 review-package AI-0001
```
