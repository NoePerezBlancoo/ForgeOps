from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from forgeops_agent.system import gpu_metrics, resource_snapshot

BENCHMARKS = (
    {
        "name": "module_comprehension",
        "prompt": """Read this ForgeOps helper and explain in at most 80 words its trust boundary and fallback behavior:\n\nfrom ipaddress import ip_address\n\ndef get_client_ip(request, source):\n    direct = request.client.host if request.client else None\n    if source != 'x-real-ip': return direct\n    forwarded = request.headers.get('x-real-ip', '').strip()\n    try: return str(ip_address(forwarded))\n    except ValueError: return direct""",
        "expected": ("x-real-ip", "fallback", "direct"),
    },
    {
        "name": "test_generation",
        "prompt": "Generate one concise pytest test for a function get_client_ip that must reject a comma-separated spoofed X-Real-IP and return the direct peer. Output only Python code.",
        "expected": ("pytest", "203.0.113", "10.0.0", "assert"),
    },
    {
        "name": "controlled_bug_fix",
        "prompt": "Fix this controlled bug. Empty input must return 0 and the last element must be included. Output only the corrected function:\n\ndef total(values):\n    result = 0\n    for index in range(0, len(values) - 1):\n        result += values[index]\n    return result",
        "expected": ("for", "values", "return"),
        "forbidden": ("len(values) - 1",),
    },
    {
        "name": "instruction_following",
        "prompt": "Return exactly this text and nothing else: FORGEOPS_POLICY_OK",
        "exact": "FORGEOPS_POLICY_OK",
    },
)


def _post(url: str, payload: dict[str, Any], timeout: int = 600) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _score(case: dict[str, Any], content: str) -> float:
    if "exact" in case:
        return 1.0 if content.strip() == case["exact"] else 0.0
    normalized = content.lower()
    expected = case.get("expected", ())
    positive = sum(item.lower() in normalized for item in expected) / max(1, len(expected))
    if any(item.lower() in normalized for item in case.get("forbidden", ())):
        positive *= 0.25
    return round(positive, 3)


def benchmark_models(
    repo_root: Path,
    base_url: str,
    models: list[str],
    context_tokens: int,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for model in models:
        cases: list[dict[str, Any]] = []
        for case in BENCHMARKS:
            before = resource_snapshot(repo_root)
            started = time.monotonic()
            response = _post(
                f"{base_url.rstrip('/')}/api/chat",
                {
                    "model": model,
                    "messages": [{"role": "user", "content": case["prompt"]}],
                    "stream": False,
                    "options": {"num_ctx": context_tokens, "temperature": 0},
                    "keep_alive": "10m",
                },
            )
            duration = time.monotonic() - started
            content = response.get("message", {}).get("content", "")
            eval_count = int(response.get("eval_count") or 0)
            eval_duration = int(response.get("eval_duration") or 0)
            cases.append(
                {
                    "name": case["name"],
                    "score": _score(case, content),
                    "duration_seconds": round(duration, 2),
                    "tokens_per_second": round(eval_count / (eval_duration / 1e9), 2)
                    if eval_duration
                    else None,
                    "response_preview": content.strip()[:500],
                    "resources_before": before,
                    "gpu_after": gpu_metrics(),
                }
            )
        tool_response = _post(
            f"{base_url.rstrip('/')}/api/chat",
            {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Use the read_file tool once for backend/app/core/request.py.",
                    }
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "description": "Read one repository file",
                            "parameters": {
                                "type": "object",
                                "properties": {"path": {"type": "string"}},
                                "required": ["path"],
                            },
                        },
                    }
                ],
                "stream": False,
                "options": {"num_ctx": context_tokens, "temperature": 0},
            },
        )
        tool_calls = tool_response.get("message", {}).get("tool_calls") or []
        cases.append(
            {
                "name": "tool_calling",
                "score": 1.0 if tool_calls else 0.0,
                "duration_seconds": round((tool_response.get("total_duration") or 0) / 1e9, 2),
                "tokens_per_second": None,
                "response_preview": json.dumps(tool_calls)[:500],
                "gpu_after": gpu_metrics(),
            }
        )
        quality = round(sum(case["score"] for case in cases) / len(cases), 3)
        speeds = [case["tokens_per_second"] for case in cases if case.get("tokens_per_second")]
        results.append(
            {
                "model": model,
                "quality_score": quality,
                "average_tokens_per_second": round(sum(speeds) / len(speeds), 2) if speeds else None,
                "cases": cases,
            }
        )
        _post(
            f"{base_url.rstrip('/')}/api/generate",
            {"model": model, "keep_alive": 0},
            timeout=60,
        )
    ranked = sorted(
        results,
        key=lambda item: (
            item["quality_score"],
            item["average_tokens_per_second"] or 0,
        ),
        reverse=True,
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "context_tokens": context_tokens,
        "primary": ranked[0]["model"],
        "fallback": ranked[1]["model"] if len(ranked) > 1 else None,
        "selection_method": "Highest controlled quality score; speed breaks ties",
        "models": results,
    }
