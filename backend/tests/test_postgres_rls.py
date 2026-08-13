import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth.security import hash_password
from app.companies.models import Company
from app.core.config import settings
from app.core.database import set_database_context
from app.core.enums import NotificationType, UserRole
from app.invitations.models import UserInvitation
from app.notifications.models import Notification
from app.plants.models import Plant
from app.users.models import User

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Requiere PostgreSQL migrado")


def _runtime_engine():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, poolclass=NullPool)
    runtime_role = (settings.database_runtime_role or "").strip()
    if not runtime_role:
        return engine

    @event.listens_for(engine, "connect")
    def activate_runtime_role(dbapi_connection, connection_record):
        with dbapi_connection.cursor() as cursor:
            cursor.execute(f'SET ROLE "{runtime_role}"')

    return engine


def test_rls_blocks_tenant_reads_and_writes_but_allows_platform():
    engine = _runtime_engine()

    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, expire_on_commit=False)
    suffix = uuid.uuid4().hex[:8]
    try:
        set_database_context(db, "system")
        alpha = Company(name=f"RLS Alpha {suffix}", tax_id=f"RLS-A-{suffix}")
        beta = Company(name=f"RLS Beta {suffix}", tax_id=f"RLS-B-{suffix}")
        db.add_all([alpha, beta])
        db.flush()
        alpha_plant = Plant(company_id=alpha.id, name="Alpha Plant", code=f"A{suffix}")
        beta_plant = Plant(company_id=beta.id, name="Beta Plant", code=f"B{suffix}")
        db.add_all([alpha_plant, beta_plant])
        db.flush()
        db.expunge_all()

        set_database_context(db, "tenant", alpha.id)
        visible = list(db.scalars(select(Plant).order_by(Plant.code)))
        hidden = db.scalar(select(Plant).where(Plant.id == beta_plant.id))
        assert [plant.company_id for plant in visible] == [alpha.id]
        assert hidden is None

        db.expunge_all()
        set_database_context(db, "platform")
        platform_rows = list(
            db.scalars(select(Plant).where(Plant.id.in_([alpha_plant.id, beta_plant.id])))
        )
        assert {plant.company_id for plant in platform_rows} == {alpha.id, beta.id}

        set_database_context(db, "tenant", alpha.id)
        db.add(Plant(company_id=beta.id, name="Cross tenant", code=f"X{suffix}"))
        with pytest.raises(DBAPIError):
            db.flush()
    finally:
        db.rollback()
        if transaction.is_active:
            transaction.rollback()
        db.close()
        connection.close()
        engine.dispose()


def test_rls_context_is_transaction_local_across_connection_reuse():
    engine = _runtime_engine()
    suffix = uuid.uuid4().hex[:8]
    alpha_id = beta_id = alpha_plant_id = beta_plant_id = None
    try:
        with Session(engine, expire_on_commit=False) as db:
            set_database_context(db, "system")
            alpha = Company(name=f"Pool Alpha {suffix}", tax_id=f"POOL-A-{suffix}")
            beta = Company(name=f"Pool Beta {suffix}", tax_id=f"POOL-B-{suffix}")
            db.add_all([alpha, beta])
            db.flush()
            alpha_plant = Plant(company_id=alpha.id, name="Alpha Pool Plant", code=f"PA{suffix}")
            beta_plant = Plant(company_id=beta.id, name="Beta Pool Plant", code=f"PB{suffix}")
            db.add_all([alpha_plant, beta_plant])
            db.commit()
            alpha_id, beta_id = alpha.id, beta.id
            alpha_plant_id, beta_plant_id = alpha_plant.id, beta_plant.id

        expected = ((alpha_id, alpha_plant_id), (beta_id, beta_plant_id))
        for company_id, plant_id in expected * 10:
            with Session(engine) as db:
                set_database_context(db, "tenant", company_id)
                visible = list(db.scalars(select(Plant.id).order_by(Plant.id)))
                assert visible == [plant_id]
                db.commit()

            with Session(engine) as db:
                assert list(db.scalars(select(Plant.id))) == []
                db.commit()
    finally:
        if alpha_id and beta_id:
            with Session(engine) as db:
                set_database_context(db, "system")
                db.execute(delete(Plant).where(Plant.company_id.in_([alpha_id, beta_id])))
                db.execute(delete(Company).where(Company.id.in_([alpha_id, beta_id])))
                db.commit()
        engine.dispose()


def test_invitations_and_notifications_enforce_tenant_and_recipient_boundaries():
    engine = _runtime_engine()
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, expire_on_commit=False)
    suffix = uuid.uuid4().hex[:8]
    try:
        set_database_context(db, "system")
        alpha = Company(name=f"Notify Alpha {suffix}", tax_id=f"NOT-A-{suffix}")
        beta = Company(name=f"Notify Beta {suffix}", tax_id=f"NOT-B-{suffix}")
        db.add_all([alpha, beta])
        db.flush()
        alpha_user = User(
            company_id=alpha.id,
            full_name="Alpha User",
            email=f"alpha-{suffix}@rls.local",
            password_hash=hash_password("RlsSecure123!"),
            role=UserRole.ADMIN,
        )
        beta_user = User(
            company_id=beta.id,
            full_name="Beta User",
            email=f"beta-{suffix}@rls.local",
            password_hash=hash_password("RlsSecure123!"),
            role=UserRole.ADMIN,
        )
        db.add_all([alpha_user, beta_user])
        db.flush()
        invitations = [
            UserInvitation(
                company_id=company.id,
                email=f"invite-{label}-{suffix}@rls.local",
                full_name=f"{label.title()} Invite",
                role=UserRole.TECHNICIAN,
                token_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                inviter_id=user.id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
            for company, user, label in (
                (alpha, alpha_user, "alpha"),
                (beta, beta_user, "beta"),
            )
        ]
        notifications = [
            Notification(
                company_id=company.id,
                recipient_id=user.id,
                type=NotificationType.WORK_ORDER_ASSIGNED,
                title="Assigned",
                body="Tenant-specific notification",
                dedupe_key=f"rls-{label}-{suffix}",
            )
            for company, user, label in (
                (alpha, alpha_user, "alpha"),
                (beta, beta_user, "beta"),
            )
        ]
        db.add_all([*invitations, *notifications])
        db.flush()
        db.expunge_all()

        set_database_context(db, "tenant", alpha.id)
        assert list(db.scalars(select(UserInvitation.id))) == [invitations[0].id]
        assert list(db.scalars(select(Notification.id))) == [notifications[0].id]

        db.expunge_all()
        set_database_context(db, "auth")
        invitation_ids = {invitations[0].id, invitations[1].id}
        assert set(
            db.scalars(
                select(UserInvitation.id).where(UserInvitation.id.in_(invitation_ids))
            )
        ) == {
            invitations[0].id,
            invitations[1].id,
        }
        assert list(db.scalars(select(Notification.id))) == []
    finally:
        db.rollback()
        if transaction.is_active:
            transaction.rollback()
        db.close()
        connection.close()
        engine.dispose()
