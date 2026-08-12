import os
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.audit.service import add_audit_event
from app.auth.security import hash_password
from app.companies.models import Company
from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.models import *  # noqa: F403
from app.plants.models import Plant
from app.users.models import User
from app.users.schemas import UserCreate


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Falta la variable {name}")
    return value


def main() -> None:
    try:
        company_name = required("BOOTSTRAP_COMPANY_NAME")
        tax_id = required("BOOTSTRAP_COMPANY_TAX_ID").upper()
        admin_email = required("BOOTSTRAP_ADMIN_EMAIL").lower()
        admin_password = required("BOOTSTRAP_ADMIN_PASSWORD")
        admin_name = required("BOOTSTRAP_ADMIN_NAME")
        user_payload = UserCreate(
            full_name=admin_name,
            email=admin_email,
            password=admin_password,
            role=UserRole.ADMIN,
            job_title=os.getenv("BOOTSTRAP_ADMIN_JOB_TITLE", "Administrador de ForgeOps"),
        )
    except (ValueError, TypeError) as exc:
        print(f"Bootstrap cancelado: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    with SessionLocal() as db:
        company = db.scalar(select(Company).where(Company.tax_id == tax_id))
        if not company:
            company = Company(
                name=company_name,
                tax_id=tax_id,
                address=os.getenv("BOOTSTRAP_COMPANY_ADDRESS") or None,
                email=os.getenv("BOOTSTRAP_COMPANY_EMAIL") or admin_email,
                industry=os.getenv("BOOTSTRAP_COMPANY_INDUSTRY") or None,
                timezone=os.getenv("BOOTSTRAP_TIMEZONE", "Europe/Madrid"),
                locale=os.getenv("BOOTSTRAP_LOCALE", "es-ES"),
                work_order_prefix=os.getenv("BOOTSTRAP_WORK_ORDER_PREFIX", "OT").upper(),
                active=True,
            )
            db.add(company)
            db.flush()

        user = db.scalar(select(User).where(User.email == admin_email))
        if user and user.company_id != company.id:
            print("Bootstrap cancelado: el correo pertenece a otra empresa", file=sys.stderr)
            raise SystemExit(3)
        if not user:
            user = User(
                company_id=company.id,
                full_name=user_payload.full_name,
                email=user_payload.email,
                job_title=user_payload.job_title,
                password_hash=hash_password(user_payload.password),
                password_changed_at=datetime.now(UTC),
                role=UserRole.ADMIN,
                active=True,
            )
            db.add(user)
            db.flush()
            add_audit_event(
                db,
                company.id,
                user.id,
                "BOOTSTRAP",
                "COMPANY",
                "Empresa y administrador inicial preparados",
                company.id,
            )

        plant_name = os.getenv("BOOTSTRAP_PLANT_NAME", "").strip()
        plant_code = os.getenv("BOOTSTRAP_PLANT_CODE", "").strip().upper()
        if plant_name and plant_code:
            plant = db.scalar(
                select(Plant).where(
                    Plant.company_id == company.id,
                    Plant.code == plant_code,
                )
            )
            if not plant:
                db.add(
                    Plant(
                        company_id=company.id,
                        name=plant_name,
                        code=plant_code,
                        active=True,
                    )
                )
        db.commit()
        print(f"Bootstrap completado para {company.name} ({user.email})")


if __name__ == "__main__":
    main()
