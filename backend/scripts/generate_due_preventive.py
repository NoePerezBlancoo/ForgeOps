from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import joinedload

import app.models  # noqa: F401
from app.core.database import SessionLocal, set_database_context
from app.core.enums import UserRole
from app.maintenance.models import PreventivePlan
from app.maintenance.service import generate_due_work_orders
from app.users.models import User

MANAGER_ROLES = (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER)


def main() -> None:
    generated_total = 0
    skipped_total = 0
    companies_total = 0
    with SessionLocal() as db:
        set_database_context(db, "system")
        company_ids = list(
            db.scalars(
                select(PreventivePlan.company_id)
                .where(
                    PreventivePlan.active.is_(True),
                    PreventivePlan.next_execution <= datetime.now(UTC),
                )
                .distinct()
            )
        )
        for company_id in company_ids:
            set_database_context(db, "tenant", company_id)
            manager = db.scalar(
                select(User)
                .options(joinedload(User.company))
                .where(
                    User.company_id == company_id,
                    User.active.is_(True),
                    User.role.in_(MANAGER_ROLES),
                )
                .order_by(User.created_at)
                .limit(1)
            )
            if not manager or not manager.company.write_enabled:
                db.rollback()
                continue
            generated, skipped = generate_due_work_orders(db, manager)
            generated_total += generated
            skipped_total += skipped
            companies_total += 1
            set_database_context(db, "system")
    print(
        "Preventivos procesados: "
        f"empresas={companies_total}, generados={generated_total}, omitidos={skipped_total}"
    )


if __name__ == "__main__":
    main()
