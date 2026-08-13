import json
import os
import re
import sys
from pathlib import PurePosixPath


DENIED_COMMANDS = (
    r"\brm\s+-rf\b",
    r"\bgit\s+(?:commit|push|merge|clean|worktree)\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+checkout\s+--\b",
    r"\brailway\b",
    r"\bgh\s+repo\s+delete\b",
    r"\bdrop\s+(?:database|schema)\b",
    r"\b(?:diskpart|format|shutdown|reboot)\b",
    r"(?:\.env\.production|\.ssh|\.aws|AppData|/mnt/[a-z]/Users)",
)


def deny(reason: str) -> None:
    print(json.dumps({"decision": "deny", "reason": reason}))
    raise SystemExit(2)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        deny("Malformed tool request")
    tool_input = payload.get("tool_input") or {}
    command = str(tool_input.get("command") or "")
    for pattern in DENIED_COMMANDS:
        if re.search(pattern, command, flags=re.IGNORECASE):
            deny("Command denied by ForgeOps local-agent policy")
    raw_path = tool_input.get("path") or tool_input.get("file_path")
    if raw_path:
        path = PurePosixPath(str(raw_path))
        if path.is_absolute() and not str(path).startswith("/workspace/"):
            deny("File access outside /workspace is denied")
        if ".." in path.parts:
            deny("Parent-directory traversal is denied")
    working_dir = str(payload.get("working_dir") or os.environ.get("OPENHANDS_PROJECT_DIR", ""))
    if working_dir and not working_dir.startswith("/workspace"):
        deny("Tool execution outside /workspace is denied")


if __name__ == "__main__":
    main()
