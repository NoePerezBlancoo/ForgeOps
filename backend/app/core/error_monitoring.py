import sentry_sdk

from app.core.config import settings


def configure_error_monitoring() -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=f"forgeops@{settings.app_version}+{settings.build_commit}",
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )
