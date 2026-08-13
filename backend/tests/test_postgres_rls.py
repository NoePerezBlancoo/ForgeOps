import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.assets.models import Asset
from app.auth.security import hash_password
from app.companies.models import Company
from app.core.config import settings
from app.core.database import set_database_context
from app.core.enums import (
    AssetStatus,
    Criticality,
    InventoryMovementType,
    NotificationType,
    Priority,
    UserRole,
    WorkOrderStatus,
    WorkOrderType,
)
from app.inventory.models import InventoryItem, InventoryMovement
from app.invitations.models import UserInvitation
from app.maintenance.models import ChecklistTemplate, ChecklistTemplateItem
from app.notifications.models import Notification
from app.plants.models import Plant
from app.users.models import User
from app.work_orders.models import WorkOrder, WorkOrderChecklistItem

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


def test_preventive_checklists_enforce_tenant_boundaries():
    engine = _runtime_engine()
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, expire_on_commit=False)
    suffix = uuid.uuid4().hex[:8]
    try:
        set_database_context(db, "system")
        companies = [
            Company(name=f"Checklist {label} {suffix}", tax_id=f"CHK-{label}-{suffix}")
            for label in ("A", "B")
        ]
        db.add_all(companies)
        db.flush()
        plants = [
            Plant(company_id=company.id, name=f"Plant {index}", code=f"C{index}{suffix}")
            for index, company in enumerate(companies, start=1)
        ]
        users = [
            User(
                company_id=company.id,
                full_name=f"Checklist Admin {index}",
                email=f"checklist-{index}-{suffix}@rls.local",
                password_hash=hash_password("RlsSecure123!"),
                role=UserRole.ADMIN,
            )
            for index, company in enumerate(companies, start=1)
        ]
        db.add_all([*plants, *users])
        db.flush()
        assets = [
            Asset(
                company_id=company.id,
                plant_id=plant.id,
                code=f"CHK-{index}-{suffix}",
                name=f"Checklist asset {index}",
                status=AssetStatus.ACTIVE,
                criticality=Criticality.HIGH,
            )
            for index, (company, plant) in enumerate(
                zip(companies, plants, strict=True), start=1
            )
        ]
        templates = [
            ChecklistTemplate(
                company_id=company.id,
                name=f"Checklist {index}",
                active=True,
            )
            for index, company in enumerate(companies, start=1)
        ]
        db.add_all([*assets, *templates])
        db.flush()
        template_items = [
            ChecklistTemplateItem(
                company_id=company.id,
                template_id=template.id,
                title="Tenant-specific check",
                position=1,
                required=True,
            )
            for company, template in zip(companies, templates, strict=True)
        ]
        orders = [
            WorkOrder(
                company_id=company.id,
                plant_id=plant.id,
                asset_id=asset.id,
                created_by=user.id,
                number=f"CHK-{index}-{suffix}",
                title="RLS checklist order",
                description="Order used to verify checklist row isolation.",
                type=WorkOrderType.PREVENTIVE,
                priority=Priority.MEDIUM,
                status=WorkOrderStatus.OPEN,
            )
            for index, (company, plant, asset, user) in enumerate(
                zip(companies, plants, assets, users, strict=True), start=1
            )
        ]
        db.add_all([*template_items, *orders])
        db.flush()
        snapshots = [
            WorkOrderChecklistItem(
                company_id=company.id,
                work_order_id=order.id,
                source_template_item_id=item.id,
                title=item.title,
                position=1,
                required=True,
            )
            for company, order, item in zip(
                companies, orders, template_items, strict=True
            )
        ]
        db.add_all(snapshots)
        db.flush()
        template_ids = {template.id for template in templates}
        item_ids = {item.id for item in template_items}
        snapshot_ids = {snapshot.id for snapshot in snapshots}
        db.expunge_all()

        set_database_context(db, "tenant", companies[0].id)
        assert set(db.scalars(select(ChecklistTemplate.id).where(
            ChecklistTemplate.id.in_(template_ids)
        ))) == {templates[0].id}
        assert set(db.scalars(select(ChecklistTemplateItem.id).where(
            ChecklistTemplateItem.id.in_(item_ids)
        ))) == {template_items[0].id}
        assert set(db.scalars(select(WorkOrderChecklistItem.id).where(
            WorkOrderChecklistItem.id.in_(snapshot_ids)
        ))) == {snapshots[0].id}

        db.expunge_all()
        set_database_context(db, "auth")
        assert not list(db.scalars(select(ChecklistTemplate.id).where(
            ChecklistTemplate.id.in_(template_ids)
        )))
        assert not list(db.scalars(select(WorkOrderChecklistItem.id).where(
            WorkOrderChecklistItem.id.in_(snapshot_ids)
        )))

        db.expunge_all()
        set_database_context(db, "platform")
        assert set(db.scalars(select(ChecklistTemplate.id).where(
            ChecklistTemplate.id.in_(template_ids)
        ))) == template_ids
        assert set(db.scalars(select(WorkOrderChecklistItem.id).where(
            WorkOrderChecklistItem.id.in_(snapshot_ids)
        ))) == snapshot_ids
    finally:
        db.rollback()
        if transaction.is_active:
            transaction.rollback()
        db.close()
        connection.close()
        engine.dispose()


def test_inventory_movements_and_work_order_links_enforce_tenant_boundaries():
    engine = _runtime_engine()
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, expire_on_commit=False)
    suffix = uuid.uuid4().hex[:8]
    try:
        set_database_context(db, "system")
        companies = [
            Company(name=f"Inventory {label} {suffix}", tax_id=f"INV-{label}-{suffix}")
            for label in ("A", "B")
        ]
        db.add_all(companies)
        db.flush()
        plants = [
            Plant(company_id=company.id, name=f"Inventory Plant {index}", code=f"I{index}{suffix}")
            for index, company in enumerate(companies, start=1)
        ]
        users = [
            User(
                company_id=company.id,
                full_name=f"Inventory Admin {index}",
                email=f"inventory-{index}-{suffix}@rls.local",
                password_hash=hash_password("RlsSecure123!"),
                role=UserRole.ADMIN,
            )
            for index, company in enumerate(companies, start=1)
        ]
        db.add_all([*plants, *users])
        db.flush()
        assets = [
            Asset(
                company_id=company.id,
                plant_id=plant.id,
                code=f"INV-{index}-{suffix}",
                name=f"Inventory asset {index}",
                status=AssetStatus.ACTIVE,
                criticality=Criticality.HIGH,
            )
            for index, (company, plant) in enumerate(
                zip(companies, plants, strict=True), start=1
            )
        ]
        items = [
            InventoryItem(
                company_id=company.id,
                code=f"SP-{index}-{suffix}",
                name=f"Spare part {index}",
                stock=Decimal("8.000"),
                minimum_stock=Decimal("2.000"),
                unit="ud",
                cost=Decimal("12.50"),
            )
            for index, company in enumerate(companies, start=1)
        ]
        db.add_all([*assets, *items])
        db.flush()
        orders = [
            WorkOrder(
                company_id=company.id,
                plant_id=plant.id,
                asset_id=asset.id,
                created_by=user.id,
                number=f"INV-{index}-{suffix}",
                title="Inventory-linked order",
                description="Order used to verify inventory movement isolation.",
                type=WorkOrderType.CORRECTIVE,
                priority=Priority.MEDIUM,
                status=WorkOrderStatus.OPEN,
            )
            for index, (company, plant, asset, user) in enumerate(
                zip(companies, plants, assets, users, strict=True), start=1
            )
        ]
        db.add_all(orders)
        db.flush()
        movements = [
            InventoryMovement(
                company_id=company.id,
                item_id=item.id,
                user_id=user.id,
                work_order_id=order.id,
                movement_type=InventoryMovementType.CONSUMPTION,
                quantity=Decimal("-1.000"),
                resulting_stock=Decimal("7.000"),
                unit_cost=Decimal("12.50"),
                total_cost=Decimal("12.50"),
                reason="Tenant-specific material consumption",
            )
            for company, item, user, order in zip(
                companies, items, users, orders, strict=True
            )
        ]
        db.add_all(movements)
        db.flush()
        item_ids = {item.id for item in items}
        movement_ids = {movement.id for movement in movements}
        db.expunge_all()

        set_database_context(db, "tenant", companies[0].id)
        assert set(db.scalars(select(InventoryItem.id).where(
            InventoryItem.id.in_(item_ids)
        ))) == {items[0].id}
        assert set(db.scalars(select(InventoryMovement.id).where(
            InventoryMovement.id.in_(movement_ids)
        ))) == {movements[0].id}

        with pytest.raises(DBAPIError):
            with db.begin_nested():
                movement = db.get(InventoryMovement, movements[0].id)
                movement.reason = "Historical movement must remain immutable"
                db.flush()

        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.add(
                    InventoryMovement(
                        company_id=companies[1].id,
                        item_id=items[1].id,
                        user_id=users[1].id,
                        work_order_id=orders[1].id,
                        movement_type=InventoryMovementType.CONSUMPTION,
                        quantity=Decimal("-1.000"),
                        resulting_stock=Decimal("6.000"),
                        unit_cost=Decimal("12.50"),
                        total_cost=Decimal("12.50"),
                        reason="Cross-tenant movement must fail",
                    )
                )
                db.flush()

        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.add(
                    InventoryMovement(
                        company_id=companies[0].id,
                        item_id=items[0].id,
                        user_id=users[1].id,
                        work_order_id=orders[0].id,
                        movement_type=InventoryMovementType.CONSUMPTION,
                        quantity=Decimal("-1.000"),
                        resulting_stock=Decimal("6.000"),
                        unit_cost=Decimal("12.50"),
                        total_cost=Decimal("12.50"),
                        reason="Cross-tenant author link must fail",
                    )
                )
                db.flush()

        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.add(
                    InventoryMovement(
                        company_id=companies[0].id,
                        item_id=items[1].id,
                        user_id=users[0].id,
                        work_order_id=orders[0].id,
                        movement_type=InventoryMovementType.CONSUMPTION,
                        quantity=Decimal("-1.000"),
                        resulting_stock=Decimal("6.000"),
                        unit_cost=Decimal("12.50"),
                        total_cost=Decimal("12.50"),
                        reason="Cross-tenant item link must fail",
                    )
                )
                db.flush()
    finally:
        db.rollback()
        if transaction.is_active:
            transaction.rollback()
        db.close()
        connection.close()
        engine.dispose()
