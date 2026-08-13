from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.assets.models import Asset
from app.companies.models import Company
from app.core.enums import (
    IncidentStatus,
    Priority,
    WorkOrderParticipantRole,
    WorkOrderStatus,
    WorkOrderType,
)
from app.incidents.models import Incident
from app.users.models import User
from app.work_orders.models import WorkOrder, WorkOrderParticipant, WorkSession
from tests.conftest import login


def test_operational_dashboard_calculates_period_metrics(client, database):
    headers = login(client, "admin@alpha.local", "Admin123!")
    company = database.scalar(select(Company).where(Company.name == "Alpha Factory"))
    asset = database.scalar(select(Asset).where(Asset.company_id == company.id))
    admin = database.scalar(select(User).where(User.email == "admin@alpha.local"))
    technician = database.scalar(select(User).where(User.email == "tech@alpha.local"))
    now = datetime.now(UTC)
    database.add_all(
        [
            Incident(
                company_id=company.id,
                plant_id=asset.plant_id,
                asset_id=asset.id,
                reported_by=admin.id,
                title="Averia resuelta del periodo",
                description="Evento para calcular el tiempo medio de resolucion.",
                priority=Priority.HIGH,
                status=IncidentStatus.RESOLVED,
                reported_at=now - timedelta(hours=5),
                resolved_at=now - timedelta(hours=1),
                downtime_minutes=180,
            ),
            Incident(
                company_id=company.id,
                plant_id=asset.plant_id,
                asset_id=asset.id,
                reported_by=admin.id,
                title="Averia fuera del periodo",
                description="No debe formar parte de las metricas de siete dias.",
                priority=Priority.LOW,
                status=IncidentStatus.RESOLVED,
                reported_at=now - timedelta(days=40),
                resolved_at=now - timedelta(days=39),
                downtime_minutes=600,
            ),
        ]
    )
    order = WorkOrder(
        company_id=company.id,
        plant_id=asset.plant_id,
        asset_id=asset.id,
        assigned_to=technician.id,
        created_by=admin.id,
        number="OT-REPORT-001",
        title="Intervencion vencida",
        description="Orden activa utilizada para validar carga operativa.",
        type=WorkOrderType.CORRECTIVE,
        priority=Priority.HIGH,
        status=WorkOrderStatus.IN_PROGRESS,
        scheduled_date=now - timedelta(days=1),
        started_at=now - timedelta(hours=2),
    )
    database.add(order)
    database.flush()
    participant = WorkOrderParticipant(
        company_id=company.id,
        work_order_id=order.id,
        user_id=technician.id,
        role=WorkOrderParticipantRole.LEAD,
        active=True,
    )
    database.add(participant)
    database.flush()
    database.add(
        WorkSession(
            company_id=company.id,
            work_order_id=order.id,
            participant_id=participant.id,
            user_id=technician.id,
            started_at=now - timedelta(hours=2),
        )
    )
    database.commit()

    response = client.get("/api/v1/dashboard?period_days=7", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["period_days"] == 7
    assert data["downtime_hours"] == 3.0
    assert data["mttr_hours"] == 4.0
    assert data["resolved_incidents"] == 1
    assert data["overdue_work_orders"] == 1
    assert len(data["incident_trend"]) == 7
    assert sum(item["value"] for item in data["incident_trend"]) == 1
    assert data["top_assets"][0]["asset_code"] == "A-001"
    assert data["top_assets"][0]["downtime_hours"] == 3.0
    workload = next(
        item
        for item in data["technician_workload"]
        if item["user_id"] == str(technician.id)
    )
    assert workload["active_work_orders"] == 1
    assert workload["in_progress_work_orders"] == 1
    assert workload["active_sessions"] == 1


def test_dashboard_export_is_validated_and_tenant_scoped(client, database):
    alpha_headers = login(client, "admin@alpha.local", "Admin123!")
    beta_headers = login(client, "admin@beta.local", "Admin123!")
    alpha_asset = database.scalar(select(Asset).where(Asset.code == "A-001"))
    alpha_admin = database.scalar(select(User).where(User.email == "admin@alpha.local"))
    database.add(
        Incident(
            company_id=alpha_asset.company_id,
            plant_id=alpha_asset.plant_id,
            asset_id=alpha_asset.id,
            reported_by=alpha_admin.id,
            title="Incidencia solo Alpha",
            description="Registro utilizado para validar el aislamiento del CSV.",
            priority=Priority.MEDIUM,
            status=IncidentStatus.OPEN,
            downtime_minutes=30,
        )
    )
    database.commit()

    assert client.get("/api/v1/dashboard?period_days=15", headers=alpha_headers).status_code == 422
    alpha_export = client.get(
        "/api/v1/dashboard/export?period_days=30", headers=alpha_headers
    )
    beta_export = client.get(
        "/api/v1/dashboard/export?period_days=30", headers=beta_headers
    )

    assert alpha_export.status_code == 200, alpha_export.text
    assert alpha_export.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in alpha_export.headers["content-disposition"]
    assert alpha_export.content.startswith(b"\xef\xbb\xbf")
    assert "ForgeOps - Informe operativo" in alpha_export.text
    assert "A-001" in alpha_export.text
    assert "A-001" not in beta_export.text
