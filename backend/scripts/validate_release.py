import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


class ReleaseValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseTarget:
    api_url: str
    app_url: str
    expected_version: str
    expected_environment: str
    expected_commit: str | None = None
    timeout: float = 20.0


def _endpoint(base_url: str, path: str) -> str:
    return urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))


def _fetch(url: str, timeout: float) -> tuple[int, dict[str, str], bytes]:
    request = Request(
        url,
        headers={
            "Accept": "application/json,text/html;q=0.9",
            "User-Agent": "ForgeOps-Release-Validator/1",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status, dict(response.headers.items()), response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise ReleaseValidationError(f"{url} returned HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise ReleaseValidationError(f"{url} is unreachable: {exc.reason}") from exc


def _fetch_json(url: str, timeout: float) -> tuple[dict[str, Any], dict[str, str]]:
    status, headers, body = _fetch(url, timeout)
    if status != 200:
        raise ReleaseValidationError(f"{url} returned HTTP {status}")
    try:
        payload = json.loads(body)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ReleaseValidationError(f"{url} did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise ReleaseValidationError(f"{url} did not return a JSON object")
    return payload, headers


def validate_health(payload: dict[str, Any], target: ReleaseTarget) -> dict[str, Any]:
    if payload.get("status") != "ok":
        raise ReleaseValidationError("API health status is not ok")
    if payload.get("version") != target.expected_version:
        raise ReleaseValidationError(
            f"deployed version {payload.get('version')!r} does not match "
            f"{target.expected_version!r}"
        )
    if payload.get("environment") != target.expected_environment:
        raise ReleaseValidationError(
            f"deployed environment {payload.get('environment')!r} does not match "
            f"{target.expected_environment!r}"
        )
    deployed_commit = str(payload.get("commit", ""))
    if target.expected_commit and not deployed_commit.startswith(target.expected_commit):
        raise ReleaseValidationError(
            f"deployed commit {deployed_commit!r} does not match {target.expected_commit!r}"
        )
    return {
        "version": payload["version"],
        "environment": payload["environment"],
        "commit": deployed_commit,
    }


def validate_readiness(payload: dict[str, Any]) -> dict[str, bool]:
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        raise ReleaseValidationError("API readiness response has no dependency checks")
    unavailable = sorted(name for name, ready in checks.items() if ready is not True)
    if unavailable:
        raise ReleaseValidationError(f"readiness checks failed: {', '.join(unavailable)}")
    if payload.get("status") != "ready":
        raise ReleaseValidationError("API readiness status is not ready")
    return {str(name): True for name in checks}


def validate_release(target: ReleaseTarget) -> dict[str, Any]:
    health_url = _endpoint(target.api_url, "/health")
    ready_url = _endpoint(target.api_url, "/ready")
    login_url = _endpoint(target.app_url, "/login")
    health, health_headers = _fetch_json(health_url, target.timeout)
    readiness, _ = _fetch_json(ready_url, target.timeout)
    login_status, login_headers, login_body = _fetch(login_url, target.timeout)
    if login_status != 200 or not login_body.strip():
        raise ReleaseValidationError("frontend login did not return a non-empty HTTP 200 response")
    if "x-request-id" not in {key.lower() for key in health_headers}:
        raise ReleaseValidationError("API response is missing X-Request-ID")
    content_type = next(
        (value for key, value in login_headers.items() if key.lower() == "content-type"), ""
    )
    if "text/html" not in content_type.lower():
        raise ReleaseValidationError("frontend login did not return HTML")
    return {
        "release_validation": "passed",
        "health": validate_health(health, target),
        "readiness": validate_readiness(readiness),
        "frontend": {"login": True},
    }


def _environment_value(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a deployed ForgeOps release")
    api_url = _environment_value("RELEASE_API_URL")
    app_url = _environment_value("RELEASE_APP_URL")
    expected_version = _environment_value("EXPECTED_VERSION")
    expected_environment = _environment_value("EXPECTED_ENVIRONMENT")
    parser.add_argument("--api-url", default=api_url, required=not api_url)
    parser.add_argument("--app-url", default=app_url, required=not app_url)
    parser.add_argument(
        "--expected-version", default=expected_version, required=not expected_version
    )
    parser.add_argument(
        "--expected-environment",
        choices=("staging", "production"),
        default=expected_environment,
        required=not expected_environment,
    )
    parser.add_argument("--expected-commit", default=_environment_value("EXPECTED_COMMIT"))
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = validate_release(
            ReleaseTarget(
                api_url=args.api_url,
                app_url=args.app_url,
                expected_version=args.expected_version,
                expected_environment=args.expected_environment,
                expected_commit=args.expected_commit,
                timeout=args.timeout,
            )
        )
    except ReleaseValidationError as exc:
        print(json.dumps({"release_validation": "failed", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
