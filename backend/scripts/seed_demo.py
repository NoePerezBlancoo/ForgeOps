from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.ai.service import index_documents
from app.assets.models import Asset
from app.auth.security import hash_password
from app.companies.models import Company
from app.core.database import SessionLocal
from app.core.enums import (
    AssetStatus,
    CompanyPlan,
    Criticality,
    DocumentType,
    FrequencyType,
    IncidentStatus,
    InventoryMovementType,
    Priority,
    SubscriptionStatus,
    UserRole,
    WorkOrderStatus,
    WorkOrderType,
)
from app.documents.models import TechnicalDocument
from app.documents.storage import LocalDocumentStorage
from app.incidents.models import Incident
from app.inventory.models import InventoryItem, InventoryMovement
from app.maintenance.models import PreventivePlan
from app.models import *  # noqa: F403
from app.plants.models import Plant
from app.users.models import User
from app.work_orders.models import WorkOrder


def get_or_create_company(db) -> Company:
    company = db.scalar(select(Company).where(Company.tax_id == "B32456789"))
    if company:
        company.industry = "Fabricacion metalmecanica"
        company.timezone = "Europe/Madrid"
        company.locale = "es-ES"
        company.work_order_prefix = "OT"
        company.plan = CompanyPlan.DEMO
        company.subscription_status = SubscriptionStatus.ACTIVE
        return company
    company = Company(
        name="MetalWorks Demo S.L.",
        tax_id="B32456789",
        address="Parque Tecnoloxico de Galicia, Ourense",
        phone="+34 988 555 014",
        email="mantenimiento@metalworks-demo.local",
        industry="Fabricacion metalmecanica",
        timezone="Europe/Madrid",
        locale="es-ES",
        work_order_prefix="OT",
        plan=CompanyPlan.DEMO,
        subscription_status=SubscriptionStatus.ACTIVE,
        active=True,
    )
    db.add(company)
    db.flush()
    return company


def get_or_create_plant(db, company: Company) -> Plant:
    plant = db.scalar(select(Plant).where(Plant.company_id == company.id, Plant.code == "OUR-01"))
    if plant:
        return plant
    plant = Plant(
        company_id=company.id,
        name="Planta Ourense",
        code="OUR-01",
        address="Poligono Industrial San Cibrao das Vinas, Ourense",
        description="Planta de mecanizado, soldadura y montaje industrial.",
        active=True,
    )
    db.add(plant)
    db.flush()
    return plant


def get_or_create_users(db, company: Company) -> dict[str, User]:
    definitions = [
        (
            "admin",
            "Noe Perez",
            "admin@metalworks-demo.local",
            UserRole.ADMIN,
            "Admin123!",
            "Responsable IT y operaciones",
            "+34 600 100 101",
        ),
        (
            "manager",
            "Laura Mendez",
            "laura.mendez@metalworks-demo.local",
            UserRole.MAINTENANCE_MANAGER,
            "Manager123!",
            "Responsable de mantenimiento",
            "+34 600 100 102",
        ),
        (
            "tech1",
            "David Rodriguez",
            "david.rodriguez@metalworks-demo.local",
            UserRole.TECHNICIAN,
            "Technician123!",
            "Tecnico electromecanico",
            "+34 600 100 103",
        ),
        (
            "tech2",
            "Sara Alonso",
            "sara.alonso@metalworks-demo.local",
            UserRole.TECHNICIAN,
            "Technician123!",
            "Tecnica de automatizacion",
            "+34 600 100 104",
        ),
        (
            "viewer",
            "Carlos Silva",
            "carlos.silva@metalworks-demo.local",
            UserRole.VIEWER,
            "Viewer123!",
            "Responsable de produccion",
            "+34 600 100 105",
        ),
    ]
    result: dict[str, User] = {}
    for key, name, email, role, password, job_title, phone in definitions:
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(
                company_id=company.id,
                full_name=name,
                email=email,
                job_title=job_title,
                phone=phone,
                password_hash=hash_password(password),
                password_changed_at=datetime.now(UTC),
                role=role,
                active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.job_title = job_title
            user.phone = phone
        result[key] = user
    return result


def get_or_create_assets(db, company: Company, plant: Plant) -> list[Asset]:
    definitions = [
        (
            "CNC-001",
            "Torno CNC 01",
            "DMG Mori",
            "NLX 2500",
            AssetStatus.ACTIVE,
            Criticality.HIGH,
            "Mecanizado A",
        ),
        (
            "CNC-002",
            "Torno CNC 02",
            "Mazak",
            "QT-250",
            AssetStatus.MAINTENANCE,
            Criticality.HIGH,
            "Mecanizado A",
        ),
        (
            "MC-001",
            "Centro Mecanizado 01",
            "Haas",
            "VF-4SS",
            AssetStatus.ACTIVE,
            Criticality.CRITICAL,
            "Mecanizado B",
        ),
        (
            "ROB-001",
            "Robot Soldadura 01",
            "KUKA",
            "KR 16",
            AssetStatus.ACTIVE,
            Criticality.HIGH,
            "Soldadura",
        ),
        (
            "ROB-002",
            "Robot Soldadura 02",
            "ABB",
            "IRB 2600",
            AssetStatus.STOPPED,
            Criticality.CRITICAL,
            "Soldadura",
        ),
        (
            "CMP-001",
            "Compresor Principal",
            "Atlas Copco",
            "GA 55",
            AssetStatus.ACTIVE,
            Criticality.CRITICAL,
            "Sala Tecnica",
        ),
        (
            "LIN-001",
            "Linea Montaje 01",
            "Bosch Rexroth",
            "TS 2plus",
            AssetStatus.ACTIVE,
            Criticality.HIGH,
            "Montaje",
        ),
        (
            "GRU-001",
            "Puente Grua 01",
            "GH Cranes",
            "GHB 5T",
            AssetStatus.ACTIVE,
            Criticality.MEDIUM,
            "Nave Principal",
        ),
        (
            "PRE-001",
            "Prensa Hidraulica 01",
            "Hidroliksan",
            "CFP 200",
            AssetStatus.ACTIVE,
            Criticality.HIGH,
            "Conformado",
        ),
        (
            "REF-001",
            "Sistema Refrigeracion",
            "Daikin",
            "EWYD-BZ",
            AssetStatus.ACTIVE,
            Criticality.CRITICAL,
            "Cubierta Tecnica",
        ),
    ]
    assets: list[Asset] = []
    for index, (code, name, manufacturer, model, state, criticality, location) in enumerate(
        definitions
    ):
        asset = db.scalar(select(Asset).where(Asset.company_id == company.id, Asset.code == code))
        if not asset:
            asset = Asset(
                company_id=company.id,
                plant_id=plant.id,
                code=code,
                name=name,
                description=f"Equipo productivo {name.lower()} integrado en la planta de Ourense.",
                manufacturer=manufacturer,
                model=model,
                serial_number=f"MW-{2020 + index % 4}-{1000 + index}",
                installation_date=date(2018 + index % 6, (index % 11) + 1, 15),
                status=state,
                criticality=criticality,
                location=location,
                notes="Activo incluido en el plan de mantenimiento de planta.",
            )
            db.add(asset)
            db.flush()
        assets.append(asset)
    return assets


def get_or_create_incidents(db, company, plant, assets, users) -> dict[str, Incident]:
    now = datetime.now(UTC)
    definitions = [
        (
            "Vibracion anomala en husillo",
            0,
            Priority.HIGH,
            IncidentStatus.IN_PROGRESS,
            95,
            2,
            "Desgaste progresivo del rodamiento delantero.",
        ),
        (
            "Fallo de comunicacion con controlador",
            4,
            Priority.CRITICAL,
            IncidentStatus.ASSIGNED,
            180,
            0,
            None,
        ),
        (
            "Temperatura elevada del compresor",
            5,
            Priority.HIGH,
            IncidentStatus.WAITING,
            45,
            1,
            None,
        ),
        ("Fuga leve en circuito hidraulico", 8, Priority.MEDIUM, IncidentStatus.OPEN, 20, 0, None),
        (
            "Desalineacion de utillaje",
            3,
            Priority.MEDIUM,
            IncidentStatus.RESOLVED,
            35,
            6,
            "Golpe durante el cambio de referencia.",
        ),
        (
            "Parada intermitente de transportador",
            6,
            Priority.HIGH,
            IncidentStatus.IN_PROGRESS,
            70,
            1,
            None,
        ),
        (
            "Ruido en traslacion del puente",
            7,
            Priority.LOW,
            IncidentStatus.CLOSED,
            10,
            12,
            "Holgura en rodillo guia lateral.",
        ),
        (
            "Baja presion en circuito de refrigeracion",
            9,
            Priority.CRITICAL,
            IncidentStatus.RESOLVED,
            240,
            4,
            "Microfuga en racor de impulsion.",
        ),
    ]
    result: dict[str, Incident] = {}
    for index, (title, asset_index, priority, state, downtime, days_ago, cause) in enumerate(
        definitions
    ):
        incident = db.scalar(
            select(Incident).where(Incident.company_id == company.id, Incident.title == title)
        )
        if not incident:
            resolved = state in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}
            started = state not in {IncidentStatus.OPEN, IncidentStatus.ASSIGNED}
            incident = Incident(
                company_id=company.id,
                plant_id=plant.id,
                asset_id=assets[asset_index].id,
                reported_by=users["manager"].id,
                assigned_to=users["tech1" if index % 2 == 0 else "tech2"].id,
                title=title,
                description=(
                    "Incidencia detectada durante la operacion normal de "
                    f"{assets[asset_index].name}."
                ),
                priority=priority,
                status=state,
                reported_at=now - timedelta(days=days_ago, hours=index + 1),
                started_at=now - timedelta(days=days_ago, hours=index) if started else None,
                resolved_at=now - timedelta(days=max(days_ago - 1, 0)) if resolved else None,
                downtime_minutes=downtime,
                root_cause=cause,
                resolution="Equipo verificado y devuelto a servicio." if resolved else None,
            )
            db.add(incident)
            db.flush()
        result[title] = incident
    return result


def get_or_create_work_orders(db, company, plant, assets, users, incidents) -> None:
    now = datetime.now(UTC)
    definitions = [
        (
            "OT-DEMO-001",
            "Sustituir rodamiento de husillo",
            0,
            WorkOrderType.CORRECTIVE,
            Priority.HIGH,
            WorkOrderStatus.IN_PROGRESS,
            180,
            -1,
            "Vibracion anomala en husillo",
        ),
        (
            "OT-DEMO-002",
            "Diagnosticar bus de comunicaciones",
            4,
            WorkOrderType.CORRECTIVE,
            Priority.CRITICAL,
            WorkOrderStatus.ASSIGNED,
            120,
            0,
            "Fallo de comunicacion con controlador",
        ),
        (
            "OT-DEMO-003",
            "Limpiar radiador y comprobar ventilacion",
            5,
            WorkOrderType.CORRECTIVE,
            Priority.HIGH,
            WorkOrderStatus.WAITING,
            90,
            1,
            "Temperatura elevada del compresor",
        ),
        (
            "OT-DEMO-004",
            "Revisar latiguillos y racores",
            8,
            WorkOrderType.INSPECTION,
            Priority.MEDIUM,
            WorkOrderStatus.OPEN,
            60,
            2,
            "Fuga leve en circuito hidraulico",
        ),
        (
            "OT-DEMO-005",
            "Alinear utillaje de soldadura",
            3,
            WorkOrderType.CORRECTIVE,
            Priority.MEDIUM,
            WorkOrderStatus.COMPLETED,
            75,
            -5,
            "Desalineacion de utillaje",
        ),
        (
            "OT-DEMO-006",
            "Verificar sensores de presencia",
            6,
            WorkOrderType.CORRECTIVE,
            Priority.HIGH,
            WorkOrderStatus.IN_PROGRESS,
            120,
            0,
            "Parada intermitente de transportador",
        ),
        (
            "OT-DEMO-007",
            "Ajustar rodillo guia",
            7,
            WorkOrderType.CORRECTIVE,
            Priority.LOW,
            WorkOrderStatus.COMPLETED,
            45,
            -10,
            "Ruido en traslacion del puente",
        ),
        (
            "OT-DEMO-008",
            "Sustituir racor de impulsion",
            9,
            WorkOrderType.CORRECTIVE,
            Priority.CRITICAL,
            WorkOrderStatus.COMPLETED,
            150,
            -3,
            "Baja presion en circuito de refrigeracion",
        ),
        (
            "OT-DEMO-009",
            "Inspeccion geometrica trimestral",
            2,
            WorkOrderType.INSPECTION,
            Priority.MEDIUM,
            WorkOrderStatus.ASSIGNED,
            180,
            3,
            None,
        ),
        (
            "OT-DEMO-010",
            "Revision de aceite y filtros",
            1,
            WorkOrderType.PREVENTIVE,
            Priority.MEDIUM,
            WorkOrderStatus.IN_PROGRESS,
            120,
            0,
            None,
        ),
        (
            "OT-DEMO-011",
            "Comprobar protecciones perimetrales",
            3,
            WorkOrderType.INSPECTION,
            Priority.HIGH,
            WorkOrderStatus.OPEN,
            60,
            4,
            None,
        ),
        (
            "OT-DEMO-012",
            "Analisis de vibraciones mensual",
            5,
            WorkOrderType.PREVENTIVE,
            Priority.MEDIUM,
            WorkOrderStatus.ASSIGNED,
            90,
            5,
            None,
        ),
        (
            "OT-DEMO-013",
            "Revision de finales de carrera",
            7,
            WorkOrderType.PREVENTIVE,
            Priority.HIGH,
            WorkOrderStatus.OPEN,
            75,
            7,
            None,
        ),
        (
            "OT-DEMO-014",
            "Mejora de acceso a lubricacion",
            8,
            WorkOrderType.IMPROVEMENT,
            Priority.LOW,
            WorkOrderStatus.OPEN,
            240,
            10,
            None,
        ),
        (
            "OT-DEMO-015",
            "Limpieza de intercambiador",
            9,
            WorkOrderType.PREVENTIVE,
            Priority.HIGH,
            WorkOrderStatus.ASSIGNED,
            180,
            12,
            None,
        ),
    ]
    for index, (
        number,
        title,
        asset_index,
        order_type,
        priority,
        state,
        duration,
        day_offset,
        incident_title,
    ) in enumerate(definitions):
        exists = db.scalar(
            select(WorkOrder).where(WorkOrder.company_id == company.id, WorkOrder.number == number)
        )
        if exists:
            continue
        completed = state == WorkOrderStatus.COMPLETED
        in_progress = state == WorkOrderStatus.IN_PROGRESS
        db.add(
            WorkOrder(
                company_id=company.id,
                plant_id=plant.id,
                asset_id=assets[asset_index].id,
                incident_id=incidents[incident_title].id if incident_title else None,
                assigned_to=users["tech1" if index % 2 == 0 else "tech2"].id,
                created_by=users["manager"].id,
                number=number,
                title=title,
                description=f"Intervencion planificada sobre {assets[asset_index].name}.",
                type=order_type,
                priority=priority,
                status=state,
                scheduled_date=now + timedelta(days=day_offset),
                started_at=now + timedelta(days=day_offset, hours=1)
                if in_progress or completed
                else None,
                completed_at=now + timedelta(days=day_offset, hours=3) if completed else None,
                estimated_duration=duration,
                real_duration=duration - 15 if completed else None,
                observations="Trabajo ejecutado y validado por produccion." if completed else None,
                created_at=now - timedelta(days=14 - index),
            )
        )


def get_or_create_preventive_plans(db, company, assets, users) -> None:
    now = datetime.now(UTC)
    definitions = [
        ("Lubricacion y geometria mensual", 0, FrequencyType.MONTHS, 1, -2, 90, Priority.HIGH),
        ("Revision de filtros y aceite", 5, FrequencyType.MONTHS, 3, 8, 120, Priority.HIGH),
        (
            "Inspeccion de seguridad perimetral",
            3,
            FrequencyType.WEEKS,
            2,
            -1,
            45,
            Priority.CRITICAL,
        ),
        ("Verificacion electrica anual", 6, FrequencyType.YEARS, 1, 28, 180, Priority.MEDIUM),
        ("Analisis de vibraciones", 9, FrequencyType.MONTHS, 1, 5, 75, Priority.HIGH),
    ]
    for index, (name, asset_index, frequency, value, day_offset, duration, priority) in enumerate(
        definitions
    ):
        exists = db.scalar(
            select(PreventivePlan).where(
                PreventivePlan.company_id == company.id,
                PreventivePlan.asset_id == assets[asset_index].id,
                PreventivePlan.name == name,
            )
        )
        if exists:
            continue
        db.add(
            PreventivePlan(
                company_id=company.id,
                asset_id=assets[asset_index].id,
                assigned_to=users["tech1" if index % 2 == 0 else "tech2"].id,
                name=name,
                description=(
                    f"Intervencion preventiva estandarizada sobre {assets[asset_index].name}, "
                    "incluyendo inspeccion, mediciones y registro del resultado."
                ),
                frequency_type=frequency,
                frequency_value=value,
                next_execution=now + timedelta(days=day_offset),
                estimated_duration=duration,
                priority=priority,
                active=True,
            )
        )


def get_or_create_inventory(db, company, users) -> None:
    definitions = [
        ("ROD-6205", "Rodamiento 6205-2RS", 8, 4, "ud", "A-01-02", 18.5),
        ("FILT-GA55", "Filtro de aceite GA55", 2, 3, "ud", "A-02-01", 64.9),
        ("SENS-M18", "Sensor inductivo M18 PNP", 5, 4, "ud", "B-01-03", 32.75),
        ("CONT-24V", "Contactor 24 VDC 18A", 1, 2, "ud", "B-02-02", 41.2),
        ("ACE-H46", "Aceite hidraulico ISO VG46", 75, 40, "l", "LIQ-01", 4.35),
        ("GRAS-EP2", "Grasa multiproposito EP2", 12, 6, "kg", "LIQ-02", 8.8),
        ("CORR-A42", "Correa trapezoidal A42", 3, 3, "ud", "A-03-04", 14.1),
        ("FUS-10A", "Fusible cilindrico 10A", 20, 10, "ud", "B-03-01", 1.45),
        ("RAC-12", "Racor neumatico recto 12 mm", 6, 8, "ud", "C-01-02", 6.25),
        ("VAL-532", "Electrovalvula 5/3 24VDC", 1, 2, "ud", "C-02-01", 89.0),
    ]
    for code, name, stock, minimum, unit, location, cost in definitions:
        item = db.scalar(
            select(InventoryItem).where(
                InventoryItem.company_id == company.id, InventoryItem.code == code
            )
        )
        if item:
            continue
        item = InventoryItem(
            company_id=company.id,
            code=code,
            name=name,
            description="Repuesto homologado para los equipos de la planta de Ourense.",
            stock=stock,
            minimum_stock=minimum,
            unit=unit,
            location=location,
            cost=cost,
            active=True,
        )
        db.add(item)
        db.flush()
        db.add(
            InventoryMovement(
                company_id=company.id,
                item_id=item.id,
                user_id=users["manager"].id,
                movement_type=InventoryMovementType.RECEIPT,
                quantity=stock,
                resulting_stock=stock,
                reason="Inventario inicial validado",
            )
        )


def get_or_create_documents(db, company, assets, users) -> None:
    storage = LocalDocumentStorage()
    definitions = [
        (
            "Procedimiento de bloqueo y consignacion",
            0,
            DocumentType.SAFETY,
            "procedimiento_loto_cnc.txt",
            "PROCEDIMIENTO LOTO\n\n1. Detener el equipo.\n"
            "2. Aislar todas las energias.\n"
            "3. Verificar ausencia de energia.\n"
            "4. Registrar y liberar la intervencion.\n",
        ),
        (
            "Plan de lubricacion del compresor",
            5,
            DocumentType.PROCEDURE,
            "plan_lubricacion_compresor.txt",
            "PLAN DE LUBRICACION\n\nRevisar nivel, fugas, presion diferencial y "
            "estado del aceite. Registrar valores y desviaciones en la orden.\n",
        ),
        (
            "Referencia de diagnostico del robot",
            3,
            DocumentType.MANUAL,
            "diagnostico_robot_soldadura.txt",
            "GUIA DE DIAGNOSTICO\n\nComprobar alarmas activas, estado del bus de campo, "
            "seguridades y referencias de ejes antes del rearme.\n",
        ),
    ]
    for name, asset_index, document_type, filename, content in definitions:
        exists = db.scalar(
            select(TechnicalDocument).where(
                TechnicalDocument.company_id == company.id,
                TechnicalDocument.asset_id == assets[asset_index].id,
                TechnicalDocument.name == name,
            )
        )
        if exists:
            continue
        encoded = content.encode("utf-8")
        key = storage.store(company.id, filename, encoded)
        db.add(
            TechnicalDocument(
                company_id=company.id,
                asset_id=assets[asset_index].id,
                uploaded_by=users["manager"].id,
                name=name,
                type=document_type,
                storage_key=key,
                original_name=filename,
                mime_type="text/plain; charset=utf-8",
                file_size=len(encoded),
                description="Documento tecnico controlado para uso del equipo de mantenimiento.",
            )
        )


def seed() -> None:
    with SessionLocal() as db:
        company = get_or_create_company(db)
        plant = get_or_create_plant(db, company)
        users = get_or_create_users(db, company)
        assets = get_or_create_assets(db, company, plant)
        incidents = get_or_create_incidents(db, company, plant, assets, users)
        get_or_create_work_orders(db, company, plant, assets, users, incidents)
        get_or_create_preventive_plans(db, company, assets, users)
        get_or_create_inventory(db, company, users)
        get_or_create_documents(db, company, assets, users)
        db.commit()
        indexed = index_documents(
            db,
            company.id,
            LocalDocumentStorage(),
            force=False,
            provider=None,
        )
        print(f"Demo ForgeOps preparada sin duplicados. Documentos indexados: {indexed.indexed}.")


if __name__ == "__main__":
    seed()
