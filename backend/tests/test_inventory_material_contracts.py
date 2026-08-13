import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.core.enums import InventoryMovementType, UserRole, WorkOrderEventType
from app.inventory.models import InventoryItem, InventoryMovement
from app.inventory.schemas import InventoryItemRead, StockMovementCreate
from app.users.models import User
from app.work_orders.models import WorkOrder
from app.work_orders.schemas import (
    WorkOrderDetailRead,
    WorkOrderMaterialConsume,
    WorkOrderMaterialReturn,
)


def _names(items) -> set[str]:
    return {item.name for item in items}


def test_inventory_material_models_define_traceability_and_concurrency():
    assert inspect(InventoryItem).version_id_col is InventoryItem.__table__.c.version
    assert "ck_inventory_item_version" in _names(InventoryItem.__table__.constraints)
    assert {
        "ix_inventory_movements_work_order_created",
        "ix_inventory_movements_reversal",
    }.issubset(_names(InventoryMovement.__table__.indexes))
    assert {
        "ck_inventory_movement_quantity",
        "ck_inventory_movement_unit_cost",
        "ck_inventory_movement_return_source",
    }.issubset(_names(InventoryMovement.__table__.constraints))

    foreign_keys = {
        foreign_key.parent.name: (foreign_key.target_fullname, foreign_key.ondelete)
        for foreign_key in InventoryMovement.__table__.foreign_keys
    }
    assert foreign_keys["work_order_id"] == ("work_orders.id", "SET NULL")
    assert foreign_keys["reversal_of_id"] == ("inventory_movements.id", "SET NULL")

    relationship = inspect(WorkOrder).relationships["inventory_movements"]
    assert relationship.order_by[0].key == "created_at"
    assert "delete" not in relationship.cascade
    assert "delete-orphan" not in relationship.cascade
    assert InventoryMovement.__table__.c.id in inspect(InventoryMovement).relationships[
        "reversal_of"
    ].remote_side


def test_inventory_material_contracts_validate_positive_quantities_and_versions():
    item_id = uuid.uuid4()
    consume = WorkOrderMaterialConsume(
        item_id=item_id,
        quantity=Decimal("1.250"),
        expected_version=2,
        reason="Cambio preventivo",
    )
    returned = WorkOrderMaterialReturn(
        quantity=Decimal("0.250"),
        expected_version=3,
        reason="Material no utilizado",
    )
    assert consume.item_id == item_id
    assert returned.quantity == Decimal("0.250")
    assert "item_id" not in WorkOrderMaterialReturn.model_fields

    invalid_payloads = (
        {"item_id": item_id, "quantity": 0, "expected_version": 1},
        {"item_id": item_id, "quantity": 1, "expected_version": 0},
    )
    for payload in invalid_payloads:
        with pytest.raises(ValidationError):
            WorkOrderMaterialConsume(**payload)
    with pytest.raises(ValidationError):
        StockMovementCreate(
            movement_type=InventoryMovementType.RECEIPT,
            quantity=1,
            reason="Entrada valida",
            expected_version=0,
        )


def test_inventory_item_serialization_exposes_version():
    now = datetime.now(UTC)
    item = InventoryItem(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        code="ROD-6205",
        name="Rodamiento 6205",
        stock=Decimal("4.000"),
        minimum_stock=Decimal("2.000"),
        unit="ud",
        active=True,
        version=3,
        created_at=now,
        updated_at=now,
    )
    assert InventoryItemRead.model_validate(item).version == 3


def test_work_order_material_cost_is_signed_and_exposed_by_detail_contract():
    company_id = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        company_id=company_id,
        full_name="Tecnico",
        email="tecnico@example.test",
        password_hash="not-used",
        role=UserRole.TECHNICIAN,
        active=True,
    )
    order = WorkOrder()
    order.inventory_movements = [
        InventoryMovement(
            company_id=company_id,
            item_id=uuid.uuid4(),
            user_id=user.id,
            movement_type=InventoryMovementType.CONSUMPTION,
            quantity=Decimal("-2.000"),
            resulting_stock=Decimal("6.000"),
            unit_cost=Decimal("18.50"),
            total_cost=Decimal("37.00"),
            reason="Consumo",
            user=user,
        ),
        InventoryMovement(
            company_id=company_id,
            item_id=uuid.uuid4(),
            user_id=user.id,
            movement_type=InventoryMovementType.RETURN,
            quantity=Decimal("0.500"),
            resulting_stock=Decimal("6.500"),
            unit_cost=Decimal("18.50"),
            total_cost=Decimal("-9.25"),
            reason="Devolucion",
            user=user,
        ),
    ]
    assert order.material_cost == Decimal("27.75")
    assert {"inventory_movements", "material_cost"}.issubset(
        WorkOrderDetailRead.model_fields
    )
    assert InventoryMovementType.RETURN.value == "RETURN"
    assert WorkOrderEventType.MATERIAL_CONSUMED.value == "MATERIAL_CONSUMED"
    assert WorkOrderEventType.MATERIAL_RETURNED.value == "MATERIAL_RETURNED"
