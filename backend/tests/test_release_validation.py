import pytest

from scripts.validate_release import (
    ReleaseTarget,
    ReleaseValidationError,
    validate_health,
    validate_readiness,
)


@pytest.fixture
def target():
    return ReleaseTarget(
        api_url="https://api.example.test",
        app_url="https://app.example.test",
        expected_version="1.2.3",
        expected_environment="staging",
        expected_commit="abc1234",
    )


def test_health_requires_expected_release_identity(target):
    result = validate_health(
        {
            "status": "ok",
            "version": "1.2.3",
            "environment": "staging",
            "commit": "abc1234deadbeef",
        },
        target,
    )
    assert result["version"] == "1.2.3"
    assert result["commit"] == "abc1234deadbeef"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "degraded"),
        ("version", "1.2.2"),
        ("environment", "production"),
        ("commit", "def5678"),
    ],
)
def test_health_rejects_release_drift(target, field, value):
    payload = {
        "status": "ok",
        "version": "1.2.3",
        "environment": "staging",
        "commit": "abc1234deadbeef",
    }
    payload[field] = value
    with pytest.raises(ReleaseValidationError):
        validate_health(payload, target)


def test_readiness_requires_every_reported_dependency():
    assert validate_readiness(
        {"status": "ready", "checks": {"database": True, "redis": True}}
    ) == {"database": True, "redis": True}

    with pytest.raises(ReleaseValidationError, match="redis"):
        validate_readiness(
            {"status": "unavailable", "checks": {"database": True, "redis": False}}
        )
