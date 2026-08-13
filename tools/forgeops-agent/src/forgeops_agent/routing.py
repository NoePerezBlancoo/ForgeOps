from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from forgeops_agent.errors import ConfigurationError, PolicyError
from forgeops_agent.models import PreferredModel, Risk, Task, TaskStatus

if TYPE_CHECKING:
    from forgeops_agent.config import OrchestratorConfig


NON_RETRYABLE_STATUSES = {
    TaskStatus.FAILED_POLICY,
    TaskStatus.FAILED_SECURITY,
    TaskStatus.TIMEOUT,
    TaskStatus.CANCELLED,
    TaskStatus.INTERRUPTED,
}


@dataclass(frozen=True)
class RoutingDecision:
    risk: Risk
    preferred_model: str
    primary_alias: str
    primary_model: str
    fallback_alias: str | None
    fallback_model: str | None
    reason: str
    max_model_attempts: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risk"] = self.risk.value
        return data


class ModelRouter:
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self._validate()

    def route(self, task: Task, override: str | None = None) -> RoutingDecision:
        policy = self.config.routing_policy[task.risk.value]
        if policy.get("local_execution", "allowed") == "forbidden":
            raise PolicyError(f"{task.risk.value} tasks cannot be delegated")

        preferred = (override or task.preferred_model.value).lower()
        allowed = tuple(str(item).lower() for item in policy.get("allowed", ("auto",)))
        if preferred not in allowed:
            raise PolicyError(
                f"Model preference {preferred!r} is not allowed for {task.risk.value} tasks"
            )

        primary_alias = str(policy["primary"]).lower() if preferred == "auto" else preferred
        fallback_alias = policy.get("fallback")
        fallback_alias = str(fallback_alias).lower() if fallback_alias else None
        if primary_alias != str(policy["primary"]).lower() or fallback_alias == primary_alias:
            fallback_alias = None

        reason_key = "reason" if preferred == "auto" else "override_reason"
        reason = str(
            policy.get(
                reason_key,
                f"Explicit {preferred} model preference selected for this task."
                if preferred != "auto"
                else f"Configured {task.risk.value} routing policy selected {primary_alias}.",
            )
        )
        return RoutingDecision(
            risk=task.risk,
            preferred_model=preferred,
            primary_alias=primary_alias,
            primary_model=self.model_name(primary_alias),
            fallback_alias=fallback_alias,
            fallback_model=self.model_name(fallback_alias) if fallback_alias else None,
            reason=reason,
            max_model_attempts=self.config.max_model_attempts,
        )

    def should_fallback(
        self,
        decision: RoutingDecision,
        status: TaskStatus,
        model_attempts: int,
    ) -> bool:
        if status in NON_RETRYABLE_STATUSES:
            return False
        return bool(
            decision.fallback_alias
            and model_attempts < decision.max_model_attempts
            and status.value in self.config.fallback_statuses
        )

    def model_name(self, alias: str) -> str:
        return str(self.config.model_catalog[alias]["model"])

    def describe(self) -> dict[str, Any]:
        return {
            "max_model_attempts": self.config.max_model_attempts,
            "fallback_statuses": list(self.config.fallback_statuses),
            "models": self.config.model_catalog,
            "routing": self.config.routing_policy,
        }

    def _validate(self) -> None:
        if not self.config.model_catalog:
            raise ConfigurationError("models.yaml must define at least one model")
        for alias, definition in self.config.model_catalog.items():
            if alias not in {item.value for item in PreferredModel if item is not PreferredModel.AUTO}:
                raise ConfigurationError(f"Unsupported model alias: {alias}")
            for field in ("provider", "model", "role"):
                if not str(definition.get(field, "")).strip():
                    raise ConfigurationError(f"Model {alias} is missing {field}")
        for risk in Risk:
            policy = self.config.routing_policy.get(risk.value)
            if not isinstance(policy, dict):
                raise ConfigurationError(f"Missing routing policy for {risk.value}")
            if policy.get("local_execution", "allowed") == "forbidden":
                continue
            primary = str(policy.get("primary", "")).lower()
            fallback = policy.get("fallback")
            if primary not in self.config.model_catalog:
                raise ConfigurationError(f"Unknown primary model {primary!r} for {risk.value}")
            if fallback and str(fallback).lower() not in self.config.model_catalog:
                raise ConfigurationError(f"Unknown fallback model {fallback!r} for {risk.value}")
            allowed = {str(item).lower() for item in policy.get("allowed", ())}
            if "auto" not in allowed or not allowed.issubset(
                {item.value for item in PreferredModel}
            ):
                raise ConfigurationError(f"Invalid allowed model preferences for {risk.value}")
        if not 1 <= self.config.max_model_attempts <= 3:
            raise ConfigurationError("max_model_attempts must be between 1 and 3")
        for status in self.config.fallback_statuses:
            try:
                parsed = TaskStatus(status)
            except ValueError as exc:
                raise ConfigurationError(f"Unknown fallback status: {status}") from exc
            if parsed in NON_RETRYABLE_STATUSES:
                raise ConfigurationError(f"Unsafe fallback status: {status}")
