# Local AI troubleshooting

## Ollama does not respond

Run `Invoke-RestMethod http://127.0.0.1:11434/api/version`, confirm the Ollama tray process is running and restart it after environment-variable changes.

## WSL cannot see Ollama

WSL is not required by the automated runner. The Docker gateway reaches host Ollama without exposing port 11434 publicly. Do not change `OLLAMA_HOST` to `0.0.0.0` merely to make WSL work.

## Docker is unavailable

Start Docker Desktop and run `docker version`. Do not fall back to an unrestricted host-process agent.

## Model is slow or runs out of memory

Check `ollama ps` and `nvidia-smi`. Keep context at 32768, stop the other model, and use the configured fallback. The resource guard blocks new tasks if RAM, disk or GPU temperature crosses configured thresholds.

## Agent loops

Use `stop-all`. Tasks also have a timeout, maximum iterations and maximum attempts. Inspect the compact report before retrying.

## Worktree is locked

Run `git worktree list`. Stale supervisor/task locks are reclaimed only when their recorded process no longer exists. `cleanup` refuses to discard uncommitted work.

## Tests fail

Read `.ai/reports/AI-NNNN.md`, prepare focused feedback and run `retry`. Failed checks prevent a commit.

## Process died or Windows restarted

Run `supervise` or `status`. The recovery pass marks abandoned tasks `INTERRUPTED`; resume through an explicit retry.

## GPU out of memory

Run `ollama stop MODEL_NAME`, reduce context in `.ai/config/models.yaml`, or select the fallback. Never modify GPU voltage, BIOS or driver limits from the orchestrator.

