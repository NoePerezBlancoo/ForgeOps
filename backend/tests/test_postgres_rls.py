import os
import uuid

import pytest
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.companies.models import Company
from app.core.config import settings
from app.core.database import set_database_context
from app.plants.models import Plant

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
