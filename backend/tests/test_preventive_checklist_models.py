import subprocess
import sys
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.maintenance.models import ChecklistTemplate, ChecklistTemplateItem, PreventivePlan
from app.maintenance.schemas import ChecklistTemplateCreate, ChecklistTemplateRead
from app.work_orders.models import WorkOrder, WorkOrderChecklistItem
from app.work_orders.schemas import WorkOrderChecklistItemRead, WorkOrderChecklistItemUpdate


def _names(items) -> set[str]:
    return {item.name for item in items}


def test_checklist_model_constraints_and_ordered_relationships():
    assert "uq_checklist_template_company_name" in _names(
        ChecklistTemplate.__table__.constraints
    )
    assert "ix_checklist_template_company_active" in _names(
        ChecklistTemplate.__table__.indexes
    )
    assert {
        "uq_checklist_template_item_template_position",
        "ck_checklist_template_item_position",
    }.issubset(_names(ChecklistTemplateItem.__table__.constraints))
    assert {
        "uq_work_order_checklist_item_position",
        "ck_work_order_checklist_item_position",
    }.issubset(_names(WorkOrderChecklistItem.__table__.constraints))
    assert {
        "ix_work_order_checklist_item_completed",
        "ix_work_order_checklist_item_order_position",
    }.issubset(_names(WorkOrderChecklistItem.__table__.indexes))
    assert inspect(ChecklistTemplate).relationships["items"].order_by[0].key == "position"
    assert inspect(WorkOrder).relationships.checklist_items.order_by[0].key == "position"


def test_checklist_models_expose_plan_link_and_optimistic_version():
    assert "checklist_template_id" in PreventivePlan.__table__.columns
    assert (
        inspect(WorkOrderChecklistItem).version_id_col
        is WorkOrderChecklistItem.__table__.c.version
    )
    required = WorkOrderChecklistItem.__table__.c.required
    assert required.nullable is False


def test_checklist_contracts_validate_and_serialize_without_internal_state():
    payload = ChecklistTemplateCreate(
        name="Monthly compressor inspection",
        items=[
            {
                "title": "Check oil level",
                "instructions": "Record any leakage before topping up.",
                "position": 1,
                "required": True,
            }
        ],
    )
    assert payload.items[0].position == 1
    with pytest.raises(ValidationError):
        ChecklistTemplateCreate(name="Empty template", items=[])

    company_id = uuid.uuid4()
    template_id = uuid.uuid4()
    item_id = uuid.uuid4()
    now = datetime.now(UTC)
    template = ChecklistTemplate(
        id=template_id,
        company_id=company_id,
        name=payload.name,
        active=True,
        created_at=now,
        updated_at=now,
    )
    template.items = [
        ChecklistTemplateItem(
            id=item_id,
            company_id=company_id,
            template_id=template_id,
            title=payload.items[0].title,
            instructions=payload.items[0].instructions,
            position=1,
            required=True,
            created_at=now,
            updated_at=now,
        )
    ]
    serialized = ChecklistTemplateRead.model_validate(template).model_dump()
    assert serialized["items"][0]["title"] == "Check oil level"

    snapshot = WorkOrderChecklistItem(
        id=uuid.uuid4(),
        company_id=company_id,
        work_order_id=uuid.uuid4(),
        source_template_item_id=item_id,
        title="Check oil level",
        instructions="Record any leakage before topping up.",
        position=1,
        required=True,
        version=1,
        created_at=now,
        updated_at=now,
    )
    snapshot.completer = None
    snapshot_data = WorkOrderChecklistItemRead.model_validate(snapshot).model_dump()
    assert snapshot_data["required"] is True
    assert snapshot_data["completer"] is None
    assert WorkOrderChecklistItemUpdate(completed=True, version=1).completed is True
    with pytest.raises(ValidationError):
        WorkOrderChecklistItemUpdate(completed=True, version=0)


def test_preventive_scheduler_initializes_all_orm_mappers():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import scripts.generate_due_preventive; "
            "from sqlalchemy.orm import configure_mappers; configure_mappers()",
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr
