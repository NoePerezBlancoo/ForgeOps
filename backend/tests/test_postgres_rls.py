import os
import uuid

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.companies.models import Company
from app.core.config import settings
from app.core.database import set_database_context
from app.plants.models import Plant

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Requiere PostgreSQL migrado")


def test_rls_blocks_tenant_reads_and_writes_but_allows_platform():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def activate_runtime_role(dbapi_connection, connection_record):
        with dbapi_connection.cursor() as cursor:
            cursor.execute(f'SET ROLE "{settings.database_runtime_role}"')

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
