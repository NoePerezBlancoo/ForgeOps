from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.assets.models import Asset
from app.auth.security import hash_password
from app.companies.models import Company
from app.core.database import Base, get_db
from app.core.enums import AssetStatus, Criticality, UserRole
from app.main import app
from app.models import *  # noqa: F403
from app.plants.models import Plant
from app.users.models import User

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def database() -> Generator[Session, None, None]:
    Base.metadata.create_all(test_engine)
    db = TestingSession()
    seed_test_data(db)

    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    yield db
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def seed_test_data(db: Session) -> None:
    alpha = Company(name="Alpha Factory", tax_id="A00000001", active=True)
    beta = Company(name="Beta Factory", tax_id="B00000002", active=True)
    db.add_all([alpha, beta])
    db.flush()
    alpha_plant = Plant(company_id=alpha.id, name="Alpha Plant", code="ALPHA", active=True)
    beta_plant = Plant(company_id=beta.id, name="Beta Plant", code="BETA", active=True)
    db.add_all([alpha_plant, beta_plant])
    db.flush()
    users = [
        User(
            company_id=alpha.id,
            full_name="Alpha Admin",
            email="admin@alpha.local",
            password_hash=hash_password("Admin123!"),
            role=UserRole.ADMIN,
            active=True,
        ),
        User(
            company_id=alpha.id,
            full_name="Alpha Tech",
            email="tech@alpha.local",
            password_hash=hash_password("Tech123!"),
            role=UserRole.TECHNICIAN,
            active=True,
        ),
        User(
            company_id=alpha.id,
            full_name="Alpha Viewer",
            email="viewer@alpha.local",
            password_hash=hash_password("Viewer123!"),
            role=UserRole.VIEWER,
            active=True,
        ),
        User(
            company_id=beta.id,
            full_name="Beta Admin",
            email="admin@beta.local",
            password_hash=hash_password("Admin123!"),
            role=UserRole.ADMIN,
            active=True,
        ),
    ]
    db.add_all(users)
    db.flush()
    db.add_all(
        [
            Asset(
                company_id=alpha.id,
                plant_id=alpha_plant.id,
                code="A-001",
                name="Alpha Machine",
                status=AssetStatus.ACTIVE,
                criticality=Criticality.HIGH,
            ),
            Asset(
                company_id=beta.id,
                plant_id=beta_plant.id,
                code="B-001",
                name="Beta Machine",
                status=AssetStatus.ACTIVE,
                criticality=Criticality.HIGH,
            ),
        ]
    )
    db.commit()


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
