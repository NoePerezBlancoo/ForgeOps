from __future__ import annotations

from dataclasses import replace

import pytest
from conftest import make_config

from forgeops_agent.errors import PolicyError
from forgeops_agent.models import PreferredModel, Risk, TaskStatus
from forgeops_agent.routing import ModelRouter


@pytest.mark.parametrize(
    ("risk", "preference", "expected_primary", "expected_fallback"),
    (
        (Risk.LOW, PreferredModel.AUTO, "qwen-test", "devstral-test"),
        (Risk.LOW, PreferredModel.QWEN, "qwen-test", "devstral-test"),
        (Risk.LOW, PreferredModel.DEVSTRAL, "devstral-test", None),
        (Risk.MEDIUM, PreferredModel.AUTO, "qwen-test", "devstral-test"),
        (Risk.MEDIUM, PreferredModel.DEVSTRAL, "devstral-test", None),
        (Risk.HIGH, PreferredModel.AUTO, "devstral-test", None),
    ),
)
def test_model_router_selects_configured_policy(
    git_repo,
    sample_task,
    risk,
    preference,
    expected_primary,
    expected_fallback,
):
    router = ModelRouter(make_config(git_repo))
    task = replace(sample_task, risk=risk, preferred_model=preference)

    decision = router.route(task)

    assert decision.primary_model == expected_primary
    assert decision.fallback_model == expected_fallback


def test_model_router_blocks_critical(git_repo, sample_task):
    router = ModelRouter(make_config(git_repo))
    task = replace(sample_task, risk=Risk.CRITICAL)

    with pytest.raises(PolicyError, match="CRITICAL"):
        router.route(task)


def test_qwen_falls_back_to_devstral_for_retryable_failure(git_repo, sample_task):
    router = ModelRouter(make_config(git_repo))
    decision = router.route(sample_task)

    assert router.should_fallback(decision, TaskStatus.FAILED_TESTS, 1)
    assert decision.fallback_model == "devstral-test"


@pytest.mark.parametrize(
    "status", (TaskStatus.FAILED_SECURITY, TaskStatus.FAILED_POLICY)
)
def test_router_never_falls_back_for_security_or_policy(
    git_repo, sample_task, status
):
    router = ModelRouter(make_config(git_repo))
    decision = router.route(sample_task)

    assert not router.should_fallback(decision, status, 1)


def test_router_stops_at_max_model_attempts(git_repo, sample_task):
    config = make_config(git_repo)
    router = ModelRouter(config)
    decision = router.route(sample_task)

    assert not router.should_fallback(
        decision, TaskStatus.FAILED_TESTS, config.max_model_attempts
    )
