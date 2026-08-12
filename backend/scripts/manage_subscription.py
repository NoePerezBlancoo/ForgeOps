import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.companies.models import Company
from app.core.database import SessionLocal
from app.core.enums import CompanyPlan, SubscriptionStatus
from app.models import *  # noqa: F403
from app.users.models import User


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gestiona el acceso comercial de una empresa")
    parser.add_argument("--email", required=True, help="Correo de un usuario de la empresa")
    parser.add_argument(
        "--status",
        choices=[status.value for status in SubscriptionStatus],
        help="Nuevo estado de la suscripcion",
    )
    parser.add_argument(
        "--plan",
        choices=[plan.value for plan in CompanyPlan],
        help="Nuevo plan comercial",
    )
    parser.add_argument(
        "--extend-trial",
        type=int,
        metavar="DAYS",
        help="Amplia la prueba desde su vencimiento o desde hoy",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not any([args.status, args.plan, args.extend_trial]):
        raise SystemExit("Indica --status, --plan o --extend-trial")
    if args.extend_trial is not None and not 1 <= args.extend_trial <= 90:
        raise SystemExit("La ampliacion debe estar entre 1 y 90 dias")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email.lower().strip()))
        if not user:
            raise SystemExit("No existe ningun usuario con ese correo")
        company = db.get(Company, user.company_id)
        if not company:
            raise SystemExit("La empresa asociada no existe")

        if args.status:
            company.subscription_status = SubscriptionStatus(args.status)
        if args.plan:
            company.plan = CompanyPlan(args.plan)
        if args.extend_trial:
            now = datetime.now(UTC)
            current_end = company.trial_ends_at
            if current_end and current_end.tzinfo is None:
                current_end = current_end.replace(tzinfo=UTC)
            company.trial_started_at = company.trial_started_at or now
            company.trial_ends_at = max(current_end or now, now) + timedelta(
                days=args.extend_trial
            )
            company.plan = CompanyPlan.TRIAL
            company.subscription_status = SubscriptionStatus.TRIAL

        db.commit()
        print(
            f"{company.name}: plan={company.plan.value}, "
            f"estado={company.subscription_status.value}, "
            f"fin_prueba={company.trial_ends_at or '-'}"
        )


if __name__ == "__main__":
    main()
